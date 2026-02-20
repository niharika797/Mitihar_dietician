import pandas as pd

def Healthy_Breakfast(meal_targets, protein_targets, carb_target, fibre_targets):
    breakfast_df = pd.read_excel("/kaggle/input/e-yantra-dataset/aa.xlsx")

    target_calories = meal_targets.get("Breakfast")
    target_protein = protein_targets.get("Breakfast")
    target_carbs = carb_target.get("Breakfast")
    target_fiber = fibre_targets.get("Breakfast")
    
    tolerance = 0.2
    
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meal_counts = {}
    meal_last_used = {}
    
    def calculate_meal_plan(dataset, target_calories, target_protein, target_carbs, target_fiber):
        meal_plan = {}
        all_meals = []
    
        for _, row in dataset.iterrows():
            meal = row["name"]
            meal_calories = row["calories"]
            meal_protein = row["protein"]
            meal_carbs = row["carbs"]
            meal_fiber = row["fiber"]
            meal_recipe = row.get("instructions", "Recipe not available")
    
            if not (target_carbs * (1 - tolerance) <= meal_carbs <= target_carbs * (1 + tolerance)):
                continue
    
            calorie_diff = abs(meal_calories - target_calories)
            protein_diff = abs(meal_protein - target_protein)
            fiber_diff = abs(meal_fiber - target_fiber)
    
            normalized_calorie_diff = calorie_diff / target_calories if target_calories != 0 else calorie_diff
            normalized_protein_diff = protein_diff / target_protein if target_protein != 0 else protein_diff
            normalized_fiber_diff = fiber_diff / target_fiber if target_fiber != 0 else fiber_diff
    
            combined_similarity_score = 1 - (normalized_calorie_diff + normalized_protein_diff + normalized_fiber_diff) / 3
    
            if combined_similarity_score > 0:
                all_meals.append((
                    meal, meal_calories, combined_similarity_score, meal_protein, meal_carbs, meal_fiber, meal_recipe
                ))
    
        sorted_meals = sorted(all_meals, key=lambda x: x[2], reverse=True)
        
        for i, day in enumerate(days_of_week):
            day_meals = []
            for meal in sorted_meals:
                if meal_counts.get(meal[0], 0) < 1 and (meal[0] not in meal_last_used or i - meal_last_used[meal[0]] >= 6):
                    day_meals.append(meal)
                    meal_counts[meal[0]] = meal_counts.get(meal[0], 0) + 1
                    meal_last_used[meal[0]] = i
                    if len(day_meals) == 2:
                        break
            meal_plan[day] = day_meals
    
        return meal_plan
    
    weekly_meal_plan = calculate_meal_plan(breakfast_df, target_calories, target_protein, target_carbs, target_fiber)
    
    meal_data = []
    for day, meals in weekly_meal_plan.items():
        for meal in meals:
            meal_data.append({
                "Day": day,
                "Meal": meal[0],
                "Calories": meal[1],
                "Protein": meal[3],
                "Carbs": meal[4],
                "Fiber": meal[5],
                "Recipe": meal[6],
                "Similarity": f"{meal[2]:.2f}"
            })
    
    meal_plan_df = pd.DataFrame(meal_data)
    a=meal_plan_df.to_json(orient="index")
    import json
    print(json.dumps(a,indent=4))
    return meal_plan_df
