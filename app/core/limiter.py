import functools
import hashlib
import inspect
import ipaddress
import logging
import math
import re
import threading
import time
from typing import List

from fastapi import Request
from fastapi.responses import JSONResponse
from limits import parse as _parse_limit
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from .config import settings

_log = logging.getLogger(__name__)


def redact_url(url: str) -> str:
    """redis://:secret@host:6379/0 -> redis://***@host:6379/0 (log lines must never carry the AUTH password)."""
    return re.sub(r"://[^@/]*@", "://***@", url or "")


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
    _log.info("Rate limiter using Redis storage (fail-open on disconnect): %s", redact_url(settings.REDIS_URL))
else:
    # Development fallback: in-memory counter. ONLY safe for single-worker dev servers.
    # Set REDIS_URL in .env before running with --workers > 1 in production.
    _log.warning(
        "Rate limiter is using in-memory storage. "
        "This is UNSAFE for multi-worker deployments. "
        "Set REDIS_URL in .env to enable shared Redis storage."
    )
    limiter = FailOpenLimiter(key_func=gcp_aware_key)


# ── Friendly 429 answers + per-identifier (e.g. per-email) limits ─────────────────────

def friendly_wait(seconds: int) -> str:
    """'about 3 minutes' / 'about 1 hour' -- rounded up so the patient never retries too early."""
    minutes = max(1, math.ceil(seconds / 60))
    if minutes < 60:
        return f"about {minutes} minute{'s' if minutes != 1 else ''}"
    hours = math.ceil(minutes / 60)
    return f"about {hours} hour{'s' if hours != 1 else ''}"


def rate_limit_message(seconds: int) -> str:
    return (
        "Too many attempts. For your security, we have paused this action for a short while. "
        f"Please take a break and try again in {friendly_wait(seconds)}."
    )


def rate_limited_response(seconds: int) -> JSONResponse:
    seconds = max(1, int(seconds))
    return JSONResponse(
        status_code=429,
        content={"detail": rate_limit_message(seconds), "retry_after_seconds": seconds},
        headers={"Retry-After": str(seconds)},
    )


class RateLimitedError(Exception):
    """Raised by hit_key_limit(); main.py answers it with the same friendly 429 as a slowapi limit."""

    def __init__(self, retry_after: int):
        self.retry_after = max(1, int(retry_after))


def hit_key_limit(scope: str, identifier: str, limit: str) -> None:
    """
    Count one attempt against `limit` (e.g. "10/15 minutes") for this identifier (an email).
    Same storage as the per-IP limits (Redis when REDIS_URL is set, memory otherwise), so the
    count is shared across servers when Redis is on. The email is hashed before it is used as a
    key, so no address is stored in Redis. Fails open on storage errors, like the per-IP limits.
    Raises RateLimitedError when the limit is exceeded.
    """
    item = _parse_limit(limit)
    key = hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()[:24]
    try:
        if limiter.limiter.hit(item, scope, key):
            return
        reset_at = limiter.limiter.get_window_stats(item, scope, key)[0]
    except Exception as exc:
        if _is_storage_error(exc):
            _increment_fail_open(exc)
            return
        raise
    raise RateLimitedError(math.ceil(reset_at - time.time()))


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Replaces slowapi's bare '{"error": "Rate limit exceeded: ..."}' with the friendly answer."""
    try:
        current = request.state.view_rate_limit
        reset_at = request.app.state.limiter.limiter.get_window_stats(current[0], *current[1])[0]
        seconds = math.ceil(reset_at - time.time())
    except Exception:
        seconds = exc.limit.limit.get_expiry()  # fall back to the whole window
    return rate_limited_response(seconds)


async def rate_limited_error_handler(request: Request, exc: RateLimitedError) -> JSONResponse:
    return rate_limited_response(exc.retry_after)
