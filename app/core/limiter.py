import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

_log = logging.getLogger(__name__)

if settings.REDIS_URL:
    # Production / multi-worker: shared Redis counter so all uvicorn workers
    # enforce a single rate-limit bucket per IP.
    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
    _log.info("Rate limiter using Redis storage: %s", settings.REDIS_URL)
else:
    # Development fallback: in-memory counter. ONLY safe for single-worker dev servers.
    # Set REDIS_URL in .env before running with --workers > 1 in production.
    _log.warning(
        "Rate limiter is using in-memory storage. "
        "This is UNSAFE for multi-worker deployments. "
        "Set REDIS_URL in .env to enable shared Redis storage."
    )
    limiter = Limiter(key_func=get_remote_address)
