from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MealLogCreate(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: float
    protein: Optional[float] = 0
    carbs: Optional[float] = 0
    fat: Optional[float] = 0

class WaterLogCreate(BaseModel):
    glasses: int

class StepsLogCreate(BaseModel):
    steps: int

class WeightLogCreate(BaseModel):
    weight: float

class ActivityLogCreate(BaseModel):
    steps: int
    calories_burned: Optional[float] = 0
    activity_type: Optional[str] = "Walking"
