from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MealAdjustment(BaseModel):
    user_id: str
    date: str
    calories: float
    protein: Optional[float] = 0
    carbs: Optional[float] = 0
    fiber: Optional[float] = 0
    fat: Optional[float] = 0
    adjustment_days: Optional[int] = 7

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "date": "2024-01-20",
                "calories": 500,
                "protein": 20,
                "carbs": 60,
                "fiber": 5,
                "fat": 15,
                "adjustment_days": 7
            }
        }