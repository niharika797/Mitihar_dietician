import asyncio
import hmac
import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import update, select

from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..models.db_models import Patient, Recommendation
from ..services.weekly_summary_service import compute_weekly_summary

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/cron", tags=["internal"])


def _check_secret(x_cron_secret: str | None) -> None:
    """Reject 401 if secret is unconfigured or wrong. Constant-time compare prevents timing attacks."""
    if not settings.CRON_SECRET or not x_cron_secret or \
            not hmac.compare_digest(x_cron_secret, settings.CRON_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/flag-expiring-patients")
async def flag_expiring_patients(x_cron_secret: str | None = Header(default=None)):
    """
    Mark patients whose token_1_expiry is within 4 days as expiring_soon=True.
    Atomic UPDATE...RETURNING closes the SELECT-before-UPDATE FCM race: only the caller
    that wins the row lock gets patient IDs back; a concurrent caller sees 0 rows and
    sends 0 FCM pushes. Idempotent: WHERE expiring_soon=False eliminates re-runs.
    """
    _check_secret(x_cron_secret)
    from ..services.notification_service import notify_sub_expiring
    now = datetime.now(timezone.utc)
    warning_cutoff = now + timedelta(days=4)
    async with AsyncSessionLocal() as session:
        try:
            # Atomic: winner gets rows back; concurrent loser gets 0 → no duplicate FCM
            flagged_result = await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry != None,
                    Patient.token_1_expiry <= warning_cutoff,
                    Patient.token_1_expiry > now,
                    Patient.expiring_soon == False,
                )
                .values(expiring_soon=True)
                .returning(Patient.id, Patient.token_1_expiry)
            )
            newly_flagged = flagged_result.fetchall()  # [(id, expiry), ...]

            await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry > warning_cutoff,
                    Patient.expiring_soon == True,
                )
                .values(expiring_soon=False)
            )
            # TEST-ONLY: widen UPDATE→commit window so concurrent callers provably contend.
            # Set TEST_RACE_DELAY_SECONDS=0.1 in env; no-op (0) in production.
            _rd = float(os.environ.get("TEST_RACE_DELAY_SECONDS", "0"))
            if _rd > 0:
                await asyncio.sleep(_rd)
            await session.commit()
            _log.info("[cron] expiring_soon flags updated")

            if newly_flagged:
                patient_ids = [row[0] for row in newly_flagged]
                expiry_map = {row[0]: row[1] for row in newly_flagged}
                pat_result = await session.execute(
                    select(Patient).where(Patient.id.in_(patient_ids))
                )
                for pat in pat_result.scalars().all():
                    try:
                        days_left = max(0, (expiry_map[pat.id] - now).days)
                        notify_sub_expiring(pat, days_left)
                    except Exception:
                        pass

            return {"flagged": len(newly_flagged)}
        except Exception as exc:
            await session.rollback()
            _log.error("[cron] flag_expiring_patients failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Cron job failed")


@router.post("/deactivate-expired-patients")
async def deactivate_expired_patients(x_cron_secret: str | None = Header(default=None)):
    """
    Set token_1_active=False for patients whose token_1_expiry has passed.
    Idempotent at DB level: WHERE token_1_active=True means second call updates 0 rows.
    PostgreSQL row-level locking on UPDATE ensures concurrent calls don't double-write:
    the second transaction waits, then sees already-False rows and exits cleanly.
    """
    _check_secret(x_cron_secret)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                update(Patient)
                .where(
                    Patient.token_1_active == True,
                    Patient.token_1_expiry != None,
                    Patient.token_1_expiry <= now,
                )
                .values(token_1_active=False, expiring_soon=False)
                .returning(Patient.id)
            )
            deactivated = result.fetchall()
            await session.commit()
            count = len(deactivated)
            _log.info("[cron] expired patients deactivated: %d", count)
            return {"deactivated": count}
        except Exception as exc:
            await session.rollback()
            _log.error("[cron] deactivate_expired_patients failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Cron job failed")


@router.post("/complete-expired-plans")
async def complete_expired_plans_endpoint(x_cron_secret: str | None = Header(default=None)):
    """
    Snapshot weekly summaries for the week that just ended (Mon–Sun).
    compute_weekly_summary is idempotent: re-running for same patient/week overwrites.
    """
    _check_secret(x_cron_secret)
    from datetime import date
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

            ok, failed = 0, 0
            for pid in patient_ids:
                try:
                    await compute_weekly_summary(session, pid, last_monday)
                    ok += 1
                except Exception as exc:
                    _log.error("[cron] complete_expired_plans: patient %s failed: %s", pid, exc, exc_info=True)
                    failed += 1

            return {"week": str(last_monday), "processed": ok, "failed": failed}
        except Exception as exc:
            _log.error("[cron] complete_expired_plans: outer failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Cron job failed")
