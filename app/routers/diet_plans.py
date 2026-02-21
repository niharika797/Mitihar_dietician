# app/routers/diet_plans.py
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict
from ..services.diet_plan_service import DietPlanService
from ..services.user_service import get_current_user
from ..models.user import UserInDB
from ..models.diet_plan import DietPlan
from ..core.exceptions import DietPlanNotFoundException
from ..services.meal_generator.meal_generator import meal_generator  # Use singleton
from datetime import datetime

router = APIRouter()
from ..core.limiter import limiter

diet_plan_service = DietPlanService()

@router.get("/my-plan", response_model=DietPlan)
async def get_my_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Get the current user's diet plan."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()
    return diet_plan
@router.get("/today", response_model=DietPlan)
async def get_today_meals(current_user: UserInDB = Depends(get_current_user)):
    """Get today's meals from the user's diet plan."""
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        raise DietPlanNotFoundException()
    
    today_str = datetime.today().strftime("%Y-%m-%d")
    today_meals = [m for m in diet_plan.meals if m.get("Date") == today_str]
    
    # Generate ingredient checklist for today only
    today_ingredients = meal_generator.generate_ingredient_checklist(today_meals)
    
    # Handle both DataFrame and list returns
    ingredient_list = today_ingredients.to_dict(orient="records") if hasattr(today_ingredients, 'to_dict') else today_ingredients

    return DietPlan(
        user_id=diet_plan.user_id,
        created_at=diet_plan.created_at,
        meals=today_meals,
        ingredient_checklist=ingredient_list
    )

@router.post("/generate", response_model=DietPlan)
@limiter.limit("10/hour")
async def generate_diet_plan(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
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

@router.delete("/delete", responses={
    200: {"description": "Diet plan deleted successfully", "content": {"application/json": {"example": {"message": "Diet plan deleted successfully"}}}},
    404: {"description": "Diet plan not found"}
})
async def delete_diet_plan(current_user: UserInDB = Depends(get_current_user)):
    """Delete the current user's diet plan."""
    success = await diet_plan_service.delete_diet_plan(str(current_user.id))
    if not success:
        raise DietPlanNotFoundException()
    return {"message": "Diet plan deleted successfully"}


@router.get("/ingredient-checklist", response_model=List[Dict], responses={
    200: {
        "description": "Ingredient checklist for today's meals. Returns an empty list [] if no diet plan exists for the user.",
        "content": {"application/json": {"example": []}}
    }
})
async def get_ingredient_checklist_today(current_user: UserInDB = Depends(get_current_user)):
    """
    Get the ingredient checklist for today's meals only.
    Returns an empty list [] if no diet plan is found (valid empty state).
    """
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        return []
    
    today_str = datetime.today().strftime("%Y-%m-%d")
    today_meals = [m for m in diet_plan.meals if m.get("Date") == today_str]
    
    ingredient_checklist = meal_generator.generate_ingredient_checklist(today_meals)
    if hasattr(ingredient_checklist, 'to_dict'):
        return ingredient_checklist.to_dict(orient="records")
    return ingredient_checklist

@router.get("/weekly-ingredients", response_model=List[Dict], responses={
    200: {
        "description": "Weekly ingredient checklist. Returns an empty list [] if no diet plan exists for the user.",
        "content": {"application/json": {"example": []}}
    }
})
async def get_weekly_ingredients(current_user: UserInDB = Depends(get_current_user)):
    """
    Get the weekly ingredient checklist for all meals.
    Returns an empty list [] if no diet plan is found (valid empty state).
    """
    diet_plan = await diet_plan_service.get_diet_plan(str(current_user.id))
    if not diet_plan:
        return []
    
    if not diet_plan.ingredient_checklist:
        # If ingredient checklist is empty, generate it from all meals
        ingredient_checklist = meal_generator.generate_ingredient_checklist(diet_plan.meals)
        if hasattr(ingredient_checklist, 'to_dict'):
            return ingredient_checklist.to_dict(orient="records")
        return ingredient_checklist
        
    return diet_plan.ingredient_checklist