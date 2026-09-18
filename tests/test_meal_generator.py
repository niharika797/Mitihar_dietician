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
        meal_targets={"Breakfast": 500, "Lunch": 700, "Dinner": 500},
        user_data=user_data
    )

    assert ctx.targets["tdee"] == 2000
    assert ctx.meal_targets["Breakfast"] == 500
    assert ctx.user_data["gender"] == "male"
