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
    f"{settings.API_V1_STR}/patients",
)

_AUTH_PREFIXES = (
    f"{settings.API_V1_STR}/auth",
)

# Onboarding endpoints must always pass through regardless of subscription status —
# a newly registered patient has sub_status=inactive and needs these to complete setup.
_ONBOARDING_EXCLUSIONS = (
    f"{settings.API_V1_STR}/patients/onboarding",
    f"{settings.API_V1_STR}/patients/disclaimer",
    f"{settings.API_V1_STR}/patients/activate",
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

        if any(path.startswith(p) for p in _ONBOARDING_EXCLUSIONS):
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
# Security headers middleware (outermost — wraps all responses)
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds browser-enforced security headers to every response.
    Must be registered as the outermost middleware (added LAST via add_middleware)
    so it can annotate responses from all inner layers including CORS.

    Headers applied:
      X-Content-Type-Options   — prevents MIME sniffing attacks
      X-Frame-Options          — blocks clickjacking via <iframe>
      X-XSS-Protection         — legacy XSS filter for older browsers
      Referrer-Policy          — limits referrer leakage to same origin
      Content-Security-Policy  — whitelists allowed content sources
      Permissions-Policy       — disables browser APIs doctors don't need
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent browsers from guessing content types (e.g. treating a JSON
        # response as executable HTML)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Block the entire site from being embedded in an <iframe>.
        # Prevents clickjacking — attacker overlays a transparent iframe over
        # the login button to steal credentials.
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS filter — modern browsers use CSP, but this covers older ones
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Only send the origin (no path) in the Referer header when navigating
        # cross-origin. Prevents patient data from leaking into third-party logs.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy — whitelist every source the app legitimately
        # needs. Anything not listed is blocked by the browser before it runs.
        # Tighten 'unsafe-inline' on script-src once inline scripts are removed.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            f"connect-src 'self' {' '.join(settings.CORS_ORIGINS)}; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )

        # Disable browser APIs that the clinical dashboard has no business using.
        # Prevents a compromised dependency from silently accessing camera/mic/GPS.
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), accelerometer=()"
        )

        return response


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

        # Admin login lives on the auth router (/api/v1/auth/admin/login), already
        # excluded by the outer gate above which only fires on /api/v1/admin paths.
        # No additional skip needed here.

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
