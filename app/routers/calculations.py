from fastapi import APIRouter, Depends
from ..services.user_service import get_current_user
from ..models.user import User
from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee, calculate_bmi
from pydantic import BaseModel

router = APIRouter()

@router.get("/bmr")
async def get_bmr(current_user: User = Depends(get_current_user)):
    bmr = calculate_bmr(
        current_user.gender,
        float(current_user.weight),
        float(current_user.height),
        int(current_user.age)
    )
    return {"bmr": round(bmr, 2)}

@router.get("/tdee")
async def get_tdee(current_user: User = Depends(get_current_user)):
    bmr = calculate_bmr(
        current_user.gender,
        float(current_user.weight),
        float(current_user.height),
        int(current_user.age)
    )
    tdee = calculate_tdee(bmr, current_user.activity_level)
    return {"tdee": round(tdee, 2)}

@router.get("/bmi")
async def get_bmi(current_user: User = Depends(get_current_user)):
    bmi = calculate_bmi(float(current_user.height), float(current_user.weight))
    return {"bmi": round(bmi, 2)}