import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel

from sqlalchemy import select, case as sa_case, func as sa_func, or_, not_, false
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import MealTemplate, FoodItem, PatientMealConfig, PatientDishPreferences
from .tag_utils import get_avoid_tags, get_prefer_tags
from .calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

logger = logging.getLogger(__name__)

# NOTE: meal_templates DB table (180 rows, schema: id/meal_time/region/diet_type/plan_type/slots)
# is NOT used in the live generation path. Slot composition is handled by
# in-code constants (BREAKFAST_SLOTS, LUNCH_SLOTS, DINNER_SLOTS etc.) established in R-2.
# meal_templates was only referenced in _find_food_item_single_diet() which was
# removed in R-9. The table is retained for historical reference only.
# Do not query meal_templates in new code without product owner approval.

# ── Upgrade 4: Slot-quality blocklist ─────────────────────────────────────────
BLOCKLIST_PATTERNS = [
    "chutney", "powder", "masala powder", "pickle", "achar",
    "papad", "papadum", "murabba", "jam", "sauce", "dip",
]
PROTECTED_SLOTS = ["grain", "dal_protein", "main_dish", "sabzi", "one_pot"]

DEFAULT_SPLIT = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.25}

# ── Session 22B: one-pot meal variant (Lunch/Dinner only) ─────────────────────
ONE_POT_PROBABILITY = 0.40
ONE_POT_SLOTS = [
    {"slot_type": "one_pot",       "calorie_pct": 0.70, "required": True},
    {"slot_type": "accompaniment", "calorie_pct": 0.30, "required": True},
]

# ── Session 22E: beverage removed from Breakfast generation ───────────────────
# In-code override (ONE_POT_SLOTS precedent): the 36 Breakfast rows in
# meal_templates still carry main 0.70 / accompaniment 0.20 / beverage 0.10
# and are shadowed by this constant. Beverages are doctor-pinned or
# patient-logged only; the beverage 10% is redistributed 0.78/0.22.
BREAKFAST_SLOTS = [
    {"slot_type": "main_dish",     "calorie_pct": 0.78, "required": True},
    {"slot_type": "accompaniment", "calorie_pct": 0.22, "required": True},
]

# ── R-2: diet-type pool hierarchy + fallback (rebuild_spec §3.1) ──────────────
# DIET_TYPE_HIERARCHY: diet types tried, in order, as the PRIMARY pool for a
# patient's own diet preference (Levels 1-2 of the exhaustion cascade).
# Eggetarian merged into the Non-Veg pool per PD decision (Session 22, Jun 16):
# Non-Veg patients accept Eggetarian dishes as part of their own pool, not a
# fallback. Eggetarian patients still privilege their own dishes first.
DIET_TYPE_HIERARCHY = {
    "Vegetarian":     ["Vegetarian"],
    "Non-Vegetarian": ["Non-Vegetarian", "Eggetarian"],
    "Eggetarian":     ["Eggetarian", "Vegetarian"],
}
# DIET_TYPE_FALLBACK: NEW Level 3 — tried only after the primary pool
# (Levels 1-2) is fully exhausted. Vegetarian is always reachable since
# Vegetarian itself has no further fallback (empty list).
DIET_TYPE_FALLBACK = {
    "Non-Vegetarian": ["Vegetarian"],
    "Eggetarian":     ["Vegetarian"],
    "Vegetarian":     [],
}

class MealPlanTargets(BaseModel):
    """
    Container for all nutritional targets of a meal plan.
    """
    targets: Dict
    meal_targets: Dict
    user_data: Dict
    meal_history: Dict[str, set] = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.meal_history:
            self.meal_history = {
                "Breakfast": set(),
                "Lunch": set(),
                "Dinner": set()
            }


class MealGenerator:
    """
    Generates personalized meal plans based on user data and dietary requirements.
    """
    def __init__(self):
        # Initialize meal history tracking template
        self._default_history = {
            "Breakfast": set(),
            "Lunch": set(),
            "Dinner": set()
        }

    def _normalize_diet_label(self, raw_diet: str) -> str:
        if not isinstance(raw_diet, str):
            return "Vegetarian"  # Safe default
        cleaned = raw_diet.strip()
        lower = cleaned.lower()
        if lower == "vegetarian":
            return "Vegetarian"
        if "non" in lower:
            return "Non-Vegetarian"
        if "egg" in lower:
            return "Eggetarian"
        return cleaned.title()

    def _calculate_targets(self, user_data: Dict) -> Dict:
        height = user_data["height"]
        weight = user_data["weight"]
        age = user_data["age"]
        gender = user_data["gender"]
        activity_level = user_data["activity_level"]
        meal_plan_purchased = user_data.get("health_condition", "Healthy")
        health_condition = user_data.get("health_condition")

        bmi = calculate_bmi(height, weight)
        bmr = calculate_bmr(gender, weight, height, age)
        tdee = calculate_tdee(bmr, activity_level)
        # health_sub_goal: first health goal (e.g. 'weight_loss', 'muscle_gain') used to
        # pick the correct macro split for Gym-Friendly and Diabetic-Friendly conditions.
        raw_goals = user_data.get("health_goals") or []
        health_sub_goal = raw_goals[0].lower().replace(" ", "_") if raw_goals else None
        # medical_conditions: passed through for PCOS / Thyroid macro overrides
        medical_conditions = user_data.get("medical_conditions") or []
        protein, carbs, fiber, fat = calculate_macronutrients(
            tdee, meal_plan_purchased, health_sub_goal, medical_conditions
        )

        return {
            "bmi": bmi,
            "bmr": bmr,
            "tdee": tdee,
            "protein": protein,
            "carbs": carbs,
            "fiber": fiber,
            "fat": fat
        }

    async def generate_meal_plan(self, user_data: Dict, session: AsyncSession) -> Dict:
        if "start_date" not in user_data:
            user_data["start_date"] = datetime.now().strftime("%Y-%m-%d")
            
        targets = self._calculate_targets(user_data)

        effective_tdee = targets["tdee"] * 0.85

        split = DEFAULT_SPLIT
        patient_id = user_data.get("id")
        if patient_id:
            result = await session.execute(
                select(PatientMealConfig).where(PatientMealConfig.patient_id == int(patient_id))
            )
            config = result.scalar_one_or_none()
            if config and config.meal_split_override:
                o = config.meal_split_override
                split = {
                    "Breakfast": o["Breakfast"] / 100,
                    "Lunch":     o["Lunch"] / 100,
                    "Dinner":    o["Dinner"] / 100,
                }

            # Load patient dish preferences
            pref_result = await session.execute(
                select(PatientDishPreferences)
                .where(PatientDishPreferences.patient_id == int(patient_id))
            )
            prefs = pref_result.scalars().all()
            pinned_food_ids = {p.food_item_id for p in prefs if p.preference_type == "pin"}
            blocked_food_ids = {p.food_item_id for p in prefs if p.preference_type == "block"}
        else:
            pinned_food_ids = set()
            blocked_food_ids = set()

        _conditions = user_data.get("medical_conditions") or []
        patient_avoid_tags = frozenset(get_avoid_tags(_conditions))
        patient_prefer_tags = frozenset(get_prefer_tags(_conditions))

        meal_targets_calc = {
            "Breakfast": effective_tdee * split["Breakfast"],
            "Lunch":     effective_tdee * split["Lunch"],
            "Dinner":    effective_tdee * split["Dinner"],
        }

        ctx = MealPlanTargets(
            targets=targets,
            meal_targets=meal_targets_calc,
            user_data=user_data
        )

        meal_types = ["Breakfast", "Lunch", "Dinner"]
        organized_meals = []
        organized_combos = []          # R-2: 84 weekly_combos rows (4 per slot)
        combo0_ingredient_sources = [] # ingredient checklist built from combo-0 only
        
        start_date = datetime.strptime(user_data["start_date"], "%Y-%m-%d")
        
        region = user_data.get("region", "North")
        raw_diet = user_data.get("diet", "Vegetarian")
        diet_type = self._normalize_diet_label(raw_diet)
        plan_type = user_data.get("health_condition", "Healthy")

        meal_time_mapping = {
            "Breakfast": "Breakfast",
            "Lunch":     "Lunch",
            "Dinner":    "Dinner",
        }

        daily_used_ids  = set()   # HARD block — cleared every day, no same dish twice per day
        prior_seed      = frozenset(user_data.get("prior_used_food_ids") or [])
        weekly_used_ids = set(prior_seed)
        # Acts as SOFT preference — dropped at Level 2 if pool is exhausted.
        preferred_food_ids: frozenset = frozenset(user_data.get("preferred_food_ids") or frozenset())
        avoided_food_ids: frozenset = frozenset(user_data.get("avoided_food_ids") or frozenset())

        # ── Upgrade 1: Non-veg weekly budget pre-allocation ────────────────
        nonveg_assigned: set = set()   # (day_idx, db_meal_time) tuples
        if diet_type == "Non-Vegetarian":
            nonveg_budget = min(int(user_data.get("nonveg_meals_per_week", 3)), 4)
            candidate_slots = [
                (d, mt) for d in range(7) for mt in ["Lunch", "Dinner"]
            ]
            random.shuffle(candidate_slots)
            days_taken: set = set()
            for d, mt in candidate_slots:
                if len(nonveg_assigned) >= nonveg_budget:
                    break
                if d in days_taken:      # no two non-veg meals on same day
                    continue
                nonveg_assigned.add((d, mt))
                days_taken.add(d)
            logger.info(f"Non-veg budget: {nonveg_budget}, assigned slots: {nonveg_assigned}")

        # ── Allergy filtering: build lowercase set from patient's food_allergies ──
        raw_allergies: list = user_data.get("food_allergies") or []
        # Normalise: skip "none" / "None" — means patient has no allergies
        allergies: frozenset[str] = frozenset(
            a.strip().lower()
            for a in raw_allergies
            if a.strip().lower() not in ("", "none")
        )
        if allergies:
            logger.info(f"Allergy filter active for patient {user_data.get('id')}: {allergies}")

        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            daily_used_ids.clear()   # new day → today's slate is clean

            for meal_type in meal_types:
                if meal_type not in ctx.meal_targets:
                    continue
                
                db_meal_time = meal_time_mapping.get(meal_type)
                if not db_meal_time:
                    continue
                
                # ── Upgrade 1: per-slot diet type ────────────────────────
                if (day_offset, db_meal_time) in nonveg_assigned:
                    query_diet = "Non-Vegetarian"
                else:
                    query_diet = "Vegetarian"   # all non-assigned slots are veg

                # Fetch Template (use query_diet for template lookup)
                stmt = select(MealTemplate).where(
                    MealTemplate.meal_time == db_meal_time,
                    MealTemplate.region == region,
                    MealTemplate.diet_type == query_diet,
                    MealTemplate.plan_type == plan_type
                )
                result = await session.execute(stmt)
                template = result.scalars().first()

                if not template:
                    stmt_fallback = select(MealTemplate).where(
                        MealTemplate.meal_time == db_meal_time,
                        MealTemplate.diet_type == query_diet,
                        MealTemplate.plan_type == plan_type
                    )
                    result = await session.execute(stmt_fallback)
                    template = result.scalars().first()

                # If still no template for query_diet, try Vegetarian template
                if not template and query_diet != "Vegetarian":
                    stmt_veg = select(MealTemplate).where(
                        MealTemplate.meal_time == db_meal_time,
                        MealTemplate.region == region,
                        MealTemplate.diet_type == "Vegetarian",
                        MealTemplate.plan_type == plan_type
                    )
                    result = await session.execute(stmt_veg)
                    template = result.scalars().first()

                if not template:
                    logger.warning(f"No template found for {db_meal_time}, {query_diet}, {plan_type}")
                    continue

                # One-pot roll: Lunch/Dinner only, per slot per day. Standard
                # slots stay as a fallback attempt so a thin one_pot pool never
                # drops the whole meal.
                if db_meal_time == "Breakfast":
                    slot_lists = [BREAKFAST_SLOTS]   # Session 22E: shadows template.slots
                else:
                    slot_lists = [template.slots]
                    if random.random() < ONE_POT_PROBABILITY:
                        slot_lists.insert(0, ONE_POT_SLOTS)

                # R-2: 4 combos per slot (PD-1). combo_slot_used_ids accumulates
                # across the 4 runs so the same dish never repeats within this
                # slot's combos; daily_used_ids/weekly_used_ids stay frozen for
                # all 4 runs and only fold in combo-0's picks once the slot is done.
                for slots in slot_lists:
                    meal_target = ctx.meal_targets[meal_type]
                    combo_slot_used_ids: set = set()
                    all_combos_for_slot: list = []
                    combo0_lookup = None
                    slot_failed = False

                    for combo_idx in range(4):
                        dishes, ok = await self._fill_slot_dishes(
                            session, slots, query_diet, region, db_meal_time, plan_type,
                            meal_target,
                            daily_used_ids, weekly_used_ids, combo_slot_used_ids,
                            user_diet=diet_type,   # original user diet for breakfast-egg exception
                            allergies=allergies,
                            blocked_food_ids=frozenset(blocked_food_ids),
                            patient_avoid_tags=patient_avoid_tags,
                            patient_prefer_tags=patient_prefer_tags,
                            pinned_food_ids=pinned_food_ids,
                            preferred_food_ids=preferred_food_ids,
                            avoided_food_ids=avoided_food_ids,
                            combo0_lookup=combo0_lookup,
                            combo_idx=combo_idx,
                        )
                        if not ok or (combo_idx == 0 and not dishes):
                            logger.warning(f"Required slot not found for {meal_type} combo {combo_idx}")
                            slot_failed = True
                            break

                        combo_slot_used_ids.update(d["food_id"] for d in dishes)
                        all_combos_for_slot.append(dishes)
                        if combo_idx == 0:
                            combo0_lookup = {d["slot_type"]: d for d in dishes}

                    if slot_failed or not all_combos_for_slot:
                        continue  # try next slot list (e.g. one_pot → standard template)

                    weekly_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])
                    daily_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])

                    ingredients_scaling: dict = {}
                    for dish in all_combos_for_slot[0]:
                        for ing in dish["ingredients"]:
                            ingredients_scaling[ing["name"]] = round(
                                ingredients_scaling.get(ing["name"], 0) + ing["amount_g"], 2
                            )
                    combo0_ingredient_sources.append({"Ingredients Scaling": ingredients_scaling})

                    for combo_idx, combo_dishes in enumerate(all_combos_for_slot):
                        organized_combos.append({
                            "slot_date": date_str,
                            "meal_type": meal_type,
                            "combo_index": combo_idx,
                            "slot_composition": [d["slot_type"] for d in combo_dishes],
                            "total_calories": round(sum(d["scaled_calories"] for d in combo_dishes), 2),
                            "dishes": combo_dishes,
                        })
                    break

        ingredient_checklist = self.generate_ingredient_checklist(combo0_ingredient_sources)

        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            elif isinstance(obj, np.generic):
                return obj.item()
            return obj

        checklist_records = (
            ingredient_checklist.to_dict('records')
            if hasattr(ingredient_checklist, 'to_dict')
            else (ingredient_checklist if isinstance(ingredient_checklist, list) else [])
        )

        return convert_numpy({
            "meals": organized_meals,        # [] for v2 — kept for backward compat
            "combos": organized_combos,      # 84 combo dicts (4 per slot) — v2
            "ingredient_checklist": checklist_records,
            "used_food_ids": list(weekly_used_ids - prior_seed),
            # Only IDs picked THIS generation — never the seed. Persisting the
            # accumulated union snowballs the exclusion set across regenerations
            # until the candidate pool is exhausted and variety collapses.
        })

    @staticmethod
    def _build_dish_ingredients(food_item: FoodItem, factor: float) -> list:
        """Per-dish ingredient list with portion-scaled gram amounts (pantry staples skipped)."""
        dish_ingredients: list = []
        try:
            for _ing in (food_item.ingredients or []):
                if not isinstance(_ing, dict):
                    continue
                if _ing.get("is_pantry_staple"):
                    continue
                _name = _ing.get("name") or ""
                if not _name:
                    continue
                _raw = _ing.get("amount_g") or _ing.get("quantity") or 0
                try:
                    _amt = round(float(_raw) * factor, 1)
                except (ValueError, TypeError):
                    _amt = 0.0
                if _amt > 0:
                    dish_ingredients.append({"name": _name, "amount_g": _amt})
        except Exception as _exc:
            logger.warning(f"dish_ingredients build failed for food_item {food_item.id}: {_exc}")
            dish_ingredients = []
        return dish_ingredients

    @staticmethod
    def _derive_diet_label(dishes: list) -> str:
        """Slot label derived from the actual dishes, not the query diet."""
        diet_types = {d.get("diet_type", "Vegetarian") for d in dishes}
        if "Non-Vegetarian" in diet_types:
            return "Non-Vegetarian"
        if "Eggetarian" in diet_types:
            return "Eggetarian"
        return "Vegetarian"

    # ── Upgrade 2: Diet-type fallback chain ────────────────────────────────────
    @staticmethod
    def _diet_fallback_chain(user_diet: str, meal_time: str) -> list[str]:
        """Return ordered list of diet_types to try for a given slot."""
        if meal_time == "Breakfast":
            if user_diet in ("Non-Vegetarian", "Eggetarian"):
                return ["Eggetarian", "Vegetarian"]
            return ["Vegetarian"]
        # Lunch / Dinner
        if user_diet == "Non-Vegetarian":
            return ["Non-Vegetarian", "Eggetarian", "Vegetarian"]
        if user_diet == "Eggetarian":
            return ["Eggetarian", "Vegetarian"]
        return ["Vegetarian"]

    @staticmethod
    def _assemble_dish(food_item: FoodItem, target_cal: float) -> dict:
        """Build the per-dish output record (R-2 combo schema).

        Adds scaled_calories/factor/diet_type on top of the v1 dish dict —
        these are what generate_meal_plan's combo-assembly loop reads
        (d["food_id"], d["slot_type"], d["scaled_calories"], d["ingredients"]).
        """
        cal_per_serving = float(food_item.cal_per_serving)
        factor = target_cal / cal_per_serving if cal_per_serving > 0 else 1.0
        factor = max(0.5, min(3.0, factor))
        return {
            "food_id":         food_item.id,
            "recipe_name":     food_item.recipe_name,
            "slot_type":       food_item.slot_type,
            "diet_type":       food_item.diet_type,
            "calories":        cal_per_serving,
            "scaled_calories": round(cal_per_serving * factor, 2),
            "factor":          round(factor, 3),
            "protein":         round(float(food_item.protein_per_serving) * factor, 2),
            "carbs":           round(float(food_item.carbs_per_serving) * factor, 2),
            "fat":             round(float(food_item.fat_per_serving) * factor, 2),
            "fiber":           round(float(food_item.fiber_per_serving) * factor, 2) if food_item.fiber_per_serving else 0.0,
            "ingredients":     MealGenerator._build_dish_ingredients(food_item, factor),
        }

    async def _pick_for_slot(
        self,
        session: AsyncSession,
        slot_type: str,
        diet_type: str,
        region: str,
        meal_time: str,
        plan_type: str,
        target_cal: float,
        daily_used_ids: set,
        weekly_used_ids: set,
        combo_slot_used_ids: set,
        allergies: frozenset = frozenset(),
        blocked_food_ids: frozenset = frozenset(),
        patient_avoid_tags: frozenset = frozenset(),
        patient_prefer_tags: frozenset = frozenset(),
        pinned_food_ids: frozenset = frozenset(),
        preferred_food_ids: frozenset = frozenset(),
        avoided_food_ids: frozenset = frozenset(),
    ) -> Optional[FoodItem]:
        """
        R-2 pool query for one combo's one slot. Pin is a PREFERENCE SIGNAL
        only (rebuild_spec §3.4) — pinned_food_ids boosts prefer_sort, never
        force-injects.

        Levels 1-2 — diet_type's own pool (DIET_TYPE_HIERARCHY), weekly memory
        excluded then dropped. Level 3 (NEW) — DIET_TYPE_FALLBACK diet types,
        weekly memory dropped. combo_slot_used_ids/daily_used_ids are HARD
        blocks at every level — never dropped (no duplicate dish within this
        slot's 4 combos, none twice in the same day).
        """
        region_sort = sa_case((FoodItem.region_tags.any(region), 0), else_=1)
        cal_sort = sa_func.abs(FoodItem.cal_per_serving - target_cal) if target_cal > 0 else FoodItem.id
        prefer_sort = or_(
            *[FoodItem.prefer_tags.contains([tag]) for tag in patient_prefer_tags],
            FoodItem.id.in_(pinned_food_ids),
            FoodItem.id.in_(preferred_food_ids) if preferred_food_ids else false(),
        ).desc()

        def base_stmt(try_diet: str, include_weekly: bool):
            s = select(FoodItem).where(
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == try_diet,
                FoodItem.meal_time_tags.any(meal_time),
                FoodItem.is_verified == True,  # noqa: E712 — Change 1: never serve unverified/test dishes
            )
            if target_cal > 0:
                s = s.where(FoodItem.cal_per_serving.between(target_cal / 3.0, target_cal / 0.5))
            excluded = set(daily_used_ids) | set(combo_slot_used_ids)
            if include_weekly:
                excluded |= set(weekly_used_ids)
            if excluded:
                s = s.where(FoodItem.id.notin_(excluded))
            if blocked_food_ids:
                s = s.where(FoodItem.id.notin_(blocked_food_ids))
            if avoided_food_ids:
                s = s.where(FoodItem.id.notin_(avoided_food_ids))
            if patient_avoid_tags:
                s = s.where(not_(or_(*[FoodItem.avoid_tags.contains([tag]) for tag in patient_avoid_tags])))
            return s.order_by(prefer_sort, region_sort, cal_sort).limit(10)

        def _is_allergenic(item: FoodItem) -> bool:
            if not allergies:
                return False
            for ing in (item.ingredients or []):
                ing_name = str(ing.get("name") or "").lower()
                if any(allergen in ing_name for allergen in allergies):
                    return True
            return False

        def _pick(items: list) -> Optional[FoodItem]:
            for item in items:
                if slot_type in PROTECTED_SLOTS:
                    name_lower = item.recipe_name.lower()
                    if any(pat in name_lower for pat in BLOCKLIST_PATTERNS):
                        continue
                if _is_allergenic(item):
                    continue
                return item
            return None

        async def fetch(s) -> list:
            return (await session.execute(s)).scalars().all()

        primary_chain = DIET_TYPE_HIERARCHY.get(diet_type, [diet_type])

        # Level 1 — primary pool, weekly memory excluded (soft variety preference)
        for try_diet in primary_chain:
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=True)))) is not None:
                return picked

        # Level 2 — primary pool, weekly memory dropped (weekly exclusion exhausted)
        for try_diet in primary_chain:
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=False)))) is not None:
                return picked

        # Level 3 (NEW) — fallback diet types (e.g. Vegetarian for Non-Veg/Eggetarian)
        for try_diet in DIET_TYPE_FALLBACK.get(diet_type, []):
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=False)))) is not None:
                return picked

        return None

    async def _fill_slot_dishes(
        self,
        session: AsyncSession,
        slots: list,
        query_diet: str,
        region: str,
        meal_time: str,
        plan_type: str,
        meal_target: float,
        daily_used_ids: set,
        weekly_used_ids: set,
        combo_slot_used_ids: set,
        user_diet: str = None,
        allergies: frozenset = frozenset(),
        blocked_food_ids: frozenset = frozenset(),
        patient_avoid_tags: frozenset = frozenset(),
        patient_prefer_tags: frozenset = frozenset(),
        pinned_food_ids: frozenset = frozenset(),
        preferred_food_ids: frozenset = frozenset(),
        avoided_food_ids: frozenset = frozenset(),
        combo0_lookup: Optional[dict] = None,
        combo_idx: int = 0,
    ) -> tuple[list, bool]:
        """
        Fill one combo's dishes for one slot list (PD-1 — 4 combos/slot).

        Returns (dishes, ok). ok=False means a REQUIRED slot_type came up
        empty at every fallback level including Level 4 duplication — caller
        abandons this slot_list attempt (e.g. one_pot → falls back to the
        standard template).

        Level 4 (NEW, last resort): if combo_idx > 0 and the slot is still
        empty after Levels 1-3, reuse combo-0's dish for this slot_type
        verbatim (logged as a warning) rather than failing the whole slot.
        Never raises.
        """
        dishes: list = []
        # Breakfast uses user_diet so the breakfast-egg exception still fires
        # even though query_diet is forced to Vegetarian for unassigned slots.
        # Lunch/Dinner honor query_diet so the non-veg weekly budget holds.
        chain_diet = user_diet if (meal_time == "Breakfast" and user_diet is not None) else query_diet

        for slot in slots:
            slot_type = slot["slot_type"]
            required = slot.get("required", True)
            target_cal = meal_target * slot["calorie_pct"]

            food_item = await self._pick_for_slot(
                session, slot_type, chain_diet, region, meal_time, plan_type, target_cal,
                daily_used_ids, weekly_used_ids, combo_slot_used_ids,
                allergies=allergies,
                blocked_food_ids=blocked_food_ids,
                patient_avoid_tags=patient_avoid_tags,
                patient_prefer_tags=patient_prefer_tags,
                pinned_food_ids=pinned_food_ids,
                preferred_food_ids=preferred_food_ids,
                avoided_food_ids=avoided_food_ids,
            )

            if food_item is not None:
                dishes.append(self._assemble_dish(food_item, target_cal))
                continue

            # Level 4 — pool exhausted at every diet level; duplicate combo-0's
            # pick for this slot_type rather than dropping the slot.
            if combo0_lookup and slot_type in combo0_lookup:
                logger.warning(
                    f"Pool exhausted for slot_type={slot_type} diet={chain_diet} "
                    f"combo_idx={combo_idx} — reusing combo-0 dish "
                    f"food_id={combo0_lookup[slot_type]['food_id']}"
                )
                dishes.append(dict(combo0_lookup[slot_type]))
                continue

            if required:
                logger.warning(
                    f"Required slot_type={slot_type} not found (diet={chain_diet}, "
                    f"combo_idx={combo_idx}) — no Level-4 fallback available (combo-0 itself)"
                )
                return dishes, False
            # optional slot, no candidate, no combo-0 fallback to duplicate — skip it

        return dishes, True

    def generate_ingredient_checklist(self, meals):
        all_ingredients = {}
        for meal in meals:
            ingredients_scaled = meal.get("Ingredients Scaling", {})
            for ingredient, amount in ingredients_scaled.items():
                # ── Upgrade 5: normalize to title case before grouping ────
                normalized = ingredient.strip().title()
                if normalized in all_ingredients:
                    all_ingredients[normalized] += amount
                else:
                    all_ingredients[normalized] = amount

        # ── Upgrade 3B: skip pantry staples ───────────────────────────────
        # (raw ingredient dicts with is_pantry_staple are in Ingredients Scaling
        #  but here we only have name→total_g. Pantry filtering happens at
        #  the Ingredients Scaling build step — see generate_meal_plan.)

        ingredients_df = pd.DataFrame([
            {"Ingredient": k, "Total Amount (g)": round(v, 2)}
            for k, v in all_ingredients.items()
        ])

        if ingredients_df.empty:
            return pd.DataFrame()

        return ingredients_df.sort_values("Total Amount (g)", ascending=False)

# Singleton instance
meal_generator = MealGenerator()
