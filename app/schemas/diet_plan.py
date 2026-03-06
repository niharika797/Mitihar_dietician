from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DietPlanResponse(BaseModel):
    """
    Replaces the legacy app/models/diet_plan.py DietPlan class.
    Matches the exact same fields so existing endpoints need only a class name swap.
    """
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    meals: list[dict] = []
    ingredient_checklist: list[dict] = []
    version: int = 1

    model_config = {"from_attributes": False}
