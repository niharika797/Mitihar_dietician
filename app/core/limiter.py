import ipaddress
import logging
from typing import List

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

_log = logging.getLogger(__name__)

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
    limiter = Limiter(key_func=gcp_aware_key, storage_uri=settings.REDIS_URL)
    _log.info("Rate limiter using Redis storage: %s", settings.REDIS_URL)
else:
    # Development fallback: in-memory counter. ONLY safe for single-worker dev servers.
    # Set REDIS_URL in .env before running with --workers > 1 in production.
    _log.warning(
        "Rate limiter is using in-memory storage. "
        "This is UNSAFE for multi-worker deployments. "
        "Set REDIS_URL in .env to enable shared Redis storage."
    )
    limiter = Limiter(key_func=gcp_aware_key)
