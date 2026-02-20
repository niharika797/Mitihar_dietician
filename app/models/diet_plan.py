from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class Meal(BaseModel):
    """Represents a single meal with its details."""
    name: Optional[str] = None
    meal: Optional[str] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    similarity: Optional[float] = None  
    ingredients: List[str] | None = []
    instructions: str | None = ""

class MealPlan(BaseModel):
    """Represents a meal plan with meals categorized by type."""
    Breakfast: Optional[List[Meal]] = []
    MorningSnacks: Optional[List[Meal]] = []
    Lunch: Optional[List[Meal]] = []
    Dinner: Optional[List[Meal]] = []
    EveningSnacks: Optional[List[Meal]] = []

class DietPlan(BaseModel):
    """Represents the complete diet plan for a user."""
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    meals: Dict[str, List] = {}
    ingredient_checklist: List[Dict]=[]