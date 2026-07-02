import functools
import inspect
import ipaddress
import logging
import threading
from typing import List

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings

_log = logging.getLogger(__name__)

# Fail-open counter — incremented every time the rate limiter bypasses a request
# due to Redis/storage unavailability. Visible in GCP Cloud Logging as structured
# WARNING lines (severity >= WARNING is indexed and alertable via log-based metrics).
_fail_open_lock = threading.Lock()
_fail_open_count = 0


def _increment_fail_open(exc: Exception) -> None:
    global _fail_open_count
    with _fail_open_lock:
        _fail_open_count += 1
        count = _fail_open_count
    _log.warning(
        "RATE_LIMITER_FAIL_OPEN count=%d error=%s: %s",
        count,
        type(exc).__name__,
        exc,
    )


def _is_storage_error(exc: Exception) -> bool:
    """True only for Redis/storage connectivity failures — not for RateLimitExceeded."""
    if isinstance(exc, RateLimitExceeded):
        return False
    try:
        import redis.exceptions
        if isinstance(exc, redis.exceptions.RedisError):
            return True
    except ImportError:
        pass
    try:
        from limits.errors import StorageError
        if isinstance(exc, StorageError):
            return True
    except ImportError:
        pass
    return False


class FailOpenLimiter(Limiter):
    """
    slowapi.Limiter subclass: fails open on Redis/storage errors instead of 500.

    When Redis is reachable: rate limiting enforces normally.
    When Redis goes down mid-flight: logs the error, allows the request through.
    RateLimitExceeded (Redis is up, limit hit) is always re-raised — never swallowed.
    """

    def limit(self, *args, **kwargs):
        original_decorator = super().limit(*args, **kwargs)

        def safe_decorator(func):
            decorated = original_decorator(func)

            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*fargs, **fkwargs):
                    try:
                        return await decorated(*fargs, **fkwargs)
                    except RateLimitExceeded:
                        raise
                    except Exception as exc:
                        if _is_storage_error(exc):
                            _increment_fail_open(exc)
                            return await func(*fargs, **fkwargs)
                        raise
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*fargs, **fkwargs):
                    try:
                        return decorated(*fargs, **fkwargs)
                    except RateLimitExceeded:
                        raise
                    except Exception as exc:
                        if _is_storage_error(exc):
                            _increment_fail_open(exc)
                            return func(*fargs, **fkwargs)
                        raise
                return sync_wrapper

        return safe_decorator

# Parse trusted proxy CIDRs once at startup.
_trusted_networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
if settings.TRUSTED_PROXY_CIDR:
    for cidr in settings.TRUSTED_PROXY_CIDR.split(","):
        cidr = cidr.strip()
        if cidr:
            try:
                _trusted_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                _log.warning("Invalid TRUSTED_PROXY_CIDR entry ignored: %r", cidr)
    _log.info("Rate limiter trusts X-Forwarded-For from %d CIDR(s): %s", len(_trusted_networks), settings.TRUSTED_PROXY_CIDR)


def gcp_aware_key(request: Request) -> str:
    """
    Rate-limit key that is safe against X-Forwarded-For spoofing.

    Only reads the leftmost XFF IP when the immediate TCP peer (request.client.host)
    falls inside TRUSTED_PROXY_CIDR. In every other case the raw socket IP is used,
    which prevents an attacker from trivially rotating rate-limit buckets by sending
    arbitrary X-Forwarded-For headers from an untrusted network.

    Dev: set TRUSTED_PROXY_CIDR=127.0.0.1 so the local loopback is trusted.
    Production (GCP Cloud Run): set TRUSTED_PROXY_CIDR to the Cloud Load Balancer
    IP range supplied by GCP (typically 130.211.0.0/22,35.191.0.0/16).
    """
    client_host = request.client.host if request.client else "unknown"

    if _trusted_networks:
        try:
            addr = ipaddress.ip_address(client_host)
            if any(addr in net for net in _trusted_networks):
                xff = request.headers.get("X-Forwarded-For", "")
                if xff:
                    # XFF is "client, proxy1, proxy2" — leftmost is the real client.
                    leftmost = xff.split(",")[0].strip()
                    if leftmost:
                        return leftmost
        except ValueError:
            pass  # unparseable client IP → fall through to raw socket

    return client_host


if settings.REDIS_URL:
    # Production / multi-worker: shared Redis counter so all uvicorn workers
    # enforce a single rate-limit bucket per IP.
    # FailOpenLimiter: if Redis goes down at runtime, requests are allowed through
    # (logged as errors) rather than returning 500/502 to clients.
    limiter = FailOpenLimiter(key_func=gcp_aware_key, storage_uri=settings.REDIS_URL)
    _log.info("Rate limiter using Redis storage (fail-open on disconnect): %s", settings.REDIS_URL)
else:
    # Development fallback: in-memory counter. ONLY safe for single-worker dev servers.
    # Set REDIS_URL in .env before running with --workers > 1 in production.
    _log.warning(
        "Rate limiter is using in-memory storage. "
        "This is UNSAFE for multi-worker deployments. "
        "Set REDIS_URL in .env to enable shared Redis storage."
    )
    limiter = FailOpenLimiter(key_func=gcp_aware_key)
