import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .core.config import settings
from .core.database import AsyncSessionLocal
from .core.middleware import SubscriptionCheckMiddleware, DoctorIsolationMiddleware, AdminIPWhitelistMiddleware, SecurityHeadersMiddleware
from .routers import auth, users, diet_plans
from .routers.calculations import router as calculations_router
from .routers.progress import router as progress_router
from .routers.meal_plan import router as meal_plan_router
from .routers.patients import router as patients_router
from .routers.doctor import router as doctor_router
from .routers.admin import router as admin_router

_log = logging.getLogger(__name__)


# ─── X-Request-ID middleware ──────────────────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Daily cron: flag expiring patients ───────────────────────────────────────
async def _flag_expiring_patients() -> None:
    """Mark patients whose token_1_expiry is within 4 days as expiring_soon=True."""
    from sqlalchemy import update, select
    from .models.db_models import Patient
    from .services.notification_service import notify_sub_expiring
    now = datetime.now(timezone.utc)
    warning_cutoff = now + timedelta(days=4)
    async with AsyncSessionLocal() as session:
        try:
            # Fetch patients about to be newly flagged so we can notify them
            newly_expiring_result = await session.execute(
                select(Patient).where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry != None,
                    Patient.token_1_expiry <= warning_cutoff,
                    Patient.token_1_expiry > now,
                    Patient.expiring_soon == False,
                )
            )
            newly_expiring = newly_expiring_result.scalars().all()

            await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry != None,
                    Patient.token_1_expiry <= warning_cutoff,
                    Patient.token_1_expiry > now,
                    Patient.expiring_soon == False,
                )
                .values(expiring_soon=True)
            )
            await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry > warning_cutoff,
                    Patient.expiring_soon == True,
                )
                .values(expiring_soon=False)
            )
            await session.commit()
            _log.info("[cron] expiring_soon flags updated")

            # Fire FCM notifications — fire-and-forget, never block cron
            for pat in newly_expiring:
                try:
                    days_left = max(0, (pat.token_1_expiry - now).days)
                    notify_sub_expiring(pat, days_left)
                except Exception:
                    pass
        except Exception as exc:
            await session.rollback()
            _log.error(f"[cron] flag_expiring_patients failed: {exc}", exc_info=True)


# ─── Daily cron: deactivate expired patients ──────────────────────────────────
async def _deactivate_expired_patients() -> None:
    """Set token_1_active=False for patients whose token_1_expiry has passed."""
    from sqlalchemy import update
    from .models.db_models import Patient
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry != None,
                    Patient.token_1_expiry <= now,
                )
                .values(token_1_active=False, expiring_soon=False)
            )
            await session.commit()
            _log.info("[cron] expired patients deactivated")
        except Exception as exc:
            await session.rollback()
            _log.error(f"[cron] deactivate_expired_patients failed: {exc}", exc_info=True)


# ─── Weekly cron (Sunday 01:00 UTC): snapshot completed week summaries ────────
async def complete_expired_plans() -> None:
    """
    Run once per week (Sunday 01:00 UTC) for the week that just ended (Mon–Sun).
    Calls compute_weekly_summary() for every patient who had a v2 plan last week,
    so the summary is cached before R-7B reads it to seed next-week generation.
    """
    from datetime import date, timedelta
    from sqlalchemy import select
    from .models.db_models import Recommendation
    from .services.weekly_summary_service import compute_weekly_summary

    today = datetime.now(timezone.utc).date()
    last_monday = today - timedelta(days=today.weekday() + 7)

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Recommendation.patient_id)
                .where(
                    Recommendation.generation_version == 2,
                    Recommendation.week_start_date == last_monday,
                )
                .distinct()
            )
            patient_ids = [row[0] for row in result.all()]
            _log.info("[cron] complete_expired_plans: %d patients for week %s", len(patient_ids), last_monday)
            for pid in patient_ids:
                try:
                    await compute_weekly_summary(session, pid, last_monday)
                except Exception as exc:
                    _log.error("[cron] complete_expired_plans: patient %s failed: %s", pid, exc, exc_info=True)
        except Exception as exc:
            _log.error("[cron] complete_expired_plans: outer failure: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── T1-8: COOKIE_SECURE startup guard ────────────────────────────────────────
    import socket
    if not settings.COOKIE_SECURE:
        hostname = socket.gethostname()
        is_local = hostname in ("localhost", "127.0.0.1") or hostname.startswith("DESKTOP-") \
            or hostname.endswith(".local")
        if not is_local:
            _log.critical(
                "SECURITY WARNING: COOKIE_SECURE=False on a non-localhost host (%s). "
                "Refresh tokens will be sent over plain HTTP and can be intercepted. "
                "Set COOKIE_SECURE=True in .env before deploying to production.",
                hostname,
            )

    # ── Firebase Admin SDK (push notifications) ───────────────────────
    from .services.notification_service import init_firebase
    init_firebase()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_flag_expiring_patients,      CronTrigger(hour=1, minute=0))
    scheduler.add_job(_deactivate_expired_patients, CronTrigger(hour=1, minute=5))
    scheduler.add_job(
        complete_expired_plans,
        CronTrigger(day_of_week="sun", hour=1, minute=0),
        id="complete_weekly_plans",
        replace_existing=True,
    )
    scheduler.start()
    _log.info("APScheduler started — daily token crons + weekly summary cron registered")
    yield
    scheduler.shutdown(wait=False)
    _log.info("APScheduler shut down")

# NOTE: slowapi uses in-memory storage by default.
# Set REDIS_URL in .env before multi-worker production deployment.
# TODO: Switch to RedisStorage before multi-worker/production deployment
limiter = Limiter(key_func=get_remote_address)
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