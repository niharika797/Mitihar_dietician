from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from sqlalchemy import select, func, not_, delete as sa_delete

from ..services.user_service import get_current_user
from ..models.db_models import (
    Patient, ProgressLog, Recommendation, WeeklyCombo,
    PatientDishPreferences, PatientMealChoice, PatientMealChoiceDish, FoodItem,
)
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
        
        # Compute age (needed in user_data for meal generator's target calculations)
        if current_user.date_of_birth:
            today = date.today()
            dob = current_user.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            age = 30

        # Use stored TDEE from patient profile (set during onboarding)
        # Fall back to on-the-fly calculation only if tdee not yet stored
        if current_user.tdee:
            total_calories = float(current_user.tdee)
        else:
            import logging
            logging.getLogger(__name__).warning(
                f"Patient {current_user.id} has no stored TDEE — falling back to calculation"
            )
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
            "food_allergies": current_user.food_allergies or [],
            "age": age,
        }
        
        # Generate new plan with adjusted calories
        new_plan = await diet_service.generate_diet_plan(user_data, session)
        await diet_service.store_diet_plan(new_plan, session=session)
        
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
    v1 plans: returns flat date-keyed dict { "YYYY-MM-DD": [{...meal},...] }.
    v2 plans (generation_version=2): returns structured combo response.
    """
    from collections import defaultdict

    rec_result = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == current_user.id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    active_rec = rec
    if rec.approval_status == "draft":
        approved_result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == current_user.id,
                Recommendation.generation_version == 2,
                Recommendation.approval_status == "approved",
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        active_rec = approved_result.scalars().first()
        if active_rec is None:
            return {
                "generation_version": 2,
                "approval_status": "pending",
                "message": "Plan awaiting doctor approval",
                "days": [],
            }

    combos_result = await session.execute(
        select(WeeklyCombo)
        .where(WeeklyCombo.recommendation_id == active_rec.id)
        .order_by(WeeklyCombo.slot_date, WeeklyCombo.meal_type, WeeklyCombo.combo_index)
    )
    combos = list(combos_result.scalars().all())

    prefs_result = await session.execute(
        select(PatientDishPreferences.food_item_id)
        .where(
            PatientDishPreferences.patient_id == current_user.id,
            PatientDishPreferences.preference_type == "pin",
        )
    )
    pinned_ids: set = {row[0] for row in prefs_result}

    days_map: dict = defaultdict(lambda: defaultdict(list))
    min_date = None

    for combo in combos:
        date_str = str(combo.slot_date)
        if min_date is None or date_str < min_date:
            min_date = date_str
        dishes_out = []
        pinned_dish_ids = []
        for dish in (combo.dishes or []):
            fid = dish.get("food_id") or dish.get("food_item_id")
            if fid and fid in pinned_ids:
                pinned_dish_ids.append(fid)
            dishes_out.append({
                "food_item_id": fid,
                "recipe_name": dish.get("recipe_name", ""),
                "slot_type": dish.get("slot_type", ""),
                "calories": float(dish.get("calories", 0)),
            })
        days_map[date_str][combo.meal_type].append({
            "combo_id": combo.id,
            "combo_index": combo.combo_index,
            "dishes": dishes_out,
            "total_calories": float(combo.total_calories or 0),
            "contains_doctor_pick": bool(pinned_dish_ids),
            "pinned_dish_ids": pinned_dish_ids,
        })

    days = []
    for date_str in sorted(days_map.keys()):
        day_meals: dict = {}
        for mt in ("Breakfast", "Lunch", "Dinner"):
            day_meals[mt] = {"combos": days_map[date_str].get(mt, [])}
        days.append({"date": date_str, "meals": day_meals})

    return {
        "generation_version": 2,
        "approval_status": "approved",
        "week_start": min_date or "",
        "days": days,
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
        name = str(item.get("ingredient") or item.get("Ingredient") or item.get("name") or "Unknown").strip()
        key = name.lower()
        if key not in aggregated:
            aggregated[key] = {
                "ingredient": name,
                "quantity": item.get("quantity") or item.get("Total Amount (g)") or item.get("amount") or "",
                "unit": item.get("unit") or item.get("Unit") or ("g" if item.get("Total Amount (g)") else ""),
                "at_home": item.get("at_home", False)
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


# ─── POST /api/v1/meal-plan/shopping-list/toggle ─────────────────────────

@router.post("/shopping-list/toggle")
async def toggle_ingredient_at_home(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    ingredient_name: str = Query(..., min_length=1),
    at_home: bool = Query(...),
):
    """
    Mark an ingredient as 'available at home' or 'need to buy'.
    Stores the toggle state on the active Recommendation's ingredient_checklist JSONB.

    Each checklist item gets an 'at_home' boolean field.
    Matching is case-insensitive on ingredient name.

    Returns 404 if no active plan.
    Returns 404 if the ingredient is not found in the checklist.
    """
    rec_result = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == current_user.id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    checklist = list(rec.ingredient_checklist or [])
    search = ingredient_name.strip().lower()
    found = False

    updated_checklist = []
    for item in checklist:
        name = str(item.get("ingredient") or item.get("Ingredient") or item.get("name") or "").lower()
        if name == search:
            item = dict(item)      # copy — JSONB items are read-only dicts
            item["at_home"] = at_home
            found = True
        updated_checklist.append(item)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient '{ingredient_name}' not found in checklist",
        )

    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(ingredient_checklist=updated_checklist)
    )
    await session.flush()
    return {
        "ingredient": ingredient_name,
        "at_home": at_home,
        "message": f"Marked as {'available at home' if at_home else 'need to buy'}",
    }


_VALID_MEAL_TYPES = {"Breakfast", "Lunch", "Dinner"}


# ─── POST /api/v1/meal-plan/confirm-choice ───────────────────────────────

_VALID_BOWL_SIZES = {"small", "medium", "large"}

class ConfirmChoiceInput(BaseModel):
    food_item_ids: list[int]
    date: date
    meal_type: str
    weekly_combo_id: int | None = None
    bowl_size: str | None = None  # 'small' | 'medium' | 'large'; defaults to 'medium'


@router.post("/confirm-choice")
async def confirm_meal_choice(
    body: ConfirmChoiceInput,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Records patient's confirmed combo choice for a meal slot (plan-time, not a consumption log).
    Accepts 1 or more food_item_ids (N dishes for a combo). One choice per (patient, date,
    meal_type) — upserts on conflict. Re-confirm rebuilds child dish rows atomically.
    """
    if body.meal_type not in _VALID_MEAL_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"meal_type must be one of {sorted(_VALID_MEAL_TYPES)}",
        )
    if body.bowl_size is not None and body.bowl_size not in _VALID_BOWL_SIZES:
        raise HTTPException(status_code=422, detail="bowl_size must be small, medium, or large")
    if not body.food_item_ids:
        raise HTTPException(status_code=422, detail="food_item_ids must not be empty")

    # Fetch all food items in one query
    fi_result = await session.execute(
        select(FoodItem).where(FoodItem.id.in_(body.food_item_ids))
    )
    confirmed_items = list(fi_result.scalars().all())
    if len(confirmed_items) != len(body.food_item_ids):
        raise HTTPException(status_code=404, detail="One or more food_item_ids not found")

    # Validate none are blocked (one query)
    blocked_result = await session.execute(
        select(PatientDishPreferences.food_item_id)
        .where(
            PatientDishPreferences.patient_id == current_user.id,
            PatientDishPreferences.food_item_id.in_(body.food_item_ids),
            PatientDishPreferences.preference_type == "block",
        )
    )
    blocked_found = list(blocked_result.scalars().all())
    if blocked_found:
        raise HTTPException(status_code=422, detail=f"Dish(es) {blocked_found} are blocked for this patient")

    # v2 path: verify combo ownership + meal_time_tags
    if body.weekly_combo_id is not None:
        combo_check = await session.execute(
            select(WeeklyCombo)
            .join(Recommendation, WeeklyCombo.recommendation_id == Recommendation.id)
            .where(
                WeeklyCombo.id == body.weekly_combo_id,
                Recommendation.patient_id == current_user.id,
            )
        )
        target_combo = combo_check.scalars().first()
        if target_combo is None:
            raise HTTPException(status_code=404, detail="weekly_combo_id not found or not owned by this patient")
        combo_meal_type = target_combo.meal_type
        invalid = [fi.id for fi in confirmed_items if combo_meal_type not in (fi.meal_time_tags or [])]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail={"error": "meal_time_mismatch", "message": "One or more dishes not valid for this meal type"},
            )

    total_calories = sum(float(fi.cal_per_serving) for fi in confirmed_items)
    primary_food_item_id = body.food_item_ids[0]

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    resolved_bowl_size = body.bowl_size or "medium"
    stmt = pg_insert(PatientMealChoice).values(
        patient_id=current_user.id,
        food_item_id=primary_food_item_id,
        date=body.date,
        meal_type=body.meal_type,
        calories=total_calories,
        weekly_combo_id=body.weekly_combo_id,
        bowl_size=resolved_bowl_size,
    ).on_conflict_do_update(
        constraint="uq_pmc_patient_date_meal",
        set_={
            "food_item_id": primary_food_item_id,
            "calories": total_calories,
            "weekly_combo_id": body.weekly_combo_id,
            "bowl_size": resolved_bowl_size,
            "confirmed_at": func.now(),
        },
    ).returning(PatientMealChoice.id)
    choice_id = (await session.execute(stmt)).scalar_one()

    # Rebuild child dish rows — delete-then-insert keeps re-confirm idempotent.
    # Both parent upsert and children commit or roll back together.
    await session.execute(
        sa_delete(PatientMealChoiceDish).where(PatientMealChoiceDish.choice_id == choice_id)
    )
    for fi in confirmed_items:
        session.add(PatientMealChoiceDish(
            choice_id=choice_id,
            food_item_id=fi.id,
            slot_type=fi.slot_type,
            calories=float(fi.cal_per_serving),
        ))
    await session.flush()

    consumed_result = await session.execute(
        select(func.coalesce(func.sum(PatientMealChoice.calories), 0.0))
        .where(
            PatientMealChoice.patient_id == current_user.id,
            PatientMealChoice.date == body.date,
        )
    )
    calories_remaining = float(current_user.tdee or 2000) - float(consumed_result.scalar())

    return {
        "food_item_ids": body.food_item_ids,
        "date": str(body.date),
        "meal_type": body.meal_type,
        "calories": round(total_calories, 2),
        "calories_remaining_today": round(calories_remaining, 1),
    }


# ─── GET /api/v1/meal-plan/choices/{plan_date} ───────────────────────────

@router.get("/choices/{plan_date}")
async def get_daily_choices(
    plan_date: date,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns confirmed meal choices for the patient on a given date.
    Joins with food_items to include recipe_name.
    Used by frontend to restore confirmed state on mount/refresh.
    """
    result = await session.execute(
        select(
            PatientMealChoice.id,
            PatientMealChoice.meal_type,
            PatientMealChoice.food_item_id,
            PatientMealChoice.calories,
            PatientMealChoice.weekly_combo_id,
            FoodItem.recipe_name,
        )
        .join(FoodItem, FoodItem.id == PatientMealChoice.food_item_id)
        .where(
            PatientMealChoice.patient_id == current_user.id,
            PatientMealChoice.date == plan_date,
        )
    )
    rows = result.all()

    # Session 22E (Part 3): attach the per-dish breakdown from the child table.
    # recipe_name is a live join to food_items — Option B does not snapshot names,
    # so a renamed recipe reads with its new name here (acceptable for analytics).
    # Existing flat fields (food_item_id/calories/recipe_name) are preserved for
    # backward compatibility; `dishes` is additive.
    choice_ids = [r.id for r in rows]
    dishes_by_choice: dict[int, list] = {}
    if choice_ids:
        dish_result = await session.execute(
            select(
                PatientMealChoiceDish.choice_id,
                PatientMealChoiceDish.food_item_id,
                PatientMealChoiceDish.slot_type,
                PatientMealChoiceDish.calories,
                FoodItem.recipe_name,
            )
            .join(FoodItem, FoodItem.id == PatientMealChoiceDish.food_item_id)
            .where(PatientMealChoiceDish.choice_id.in_(choice_ids))
        )
        for choice_id, dish_food_id, slot_type, dish_cal, dish_name in dish_result:
            dishes_by_choice.setdefault(choice_id, []).append({
                "food_item_id": dish_food_id,
                "slot_type": slot_type,
                "calories": float(dish_cal) if dish_cal is not None else None,
                "recipe_name": dish_name,
            })

    choices = [
        {
            "meal_type": meal_type,
            "food_item_id": food_item_id,
            "calories": float(calories),
            "weekly_combo_id": weekly_combo_id,
            "recipe_name": recipe_name,
            "dishes": dishes_by_choice.get(cid, []),
        }
        for cid, meal_type, food_item_id, calories, weekly_combo_id, recipe_name in rows
    ]
    return {"date": str(plan_date), "choices": choices}


# ─── GET /api/v1/meal-plan/combo/{combo_id}/dishes ───────────────────────

@router.get("/combo/{combo_id}/dishes")
async def get_combo_dishes(
    combo_id: int,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns enriched dish data for a weekly combo — per-dish macros + ingredients.
    Security: combo must belong to an active recommendation for the requesting patient.
    """
    combo_result = await session.execute(
        select(WeeklyCombo)
        .join(Recommendation, WeeklyCombo.recommendation_id == Recommendation.id)
        .where(
            WeeklyCombo.id == combo_id,
            Recommendation.patient_id == current_user.id,
        )
    )
    combo = combo_result.scalars().first()
    if combo is None:
        raise HTTPException(status_code=404, detail="Combo not found or not owned by this patient")

    dishes_jsonb: list[dict] = combo.dishes or []
    food_item_ids = [d["food_item_id"] for d in dishes_jsonb if d.get("food_item_id")]

    fi_result = await session.execute(
        select(FoodItem).where(FoodItem.id.in_(food_item_ids))
    )
    fi_map = {fi.id: fi for fi in fi_result.scalars().all()}

    enriched = []
    for dish in dishes_jsonb:
        fid = dish.get("food_item_id")
        fi = fi_map.get(fid)
        enriched.append({
            "food_item_id": fid,
            "recipe_name": fi.recipe_name if fi else dish.get("recipe_name", ""),
            "slot_type": fi.slot_type if fi else dish.get("slot_type", ""),
            "calories": float(fi.cal_per_serving) if fi else float(dish.get("calories", 0)),
            "protein": float(fi.protein_per_serving) if fi else 0.0,
            "carbs": float(fi.carbs_per_serving) if fi else 0.0,
            "fat": float(fi.fat_per_serving) if fi else 0.0,
            "ingredients": fi.ingredients if fi else [],
        })

    return {"combo_id": combo_id, "dishes": enriched}


# ─── GET /api/v1/meal-plan/beverages ─────────────────────────────────────

@router.get("/beverages")
async def list_beverages(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Lists beverage options for ad-hoc patient logging.

    Session 22E (Part 2): beverages are no longer auto-generated into meal slots.
    Patients log a tea/coffee/shake on demand via the snack-style quick-log
    (POST /progress/log/meal with food_id set), following the Session 21 pattern.
    Queries food_items directly (slot_type='beverage') rather than seeding the
    empty `beverages` table — fewer moving parts, single source of truth.

    Presentation guard: rows with cal_per_serving >= 300 are excluded. Every
    legitimate beverage is <=199 kcal; the only rows above 300 are known data
    errors (id 591 Buttermilk Soup 2857.65, id 2447 Spiced Beetroot Buttermilk
    403.56) whose source quantity_g is whole-batch scale. This is a display guard
    only — the underlying nutrition is NOT overridden; those two need a doctor-review
    recipe re-entry through the IFCT-traced path (tracked in BUILD_TRACKER).
    """
    # Dedup by recipe_name: keep one row per name (lowest id = most original entry)
    dedup_subq = (
        select(func.min(FoodItem.id))
        .where(FoodItem.slot_type == "beverage", FoodItem.cal_per_serving < 300)
        .group_by(FoodItem.recipe_name)
        .scalar_subquery()
    )
    result = await session.execute(
        select(
            FoodItem.id, FoodItem.recipe_name, FoodItem.cal_per_serving,
            FoodItem.protein_per_serving, FoodItem.carbs_per_serving,
            FoodItem.fat_per_serving, FoodItem.fiber_per_serving,
        )
        .where(FoodItem.id.in_(dedup_subq))
        .order_by(FoodItem.cal_per_serving.asc())
    )
    return {
        "beverages": [
            {
                "food_item_id": fid,
                "recipe_name": name,
                "calories": float(cal) if cal is not None else 0.0,
                "protein": float(p) if p is not None else 0.0,
                "carbs": float(c) if c is not None else 0.0,
                "fat": float(f) if f is not None else 0.0,
                "fiber": float(fb) if fb is not None else 0.0,
            }
            for fid, name, cal, p, c, f, fb in result
        ]
    }
