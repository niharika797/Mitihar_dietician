# app/routers/diet_plans.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict
from ..services.diet_plan_service import DietPlanService
from ..services.user_service import get_current_user
from ..models.user import UserInDB
from ..models.diet_plan import DietPlan
from ..core.exceptions import DietPlanNotFoundException
from ..services.meal_generator.meal_generator import meal_generator  # Use singleton
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db

router = APIRouter()
from ..core.limiter import limiter

logger = logging.getLogger(__name__)
diet_plan_service = DietPlanService()


def _validate_generated_plan(diet_plan: DietPlan, user_diet: str) -> str | None:
    """
    Validates a generated DietPlan against the required structure.
    Returns None if valid, or an error string describing the failure.
    """
    meals = getattr(diet_plan, "meals", None) or []
    checklist = getattr(diet_plan, "ingredient_checklist", None) or []

    # 1. Must have exactly 35 meals (7 days × 5 meal types × 1 option)
    if len(meals) != 35:
        return f"Expected 35 meals, got {len(meals)}"

    # 2. Every meal must have a Date field
    missing_date = [i for i, m in enumerate(meals) if not m.get("Date")]
    if missing_date:
        return f"Meals at indices {missing_date[:5]} are missing the 'Date' field"

    # 3. ingredient_checklist must be non-empty
    if not checklist:
        return "ingredient_checklist is empty"

    # 4. Diet-type constraint validation
    diet_lower = user_diet.lower().strip()
    if diet_lower == "vegetarian":
        non_veg_meals = [m for m in meals if "Vegetarian" not in str(m)]
        if non_veg_meals:
            return f"{len(non_veg_meals)} meals do not contain 'Vegetarian' in their data"
    elif diet_lower in ["non-vegetarian", "non vegetarian", "non_vegetarian"]:
        has_non_veg = any(
            "Non-Vegetarian" in str(m) or "Non-Veg" in str(m) or "Non Vegetarian" in str(m)
            for m in meals
        )
        if not has_non_veg:
            return "No Non-Vegetarian meals found for non-vegetarian user"

    return None  # All checks passed


@router.get("/my-plan", response_model=DietPlan)
async def get_my_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Get the current user's diet plan, always including ingredient_checklist."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()

    # Ensure ingredient_checklist is always populated — regenerate on-the-fly if missing
    if not diet_plan.ingredient_checklist:
        logger.warning(
            f"ingredient_checklist missing for user {current_user.id}, regenerating from meals."
        )
        checklist_raw = meal_generator.generate_ingredient_checklist(diet_plan.meals)
        if hasattr(checklist_raw, "to_dict"):
            checklist_raw = checklist_raw.to_dict("records")
        diet_plan.ingredient_checklist = checklist_raw if checklist_raw else []

    return diet_plan


@router.get("/today", response_model=DietPlan)
async def get_today_meals(current_user: UserInDB = Depends(get_current_user)):
    """Get today's meals from the user's diet plan."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()

    today_str = datetime.today().strftime("%Y-%m-%d")
    today_meals = [m for m in diet_plan.meals if m.get("Date") == today_str]

    # Generate ingredient checklist for today only
    today_ingredients = meal_generator.generate_ingredient_checklist(today_meals)

    # Handle both DataFrame and list returns
    ingredient_list = (
        today_ingredients.to_dict(orient="records")
        if hasattr(today_ingredients, "to_dict")
        else today_ingredients
    )

    return DietPlan(
        user_id=diet_plan.user_id,
        created_at=diet_plan.created_at,
        meals=today_meals,
        ingredient_checklist=ingredient_list,
    )


@router.post("/generate", response_model=DietPlan)
@limiter.limit("10/hour")
async def generate_diet_plan(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Generate a new 7-day diet plan for the current user.

    Implements a retry loop (max 3 attempts) to handle cases where the
    generator returns a structurally invalid plan. Returns HTTP 503 if
    all attempts fail — never HTTP 500.
    """
    # Block if user already has an active plan
    existing_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail="Diet plan already exists for this user",
        )

    user_diet = getattr(current_user, "diet", "vegetarian") or "vegetarian"
    MAX_ATTEMPTS = 3
    last_error = "Unknown generation error"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logger.info(
                f"Diet plan generation attempt {attempt}/{MAX_ATTEMPTS} "
                f"for user {current_user.id} (diet={user_diet})"
            )

            diet_plan = await diet_plan_service.generate_diet_plan(
                current_user.model_dump(), session
            )

            # If ingredient_checklist came back empty, try to regenerate it
            # before validation so we don't waste a full retry on a trivial issue
            checklist = getattr(diet_plan, "ingredient_checklist", None) or []
            if not checklist:
                meals = getattr(diet_plan, "meals", []) or []
                checklist_raw = meal_generator.generate_ingredient_checklist(meals)
                if hasattr(checklist_raw, "to_dict"):
                    checklist_raw = checklist_raw.to_dict("records")
                if checklist_raw:
                    diet_plan.ingredient_checklist = checklist_raw

            # Validate the full plan structure
            validation_error = _validate_generated_plan(diet_plan, user_diet)
            if validation_error:
                last_error = validation_error
                logger.warning(
                    f"Attempt {attempt} produced invalid plan: {validation_error}"
                )
                continue  # Retry

            # Valid plan — persist and return
            await diet_plan_service.store_diet_plan(diet_plan)
            logger.info(
                f"Diet plan generated and stored successfully on attempt {attempt} "
                f"for user {current_user.id}"
            )
            return diet_plan

        except HTTPException:
            raise  # Never swallow HTTP exceptions (e.g., the 400 above)
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                f"Diet plan generation attempt {attempt} raised an exception: {exc}",
                exc_info=True,
            )
            # Continue to next attempt

    # All retries exhausted
    logger.error(
        f"All {MAX_ATTEMPTS} diet plan generation attempts failed for user "
        f"{current_user.id}. Last error: {last_error}"
    )
    raise HTTPException(
        status_code=503,
        detail="Plan generation failed, please try again",
    )


@router.put("/update", response_model=DietPlan)
async def update_diet_plan(
    updated_plan: DietPlan,
    current_user: UserInDB = Depends(get_current_user),
):
    """Update the current user's diet plan."""
    success = await diet_plan_service.update_diet_plan(
        str(current_user.id), updated_plan
    )
    if not success:
        raise DietPlanNotFoundException()
    return updated_plan


@router.delete(
    "/delete",
    responses={
        200: {
            "description": "Diet plan deleted successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Diet plan deleted successfully"}
                }
            },
        },
        404: {"description": "Diet plan not found"},
    },
)
async def delete_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Delete the current user's diet plan."""
    success = await diet_plan_service.delete_diet_plan(str(current_user.id))
    if not success:
        raise DietPlanNotFoundException()
    return {"message": "Diet plan deleted successfully"}


@router.get(
    "/ingredient-checklist",
    response_model=List[Dict],
    responses={
        200: {
            "description": (
                "Ingredient checklist for today's meals. "
                "Returns an empty list [] if no diet plan exists for the user."
            ),
            "content": {"application/json": {"example": []}},
        }
    },
)
async def get_ingredient_checklist_today(
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get the ingredient checklist for today's meals only.
    Returns an empty list [] if no diet plan is found (valid empty state).
    """
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        return []

    today_str = datetime.today().strftime("%Y-%m-%d")
    today_meals = [m for m in diet_plan.meals if m.get("Date") == today_str]

    ingredient_checklist = meal_generator.generate_ingredient_checklist(today_meals)
    if hasattr(ingredient_checklist, "to_dict"):
        return ingredient_checklist.to_dict(orient="records")
    return ingredient_checklist


@router.get(
    "/weekly-ingredients",
    response_model=List[Dict],
    responses={
        200: {
            "description": (
                "Weekly ingredient checklist. "
                "Returns an empty list [] if no diet plan exists for the user."
            ),
            "content": {"application/json": {"example": []}},
        }
    },
)
async def get_weekly_ingredients(current_user: UserInDB = Depends(get_current_user)):
    """
    Get the weekly ingredient checklist for all meals.
    Returns an empty list [] if no diet plan is found (valid empty state).
    """
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        return []

    if not diet_plan.ingredient_checklist:
        # If ingredient checklist is empty, generate it from all meals
        ingredient_checklist = meal_generator.generate_ingredient_checklist(
            diet_plan.meals
        )
        if hasattr(ingredient_checklist, "to_dict"):
            return ingredient_checklist.to_dict(orient="records")
        return ingredient_checklist

    return diet_plan.ingredient_checklist
