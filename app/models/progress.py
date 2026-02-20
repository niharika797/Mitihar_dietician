from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Progress(BaseModel):
    user_id: str
    date: datetime
    calories_consumed: float
    protein_percentage: float
    carbs_percentage: float
    fat_percentage: float
    weight: Optional[float] = None

class WeightLog(BaseModel):
    user_id: str
    date: datetime
    weight: float