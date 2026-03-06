from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.user_service import get_current_user
from ..services.progress_service import (
    log_meal, log_water, log_steps, log_weight, log_activity,
    get_today_summary, get_weekly_summary,
    calculate_and_store_calorie_adjustment,
    get_meal_log_by_id, update_meal_log, delete_meal_log,
    get_weight_history, get_weekly_report, calculate_and_store_streak,
)
from ..schemas.progress import (
    MealLogCreate, WaterLogCreate, StepsLogCreate,
    WeightLogCreate, ActivityLogCreate,
    MealLogUpdate, MealLogResponse, WeeklyReportResponse,
)
from ..core.database import get_db
from ..models.db_models import Patient

router = APIRouter()


@router.post("/log/meal")
async def post_log_meal(
    meal: MealLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log a meal consumed by the user."""
    await log_meal(session, current_user.id, meal.model_dump())

    # Trigger calorie adjustment calculation if today's total crosses 80% of TDEE
    if current_user.tdee:
        summary = await get_today_summary(session, current_user.id)
        today_calories = summary["total_calories"]
        threshold = float(current_user.tdee) * 0.80
        if today_calories >= threshold:
            await calculate_and_store_calorie_adjustment(
                session,
                current_user.id,
                float(current_user.tdee),
                today_calories,
            )

    return {"message": "Meal logged successfully"}


@router.post("/log/water")
async def post_log_water(
    water: WaterLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log water intake."""
    await log_water(session, current_user.id, water.glasses)
    return {"message": "Water intake logged successfully"}


@router.post("/log/steps")
async def post_log_steps(
    steps: StepsLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log daily steps."""
    await log_steps(session, current_user.id, steps.steps)
    return {"message": "Steps logged successfully"}


@router.post("/log/weight")
async def post_log_weight(
    weight: WeightLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log current weight."""
    await log_weight(session, current_user.id, weight.weight)
    return {"message": "Weight logged successfully"}


@router.post("/log/activity")
async def post_log_activity(
    activity: ActivityLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log daily activity."""
    await log_activity(session, current_user.id, activity.model_dump())
    return {"message": "Activity logged successfully"}


@router.get("/weight")
async def get_weight(
    current_user: Patient = Depends(get_current_user),
):
    """Get current weight from patient profile."""
    return {"current_weight": float(current_user.weight_kg)}


@router.get("/today")
async def get_today_stats(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get summarised stats for today — uses patient.tdee instead of hardcoded 2000."""
    summary = await get_today_summary(session, current_user.id)
    target = float(current_user.tdee) if current_user.tdee else 2000.0

    return {
        "calories": {
            "consumed": summary["total_calories"],
            "target": target,
            "remaining": target - summary["total_calories"],
        },
        "water_intake": {
            "glasses": summary["water_glasses"],
            "target": 8,
        },
        "activity": {
            "steps": summary["steps"],
            "target_steps": 10000,
        },
    }


@router.get("/weekly")
async def get_weekly_stats(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get weekly progress summary."""
    daily_data = await get_weekly_summary(session, current_user.id)
    total_cals = sum(d["calories"] for d in daily_data)
    avg_cals = total_cals / 7 if daily_data else 0

    return {
        "daily_data": daily_data,
        "summary": {
            "average_calories_consumed": round(avg_cals, 1),
        },
    }


# ─── PUT /api/v1/progress/log/meal/{log_id} ──────────────────────────────

@router.put("/log/meal/{log_id}", response_model=MealLogResponse)
async def edit_meal_log(
    log_id: int,
    data: MealLogUpdate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Edit a logged meal. Only allowed within 24 hours of logging."""
    try:
        updated = await update_meal_log(
            session, current_user.id, log_id,
            data.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if updated is None:
        raise HTTPException(status_code=404, detail="Meal log not found")
    return updated


# ─── DELETE /api/v1/progress/log/meal/{log_id} ───────────────────────────

@router.delete("/log/meal/{log_id}")
async def remove_meal_log(
    log_id: int,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a logged meal. Only allowed within 24 hours of logging."""
    try:
        deleted = await delete_meal_log(session, current_user.id, log_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail="Meal log not found")
    return {"message": "Meal log deleted"}


# ─── PUT /api/v1/progress/log/water ──────────────────────────────────────

@router.put("/log/water")
async def update_water_log(
    water: WaterLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Overwrite today's water glass count (replaces, does not add)."""
    from ..services.progress_service import _get_or_create_progress
    from datetime import date as _date
    row = await _get_or_create_progress(session, current_user.id, _date.today())
    row.water_glasses = water.glasses
    await session.flush()
    return {"message": "Water log updated", "glasses": water.glasses}


# ─── PUT /api/v1/progress/log/steps ──────────────────────────────────────

@router.put("/log/steps")
async def update_steps_log(
    steps: StepsLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Overwrite today's step count (replaces, does not add)."""
    from ..services.progress_service import _get_or_create_progress
    from datetime import date as _date
    row = await _get_or_create_progress(session, current_user.id, _date.today())
    row.steps = steps.steps
    await session.flush()
    return {"message": "Steps log updated", "steps": steps.steps}


# ─── PUT /api/v1/progress/log/weight ─────────────────────────────────────

@router.put("/log/weight")
async def update_weight_log(
    weight: WeightLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Overwrite today's logged weight."""
    from ..services.progress_service import _get_or_create_progress
    from datetime import date as _date
    from decimal import Decimal
    row = await _get_or_create_progress(session, current_user.id, _date.today())
    row.weight_kg = Decimal(str(weight.weight))
    await session.flush()
    return {"message": "Weight log updated", "weight_kg": weight.weight}


# ─── DELETE /api/v1/progress/log/water ───────────────────────────────────

@router.delete("/log/water")
async def delete_water_log(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Reset today's water log to 0."""
    from ..services.progress_service import _get_or_create_progress
    from datetime import date as _date
    row = await _get_or_create_progress(session, current_user.id, _date.today())
    row.water_glasses = 0
    await session.flush()
    return {"message": "Water log reset"}


# ─── DELETE /api/v1/progress/log/steps ───────────────────────────────────

@router.delete("/log/steps")
async def delete_steps_log(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Reset today's step log to 0."""
    from ..services.progress_service import _get_or_create_progress
    from datetime import date as _date
    row = await _get_or_create_progress(session, current_user.id, _date.today())
    row.steps = 0
    await session.flush()
    return {"message": "Steps log reset"}


# ─── GET /api/v1/progress/weight-history ─────────────────────────────────

@router.get("/weight-history")
async def get_weight_history_endpoint(
    days: int = 30,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return weight entries for last N days (default 30). Max 365."""
    days = min(max(days, 1), 365)
    history = await get_weight_history(session, current_user.id, days)
    return {"days": days, "entries": history}


# ─── GET /api/v1/progress/weekly-report ──────────────────────────────────

@router.get("/weekly-report")
async def get_weekly_report_endpoint(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Full 7-day report — daily breakdown + totals + averages vs TDEE target."""
    tdee = float(current_user.tdee) if current_user.tdee else 2000.0
    report = await get_weekly_report(session, current_user.id, tdee)
    return report


# ─── GET /api/v1/progress/streak ─────────────────────────────────────────

@router.get("/streak")
async def get_streak(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return current consecutive logging streak and store it on today's ProgressLog."""
    streak = await calculate_and_store_streak(session, current_user.id)
    return {"streak_days": streak}