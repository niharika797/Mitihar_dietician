import logging
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
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


# ─── Daily cron: flag expiring patients ───────────────────────────────────────
async def _flag_expiring_patients() -> None:
    """Mark patients whose token_1_expiry is within 4 days as expiring_soon=True."""
    from sqlalchemy import update
    from .models.db_models import Patient
    now = datetime.now(timezone.utc)
    warning_cutoff = now + timedelta(days=4)
    async with AsyncSessionLocal() as session:
        try:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_flag_expiring_patients,      CronTrigger(hour=1, minute=0))
    scheduler.add_job(_deactivate_expired_patients, CronTrigger(hour=1, minute=5))
    scheduler.start()
    _log.info("APScheduler started — daily token crons registered")
    yield
    scheduler.shutdown(wait=False)
    _log.info("APScheduler shut down")

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
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)        # outermost — must be last

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

@app.get("/")
async def root():
    return {"message": "Welcome to Diet Plan API"}