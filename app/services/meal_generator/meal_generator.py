import logging
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel

from sqlalchemy import select, case as sa_case, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import MealTemplate, FoodItem
from .calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

logger = logging.getLogger(__name__)

# ── Upgrade 4: Slot-quality blocklist ─────────────────────────────────────────
BLOCKLIST_PATTERNS = [
    "chutney", "powder", "masala powder", "pickle", "achar",
    "papad", "papadum", "murabba", "jam", "sauce", "dip",
]
PROTECTED_SLOTS = ["grain", "dal_protein", "main_dish", "sabzi"]

class MealPlanTargets(BaseModel):
    """
    Container for all nutritional targets of a meal plan.
    """
    targets: Dict
    meal_targets: Dict
    protein_targets: Dict
    carb_targets: Dict
    fiber_targets: Dict
    fat_targets: Dict
    user_data: Dict
    meal_history: Dict[str, set] = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.meal_history:
            self.meal_history = {
                "Breakfast": set(),
                "MorningSnacks": set(),
                "Lunch": set(),
                "EveningSnacks": set(),
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
            "MorningSnacks": set(),
            "Lunch": set(),
            "EveningSnacks": set(),
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

    def _calculate_meal_targets(self, user_data: Dict, targets: Dict) -> Dict:
        tdee = targets["tdee"]
        plan = user_data.get("health_condition", "Healthy")
        if plan == "Healthy":
            return {
                "Breakfast": tdee * 0.25,
                "MorningSnacks": tdee * 0.05,
                "Lunch": tdee * 0.30,
                "EveningSnacks": tdee * 0.05,
                "Dinner": tdee * 0.25,
            }
        elif plan == "Gym-Friendly":
            return {
                "Breakfast": tdee * 0.25,
                "MorningSnacks": tdee * 0.05,
                "Lunch": tdee * 0.35,
                "EveningSnacks": tdee * 0.05,   
                "Dinner": tdee * 0.30,
            }
        else:  # Diabetic-Friendly
            return {
                    "Breakfast": tdee * 0.25,
                    "MorningSnacks": tdee * 0.05,
                    "Lunch": tdee * 0.35,
                    "EveningSnacks": tdee * 0.05,
                    "Dinner": tdee * 0.30,
            }

    def _calculate_protein_targets(self, user_data: Dict, targets: Dict) -> Dict:
        protein = targets["protein"]
        plan = user_data.get("health_condition", "Healthy")
        if plan == "Healthy":
            return {
                "Breakfast": protein * 0.25,
                "MorningSnacks": protein * 0.10,
                "Lunch": protein * 0.30,
                "EveningSnacks": protein * 0.10,
                "Dinner": protein * 0.25,
            }
        elif plan == "Gym-Friendly":
            return {
                "Breakfast": protein * 0.30,
                "MorningSnacks": protein * 0.10,
                "Lunch": protein * 0.25,
                "EveningSnacks": protein * 0.10,
                "Dinner": protein * 0.25,
            }
        else:  # Diabetic-Friendly
            return {
                "Breakfast": protein * 0.30,
                "MorningSnacks": protein * 0.10,
                "Lunch": protein * 0.25,
                "EveningSnacks": protein * 0.10,
                "Dinner": protein * 0.25,
            }

    def _calculate_carb_targets(self, user_data: Dict, targets: Dict) -> Dict:
        carbs = targets["carbs"]
        plan = user_data.get("health_condition", "Healthy")
        if plan == "Healthy":
            return {
                "Breakfast": carbs * 0.25,
                "MorningSnacks": carbs * 0.10,
                "Lunch": carbs * 0.30,
                "EveningSnacks": carbs * 0.10,
                "Dinner": carbs * 0.25,
            }
        elif plan == "Gym-Friendly":
            return {
                    "Breakfast": carbs * 0.30,
                "MorningSnacks": carbs * 0.10,
                "Lunch": carbs * 0.25,
                "EveningSnacks": carbs * 0.10,
                "Dinner": carbs * 0.30,
            }
        else:  # Diabetic-Friendly
            return {
                "Breakfast": carbs * 0.30,
                "MorningSnacks": carbs * 0.10,
                "Lunch": carbs * 0.25,
                "EveningSnacks": carbs * 0.10,
                "Dinner": carbs * 0.30,
            }

    def _calculate_fiber_targets(self, user_data: Dict, targets: Dict) -> Dict:
        fiber = targets["fiber"]
        plan = user_data.get("health_condition", "Healthy")
        if plan == "Healthy":
            return {
                "Breakfast": fiber * 0.25,
                "MorningSnacks": fiber * 0.10,
                "Lunch": fiber * 0.30,
                "EveningSnacks": fiber * 0.10,
                "Dinner": fiber * 0.25,
            }
        elif plan == "Gym-Friendly":
            return {
                "Breakfast": fiber * 0.30,
                "MorningSnacks": fiber * 0.10,
                "Lunch": fiber * 0.35,
                "EveningSnacks": fiber * 0.10, 
                "Dinner": fiber * 0.30,
            }
        else:  # Diabetic-Friendly
            return {
                "Breakfast": fiber * 0.30,
                "MorningSnacks": fiber * 0.10,
                "Lunch": fiber * 0.35,
                "EveningSnacks": fiber * 0.10,
                "Dinner": fiber * 0.30,
            }

    def _calculate_fat_targets(self, user_data: Dict, targets: Dict) -> Dict:
        fat = targets["fat"]
        plan = user_data.get("health_condition", "Healthy")
        if plan == "Healthy":
            return {
                "Breakfast": fat * 0.25,
                "MorningSnacks": fat * 0.10,
                "Lunch": fat * 0.30,
                "EveningSnacks": fat * 0.10,
                "Dinner": fat * 0.25,
            }
        elif plan == "Gym-Friendly":
            return {
                "Breakfast": fat * 0.30,
                "MorningSnacks": fat * 0.10,
                "Lunch": fat * 0.35,
                "EveningSnacks": fat * 0.10,
                "Dinner": fat * 0.30, 
            }
        else:  # Diabetic-Friendly
            return {
                "Breakfast": fat * 0.25,
                "MorningSnacks": fat * 0.10,
                "Lunch": fat * 0.30,
                "EveningSnacks": fat * 0.10,
                "Dinner": fat * 0.25,
            }

    async def generate_meal_plan(self, user_data: Dict, session: AsyncSession) -> Dict:
        if "start_date" not in user_data:
            user_data["start_date"] = datetime.now().strftime("%Y-%m-%d")
            
        targets = self._calculate_targets(user_data)
        ctx = MealPlanTargets(
            targets=targets,
            meal_targets=self._calculate_meal_targets(user_data, targets),
            protein_targets=self._calculate_protein_targets(user_data, targets),
            carb_targets=self._calculate_carb_targets(user_data, targets),
            fiber_targets=self._calculate_fiber_targets(user_data, targets),
            fat_targets=self._calculate_fat_targets(user_data, targets),
            user_data=user_data
        )

        meal_types = ["Breakfast", "MorningSnacks", "Lunch", "EveningSnacks", "Dinner"]
        organized_meals = []
        
        start_date = datetime.strptime(user_data["start_date"], "%Y-%m-%d")
        
        region = user_data.get("region", "North")
        raw_diet = user_data.get("diet", "Vegetarian")
        diet_type = self._normalize_diet_label(raw_diet)
        plan_type = user_data.get("health_condition", "Healthy")

        # Map morning/evening snacks to Morning_Snack for DB querying
        meal_time_mapping = {
            "Breakfast":    "Breakfast",
            "Lunch":        "Lunch",
            "Dinner":       "Dinner",
            "MorningSnacks": "Morning_Snack",
            "EveningSnacks": "Evening_Snack",   # separate pool from morning snack
        }

        daily_used_ids  = set()   # HARD block — cleared every day, no same dish twice per day
        weekly_used_ids = set(user_data.get("prior_used_food_ids") or [])
        # Seeded from last 2 plans' used IDs for cross-week variety.
        # Acts as SOFT preference — dropped at Level 2 if pool is exhausted.

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

                if True:  # single meal per day per meal_type
                    meal_option = {
                        "Date": date_str,
                        "Meal Type": meal_type,
                        "Diet Type": query_diet,
                        "Region": region,
                        "Total Calories": 0.0,
                        "Total Protein": 0.0,
                        "Total Carbs": 0.0,
                        "Total Fiber": 0.0,
                        "Total Fat": 0.0,
                        "Menu Names": [],
                        "Ingredients Scaling": {},
                    }
                    
                    slot_failed = False
                    for slot in template.slots:
                        slot_type = slot["slot_type"]
                        required = slot.get("required", True)
                        cal_pct = slot["calorie_pct"]

                        target_cal = ctx.meal_targets[meal_type] * cal_pct

                        food_item = await self._find_food_item(
                            session, slot_type, query_diet, region, db_meal_time, plan_type,
                            daily_used_ids, weekly_used_ids, target_cal,
                            user_diet=diet_type,   # original user diet for breakfast-egg exception
                            allergies=allergies,
                        )
                        if not food_item:
                            if required:
                                logger.warning(f"Required slot {slot_type} not found for {meal_type}")
                                slot_failed = True
                                break
                            else:
                                continue
                        
                        daily_used_ids.add(food_item.id)
                        weekly_used_ids.add(food_item.id)

                        if float(food_item.cal_per_serving) > 0:
                            factor = target_cal / float(food_item.cal_per_serving)
                        else:
                            factor = 1.0
                        
                        factor = max(0.5, min(3.0, factor))

                        meal_option["Menu Names"].append(food_item.recipe_name)
                        meal_option["Total Calories"] += float(food_item.cal_per_serving) * factor
                        meal_option["Total Protein"] += float(food_item.protein_per_serving) * factor
                        meal_option["Total Carbs"] += float(food_item.carbs_per_serving) * factor
                        meal_option["Total Fiber"] += float(food_item.fiber_per_serving) * factor
                        meal_option["Total Fat"] += float(food_item.fat_per_serving) * factor

                        for ing in food_item.ingredients:
                            name = ing["name"]
                            # ── Upgrade 3B: skip pantry staples ──────────
                            if ing.get("is_pantry_staple"):
                                continue
                            raw_amt = ing.get("amount_g") or ing.get("quantity") or 0
                            try:
                                amt = float(raw_amt) * factor
                            except (ValueError, TypeError):
                                amt = 0.0
                            meal_option["Ingredients Scaling"][name] = round(meal_option["Ingredients Scaling"].get(name, 0) + amt, 2)
                    
                    if not slot_failed and meal_option["Menu Names"]:
                        meal_option["Menu Names"] = " + ".join(meal_option["Menu Names"])
                        meal_option["Total Calories"] = round(meal_option["Total Calories"], 2)
                        meal_option["Total Protein"] = round(meal_option["Total Protein"], 2)
                        meal_option["Total Carbs"] = round(meal_option["Total Carbs"], 2)
                        meal_option["Total Fiber"] = round(meal_option["Total Fiber"], 2)
                        meal_option["Total Fat"] = round(meal_option["Total Fat"], 2)
                        organized_meals.append(meal_option)

        ingredient_checklist = self.generate_ingredient_checklist(organized_meals)

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
            "meals": organized_meals,
            "ingredient_checklist": checklist_records,
            "used_food_ids": list(weekly_used_ids),
            # weekly_used_ids accumulates all food_item IDs used this generation.
            # Persisted by diet_plan_service so next generation can seed from here.
        })

    # ── Upgrade 2: Diet-type fallback chain ────────────────────────────────────
    @staticmethod
    def _diet_fallback_chain(user_diet: str, meal_time: str) -> list[str]:
        """Return ordered list of diet_types to try for a given slot."""
        if meal_time in ("Breakfast", "Morning_Snack", "Evening_Snack"):
            if user_diet in ("Non-Vegetarian", "Eggetarian"):
                return ["Eggetarian", "Vegetarian"]
            return ["Vegetarian"]
        # Lunch / Dinner
        if user_diet == "Non-Vegetarian":
            return ["Non-Vegetarian", "Eggetarian", "Vegetarian"]
        if user_diet == "Eggetarian":
            return ["Eggetarian", "Vegetarian"]
        return ["Vegetarian"]

    async def _find_food_item(
        self,
        session: AsyncSession,
        slot_type: str,
        diet_type: str,
        region: str,
        meal_time: str,
        plan_type: str,
        daily_used_ids: set,
        weekly_used_ids: set,
        target_cal: float = 0,
        user_diet: str = None,       # original user diet — used for breakfast-egg fallback
        allergies: frozenset = frozenset(),  # lowercase allergen strings to exclude
    ) -> Optional[FoodItem]:
        """
        4-level waterfall wrapped with a diet-type fallback chain.
        BETWEEN and daily_used_ids are NEVER dropped.

        user_diet: the patient's original diet preference (Non-Vegetarian / Eggetarian).
                   diet_type: the per-slot override (query_diet).
                   The fallback chain uses user_diet for breakfast so Non-Veg/Eggetarian
                   users can still get egg dishes at Breakfast even though query_diet="Vegetarian".
        """
        # Use user_diet for chain decisions so breakfast-egg exception fires correctly.
        # Fall back to diet_type if user_diet not provided (backward compat).
        chain_diet = user_diet if user_diet is not None else diet_type
        diet_chain = self._diet_fallback_chain(chain_diet, meal_time)

        for try_diet in diet_chain:
            result = await self._find_food_item_single_diet(
                session, slot_type, try_diet, region, meal_time, plan_type,
                daily_used_ids, weekly_used_ids, target_cal,
                allergies=allergies,
            )
            if result is not None:
                return result

        return None

    async def _find_food_item_single_diet(
        self,
        session: AsyncSession,
        slot_type: str,
        diet_type: str,
        region: str,
        meal_time: str,
        plan_type: str,
        daily_used_ids: set,
        weekly_used_ids: set,
        target_cal: float = 0,
        allergies: frozenset = frozenset(),
    ) -> Optional[FoodItem]:
        """
        2-level lookup with region as a sort-priority (not a hard filter).

        Level 1 — full filters + weekly memory:
          Candidates ordered: regional items first, then by calorie proximity.
          weekly_used_ids excluded (soft preference — cross-week variety).

        Level 2 — drop weekly memory:
          Same ordering, weekly exclusion removed.
          daily_used_ids hard block is NEVER dropped.

        This replaces the old 4-level waterfall where region was a hard filter,
        causing silent fallback to Level 4 (no region, no memory) for most queries
        on the ~2k dataset.
        """
        # ── region-priority sort: regional items bubble to top ──────────────
        region_sort = sa_case((FoodItem.region_tags.any(region), 0), else_=1)
        cal_sort    = sa_func.abs(FoodItem.cal_per_serving - target_cal) if target_cal > 0 else FoodItem.id

        def base_stmt():
            s = select(FoodItem).where(
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == diet_type,
                FoodItem.meal_time_tags.any(meal_time),
                FoodItem.plan_type_tags.any(plan_type),
            )
            if target_cal > 0:
                s = s.where(FoodItem.cal_per_serving.between(target_cal / 3.0, target_cal / 0.5))
            if daily_used_ids:
                s = s.where(FoodItem.id.notin_(daily_used_ids))
            return s.order_by(region_sort, cal_sort).limit(10)

        def _is_allergenic(item: FoodItem) -> bool:
            if not allergies:
                return False
            for ing in (item.ingredients or []):
                ing_name = str(ing.get("name") or "").lower()
                if any(allergen in ing_name for allergen in allergies):
                    return True
            return False

        def _pick(items: list) -> Optional[FoodItem]:
            """Apply blocklist + allergy filtering. Return first valid candidate."""
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

        # Level 1 — exclude weekly memory (soft variety preference)
        s = base_stmt()
        if weekly_used_ids:
            s = s.where(FoodItem.id.notin_(weekly_used_ids))
        if (picked := _pick(await fetch(s))) is not None:
            return picked

        # Level 2 — drop weekly memory (weekly exclusion exhausted)
        s = base_stmt()
        if (picked := _pick(await fetch(s))) is not None:
            return picked

        return None

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
