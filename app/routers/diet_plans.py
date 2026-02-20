# app/routers/diet_plans.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from ..services.diet_plan_service import DietPlanService
from ..services.user_service import get_current_user
from ..models.user import UserInDB
from ..models.diet_plan import DietPlan
from ..core.exceptions import DietPlanNotFoundException
from ..services.meal_generator.meal_generator import MealGenerator  # Add this import
from datetime import datetime

router = APIRouter()
diet_plan_service = DietPlanService()

@router.get("/my-plan", response_model=DietPlan)
async def get_my_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Get the current user's diet plan."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()
    return diet_plan
@router.get("/today", response_model=DietPlan)
async def get_today_date():
    """
    Get today's date in YYYY-MM-DD format
    """
    start_date = datetime.today().strftime("%Y-%m-%d")
    return {"date": start_date}

@router.post("/generate", response_model=DietPlan)
async def generate_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Generate a new diet plan for the current user."""
    # First check if user already has a plan
    existing_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail="Diet plan already exists for this user"
        )

    
    diet_plan = await diet_plan_service.generate_diet_plan(current_user.model_dump())
    plan_id = await diet_plan_service.store_diet_plan(diet_plan)
    return diet_plan

@router.put("/update", response_model=DietPlan)
async def update_diet_plan(
    updated_plan: DietPlan,
    current_user: UserInDB = Depends(get_current_user)
):
    """Update the current user's diet plan."""
    success = await diet_plan_service.update_diet_plan(
        str(current_user.id),
        updated_plan
    )
    if not success:
        raise DietPlanNotFoundException()
    return updated_plan

@router.delete("/delete")
async def delete_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Delete the current user's diet plan."""
    success = await diet_plan_service.delete_diet_plan(str(current_user.id))
    if not success:
        raise DietPlanNotFoundException()
    return {"message": "Diet plan deleted successfully"}


@router.get("/ingredient-checklist", response_model=List[Dict])
async def get_ingredient_checklist(current_user: UserInDB = Depends(get_current_user)):
    """Get the ingredient checklist for the current user's diet plan."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()
    
    # Flatten the meals dictionary into a list
    all_meals = []
    for meal_list in diet_plan.meals.values():
        if isinstance(meal_list, list):
            all_meals.extend(meal_list)
    
    meal_generator = MealGenerator(current_user.model_dump())
    ingredient_checklist = meal_generator.generate_ingredient_checklist(all_meals)
    
    return ingredient_checklist.to_dict(orient="records")

@router.get("/weekly-ingredients", response_model=List[Dict])
async def get_weekly_ingredients(current_user: UserInDB = Depends(get_current_user)):
    """Get the weekly ingredient checklist for all meals."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()
    
    if not diet_plan.ingredient_checklist:
        # If ingredient checklist is empty, generate it
        meal_generator = MealGenerator(current_user.model_dump())
        meals_dict = diet_plan.meals if isinstance(diet_plan.meals, dict) else {"all_meals": diet_plan.meals}
        ingredient_checklist = meal_generator.generate_ingredient_checklist(meals_dict)
        return ingredient_checklist.to_dict(orient="records")
        
    return diet_plan.ingredient_checklist