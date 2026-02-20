from fastapi import APIRouter, Depends, HTTPException
from ..services.user_service import UserService, get_current_user
from ..models.user import User
from ..services.diet_plan_service import DietPlanService

router = APIRouter()
user_service = UserService()
diet_plan_service = DietPlanService()

@router.get("/me")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    user_data = current_user.model_dump(exclude={"hashed_password"})
    # user_data.pop("hashed_password", None)
    return user_data

@router.get("/bmi")
async def get_user_bmi(current_user: User = Depends(get_current_user)):
    bmi = await diet_plan_service.calculate_bmi(current_user.height, current_user.weight)
    return {"bmi": bmi}