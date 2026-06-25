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
    combos: list[dict] = []
    # R-2: 84 weekly_combos rows (4 per slot) — [] for v1, populated for v2.
    ingredient_checklist: list[dict] = []
    version: int = 1
    generation_version: int = 1
    # 1 = legacy single-combo JSONB (meals); 2 = relational multi-combo (combos).
    used_food_ids: list[int] = []
    # IDs of every food_item used in this plan — persisted for cross-week variety

    model_config = {"from_attributes": False}
