"""
Middleware layers for Mityahar.

Both layers are ZERO-DB — they read only from JWT claims (no DB query per request).
subscription_status and doctor_id are embedded in the JWT at login time.

  1. SubscriptionCheckMiddleware — blocks inactive patients on protected routes
  2. DoctorIsolationMiddleware   — restricts /doctor routes, injects request.state.doctor_id
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt

from .config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return auth[7:].strip() or None


def _safe_decode(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_iat": True, "verify_nbf": True},
        )
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Subscription-check middleware (zero DB queries)
# ---------------------------------------------------------------------------

_SUBSCRIPTION_PREFIXES = (
    f"{settings.API_V1_STR}/meal-plan",
    f"{settings.API_V1_STR}/progress",
    f"{settings.API_V1_STR}/diet-plans",
)

_AUTH_PREFIXES = (
    f"{settings.API_V1_STR}/auth",
    f"{settings.API_V1_STR}/doctors/auth",
)


class SubscriptionCheckMiddleware(BaseHTTPMiddleware):
    """
    Reads 'sub_status' claim from JWT — no DB query.
    Blocks patients with sub_status='inactive' on protected routes.
    Auth routes and non-patient roles are never blocked.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(p) for p in _AUTH_PREFIXES):
            return await call_next(request)

        if not any(path.startswith(p) for p in _SUBSCRIPTION_PREFIXES):
            return await call_next(request)

        token = _extract_token(request)
        if token is None:
            return await call_next(request)  # let route dep produce 401

        payload = _safe_decode(token)
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        if payload.get("role") != "patient":
            return await call_next(request)

        # Read subscription status directly from JWT claim — zero DB hit
        sub_status = payload.get("sub_status", "inactive")
        if sub_status == "inactive":
            return JSONResponse(
                status_code=402,
                content={
                    "detail": "Subscription expired",
                    "code": "SUBSCRIPTION_EXPIRED",
                },
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Doctor-isolation middleware (zero DB queries)
# ---------------------------------------------------------------------------

class DoctorIsolationMiddleware(BaseHTTPMiddleware):
    """
    Reads 'doctor_id' claim from JWT — no DB query.
    Restricts /doctor/* to role=doctor only.
    Injects request.state.doctor_id before handler runs.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        doctor_prefix = f"{settings.API_V1_STR}/doctor"

        if path.startswith(f"{settings.API_V1_STR}/doctors/auth"):
            return await call_next(request)

        if not path.startswith(doctor_prefix):
            return await call_next(request)

        token = _extract_token(request)
        if token is None:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        payload = _safe_decode(token)
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        if payload.get("role") != "doctor":
            return JSONResponse(status_code=403, content={"detail": "Doctor role required"})

        # Read doctor_id directly from JWT claim — zero DB hit
        doctor_id = payload.get("doctor_id")
        if not doctor_id:
            return JSONResponse(status_code=401, content={"detail": "Invalid token: missing doctor_id"})

        # Inject into request.state BEFORE handler runs
        request.state.doctor_id = doctor_id

        return await call_next(request)


# ---------------------------------------------------------------------------
# Admin IP-whitelist middleware (DB query only on /admin routes)
# ---------------------------------------------------------------------------

from sqlalchemy import select as sa_select
from .database import AsyncSessionLocal


class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Checks the requesting IP against the admin's allowed_ips list (stored in DB).
    Only fires on /admin routes.
    If no admin JWT present, skips check (route dep will reject unauthenticated).
    If allowed_ips is empty list [], IP whitelisting is DISABLED (any IP allowed).
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        admin_prefix = f"{settings.API_V1_STR}/admin"

        # Only intercept admin routes
        if not path.startswith(admin_prefix):
            return await call_next(request)

        # Skip the login route (admin needs to authenticate first)
        if path.startswith(f"{admin_prefix}/login") or path.startswith(f"{settings.API_V1_STR}/auth"):
            return await call_next(request)

        token = _extract_token(request)
        if token is None:
            return await call_next(request)  # no token → route dep will 401

        payload = _safe_decode(token)
        if payload is None:
            return await call_next(request)  # bad token → route dep will 401

        if payload.get("role") != "admin":
            return JSONResponse(
                status_code=403,
                content={"detail": "Admin access required"},
            )

        admin_id = payload.get("admin_id")
        if not admin_id:
            return await call_next(request)

        # DB lookup — only happens for authenticated admin requests
        try:
            from ..models.db_models import Admin as AdminModel

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    sa_select(AdminModel.allowed_ips).where(AdminModel.id == admin_id)
                )
                allowed_ips = result.scalar_one_or_none()

            # If allowed_ips is empty or None, whitelisting is disabled
            if not allowed_ips:
                return await call_next(request)

            client_ip = request.client.host if request.client else "unknown"
            if client_ip not in allowed_ips:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "IP not whitelisted",
                        "code": "IP_NOT_ALLOWED",
                    },
                )
        except Exception:
            # If DB query fails, allow through — don't lock admins out
            import logging
            logging.getLogger(__name__).warning(
                "IP whitelist check failed for admin %s — allowing through", admin_id
            )

        return await call_next(request)
