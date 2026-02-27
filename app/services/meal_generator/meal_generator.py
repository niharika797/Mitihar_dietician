import logging
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import MealTemplate, FoodItem
from .calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

logger = logging.getLogger(__name__)

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
        protein, carbs, fiber, fat = calculate_macronutrients(tdee, meal_plan_purchased, health_condition)

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
            "Breakfast": "Breakfast",
            "Lunch": "Lunch",
            "Dinner": "Dinner",
            "MorningSnacks": "Morning_Snack",
            "EveningSnacks": "Morning_Snack",
        }

        used_food_ids = set()

        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            for meal_type in meal_types:
                if meal_type not in ctx.meal_targets:
                    continue
                
                db_meal_time = meal_time_mapping.get(meal_type)
                if not db_meal_time:
                    continue
                
                # Fetch Template
                stmt = select(MealTemplate).where(
                    MealTemplate.meal_time == db_meal_time,
                    MealTemplate.region == region,
                    MealTemplate.diet_type == diet_type,
                    MealTemplate.plan_type == plan_type
                )
                result = await session.execute(stmt)
                template = result.scalars().first()

                if not template:
                    stmt_fallback = select(MealTemplate).where(
                        MealTemplate.meal_time == db_meal_time,
                        MealTemplate.diet_type == diet_type,
                        MealTemplate.plan_type == plan_type
                    )
                    result = await session.execute(stmt_fallback)
                    template = result.scalars().first()

                if not template:
                    logger.warning(f"No template found for {db_meal_time}, {diet_type}, {plan_type}")
                    continue

                if True:  # single meal per day per meal_type
                    meal_option = {
                        "Date": date_str,
                        "Meal Type": meal_type,
                        "Diet Type": diet_type,
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
                            session, slot_type, diet_type, region, db_meal_time, plan_type, used_food_ids
                        )
                        if not food_item:
                            if required:
                                logger.warning(f"Required slot {slot_type} not found for {meal_type}")
                                slot_failed = True
                                break
                            else:
                                continue
                        
                        used_food_ids.add(food_item.id)

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
                            amt = float(ing["amount_g"]) * factor
                            meal_option["Ingredients Scaling"][name] = round(meal_option["Ingredients Scaling"].get(name, 0) + amt, 2)
                    
                    if not slot_failed and meal_option["Menu Names"]:
                        meal_option["Menu Names"] = " + ".join(meal_option["Menu Names"])
                        meal_option["Total Calories"] = round(meal_option["Total Calories"], 2)
                        meal_option["Total Protein"] = round(meal_option["Total Protein"], 2)
                        meal_option["Total Carbs"] = round(meal_option["Total Carbs"], 2)
                        meal_option["Total Fiber"] = round(meal_option["Total Fiber"], 2)
                        meal_option["Total Fat"] = round(meal_option["Total Fat"], 2)
                        organized_meals.append(meal_option)

        used_food_ids.clear()

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
            "ingredient_checklist": checklist_records
        })

    async def _find_food_item(self, session: AsyncSession, slot_type: str, diet_type: str, region: str, meal_time: str, plan_type: str, used_ids: set) -> Optional[FoodItem]:
        # Try finding non-used items in preferred region
        stmt = select(FoodItem).where(
            FoodItem.slot_type == slot_type,
            FoodItem.diet_type == diet_type,
            FoodItem.region_tags.any(region),
            FoodItem.meal_time_tags.any(meal_time),
            FoodItem.plan_type_tags.any(plan_type)
        )
        if used_ids:
            stmt = stmt.where(FoodItem.id.notin_(used_ids))
        
        result = await session.execute(stmt)
        items = result.scalars().all()

        if not items:
            # Fallback 1: Ignore exact region, but exclude used_ids
            stmt = select(FoodItem).where(
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == diet_type,
                FoodItem.meal_time_tags.any(meal_time),
                FoodItem.plan_type_tags.any(plan_type)
            )
            if used_ids:
                stmt = stmt.where(FoodItem.id.notin_(used_ids))
            result = await session.execute(stmt)
            items = result.scalars().all()
        
        if not items:
            # Fallback 2: Reset history constraints
            stmt = select(FoodItem).where(
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == diet_type,
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

        if items:
            return random.choice(items)
        return None

    def generate_ingredient_checklist(self, meals):
        all_ingredients = {}
        for meal in meals:
            ingredients_scaled = meal.get("Ingredients Scaling", {})
            for ingredient, amount in ingredients_scaled.items():
                if ingredient in all_ingredients:
                    all_ingredients[ingredient] += amount
                else:
                    all_ingredients[ingredient] = amount

        ingredients_df = pd.DataFrame([
            {"Ingredient": k, "Total Amount (g)": round(v, 2)}
            for k, v in all_ingredients.items()
        ])

        if ingredients_df.empty:
            return pd.DataFrame()

        return ingredients_df.sort_values("Total Amount (g)", ascending=False)

# Singleton instance
meal_generator = MealGenerator()
