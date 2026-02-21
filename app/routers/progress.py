from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..services.user_service import get_current_user
from ..models.user import User, UserInDB
from ..services.progress_service import progress_service
from ..schemas.progress import MealLogCreate, WaterLogCreate, StepsLogCreate, WeightLogCreate
from ..core.database import get_database
from datetime import datetime
import random

router = APIRouter()

@router.post("/log/meal")
async def log_meal(
    meal: MealLogCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Log a meal consumed by the user"""
    await progress_service.log_meal(str(current_user.id), meal.model_dump(), db)
    return {"message": "Meal logged successfully"}

@router.post("/log/water")
async def log_water(
    water: WaterLogCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Log water intake"""
    await progress_service.log_water(str(current_user.id), water.glasses, db)
    return {"message": "Water intake logged successfully"}

@router.post("/log/steps")
async def log_steps(
    steps: StepsLogCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Log daily steps"""
    await progress_service.log_steps(str(current_user.id), steps.steps, db)
    return {"message": "Steps logged successfully"}

@router.post("/log/weight")
async def log_weight(
    weight: WeightLogCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Log current weight"""
    await progress_service.log_weight(str(current_user.id), weight.weight, db)
    # Also update user's current weight in profile?
    # For now, just log it.
    return {"message": "Weight logged successfully"}

@router.get("/today")
async def get_today_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get summarized stats for today"""
    logs = await progress_service.get_daily_logs(str(current_user.id), datetime.utcnow(), db)
    
    # Simple summary logic
    total_calories = sum(log["data"].get("calories", 0) for log in logs if log["type"] == "meal")
    total_water = sum(log["data"].get("glasses", 0) for log in logs if log["type"] == "water")
    total_steps = sum(log["data"].get("steps", 0) for log in logs if log["type"] == "steps")
    
    return {
        "calories": {
            "consumed": total_calories,
            "target": 2000, # Should come from diet plan
            "remaining": 2000 - total_calories
        },
        "water_intake": {
            "glasses": total_water,
            "target": 8
        },
        "activity": {
            "steps": total_steps,
            "target_steps": 10000
        }
    }