from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from sqlalchemy import select

from ..services.user_service import get_current_user
from ..models.db_models import Patient, ProgressLog, Recommendation
from ..services.diet_plan_service import DietPlanService
from ..core.database import get_db
from typing import List, Dict

router = APIRouter()

from ..core.limiter import limiter

class CalorieReductionInput(BaseModel):
    reduction_amount: int

@router.post("/adjust")
@limiter.limit("10/hour")
async def adjust_meal_plan(
    request: Request,
    reduction: CalorieReductionInput,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Adjust meal plan with rate limiting"""
    try:
        diet_service = DietPlanService()
        
        # Use stored TDEE from patient profile (set during onboarding)
        # Fall back to on-the-fly calculation only if tdee not yet stored
        if current_user.tdee:
            total_calories = float(current_user.tdee)
        else:
            import logging
            logging.getLogger(__name__).warning(
                f"Patient {current_user.id} has no stored TDEE — falling back to calculation"
            )
            if current_user.date_of_birth:
                today = date.today()
                dob = current_user.date_of_birth
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                age = 30
            from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee
            bmr = calculate_bmr(
                current_user.gender,
                float(current_user.weight_kg),
                float(current_user.height_cm),
                age,
            )
            total_calories = calculate_tdee(bmr, current_user.activity_level)
        
        # Apply yesterday's stored calorie adjustment (surplus/deficit carry-over)
        # Positive adjustment = patient ate less than TDEE → allow more today
        # Negative adjustment = patient ate more than TDEE → reduce today
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        adj_result = await session.execute(
            select(ProgressLog.calorie_adjustment).where(
                ProgressLog.patient_id == current_user.id,
                ProgressLog.log_date == yesterday,
            )
        )
        adj_row = adj_result.scalar()
        prior_adjustment = float(adj_row) if adj_row is not None else 0.0

        # Apply reduction + prior adjustment, floor at 800 kcal
        target_calories = max(
            total_calories - reduction.reduction_amount + prior_adjustment,
            800.0,
        )

        # Prepare user data dictionary with all required fields
        user_data = {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "gender": current_user.gender,
            "height": float(current_user.height_cm),
            "weight": float(current_user.weight_kg),
            "activity_level": current_user.activity_level,
            "diet": current_user.diet_type,
            "health_condition": current_user.health_condition or "Healthy",
            "region": current_user.region or "North",
            "target_calories": target_calories,
        }
        
        # Generate new plan with adjusted calories
        new_plan = await diet_service.generate_diet_plan(user_data, session)
        await diet_service.update_diet_plan(str(current_user.id), new_plan, session=session)
        
        return {
            "message": "Meal plan adjusted successfully",
            "new_target_calories": target_calories,
            "plan": new_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── GET /api/v1/meal-plan/week ──────────────────────────────────────────

@router.get("/week")
async def get_week_plan(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns the active meal plan organised as a 7-day dict keyed by date string.
    Each key maps to a list of meal objects for that day.
    Returns 404 if no active plan exists.
    """
    diet_service = DietPlanService()
    plan = await diet_service.get_diet_plan(str(current_user.id), session=session)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    # Group meals by Date field
    week: dict = {}
    for meal in plan.meals:
        day = meal.get("Date")
        if day:
            week.setdefault(day, []).append(meal)

    return {
        "plan_created_at": plan.created_at.isoformat() if plan.created_at else None,
        "days": week,
        "total_days": len(week),
    }


# ─── GET /api/v1/meal-plan/history ───────────────────────────────────────

@router.get("/history")
async def get_plan_history(
    limit: int = 10,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns metadata of past and current diet plans, newest first.
    Does not return full meals for performance (use /my-plan for active meals).
    """
    limit = min(max(limit, 1), 50)
    diet_service = DietPlanService()
    history = await diet_service.get_plan_history(
        str(current_user.id), session=session, limit=limit
    )
    return {"plans": history, "count": len(history)}


# ─── GET /api/v1/meal-plan/shopping-list ─────────────────────────────────

@router.get("/shopping-list")
async def get_shopping_list(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns the full ingredient list for the active meal plan.
    Aggregates duplicate ingredients, groups by a simple category heuristic.
    Returns 404 if no active plan exists.
    Returns empty grouped list if plan has no ingredient_checklist.
    """
    diet_service = DietPlanService()
    plan = await diet_service.get_diet_plan(str(current_user.id), session=session)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    checklist = plan.ingredient_checklist or []

    # Aggregate duplicates by ingredient name (case-insensitive)
    aggregated: dict[str, dict] = {}
    for item in checklist:
        name = str(item.get("ingredient") or item.get("name") or "Unknown").strip()
        key = name.lower()
        if key not in aggregated:
            aggregated[key] = {
                "ingredient": name,
                "quantity": item.get("quantity") or item.get("amount") or "",
                "unit": item.get("unit") or "",
            }
        # If already exists, quantities are left as-is (unit mismatch risk)
        # Full numeric aggregation deferred to Phase 2 after standardising units

    # Simple category heuristic based on keyword matching
    CATEGORIES: dict[str, list[str]] = {
        "Vegetables": ["onion", "tomato", "spinach", "potato", "carrot", "capsicum",
                       "brinjal", "cauliflower", "cabbage", "peas", "beans", "cucumber",
                       "garlic", "ginger", "green chilli", "coriander", "mint"],
        "Dairy": ["milk", "curd", "yogurt", "paneer", "cheese", "butter", "ghee", "cream"],
        "Grains & Pulses": ["rice", "wheat", "dal", "lentil", "flour", "bread", "roti",
                            "oats", "poha", "semolina", "suji", "maida", "besan",
                            "moong", "chana", "rajma", "urad"],
        "Proteins": ["chicken", "egg", "fish", "mutton", "prawn", "tofu", "soya"],
        "Fruits": ["banana", "apple", "mango", "orange", "papaya", "watermelon",
                   "grapes", "pomegranate", "guava", "lemon"],
        "Spices & Condiments": ["salt", "pepper", "cumin", "turmeric", "chilli", "masala",
                                "oil", "sugar", "honey", "vinegar", "sauce", "mustard"],
    }

    grouped: dict[str, list] = {cat: [] for cat in CATEGORIES}
    grouped["Other"] = []

    for item in aggregated.values():
        name_lower = item["ingredient"].lower()
        assigned = False
        for category, keywords in CATEGORIES.items():
            if any(kw in name_lower for kw in keywords):
                grouped[category].append(item)
                assigned = True
                break
        if not assigned:
            grouped["Other"].append(item)

    # Remove empty categories
    grouped = {k: v for k, v in grouped.items() if v}

    total_items = sum(len(v) for v in grouped.values())
    return {
        "total_items": total_items,
        "grouped": grouped,
    }
