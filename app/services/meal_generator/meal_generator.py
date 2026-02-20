from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pydantic import BaseModel  # Add this import
import pandas as pd
import random
import json

from .data_loader import load_normalized_dataset
from .calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

class MealBase(BaseModel):
    """
    Base class for defining meal structure.
    """
    name: str | None = None
    calories: float | None = None
    proteins: float | None = None
    carbs: float | None = None
    fiber: float | None = None
    ingredients: List[str] | None = []
    instructions: str | None = ""
    start_date: str
    preference: str = "vegetarian"
    non_veg_days: Optional[List[str]] = None
    tolerance: float = 50
    carb_tolerance: float = 0.10
    num_weeks: int = 1
    region: Optional[str] = None
    file_path: str
    meal_type: str
    target_calories: float
    target_protein: float
    target_fiber: float
    target_carbs: float
    target_fat: float
    start_date: str


class MealGenerator:
    """
    Generates personalized meal plans based on user data and dietary requirements.
    """
    def __init__(self, user_data: Dict):
        self.user_data = user_data
        self.targets = self._calculate_targets()
        self.meal_targets = self._calculate_meal_targets()
        self.protein_targets = self._calculate_protein_targets()
        self.carb_targets = self._calculate_carb_targets()
        self.fiber_targets = self._calculate_fiber_targets()
        self.fat_targets = self._calculate_fat_targets()
        if "start_date" not in user_data:
            user_data["start_date"] = datetime.now().strftime("%Y-%m-%d")
        self.num_weeks = 1
        self.min_days = 3
        # Initialize meal history tracking
        self._meal_history = {
            "Breakfast": set(),
            "MorningSnacks": set(),
            "Lunch": set(),
            "Dinner": set()
        }
    def _calculate_targets(self) -> Dict:
        """
        Calculates BMI, BMR, TDEE, and macronutrient targets based on user data.

        Returns:
            Dict: Dictionary containing calculated nutritional targets (bmi, bmr, tdee, protein, carbs, fiber).
        """
        height = self.user_data["height"]
        weight = self.user_data["weight"]
        age = self.user_data["age"]
        gender = self.user_data["gender"]
        activity_level = self.user_data["activity_level"]
        meal_plan_purchased = self.user_data["meal_plan_purchased"]
        health_condition = self.user_data.get("health_condition")

        bmi = calculate_bmi(height, weight)
        bmr = calculate_bmr(gender, weight, height, age)
        tdee = calculate_tdee(bmr, activity_level)
        protein, carbs, fiber,fat = calculate_macronutrients(tdee, meal_plan_purchased, health_condition)


        return {
            "bmi": bmi,
            "bmr": bmr,
            "tdee": tdee,
            "protein": protein,
            "carbs": carbs,
            "fiber": fiber,
            "fat": fat
        }

    def _calculate_meal_targets(self) -> Dict:
        """
        Calculates calorie targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing calorie targets for each meal (Breakfast, MorningSnacks, Lunch, Dinner, EveningSnacks).
        """
        tdee = self.targets["tdee"]
        
        if self.user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": tdee * 0.25,
                "MorningSnacks": tdee * 0.05,
                "Lunch": tdee * 0.30,
                "EveningSnacks": tdee * 0.05,
                "Dinner": tdee * 0.25,
            }
        elif self.user_data["meal_plan_purchased"] == "Gym-Friendly":
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

    def _calculate_protein_targets(self) -> Dict:
        """
        Calculates protein targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing protein targets for each meal.
        """
        protein = self.targets["protein"]
        if self.user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": protein * 0.25,
                "MorningSnacks": protein * 0.10,
                "Lunch": protein * 0.30,
                "EveningSnacks": protein * 0.10,
                "Dinner": protein * 0.25,
            }
        elif self.user_data["meal_plan_purchased"] == "Gym-Friendly":
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
    
    def _calculate_carb_targets(self) -> Dict:
        """
        Calculates carbohydrate targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing carbohydrate targets for each meal.
        """
        carbs = self.targets["carbs"]
        if self.user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": carbs * 0.25,
                "MorningSnacks": carbs * 0.10,
                "Lunch": carbs * 0.30,
                "EveningSnacks": carbs * 0.10,
                "Dinner": carbs * 0.25,
            }
        elif self.user_data["meal_plan_purchased"] == "Gym-Friendly":
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

    def _calculate_fiber_targets(self) -> Dict:
        """
        Calculates fiber targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing fiber targets for each meal.
        """
        fiber = self.targets["fiber"]
        if self.user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": fiber * 0.25,
                "MorningSnacks": fiber * 0.10,
                "Lunch": fiber * 0.30,
                "EveningSnacks": fiber * 0.10,
                "Dinner": fiber * 0.25,
            }
        elif self.user_data["meal_plan_purchased"] == "Gym-Friendly":
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
    def _calculate_fat_targets(self) -> Dict:
        """
        Calculates fat targets for each meal based on meal plan type.

        Returns:
            Dict: Dictionary containing fat targets for each meal.
        """
        fat = self.targets["fat"]
        if self.user_data["meal_plan_purchased"] == "Healthy":
            return {
                "Breakfast": fat * 0.25,
                "MorningSnacks": fat * 0.10,
                "Lunch": fat * 0.30,
                "EveningSnacks": fat * 0.10,
                "Dinner": fat * 0.25,
            }
        elif self.user_data["meal_plan_purchased"] == "Gym-Friendly":
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

    
    def generate_meal(self, meal_type: str) -> List[Dict]:
        try:
            if meal_type not in self.meal_targets:
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
            available_meals = grouped_dataset[~grouped_dataset['Sr. No.'].isin(self._meal_history[meal_type])]
            
            # Apply region and diet preferences
            if self.user_data.get("region"):
                region_meals = available_meals[
                    available_meals['Region'].str.lower() == self.user_data.get("region").lower()
                ]
            else:
                region_meals = available_meals

            if self.user_data.get("preference", "").lower() == "vegetarian":
                region_meals = region_meals[region_meals["DIET"].str.lower() == "vegetarian"]
                available_meals = available_meals[available_meals["DIET"].str.lower() == "vegetarian"]

            # Shuffle available meals
            region_meals = region_meals.sample(frac=1).reset_index(drop=True)
            available_meals = available_meals.sample(frac=1).reset_index(drop=True)

            full_plan = []
            start_date = datetime.strptime(self.user_data["start_date"], "%Y-%m-%d")

            for day_offset in range(7):
                current_date = start_date + timedelta(days=day_offset)
                
                # Try to find meals from region-specific options first
                meal1 = self._find_suitable_meal(region_meals, "Option 1", current_date, meal_type)
                if meal1:
                    self._meal_history[meal_type].add(meal1["Sr. No."])
                    full_plan.append(meal1)
                    # Remove selected meal from available options
                    region_meals = region_meals[region_meals['Sr. No.'] != meal1["Sr. No."]]
                    available_meals = available_meals[available_meals['Sr. No.'] != meal1["Sr. No."]]

                # Find second option from all available meals
                remaining_meals = available_meals[~available_meals['Sr. No.'].isin(self._meal_history[meal_type])]
                meal2 = self._find_suitable_meal(remaining_meals, "Option 2", current_date, meal_type, relaxed=True)
                if meal2:
                    self._meal_history[meal_type].add(meal2["Sr. No."])
                    full_plan.append(meal2)

                # Reset meal history if running low on options
                if len(self._meal_history[meal_type]) > 0.7 * len(grouped_dataset):
                    self._meal_history[meal_type].clear()

            return full_plan

        except Exception as e:
            print(f"Error generating {meal_type}: {str(e)}")
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
                
                while len(amounts_list) < len(ingredient_list):
                    amounts_list.append(0.0)
                
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
            "Total Calories": round(float(row["calories_total"]) * factor, 2),
            "Total Protein": round(float(row["Protein_total"]) * factor, 2),
            "Total Carbs": round(float(row["Carbs_total"]) * factor, 2),
            "Total Fiber": round(float(row["Fibre_total"]) * factor, 2),
            "Total Fat": round(float(row["Fat_total"]) * factor, 2),
            "Ingredients Scaling": ingredients_scaled,
            "Sr. No.": row["Sr. No."]
        }
    def generate_meal_plan(self) -> Dict:
        meal_types = ["Breakfast", "Lunch", "Dinner"]
        organized_meals = []
        start_date = datetime.strptime(self.user_data["start_date"], "%Y-%m-%d")
        
        for day_offset in range(3):  # Generate for 3 days
            current_date = start_date + timedelta(days=day_offset)
            day_complete = False
            max_retries = 5
            retry_count = 0
            
            while not day_complete and retry_count < max_retries:
                day_meals = {meal_type: [] for meal_type in meal_types}
                day_complete = True
                
                for meal_type in meal_types:
                    original_tolerance = self.user_data.get("tolerance", 100)
                    original_carb_tolerance = self.user_data.get("carb_tolerance", 0.20)
                    
                    # Increase tolerance for subsequent retries
                    tolerance_multiplier = 1.0 + (0.3 * retry_count)
                    self.user_data["tolerance"] = original_tolerance * tolerance_multiplier
                    self.user_data["carb_tolerance"] = original_carb_tolerance * tolerance_multiplier
                    
                    # Try to get both options for this meal type
                    current_meals = self.generate_meal(meal_type)
                    if current_meals and len(current_meals) >= 2:
                        for meal in current_meals[:2]:
                            meal["Date"] = current_date.strftime("%Y-%m-%d")
                            day_meals[meal_type].append(meal)
                    else:
                        day_complete = False
                        break
                    
                    # Reset tolerances
                    self.user_data["tolerance"] = original_tolerance
                    self.user_data["carb_tolerance"] = original_carb_tolerance
                
                if day_complete:
                    # Add all meals for this day to organized_meals
                    for meal_type in meal_types:
                        for i, meal in enumerate(day_meals[meal_type], 1):
                            meal["Option"] = f"Option {i}"
                            organized_meals.append(meal)
                
                retry_count += 1
            
            # Clear meal history if needed
            if retry_count >= max_retries:
                self._meal_history = {
                    "Breakfast": set(),
                    "Lunch": set(),
                    "Dinner": set()
                }

        # Sort all meals by date and type
        organized_meals.sort(key=lambda x: (
            x["Date"],
            {"Breakfast": 0, "Lunch": 1, "Dinner": 2}[x["Meal Type"]],
            int(x["Option"].split()[-1])
        ))

        # Generate ingredient checklist
        ingredient_checklist = self.generate_ingredient_checklist(organized_meals)

        return {
            "meals": organized_meals,
            "ingredient_checklist": ingredient_checklist.to_dict('records')
        }
    def _find_suitable_meal(self, available_meals, option_type, current_date, meal_type, relaxed=False):
        """Helper method to find a suitable meal from available options."""
        target_calories = self.meal_targets[meal_type]
        target_protein = self.protein_targets[meal_type]
        target_carbs = self.carb_targets[meal_type]
        target_fiber = self.fiber_targets[meal_type]
        target_fat = self.fat_targets[meal_type]
        
        tolerance = self.user_data.get("tolerance", 100) * (1.5 if relaxed else 1.0)
        carb_tolerance = self.user_data.get("carb_tolerance", 0.20) * (1.5 if relaxed else 1.0)

        for _, row in available_meals.iterrows():
            # Calculate scaling factor
            base_calories = float(row["calories_total"])
            base_protein = float(row["Protein_total"])
            base_carbs = float(row["Carbs_total"])
            
            factors = []
            if base_calories > 0: factors.append(target_calories / base_calories)
            if base_protein > 0: factors.append(target_protein / base_protein)
            if base_carbs > 0: factors.append(target_carbs / base_carbs)
            
            valid_factors = [f for f in factors if 0.5 <= f <= 2.0]
            factor = sum(valid_factors) / len(valid_factors) if valid_factors else 1.0

            # Calculate scaled nutritional values
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
            # Convert string to dict if needed
            if isinstance(meals, str):
                meals = json.loads(meals)
            
            # Handle both list and dict formats
            if isinstance(meals, dict):
                meal_list = []
                for meal_type, meal_items in meals.items():
                    if isinstance(meal_items, list):
                        meal_list.extend(meal_items)
                    else:
                        meal_list.append(meal_items)
            else:
                meal_list = meals if isinstance(meals, list) else [meals]

            # Collect all ingredients
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

            # Convert to DataFrame
            ingredients_df = pd.DataFrame([
                {"Ingredient": k, "Total Amount (g)": round(v, 2)}
                for k, v in all_ingredients.items()
            ])

            return ingredients_df.sort_values("Total Amount (g)", ascending=False)

        except Exception as e:
            print(f"Error generating ingredient checklist: {str(e)}")
            return pd.DataFrame(columns=["Ingredient", "Total Amount (g)"])

    


    # def generate_meal_plan(self) -> Dict:
    #     """
    #     Generates a complete weekly meal plan including breakfast, snacks, lunch, and dinner.

    #     Returns:
    #         Dict: A dictionary containing the weekly meal plan, categorized by meal type.
    #     """
    #     meal_plan = {
    #         "Breakfast": self.generate_meal("Breakfast"),
    #         # "MorningSnacks": self.generate_meal("MorningSnacks"),
    #         "Lunch": self.generate_meal("Lunch"),
    #         # "EveningSnacks": self.generate_meal("EveningSnacks"),
    #         "Dinner": self.generate_meal("Dinner"),
    #     }
    #     all_meals = []
    #     for meals in meal_plan.values():
    #         if meals:
    #             all_meals.extend(meals)

    #     # Generate ingredient checklist
    #     ingredient_checklist = self.generate_ingredient_checklist(all_meals)

    #     return {
    #         "meals": all_meals,
    #         "ingredient_checklist": ingredient_checklist.to_dict(orient="records")
    #     }

    # def generate_meal_plan(self) -> Dict:
    #     """
    #     Generates a complete weekly meal plan including breakfast, snacks, lunch, and dinner.

    #     Returns:
    #         Dict: A dictionary containing the weekly meal plan, categorized by meal type.
    #     """
    #     meal_plan = {
    #         "Breakfast": self.generate_meal("Breakfast",),
    #         "MorningSnacks": self.generate_snacks("MorningSnacks"),
    #         "Lunch": self.generate_lunch(),
    #         "EveningSnacks": self.generate_snacks("EveningSnacks"), #Evening snacks are generated only for diabetic plan
    #         "Dinner": self.generate_dinner(),
    #     }
    #     # Remove error entries if any meal generation failed and returned an error dict
    #     return {k: v for k, v in meal_plan.items() if not isinstance(v, dict) or "error" not in v}
    def calculate_adjusted_meal_targets(self, extra_intake: Dict[str, float], adjustment_days: int = 7) -> Dict:
    # Calculate daily adjustments
        daily_adjustments = {
            "calories": extra_intake.get("calories", 0) / adjustment_days,
            "protein": extra_intake.get("protein", 0) / adjustment_days,
            "carbs": extra_intake.get("carbs", 0) / adjustment_days,
            "fiber": extra_intake.get("fiber", 0) / adjustment_days,
            "fat": extra_intake.get("fat", 0) / adjustment_days
        }
    
        # Store original targets
        self._original_targets = {
            "meal": self.meal_targets.copy(),
            "protein": self.protein_targets.copy(),
            "carbs": self.carb_targets.copy(),
            "fiber": self.fiber_targets.copy(),
            "fat": self.fat_targets.copy()
        }
        
        # Adjust each meal type (excluding snacks)
        main_meals = ["Breakfast", "Lunch"]
        per_meal_adjustment = {
            k: v / len(main_meals) for k, v in daily_adjustments.items()
        }
        
        # Apply adjustments
        for meal_type in self.meal_targets:
            if meal_type in main_meals:
                self.meal_targets[meal_type] = max(0, self.meal_targets[meal_type] - per_meal_adjustment["calories"])
                self.protein_targets[meal_type] = max(0, self.protein_targets[meal_type] - per_meal_adjustment["protein"])
                self.carb_targets[meal_type] = max(0, self.carb_targets[meal_type] - per_meal_adjustment["carbs"])
                self.fiber_targets[meal_type] = max(0, self.fiber_targets[meal_type] - per_meal_adjustment["fiber"])
                self.fat_targets[meal_type] = max(0, self.fat_targets[meal_type] - per_meal_adjustment["fat"])
        
        return {
            "meal_targets": self.meal_targets,
            "protein_targets": self.protein_targets,
            "carb_targets": self.carb_targets,
            "fiber_targets": self.fiber_targets,
            "fat_targets": self.fat_targets,
            "adjustment_days": adjustment_days
        }

    def reset_targets(self):
        """Resets all targets to their original values"""
        if hasattr(self, '_original_targets'):
            self.meal_targets = self._original_targets["meal"]
            self.protein_targets = self._original_targets["protein"]
            self.carb_targets = self._original_targets["carbs"]
            self.fiber_targets = self._original_targets["fiber"]
            self.fat_targets = self._original_targets["fat"]