import pytest
from app.services.meal_generator.meal_generator import MealGenerator, MealPlanTargets, meal_generator

def test_meal_generator_singleton():
    instance1 = meal_generator
    instance2 = MealGenerator()
    # verify singleton instance
    assert instance1 is meal_generator
    assert isinstance(instance1, MealGenerator)

def test_meal_plan_targets_initialization():
    targets = {"tdee": 2000, "protein": 100, "carbs": 250, "fiber": 30, "fat": 60}
    user_data = {"height": 175, "weight": 70, "age": 25, "gender": "male", "activity_level": "MA", "meal_plan_purchased": "Healthy", "start_date": "2026-02-21"}
    
    ctx = MealPlanTargets(
        targets=targets,
        meal_targets={"Breakfast": 500, "Lunch": 700, "Dinner": 500, "MorningSnacks": 150, "EveningSnacks": 150},
        protein_targets={"Breakfast": 25, "Lunch": 35, "Dinner": 25, "MorningSnacks": 7.5, "EveningSnacks": 7.5},
        carb_targets={"Breakfast": 62.5, "Lunch": 87.5, "Dinner": 62.5, "MorningSnacks": 18.75, "EveningSnacks": 18.75},
        fiber_targets={"Breakfast": 7.5, "Lunch": 10.5, "Dinner": 7.5, "MorningSnacks": 2.25, "EveningSnacks": 2.25},
        fat_targets={"Breakfast": 15, "Lunch": 21, "Dinner": 15, "MorningSnacks": 4.5, "EveningSnacks": 4.5},
        user_data=user_data
    )
    
    assert ctx.meal_history["Breakfast"] == set()
    assert ctx.user_data["gender"] == "male"
