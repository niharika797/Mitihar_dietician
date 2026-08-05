from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from sqlalchemy import select, func, or_, delete as sa_delete, update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from ..services.user_service import get_current_user
from ..models.db_models import (
    Patient, ProgressLog, Recommendation, WeeklyCombo,
    PatientDishPreferences, PatientMealChoice, PatientMealChoiceDish, FoodItem,
    RecipeIngredient, Ingredient, PatientPantry,
)
from ..services.diet_plan_service import DietPlanService
from ..services.meal_generator.meal_generator import is_staple
from ..core.database import get_db

router = APIRouter()

from ..core.limiter import limiter


def _norm_name(s: str) -> str:
    """Normalize an ingredient name for pantry↔recipe matching (collapse case + whitespace)."""
    return " ".join(str(s).strip().lower().split())


# A pantry row alone no longer means "has it" — quantity_g = 0 is an explicit
# out-of-stock marker (auto-deduct writes it). NULL still means "have it, amount
# unknown". Defined once so coverage ranking, the pantry catalogue and the
# shopping list can never disagree about what "have" means.
_PANTRY_IN_STOCK = or_(PatientPantry.quantity_g.is_(None), PatientPantry.quantity_g > 0)

# Serving multipliers per bowl size. MUST stay in sync with BOWL_FACTORS in
# mitihar-patient-app/app/meals/combo-detail.tsx — the app scales the calories it
# displays by these, and the pantry deduction below scales ingredient grams by
# the same factor, so a drift would silently mis-bill stock.
BOWL_FACTORS: dict[str, float] = {"small": 0.75, "medium": 1.0, "large": 1.25}

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

    # ── Pantry coverage (pantry-first): rank combos by how much the patient can already cook.
    # Match by NORMALIZED NAME (not ingredient_id) to survive same-name/different-id dup rows.
    # Staples excluded via substring is_staple (exact-match undercounts badly: 6.8 vs 4.3/dish).
    pantry_rows = await session.execute(
        select(Ingredient.name)
        .join(PatientPantry, PatientPantry.ingredient_id == Ingredient.id)
        .where(PatientPantry.patient_id == current_user.id, _PANTRY_IN_STOCK)
    )
    pantry_names = {_norm_name(r[0]) for r in pantry_rows}

    all_food_ids = {
        fid
        for combo in combos for d in (combo.dishes or [])
        if (fid := (d.get("food_id") or d.get("food_item_id")))
    }
    dish_reqs: dict = defaultdict(set)   # food_id -> {non-staple normalized ingredient names}
    if all_food_ids:
        ri_rows = await session.execute(
            select(RecipeIngredient.food_item_id, Ingredient.name)
            .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
            .where(RecipeIngredient.food_item_id.in_(all_food_ids))
        )
        for fid, nm in ri_rows:
            if not is_staple(nm):
                dish_reqs[fid].add(_norm_name(nm))

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
        required = set()
        for dish in (combo.dishes or []):
            fid = dish.get("food_id") or dish.get("food_item_id")
            if fid:
                required |= dish_reqs.get(fid, set())
        have = required & pantry_names
        missing = sorted(required - have)
        days_map[date_str][combo.meal_type].append({
            "combo_id": combo.id,
            "combo_index": combo.combo_index,
            "dishes": dishes_out,
            "total_calories": float(combo.total_calories or 0),
            "contains_doctor_pick": bool(pinned_dish_ids),
            "pinned_dish_ids": pinned_dish_ids,
            "coverage": round(len(have) / len(required), 3) if required else 0.0,
            "have_count": len(have),
            "required_count": len(required),
            "missing_ingredients": missing[:5],
            "cookable": bool(required) and not missing,
        })

    days = []
    for date_str in sorted(days_map.keys()):
        day_meals: dict = {}
        for mt in ("Breakfast", "Lunch", "Dinner"):
            # Pantry-first: highest coverage first, stable on combo_index.
            slot_combos = sorted(
                days_map[date_str].get(mt, []),
                key=lambda c: (-c["coverage"], c["combo_index"]),
            )
            day_meals[mt] = {"combos": slot_combos}
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
    What the patient still needs to buy, derived live from the plan.

    Replaces the old read of `recommendations.ingredient_checklist`, a blob
    frozen at plan-generation time: it ignored which combos the patient actually
    picked, carried no real quantities, and tracked `at_home` in the blob rather
    than in the pantry. The column itself is untouched — /diet-plans/my-plan, the
    doctor schema and the doctor dashboard still read it.

    Per meal slot from today onwards, the dish set is whichever combo the patient
    confirmed, falling back to combo_index=0 where they haven't chosen yet.
    Required grams come from recipe_ingredients scaled by the confirmed bowl
    size, then the pantry is subtracted.

    Returns 404 if no active plan exists.
    """
    rec = (await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == current_user.id, Recommendation.is_active == True)  # noqa: E712
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )).scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    today = date.today()

    # Confirmed choices, keyed by slot, with their dishes and bowl size.
    choice_rows = (await session.execute(
        select(PatientMealChoice.date, PatientMealChoice.meal_type,
               PatientMealChoice.bowl_size, PatientMealChoiceDish.food_item_id)
        .join(PatientMealChoiceDish, PatientMealChoiceDish.choice_id == PatientMealChoice.id)
        .where(PatientMealChoice.patient_id == current_user.id,
               PatientMealChoice.date >= today)
    )).all()
    chosen: dict[tuple, dict] = {}
    for slot_date, meal_type, bowl_size, food_item_id in choice_rows:
        entry = chosen.setdefault((slot_date, meal_type),
                                  {"ids": [], "factor": BOWL_FACTORS.get(bowl_size or "medium", 1.0)})
        entry["ids"].append(food_item_id)

    # Recommended combo per remaining slot, used wherever nothing was confirmed.
    combo_rows = (await session.execute(
        select(WeeklyCombo.slot_date, WeeklyCombo.meal_type, WeeklyCombo.dishes)
        .where(WeeklyCombo.recommendation_id == rec.id,
               WeeklyCombo.combo_index == 0,
               WeeklyCombo.slot_date >= today)
    )).all()

    required: dict[int, float] = {}

    async def _add(food_ids: list[int], factor: float) -> None:
        for iid, grams in (await _dish_ingredient_grams(session, food_ids, factor)).items():
            required[iid] = required.get(iid, 0.0) + grams

    for slot_date, meal_type, dishes in combo_rows:
        key = (slot_date, meal_type)
        if key in chosen:
            continue   # the confirmed choice wins; added below
        ids = [fid for d in (dishes or []) if (fid := (d.get("food_id") or d.get("food_item_id")))]
        await _add(ids, 1.0)
    for entry in chosen.values():
        await _add(entry["ids"], entry["factor"])

    if not required:
        return {"total_items": 0, "grouped": {}}

    # Subtract what's on hand. A NULL pantry quantity means the patient said they
    # have it without saying how much -- take them at their word and mark it
    # at_home rather than guessing a shortfall.
    pantry = await _pantry_quantities(session, current_user.id)
    names: dict[int, str] = {
        iid: nm for iid, nm in (await session.execute(
            select(Ingredient.id, Ingredient.name).where(Ingredient.id.in_(required.keys()))
        )).all()
    }

    aggregated: dict[str, dict] = {}
    for iid, needed_g in required.items():
        on_hand = pantry.get(iid, 0.0)
        if iid in pantry and on_hand is None:
            still_needed, at_home = 0.0, True
        else:
            still_needed = max(0.0, needed_g - (on_hand or 0.0))
            at_home = still_needed == 0.0
        name = names.get(iid) or "Unknown"
        aggregated[name.lower()] = {
            "ingredient": name,
            "quantity": round(still_needed if not at_home else needed_g),
            "unit": "g",
            "at_home": at_home,
        }

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

    Writes to `patient_pantry`, the same store /pantry/toggle uses — previously
    this set an `at_home` flag inside the plan's ingredient_checklist JSONB, so
    ticking something here did nothing for combo coverage ranking and was lost
    on the next plan. Same thing, one source of truth.

    Marking at_home stores a NULL quantity ("have it, amount unknown"); use
    /pantry/toggle when the patient knows the grams.

    Returns 404 if the name matches no known ingredient.
    """
    ing = (await session.execute(
        select(Ingredient.id)
        .where(func.lower(func.trim(Ingredient.name)) == _norm_name(ingredient_name))
        .limit(1)
    )).scalars().first()
    if ing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient '{ingredient_name}' not found",
        )

    await _pantry_set(session, current_user.id, ing, at_home)
    return {
        "ingredient": ingredient_name,
        "at_home": at_home,
        "message": f"Marked as {'available at home' if at_home else 'need to buy'}",
    }


_VALID_MEAL_TYPES = {"Breakfast", "Lunch", "Dinner"}


# ─── GET /api/v1/meal-plan/pantry ────────────────────────────────────────
# Pantry-first meal planning: the ingredient catalogue the patient can mark as "have".
# Returns the top ~80 non-staple ingredients by recipe frequency (the ones that actually
# unlock dishes) — NOT all 705, which are noisy with synonym dupes and brand/malformed names.
# ?search= does a name lookup over the rest.

_PANTRY_CATALOGUE_LIMIT = 80
_PANTRY_SEARCH_LIMIT = 50


async def _pantry_have_ids(session: AsyncSession, patient_id: int) -> set[int]:
    """Ingredient ids the patient actually has — a row at quantity_g = 0 is
    excluded, so a depleted ingredient reads back as `have: false`."""
    rows = await session.execute(
        select(PatientPantry.ingredient_id)
        .where(PatientPantry.patient_id == patient_id, _PANTRY_IN_STOCK)
    )
    return {r[0] for r in rows}


async def _pantry_quantities(session: AsyncSession, patient_id: int) -> dict[int, float | None]:
    """ingredient_id -> grams on hand (None = have it, amount unknown).
    Includes zero rows so callers can tell "out of stock" from "never tracked"."""
    rows = await session.execute(
        select(PatientPantry.ingredient_id, PatientPantry.quantity_g)
        .where(PatientPantry.patient_id == patient_id)
    )
    return {iid: (float(q) if q is not None else None) for iid, q in rows}


async def _pantry_set(
    session: AsyncSession, patient_id: int, ingredient_id: int,
    have: bool, quantity_g: float | None = None,
) -> None:
    """Shared upsert/delete behind both /pantry/toggle and /shopping-list/toggle.

    do_update rather than do_nothing: re-toggling an ingredient the patient
    already has must be able to correct its quantity, and passing no quantity
    resets it to NULL ("have it, amount unknown") rather than keeping a stale
    number the patient never confirmed."""
    if have:
        await session.execute(
            pg_insert(PatientPantry)
            .values(patient_id=patient_id, ingredient_id=ingredient_id, quantity_g=quantity_g)
            .on_conflict_do_update(
                constraint="uq_patient_pantry",
                set_={"quantity_g": quantity_g},
            )
        )
    else:
        await session.execute(
            sa_delete(PatientPantry).where(
                PatientPantry.patient_id == patient_id,
                PatientPantry.ingredient_id == ingredient_id,
            )
        )
    await session.flush()


async def _dish_ingredient_grams(
    session: AsyncSession, food_item_ids: list[int], scale: float,
) -> dict[int, float]:
    """ingredient_id -> total grams for these dishes at this serving scale.
    Staples are dropped: they never enter the pantry catalogue, so there is
    nothing to deduct from and nothing worth putting on a shopping list."""
    if not food_item_ids:
        return {}
    rows = await session.execute(
        select(RecipeIngredient.ingredient_id, Ingredient.name, RecipeIngredient.quantity_g)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(RecipeIngredient.food_item_id.in_(food_item_ids))
    )
    out: dict[int, float] = {}
    for iid, name, grams in rows:
        if is_staple(name):
            continue
        out[iid] = out.get(iid, 0.0) + float(grams or 0) * scale
    return out


async def _apply_pantry_delta(
    session: AsyncSession, patient_id: int,
    new_grams: dict[int, float], old_grams: dict[int, float],
) -> None:
    """Draw the pantry down by (new - old) grams per ingredient.

    Only rows that already exist AND carry a known quantity are touched:
      - an ingredient the patient never added has nothing to deduct from
      - a NULL quantity means "have it, amount unknown", and subtracting from
        an unknown would fabricate a number
    Clamped at 0 in SQL rather than in Python so concurrent confirms can't race
    the value negative — the CHECK constraint would reject that anyway."""
    deltas = {
        iid: new_grams.get(iid, 0.0) - old_grams.get(iid, 0.0)
        for iid in set(new_grams) | set(old_grams)
    }
    for iid, delta in deltas.items():
        if delta == 0:
            continue
        await session.execute(
            sa_update(PatientPantry)
            .where(
                PatientPantry.patient_id == patient_id,
                PatientPantry.ingredient_id == iid,
                PatientPantry.quantity_g.is_not(None),
            )
            .values(quantity_g=func.greatest(PatientPantry.quantity_g - delta, 0))
        )
    await session.flush()


@router.get("/pantry")
async def get_pantry(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
):
    quantities = await _pantry_quantities(session, current_user.id)
    have_ids = {iid for iid, q in quantities.items() if q is None or q > 0}

    freq = func.count(RecipeIngredient.id)
    stmt = (
        select(Ingredient.id, Ingredient.name, Ingredient.name_hindi, freq.label("c"))
        .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .group_by(Ingredient.id, Ingredient.name, Ingredient.name_hindi)
        .order_by(freq.desc())
    )
    if search and search.strip():
        stmt = stmt.where(Ingredient.name.ilike(f"%{search.strip()}%")).limit(_PANTRY_SEARCH_LIMIT * 3)
    else:
        stmt = stmt.limit(_PANTRY_CATALOGUE_LIMIT * 3)   # over-fetch; staples are dropped below

    cap = _PANTRY_SEARCH_LIMIT if (search and search.strip()) else _PANTRY_CATALOGUE_LIMIT
    items = []
    for iid, name, name_hindi, _c in (await session.execute(stmt)).all():
        if is_staple(name):
            continue
        items.append({
            "ingredient_id": iid,
            "name": name,
            "name_hindi": name_hindi,
            "have": iid in have_ids,
            "quantity_g": quantities.get(iid),
        })
        if len(items) >= cap:
            break
    return {"items": items, "have_count": len(have_ids)}


# ─── POST /api/v1/meal-plan/pantry/toggle ────────────────────────────────

@router.post("/pantry/toggle")
async def toggle_pantry_item(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    ingredient_id: int = Query(...),
    have: bool = Query(...),
    quantity_g: float | None = Query(None, ge=0),
):
    """Insert a pantry row if `have`, delete it if not. Idempotent.

    `quantity_g` is optional — omitting it stores NULL, which means "have it,
    amount unknown" and is exactly the pre-quantity behaviour."""
    await _pantry_set(session, current_user.id, ingredient_id, have, quantity_g)
    return {"ingredient_id": ingredient_id, "have": have, "quantity_g": quantity_g}


# ─── GET /api/v1/meal-plan/pantry/suggestions ────────────────────────────
# Condition-aware "worth buying" ingredients, ranked by the beneficial nutrient.
# Nutrient columns are the IFCT-backed per-100g values; thresholds/rationale in
# docs/MEDICAL_THRESHOLDS.md. Sodium/hypertension intentionally absent (unmodeled salt).

def _suggestion_plan(condition: str):
    if condition == "Anemia":
        return (Ingredient.iron_per_100g, "iron-rich")
    if condition == "Osteoporosis":
        return (Ingredient.calcium_per_100g, "calcium-rich")
    if condition in ("Type 2 Diabetes", "Pre-diabetes"):
        return (Ingredient.fiber_per_100g, "high-fibre — blunts glucose")
    if condition == "PCOS/PCOD":
        return (Ingredient.fiber_per_100g, "high-fibre — helps insulin resistance")
    if condition == "High Cholesterol":
        return (Ingredient.fiber_per_100g, "high-fibre — helps lower cholesterol")
    if condition == "Heart Disease":
        return (Ingredient.fiber_per_100g, "high-fibre — heart-healthy")
    return None


@router.get("/pantry/suggestions")
async def pantry_suggestions(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    have_ids = await _pantry_have_ids(session, current_user.id)
    plans, seen_cols = [], set()
    for cond in (current_user.medical_conditions or []):
        plan = _suggestion_plan(cond)
        if plan and plan[0].key not in seen_cols:   # dedupe: several conditions share fibre
            seen_cols.add(plan[0].key)
            plans.append(plan)
    if not plans:
        return {"items": []}

    out: dict = {}
    for col, reason in plans:
        # Require the ingredient to appear in >=3 recipes so we surface real foods, not
        # obscure spice artifacts (which win a naive per-100g ranking but aren't eaten in bulk).
        rows = await session.execute(
            select(Ingredient.id, Ingredient.name, Ingredient.name_hindi)
            .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .where(col.isnot(None))
            .group_by(Ingredient.id, Ingredient.name, Ingredient.name_hindi, col)
            .having(func.count(RecipeIngredient.id) >= 3)
            .order_by(col.desc())
            .limit(40)
        )
        added = 0
        for iid, name, name_hindi in rows:
            if iid in have_ids or iid in out or is_staple(name):
                continue
            out[iid] = {"ingredient_id": iid, "name": name, "name_hindi": name_hindi, "reason": reason}
            added += 1
            if added >= 5:
                break
    return {"items": list(out.values())[:8]}


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
    resolved_bowl_size = body.bowl_size or "medium"
    bowl_factor = BOWL_FACTORS[resolved_bowl_size]

    # Read the choice being replaced BEFORE the upsert overwrites it. This slot
    # upserts on uq_pmc_patient_date_meal, so without crediting the previous
    # dishes back, every re-pick would deduct again and drain the pantry.
    prev_result = await session.execute(
        select(PatientMealChoice).where(
            PatientMealChoice.patient_id == current_user.id,
            PatientMealChoice.date == body.date,
            PatientMealChoice.meal_type == body.meal_type,
        )
    )
    prev_choice = prev_result.scalars().first()
    prev_food_ids: list[int] = []
    prev_factor = 1.0
    if prev_choice is not None:
        prev_factor = BOWL_FACTORS.get(prev_choice.bowl_size or "medium", 1.0)
        prev_rows = await session.execute(
            select(PatientMealChoiceDish.food_item_id)
            .where(PatientMealChoiceDish.choice_id == prev_choice.id)
        )
        prev_food_ids = [r[0] for r in prev_rows]

    stmt = pg_insert(PatientMealChoice).values(
        patient_id=current_user.id,
        food_item_id=primary_food_item_id,
        date=body.date,
        meal_type=body.meal_type,
        calories=total_calories,
        actual_calories=round(total_calories * bowl_factor, 2),
        weekly_combo_id=body.weekly_combo_id,
        bowl_size=resolved_bowl_size,
    ).on_conflict_do_update(
        constraint="uq_pmc_patient_date_meal",
        set_={
            "food_item_id": primary_food_item_id,
            "calories": total_calories,
            "actual_calories": round(total_calories * bowl_factor, 2),
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

    # ── Pantry auto-deduct ────────────────────────────────────────────────
    # Net delta, not a raw subtraction: credit back what the previous choice for
    # this slot reserved, then charge the new one. Re-confirming the same combo
    # nets to zero, which is what makes this endpoint safe to call repeatedly.
    await _apply_pantry_delta(
        session,
        current_user.id,
        new_grams=await _dish_ingredient_grams(session, body.food_item_ids, bowl_factor),
        old_grams=await _dish_ingredient_grams(session, prev_food_ids, prev_factor),
    )

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
        select(FoodItem)
        .options(selectinload(FoodItem.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
        .where(FoodItem.id.in_(food_item_ids))
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
            # Stage 2: recipe_ingredients is authoritative; food_items.ingredients JSONB deprecated
            "ingredients": [
                {"name": ri.ingredient.name, "amount_g": float(ri.quantity_g)}
                for ri in fi.recipe_ingredients
            ] if fi else [],
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
