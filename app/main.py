import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .core.limiter import limiter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .core.middleware import SubscriptionCheckMiddleware, DoctorIsolationMiddleware, AdminIPWhitelistMiddleware, SecurityHeadersMiddleware
from .routers import auth, users, diet_plans
from .routers.calculations import router as calculations_router
from .routers.progress import router as progress_router
from .routers.meal_plan import router as meal_plan_router
from .routers.patients import router as patients_router
from .routers.doctor import router as doctor_router
from .routers.admin import router as admin_router
from .routers.internal import router as internal_router

_log = logging.getLogger(__name__)


# ─── X-Request-ID middleware ─────────────────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── COOKIE_SECURE startup guard ───────────────────────────────────────────────
    if not settings.COOKIE_SECURE:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "COOKIE_SECURE=False in a production environment. "
                "Refresh tokens would be sent over plain HTTP and can be intercepted. "
                "Set COOKIE_SECURE=True before deploying."
            )
        else:
            _log.warning(
                "COOKIE_SECURE=False (ENVIRONMENT=%s). "
                "Acceptable for local dev — must be True in production.",
                settings.ENVIRONMENT,
            )

    # ── REQUIRE_EMAIL_VERIFICATION production warning ─────────────────────────
    if settings.ENVIRONMENT == "production" and not settings.REQUIRE_EMAIL_VERIFICATION:
        _log.critical(
            "REQUIRE_EMAIL_VERIFICATION=False in production. "
            "Patients can register without verifying their email. "
            "Intentional until Phase 7 (email sending). "
            "Set True before allowing unverified signups at scale."
        )

    # ── Firebase Admin SDK (push notifications) ───────────────────────
    from .services.notification_service import init_firebase
    init_firebase()

    # ── Redis rate-limiter startup check ──────────────────────────────
    if settings.REDIS_URL:
        import redis as redis_lib
        try:
            r = redis_lib.from_url(settings.REDIS_URL)
            r.ping()
            _log.info("Rate limiter: connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            _log.error("ERROR: REDIS_URL set but Redis unreachable: %s", e)
            _log.error("Rate limiter will fail at runtime. Check Docker container is running.")

    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Middleware ---
# Starlette processes add_middleware() in LIFO order:
# last registered = outermost (first to see requests, last to see responses).
#
# Stack (outermost → innermost):
#   SecurityHeadersMiddleware   — adds security headers to every response
#   CORSMiddleware              — handles preflight + CORS headers
#   SubscriptionCheckMiddleware — blocks inactive patients (zero-DB, JWT claims)
#   DoctorIsolationMiddleware   — restricts /doctor/*, injects doctor_id (zero-DB)
#   AdminIPWhitelistMiddleware  — IP check for /admin/* (single DB read)

app.add_middleware(AdminIPWhitelistMiddleware)       # innermost
app.add_middleware(DoctorIsolationMiddleware)
app.add_middleware(SubscriptionCheckMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cookie"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)              # outermost — runs first on request

# --- Routers ---
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(diet_plans.router, prefix=f"{settings.API_V1_STR}/diet-plans", tags=["diet-plans"])
app.include_router(calculations_router, prefix=f"{settings.API_V1_STR}/calculations", tags=["calculations"])
app.include_router(progress_router, prefix=f"{settings.API_V1_STR}/progress", tags=["progress"])
app.include_router(meal_plan_router, prefix=f"{settings.API_V1_STR}/meal-plan", tags=["meal-plan"])
app.include_router(patients_router, prefix=f"{settings.API_V1_STR}/patients", tags=["patients"])
app.include_router(doctor_router, prefix=f"{settings.API_V1_STR}/doctor", tags=["doctor"])
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(internal_router)  # no API_V1 prefix — not a public API

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    _log.exception(
        "Unhandled error: method=%s path=%s",
        request.method, request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {"message": "Welcome to Diet Plan API"}


@app.get("/health")
async def health():
    return {"status": "ok"}