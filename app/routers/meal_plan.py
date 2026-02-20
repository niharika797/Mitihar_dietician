from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..services.user_service import get_current_user
from ..models.user import User
from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee
from ..services.diet_plan_service import DietPlanService
from typing import List, Dict

router = APIRouter()

class CalorieReductionInput(BaseModel):
    reduction_amount: int

@router.post("/adjust")
async def adjust_meal_plan(
    reduction: CalorieReductionInput,
    current_user: User = Depends(get_current_user)
):
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
        user_data = {
            "id": str(current_user.id),
            "height": float(current_user.height),
            "weight": float(current_user.weight),
            "age": int(current_user.age),
            "gender": current_user.gender,
            "target_calories": round(target_calories),
            "diet_type": current_user.diet,
            "allergies": current_user.allergies if hasattr(current_user, 'allergies') else [],
            "health_conditions": current_user.health_conditions if hasattr(current_user, 'health_conditions') else [],
            "activity_level": current_user.activity_level,
            "region": current_user.region if hasattr(current_user, 'region') else "none",
            "meal_plan_purchased": getattr(current_user, 'meal_plan_purchased', True)  # Default to True if not specified
        }
        
        # Generate diet plan using existing service
        diet_plan = await diet_service.generate_diet_plan(user_data)

        return {
            "original_tdee": round(total_calories),
            "reduced_calories": reduction.reduction_amount,
            "target_calories": round(target_calories),
            "diet_plan": diet_plan
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        raise