from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class MealBase(BaseModel):
    name: str
    calories: float
    proteins: float
    carbs: float
    fats: float
    ingredients: List[str]
    instructions: str


class DietPlanBase(BaseModel):
    daily_calories: float
    meals_per_day: int
    meal_plan: Dict[str, List[MealBase]]

class DietPlanCreate(DietPlanBase):
    user_id: str

class DietPlanUpdate(BaseModel):
    daily_calories: Optional[float] = None
    meals_per_day: Optional[int] = None
    meal_plan: Optional[Dict[str, List[MealBase]]] = None

class DietPlanResponse(DietPlanBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True