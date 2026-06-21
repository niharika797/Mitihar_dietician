from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.limiter import limiter
from ..services.user_service import get_current_user
from ..services.progress_service import (
    log_meal, log_water, log_steps, log_weight, log_activity,
    get_today_summary, get_weekly_summary,
    calculate_and_store_calorie_adjustment,
    get_meal_log_by_id, update_meal_log, delete_meal_log,
    get_weight_history, get_weekly_report, calculate_and_store_streak,
    calculate_adherence,
)
from ..schemas.progress import (
    MealLogCreate, WaterLogCreate, StepsLogCreate,
    WeightLogCreate, ActivityLogCreate,
    MealLogUpdate, MealLogResponse, WeeklyReportResponse,
    MealRateRequest, MealRatingResponse,
)
from ..core.database import get_db
from ..models.db_models import Patient

router = APIRouter()


@router.post("/log/meal")
@limiter.limit("60/minute")
async def post_log_meal(
    request: Request,
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
@limiter.limit("30/minute")
async def post_log_water(
    request: Request,
    water: WaterLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log water intake."""
    await log_water(session, current_user.id, water.glasses)
    return {"message": "Water intake logged successfully"}


@router.post("/log/steps")
@limiter.limit("30/minute")
async def post_log_steps(
    request: Request,
    steps: StepsLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log daily steps."""
    await log_steps(session, current_user.id, steps.steps)
    return {"message": "Steps logged successfully"}


async def _handle_weight_change(session: AsyncSession, current_user: Patient, new_weight: float):
    from sqlalchemy import update as sa_update
    from ..models.db_models import Patient as PatientModel
    from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee, calculate_bmi
    from ..services.diet_plan_service import DietPlanService
    from ..services.user_service import get_patient_by_id

    if current_user.date_of_birth:
        from datetime import date as _date
        dob = current_user.date_of_birth
        today = _date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    else:
        age = 30
        
    height = float(current_user.height_cm) if current_user.height_cm else 170.0
    activity = getattr(current_user, "activity_level", "Lightly Active")
    
    new_bmr = calculate_bmr(current_user.gender, float(new_weight), height, age)
    new_tdee = calculate_tdee(new_bmr, activity)
    new_bmi = calculate_bmi(height, float(new_weight))

    await session.execute(
        sa_update(PatientModel)
        .where(PatientModel.id == current_user.id)
        .values(
            weight_kg=new_weight,
            bmi=round(new_bmi, 2),
            bmr=round(new_bmr, 2),
            tdee=round(new_tdee, 2),
        )
    )
    await session.flush()
    updated = await get_patient_by_id(session, current_user.id)

    diet_service = DietPlanService()
    user_data = {
        "id": updated.id,
        "age": age,
        "gender": updated.gender,
        "weight": float(new_weight),
        "height": height,
        "diet": updated.diet_type or "Anything",
        "health_state": updated.health_condition or "Healthy",
        "region": updated.region or "none",
        "target_weight": float(updated.target_weight_kg) if getattr(updated, "target_weight_kg", None) else None,
        "activity_level": activity,
        "tdee": float(updated.tdee) if getattr(updated, "tdee", None) else 2000.0,
    }
    try:
        new_plan = await diet_service.generate_diet_plan(user_data, session)
        await diet_service.store_diet_plan(new_plan, session)
        print("Auto-regenerated diet plan upon weight update")
    except Exception as e:
        print(f"Failed to auto-generate diet plan: {e}")


@router.post("/log/weight")
@limiter.limit("30/minute")
async def post_log_weight(
    request: Request,
    weight: WeightLogCreate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Log current weight."""
    await log_weight(session, current_user.id, weight.weight)
    await _handle_weight_change(session, current_user, weight.weight)
    return {"message": "Weight logged successfully"}


@router.post("/log/activity")
@limiter.limit("30/minute")
async def post_log_activity(
    request: Request,
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
        "macros": {
            "protein": summary["protein_g"],
            "carbs": summary["carbs_g"],
            "fat": summary["fat_g"],
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
    await _handle_weight_change(session, current_user, weight.weight)
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


# ─── POST /api/v1/progress/meal/rate ─────────────────────────────────────
# Phase 8 Tier 0 — patient rates a meal 👍 or 👎

@router.post("/meal/rate", response_model=MealRatingResponse, status_code=201)
@limiter.limit("120/minute")
async def rate_meal(
    request: Request,
    body: MealRateRequest,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient rates a meal serving +1 (liked) or -1 (disliked).
    One rating per (patient × food_item × recommendation).
    If the patient already rated this serving, the rating is updated.

    IDOR protection: if recommendation_id is provided, it is verified to
    belong to the current patient before the rating is written.
    This prevents a patient from anchoring their rating to another patient's
    recommendation row and poisoning the RL reward signal.
    """
    from ..models.db_models import MealRating, Recommendation
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    # ── Ownership check on recommendation_id ─────────────────────────────
    if body.recommendation_id is not None:
        rec_check = await session.execute(
            select(Recommendation.id).where(
                Recommendation.id == body.recommendation_id,
                Recommendation.patient_id == current_user.id,
            )
        )
        if rec_check.scalars().first() is None:
            raise HTTPException(
                status_code=403,
                detail="Recommendation does not belong to the current patient",
            )

    # Upsert: update rating if already exists for this (patient, food_item, recommendation)
    stmt = pg_insert(MealRating).values(
        patient_id=current_user.id,
        food_item_id=body.food_item_id,
        recommendation_id=body.recommendation_id,
        rating=body.rating,
    ).on_conflict_do_update(
        constraint="uq_meal_rating",
        set_={"rating": body.rating},
    ).returning(MealRating)

    result = await session.execute(stmt)
    await session.flush()
    row = result.scalars().first()
    return row


# ─── GET /api/v1/progress/meal/ratings ───────────────────────────────────

@router.get("/meal/ratings", response_model=list[MealRatingResponse])
async def get_my_ratings(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Return all meal ratings for the current patient.
    Used by the patient app to restore 👍/👎 button state on load.
    """
    from ..models.db_models import MealRating
    result = await session.execute(
        select(MealRating)
        .where(MealRating.patient_id == current_user.id)
        .order_by(MealRating.rated_at.desc())
        .limit(500)
    )
    return result.scalars().all()


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


# ─── GET /api/v1/progress/adherence/weekly ───────────────────────────────────

@router.get("/adherence/weekly")
async def get_weekly_adherence(
    days: int = 7,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns adherence percentage for the last N days (default 7, max 30).
    Adherence = recommended meal slots actually logged / total recommended slots.
    Only meals logged with a recommendation_id count as 'adhered'.
    Custom meals (recommendation_id=None) do not count for adherence.
    """
    days = min(max(days, 1), 30)
    result = await calculate_adherence(session, current_user.id, days)
    return result