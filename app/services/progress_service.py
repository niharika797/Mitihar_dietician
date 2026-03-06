"""
Progress tracking service — pure PostgreSQL via AsyncSession.

Uses meal_logs and progress_logs ORM models.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..models.db_models import MealLog, ProgressLog


# ---------------------------------------------------------------------------
# Meal logging
# ---------------------------------------------------------------------------

async def log_meal(
    session: AsyncSession,
    patient_id: int,
    data: dict,
) -> None:
    """Insert a row into meal_logs."""
    entry = MealLog(
        patient_id=patient_id,
        logged_date=date.today(),
        meal_type=data.get("meal_type", "Breakfast"),
        calories_consumed=data.get("calories", 0),
        protein_g=data.get("protein", 0),
        carbs_g=data.get("carbs", 0),
        fat_g=data.get("fat", 0),
        fiber_g=data.get("fiber", 0),
    )
    session.add(entry)
    await session.flush()


# ---------------------------------------------------------------------------
# Progress-log upserts  (one row per patient + date)
# ---------------------------------------------------------------------------

async def _get_or_create_progress(
    session: AsyncSession, patient_id: int, log_date: date
) -> ProgressLog:
    """Return existing ProgressLog for today, or create one."""
    result = await session.execute(
        select(ProgressLog).where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date == log_date,
        )
    )
    row = result.scalars().first()
    if row is None:
        row = ProgressLog(patient_id=patient_id, log_date=log_date)
        session.add(row)
        await session.flush()
    return row


async def log_water(session: AsyncSession, patient_id: int, glasses: int) -> None:
    row = await _get_or_create_progress(session, patient_id, date.today())
    row.water_glasses = (row.water_glasses or 0) + glasses
    await session.flush()


async def log_steps(session: AsyncSession, patient_id: int, steps: int) -> None:
    row = await _get_or_create_progress(session, patient_id, date.today())
    row.steps = (row.steps or 0) + steps
    await session.flush()


async def log_weight(session: AsyncSession, patient_id: int, weight: float) -> None:
    row = await _get_or_create_progress(session, patient_id, date.today())
    row.weight_kg = Decimal(str(weight))
    await session.flush()


async def log_activity(session: AsyncSession, patient_id: int, data: dict) -> None:
    row = await _get_or_create_progress(session, patient_id, date.today())
    row.steps = (row.steps or 0) + data.get("steps", 0)
    row.calories_burned = Decimal(str(data.get("calories_burned", 0)))
    await session.flush()


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

async def get_today_summary(
    session: AsyncSession, patient_id: int
) -> Dict[str, Any]:
    """Return calorie / water / steps totals for today."""
    today = date.today()

    # Sum calories from meal_logs
    cal_q = await session.execute(
        select(sa_func.coalesce(sa_func.sum(MealLog.calories_consumed), 0)).where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date == today,
        )
    )
    total_calories = float(cal_q.scalar())

    # Progress row
    prog_q = await session.execute(
        select(ProgressLog).where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date == today,
        )
    )
    prog = prog_q.scalars().first()

    return {
        "total_calories": total_calories,
        "water_glasses": prog.water_glasses if prog else 0,
        "steps": prog.steps if prog else 0,
    }


async def get_weekly_summary(
    session: AsyncSession, patient_id: int
) -> List[Dict[str, Any]]:
    """Return daily calorie totals for the last 7 days."""
    today = date.today()
    start = today - timedelta(days=6)

    result = await session.execute(
        select(
            MealLog.logged_date,
            sa_func.coalesce(sa_func.sum(MealLog.calories_consumed), 0).label("total_cal"),
        )
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
            MealLog.logged_date <= today,
        )
        .group_by(MealLog.logged_date)
        .order_by(MealLog.logged_date)
    )
    rows = result.all()
    return [{"date": str(r.logged_date), "calories": float(r.total_cal)} for r in rows]


async def calculate_and_store_calorie_adjustment(
    session: AsyncSession,
    patient_id: int,
    patient_tdee: float,
    today_calories: float,
) -> None:
    """
    Called when a patient's daily meal log total crosses 80% of TDEE.
    Stores the surplus/deficit vs TDEE on today's ProgressLog row so
    the next /meal-plan/adjust call can apply it to target_calories.

    Caller must pass today_calories — avoids a redundant SUM query
    since the caller already has this value.

    Adjustment formula:
      positive = deficit  (ate less than TDEE → eat more tomorrow)
      negative = surplus  (ate more than TDEE → eat less tomorrow)
      stored value = tdee - today_calories
    """
    adjustment = round(patient_tdee - today_calories, 2)
    row = await _get_or_create_progress(session, patient_id, date.today())
    row.calorie_adjustment = adjustment
    await session.flush()


async def get_meal_log_by_id(
    session: AsyncSession, patient_id: int, log_id: int
) -> Optional[MealLog]:
    """Return a MealLog only if it belongs to the given patient."""
    result = await session.execute(
        select(MealLog).where(
            MealLog.id == log_id,
            MealLog.patient_id == patient_id,
        )
    )
    return result.scalars().first()


async def update_meal_log(
    session: AsyncSession, patient_id: int, log_id: int, data: dict
) -> Optional[MealLog]:
    """
    Edit a meal log entry. Only allowed within 24 hours of creation.
    Returns None if not found. Raises ValueError if edit window has passed.
    """
    from datetime import datetime, timezone, timedelta
    log = await get_meal_log_by_id(session, patient_id, log_id)
    if log is None:
        return None

    now = datetime.now(timezone.utc)
    # created_at may be naive (no tzinfo) — normalise before comparing
    created = log.created_at
    if created.tzinfo is None:
        from datetime import timezone as _tz
        created = created.replace(tzinfo=_tz.utc)
    if now - created > timedelta(hours=24):
        raise ValueError("Edit window has passed (24 hours)")

    field_map = {
        "calories": "calories_consumed",
        "protein": "protein_g",
        "carbs": "carbs_g",
        "fat": "fat_g",
        "fiber": "fiber_g",
    }
    for k, v in data.items():
        if v is not None:
            orm_key = field_map.get(k, k)
            if hasattr(log, orm_key):
                setattr(log, orm_key, v)

    await session.flush()
    return log


async def delete_meal_log(
    session: AsyncSession, patient_id: int, log_id: int
) -> bool:
    """
    Delete a meal log entry. Only allowed within 24 hours of creation.
    Returns False if not found. Raises ValueError if delete window has passed.
    """
    from datetime import datetime, timezone, timedelta
    log = await get_meal_log_by_id(session, patient_id, log_id)
    if log is None:
        return False

    now = datetime.now(timezone.utc)
    created = log.created_at
    if created.tzinfo is None:
        from datetime import timezone as _tz
        created = created.replace(tzinfo=_tz.utc)
    if now - created > timedelta(hours=24):
        raise ValueError("Delete window has passed (24 hours)")

    await session.delete(log)
    await session.flush()
    return True


async def get_weight_history(
    session: AsyncSession, patient_id: int, days: int = 30
) -> list[dict]:
    """Return weight entries from ProgressLog for the last N days."""
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=days - 1)

    result = await session.execute(
        select(ProgressLog.log_date, ProgressLog.weight_kg)
        .where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date >= start,
            ProgressLog.weight_kg.isnot(None),
        )
        .order_by(ProgressLog.log_date.asc())
    )
    rows = result.all()
    return [
        {"date": str(r.log_date), "weight_kg": float(r.weight_kg)}
        for r in rows
    ]


async def get_weekly_report(
    session: AsyncSession, patient_id: int, patient_tdee: float
) -> dict:
    """
    Full weekly summary: daily calories/water/steps vs targets.
    Returns 7 day breakdown + totals + averages.
    """
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=6)

    # Daily calories from meal_logs
    cal_result = await session.execute(
        select(
            MealLog.logged_date,
            sa_func.coalesce(sa_func.sum(MealLog.calories_consumed), 0).label("calories"),
            sa_func.coalesce(sa_func.sum(MealLog.protein_g), 0).label("protein"),
            sa_func.coalesce(sa_func.sum(MealLog.carbs_g), 0).label("carbs"),
            sa_func.coalesce(sa_func.sum(MealLog.fat_g), 0).label("fat"),
        )
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
        )
        .group_by(MealLog.logged_date)
        .order_by(MealLog.logged_date)
    )
    cal_rows = {str(r.logged_date): r for r in cal_result.all()}

    # Daily activity from progress_logs
    prog_result = await session.execute(
        select(ProgressLog)
        .where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date >= start,
        )
    )
    prog_rows = {str(r.log_date): r for r in prog_result.scalars().all()}

    daily = []
    total_calories = 0.0
    total_water = 0
    total_steps = 0

    for i in range(7):
        day = start + timedelta(days=i)
        day_str = str(day)
        cal = cal_rows.get(day_str)
        prog = prog_rows.get(day_str)

        day_calories = float(cal.calories) if cal else 0.0
        day_water = prog.water_glasses if prog else 0
        day_steps = prog.steps if prog else 0

        total_calories += day_calories
        total_water += day_water or 0
        total_steps += day_steps or 0

        daily.append({
            "date": day_str,
            "calories_consumed": round(day_calories, 1),
            "calorie_target": round(patient_tdee, 1),
            "water_glasses": day_water or 0,
            "steps": day_steps or 0,
            "protein_g": round(float(cal.protein), 1) if cal else 0.0,
            "carbs_g": round(float(cal.carbs), 1) if cal else 0.0,
            "fat_g": round(float(cal.fat), 1) if cal else 0.0,
        })

    return {
        "week_start": str(start),
        "week_end": str(today),
        "daily": daily,
        "totals": {
            "calories": round(total_calories, 1),
            "water_glasses": total_water,
            "steps": total_steps,
        },
        "averages": {
            "calories_per_day": round(total_calories / 7, 1),
            "water_per_day": round(total_water / 7, 1),
            "steps_per_day": round(total_steps / 7, 0),
        },
    }


async def calculate_and_store_streak(
    session: AsyncSession, patient_id: int
) -> int:
    """
    Count consecutive days (going backwards from today) where the patient
    logged at least one meal. Store result in today's ProgressLog.streak_days.
    Returns the streak count.
    """
    from datetime import timedelta
    today = date.today()
    streak = 0
    check_date = today
    MAX_STREAK_DAYS = 365

    while streak < MAX_STREAK_DAYS:
        result = await session.execute(
            select(sa_func.count(MealLog.id)).where(
                MealLog.patient_id == patient_id,
                MealLog.logged_date == check_date,
            )
        )
        count = result.scalar()
        if count == 0:
            break
        streak += 1
        check_date = check_date - timedelta(days=1)

    # Store on today's ProgressLog row
    row = await _get_or_create_progress(session, patient_id, today)
    row.streak_days = streak
    await session.flush()
    return streak
