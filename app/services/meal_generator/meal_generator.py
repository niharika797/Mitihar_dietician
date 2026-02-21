from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pydantic import BaseModel  # Add this import
import pandas as pd
import random
import json
import logging

logger = logging.getLogger(__name__)

from .data_loader import load_normalized_dataset
from .calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

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
            "Dinner": set()
        }

    def _calculate_targets(self, user_data: Dict) -> Dict:
        """
        Calculates BMI, BMR, TDEE, and macronutrient targets based on user data.
        """
        height = user_data["height"]
        weight = user_data["weight"]
        age = user_data["age"]
        gender = user_data["gender"]
        activity_level = user_data["activity_level"]
        meal_plan_purchased = user_data["meal_plan_purchased"]
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
        """
        Calculates calorie targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing calorie targets for each meal (Breakfast, MorningSnacks, Lunch, Dinner, EveningSnacks).
        """
        tdee = targets["tdee"]
        
        if user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": tdee * 0.25,
                "MorningSnacks": tdee * 0.05,
                "Lunch": tdee * 0.30,
                "EveningSnacks": tdee * 0.05,
                "Dinner": tdee * 0.25,
            }
        elif user_data["meal_plan_purchased"] == "Gym-Friendly":
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
        """
        Calculates protein targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing protein targets for each meal.
        """
        protein = targets["protein"]
        if user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": protein * 0.25,
                "MorningSnacks": protein * 0.10,
                "Lunch": protein * 0.30,
                "EveningSnacks": protein * 0.10,
                "Dinner": protein * 0.25,
            }
        elif user_data["meal_plan_purchased"] == "Gym-Friendly":
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
        """
        Calculates carbohydrate targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing carbohydrate targets for each meal.
        """
        carbs = targets["carbs"]
        if user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": carbs * 0.25,
                "MorningSnacks": carbs * 0.10,
                "Lunch": carbs * 0.30,
                "EveningSnacks": carbs * 0.10,
                "Dinner": carbs * 0.25,
            }
        elif user_data["meal_plan_purchased"] == "Gym-Friendly":
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
        """
        Calculates fiber targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing fiber targets for each meal.
        """
        fiber = targets["fiber"]
        if user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": fiber * 0.25,
                "MorningSnacks": fiber * 0.10,
                "Lunch": fiber * 0.30,
                "EveningSnacks": fiber * 0.10,
                "Dinner": fiber * 0.25,
            }
        elif user_data["meal_plan_purchased"] == "Gym-Friendly":
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
        """
        Calculates fat targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing fat targets for each meal.
        """
        fat = targets["fat"]
        if user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": fat * 0.25,
                "MorningSnacks": fat * 0.10,
                "Lunch": fat * 0.30,
                "EveningSnacks": fat * 0.10,
                "Dinner": fat * 0.25,
            }
        elif user_data["meal_plan_purchased"] == "Gym-Friendly":
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
    


    def safe_parse_amount(self, amount):
        if isinstance(amount, str):
            return [float(a.strip()) if a.strip().replace(".", "", 1).isdigit() else 0.0 for a in amount.split(",")]
        elif isinstance(amount, (int, float)):
            return [float(amount)]
        elif isinstance(amount, list):
            return [float(a) if isinstance(a, (int, float)) else 0.0 for a in amount]
        else:
            return [0.0]

    
    def generate_meal(self, meal_type: str, ctx: MealPlanTargets) -> List[Dict]:
        try:
            if meal_type not in ctx.meal_targets:
                raise ValueError(f"Invalid meal type: {meal_type}")
                
            dataset = load_normalized_dataset(meal_type)
            
            # Group and filter dataset
            grouped_dataset = dataset.groupby('Sr. No.').agg({
                'MENU': lambda x: ' + '.join(x.dropna().unique()),
                'calories_total': 'sum',
                'Protein_total': 'sum',
                'Carbs_total': 'sum',
                'Fibre_total': 'sum',
                'Fat_total': 'sum',
                'DIET': 'first',
                'Region': 'first',
                'INGREDIENT': list,
                'AMOUNT (g)': list
            }).reset_index()

            # Filter out previously used meals
            available_meals = grouped_dataset[~grouped_dataset['Sr. No.'].isin(ctx.meal_history[meal_type])]
            
            # Apply region and diet preferences
            if ctx.user_data.get("region"):
                region_meals = available_meals[
                    available_meals['Region'].str.lower() == ctx.user_data.get("region").lower()
                ]
            else:
                region_meals = available_meals

            if ctx.user_data.get("preference", "").lower() == "vegetarian":
                region_meals = region_meals[region_meals["DIET"].str.lower() == "vegetarian"]
                available_meals = available_meals[available_meals["DIET"].str.lower() == "vegetarian"]

            # Shuffle available meals
            region_meals = region_meals.sample(frac=1).reset_index(drop=True)
            available_meals = available_meals.sample(frac=1).reset_index(drop=True)

            full_plan = []
            start_date = datetime.strptime(ctx.user_data["start_date"], "%Y-%m-%d")

            for day_offset in range(7):
                current_date = start_date + timedelta(days=day_offset)
                
                # Try to find meals from region-specific options first
                meal1 = self._find_suitable_meal(region_meals, "Option 1", current_date, meal_type, ctx)
                if not meal1:
                    # Fallback 1: Try without region constraint
                    meal1 = self._find_suitable_meal(available_meals, "Option 1", current_date, meal_type, ctx, relaxed=True)
                
                if not meal1:
                    # Fallback 2: Reset history and try again if still nothing
                    ctx.meal_history[meal_type].clear()
                    available_meals = grouped_dataset.copy() # Refresh available pool
                    meal1 = self._find_suitable_meal(available_meals, "Option 1", current_date, meal_type, ctx, relaxed=True)

                if meal1:
                    ctx.meal_history[meal_type].add(meal1["Sr. No."])
                    full_plan.append(meal1)
                    # Remove selected meal from available options
                    region_meals = region_meals[region_meals['Sr. No.'] != meal1["Sr. No."]]
                    available_meals = available_meals[available_meals['Sr. No.'] != meal1["Sr. No."]]

                # Find second option from all available meals
                remaining_meals = available_meals[~available_meals['Sr. No.'].isin(ctx.meal_history[meal_type])]
                meal2 = self._find_suitable_meal(remaining_meals, "Option 2", current_date, meal_type, ctx, relaxed=True)
                
                if not meal2 and not remaining_meals.empty:
                    # Desperation fallback: just pick a random one if nutritional match fails
                    row = remaining_meals.iloc[0]
                    meal2 = self._create_meal_dict(row, 1.0, current_date, meal_type, "Option 2")

                if meal2:
                    ctx.meal_history[meal_type].add(meal2["Sr. No."])
                    full_plan.append(meal2)

                # Reset meal history if running low on options
                if len(ctx.meal_history[meal_type]) > 0.8 * len(grouped_dataset):
                    ctx.meal_history[meal_type].clear()

            return full_plan

        except Exception as e:
            logger.error(f"Error generating {meal_type}: {str(e)}")
            return []

    def _meets_nutritional_requirements(self, total_calories, total_protein, total_carbs, 
                                     total_fiber, total_fat, target_calories, target_protein, 
                                     target_carbs, target_fiber, target_fat, tolerance, carb_tolerance):
        """Helper method to check if meal meets nutritional requirements."""
        return (abs(total_calories - target_calories) <= tolerance and
                abs(total_protein - target_protein) <= tolerance * 0.5 and
                abs(total_carbs - target_carbs) <= target_carbs * carb_tolerance and
                abs(total_fiber - target_fiber) <= tolerance * 0.5 and
                abs(total_fat - target_fat) <= tolerance * 0.5)

    def _create_meal_dict(self, row, factor, current_date, meal_type, option_type):
        """Helper method to create meal dictionary."""
        ingredients_scaled = {}
        for ingredients, amounts in zip(row["INGREDIENT"], row["AMOUNT (g)"]):
            if isinstance(ingredients, str):
                ingredient_list = [i.strip() for i in ingredients.split(',')]
                amounts_list = self.safe_parse_amount(amounts)
                
                if len(amounts_list) < len(ingredient_list):
                    amounts_list.extend([0.0] * (len(ingredient_list) - len(amounts_list)))
                
                for ingredient, amount in zip(ingredient_list, amounts_list):
                    if ingredient and len(ingredient) > 1:
                        clean_ingredient = ingredient.strip().capitalize()
                        current_amount = ingredients_scaled.get(clean_ingredient, 0)
                        ingredients_scaled[clean_ingredient] = round(current_amount + (amount * factor), 2)

        return {
            "Date": current_date.strftime("%Y-%m-%d"),
            "Meal Type": meal_type,
            "Option": option_type,
            "Menu Names": row["MENU"],
            "Diet Type": row["DIET"],
            "Region": row["Region"],
            "Total Calories": round(float(row["calories_total"] or 0) * factor, 2),
            "Total Protein": round(float(row["Protein_total"] or 0) * factor, 2),
            "Total Carbs": round(float(row["Carbs_total"] or 0) * factor, 2),
            "Total Fiber": round(float(row["Fibre_total"] or 0) * factor, 2),
            "Total Fat": round(float(row["Fat_total"] or 0) * factor, 2),
            "Ingredients Scaling": ingredients_scaled,
            "Sr. No.": row["Sr. No."]
        }

    def generate_meal_plan(self, user_data: Dict) -> Dict:
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

        meal_types = ["Breakfast", "Lunch", "Dinner"]
        organized_meals = []
        
        for meal_type in meal_types:
            current_meals = self.generate_meal(meal_type, ctx)
            if current_meals:
                organized_meals.extend(current_meals)
            else:
                logger.warning(f"Could not generate complete plan for {meal_type}")

        organized_meals.sort(key=lambda x: (
            x["Date"],
            {"Breakfast": 0, "Lunch": 1, "Dinner": 2}[x["Meal Type"]],
            int(x["Option"].split()[-1])
        ))

        ingredient_checklist = self.generate_ingredient_checklist(organized_meals)

        return {
            "meals": organized_meals,
            "ingredient_checklist": ingredient_checklist.to_dict('records')
        }

    def _find_suitable_meal(self, available_meals, option_type, current_date, meal_type, ctx: MealPlanTargets, relaxed=False):
        """Helper method to find a suitable meal from available options."""
        target_calories = ctx.meal_targets[meal_type]
        target_protein = ctx.protein_targets[meal_type]
        target_carbs = ctx.carb_targets[meal_type]
        target_fiber = ctx.fiber_targets[meal_type]
        target_fat = ctx.fat_targets[meal_type]
        
        tolerance = ctx.user_data.get("tolerance", 100) * (1.5 if relaxed else 1.0)
        carb_tolerance = ctx.user_data.get("carb_tolerance", 0.20) * (1.5 if relaxed else 1.0)

        for _, row in available_meals.iterrows():
            base_calories = float(row["calories_total"])
            base_protein = float(row["Protein_total"])
            
            if base_calories > 0:
                factor = target_calories / base_calories
            elif base_protein > 0:
                factor = target_protein / base_protein
            else:
                factor = 1.0
            
            factor = max(0.5, min(2.0, factor))

            total_calories = base_calories * factor
            total_protein = float(row["Protein_total"]) * factor
            total_carbs = float(row["Carbs_total"]) * factor
            total_fiber = float(row["Fibre_total"]) * factor
            total_fat = float(row["Fat_total"]) * factor

            if self._meets_nutritional_requirements(
                total_calories, total_protein, total_carbs, total_fiber, total_fat,
                target_calories, target_protein, target_carbs, target_fiber, target_fat,
                tolerance, carb_tolerance
            ):
                return self._create_meal_dict(row, factor, current_date, meal_type, option_type)
        
        return None

    def round_to_nearest(self, value, base=10):
        """Rounds a number to the nearest multiple of `base`."""
        return int(base * round(value / base))
    
    def generate_ingredient_checklist(self, meals):
        try:
            if isinstance(meals, str):
                meals = json.loads(meals)
            
            if isinstance(meals, dict):
                meal_list = []
                for meal_type, meal_items in meals.items():
                    if isinstance(meal_items, list):
                        meal_list.extend(meal_items)
                    else:
                        meal_list.append(meal_items)
            else:
                meal_list = meals if isinstance(meals, list) else [meals]

            if not meal_list:
                return pd.DataFrame()

            all_ingredients = {}
            for meal in meal_list:
                if isinstance(meal, str):
                    meal = json.loads(meal)
                
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
                return []

            return ingredients_df.sort_values("Total Amount (g)", ascending=False)
        except Exception as e:
            logger.error(f"Error generating ingredient checklist: {str(e)}")
            return pd.DataFrame()

    def calculate_adjusted_meal_targets(self, user_data: Dict, extra_intake: Dict[str, float], adjustment_days: int = 7) -> Dict:
        """Calculates adjusted targets based on extra intake."""
        targets = self._calculate_targets(user_data)
        meal_targets = self._calculate_meal_targets(user_data, targets)
        protein_targets = self._calculate_protein_targets(user_data, targets)
        carb_targets = self._calculate_carb_targets(user_data, targets)
        fiber_targets = self._calculate_fiber_targets(user_data, targets)
        fat_targets = self._calculate_fat_targets(user_data, targets)

        daily_adjustments = {
            "calories": extra_intake.get("calories", 0) / adjustment_days,
            "protein": extra_intake.get("protein", 0) / adjustment_days,
            "carbs": extra_intake.get("carbs", 0) / adjustment_days,
            "fiber": extra_intake.get("fiber", 0) / adjustment_days,
            "fat": extra_intake.get("fat", 0) / adjustment_days
        }
    
        main_meals = ["Breakfast", "Lunch"]
        per_meal_adjustment = {
            k: v / len(main_meals) for k, v in daily_adjustments.items()
        }
        
        adjusted_meal_targets = meal_targets.copy()
        adjusted_protein_targets = protein_targets.copy()
        adjusted_carb_targets = carb_targets.copy()
        adjusted_fiber_targets = fiber_targets.copy()
        adjusted_fat_targets = fat_targets.copy()

        for meal_type in adjusted_meal_targets:
            if meal_type in main_meals:
                adjusted_meal_targets[meal_type] = max(0, adjusted_meal_targets[meal_type] - per_meal_adjustment["calories"])
                adjusted_protein_targets[meal_type] = max(0, adjusted_protein_targets[meal_type] - per_meal_adjustment["protein"])
                adjusted_carb_targets[meal_type] = max(0, adjusted_carb_targets[meal_type] - per_meal_adjustment["carbs"])
                adjusted_fiber_targets[meal_type] = max(0, adjusted_fiber_targets[meal_type] - per_meal_adjustment["fiber"])
                adjusted_fat_targets[meal_type] = max(0, adjusted_fat_targets[meal_type] - per_meal_adjustment["fat"])
        
        return {
            "meal_targets": adjusted_meal_targets,
            "protein_targets": adjusted_protein_targets,
            "carb_targets": adjusted_carb_targets,
            "fiber_targets": adjusted_fiber_targets,
            "fat_targets": adjusted_fat_targets,
            "adjustment_days": adjustment_days
        }

# Singleton instance
meal_generator = MealGenerator()
