from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..services.user_service import get_current_user
from ..models.user import User
from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee
from ..services.diet_plan_service import DietPlanService
from typing import List, Dict

router = APIRouter()

from ..core.limiter import limiter

class CalorieReductionInput(BaseModel):
    reduction_amount: int

@router.post("/adjust")
@limiter.limit("10/hour")
async def adjust_meal_plan(
    request: Request,
    reduction: CalorieReductionInput,
    current_user: User = Depends(get_current_user)
):
    """Adjust meal plan with rate limiting"""
    if not getattr(current_user, 'meal_plan_purchased', False):
        raise HTTPException(
            status_code=403,
            detail="Meal plan adjustment is only available for premium members. Please purchase a plan."
        )
    
    try:
        diet_service = DietPlanService()
        
        # Calculate original TDEE
        bmr = calculate_bmr(
            current_user.gender,
            float(current_user.weight),
            float(current_user.height),
            int(current_user.age)
        )
        total_calories = calculate_tdee(bmr, current_user.activity_level)
        
        # Apply reduction
        target_calories = total_calories - reduction.reduction_amount
        
        # Prepare user data dictionary with all required fields
        user_data = current_user.model_dump()
        user_data["id"] = str(current_user.id)
        user_data["target_calories"] = target_calories
        
        # Generate new plan with adjusted calories
        new_plan = await diet_service.generate_diet_plan(user_data)
        await diet_service.update_diet_plan(str(current_user.id), new_plan)
        
        return {
            "message": "Meal plan adjusted successfully",
            "new_target_calories": target_calories,
            "plan": new_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
