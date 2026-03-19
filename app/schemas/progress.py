from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime
from typing import Optional

class MealLogCreate(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: float
    protein: Optional[float] = 0
    carbs: Optional[float] = 0
    fat: Optional[float] = 0
    fiber: Optional[float] = 0
    recommendation_id: Optional[int] = Field(default=None)
    # ID of the recommendation this meal was taken from. Null for custom meals.

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

class MealLogUpdate(BaseModel):
    meal_type: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    notes: Optional[str] = None

class MealLogResponse(BaseModel):
    id: int
    meal_type: str
    logged_date: date          # ORM column is Date, not DateTime
    calories_consumed: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    notes: Optional[str]
    model_config = {"from_attributes": True}

class WeightEntry(BaseModel):
    log_date: date             # ORM column is Date, not DateTime
    weight_kg: float

class WeeklyReportResponse(BaseModel):
    week_start: str
    week_end: str
    daily: list[dict]
    totals: dict
    averages: dict


# ── Phase 8 Tier 0: meal rating schemas ──────────────────────────────────────

class MealRateRequest(BaseModel):
    food_item_id:      int           = Field(..., gt=0)
    recommendation_id: Optional[int] = Field(default=None)
    rating:            int           = Field(..., description="+1 (liked) or -1 (disliked)")

    @model_validator(mode="after")
    def check_rating_value(self):
        if self.rating not in (1, -1):
            raise ValueError("rating must be +1 or -1")
        return self


class MealRatingResponse(BaseModel):
    id:                int
    patient_id:        int
    food_item_id:      int
    recommendation_id: Optional[int]
    rating:            int
    rated_at:          datetime
    model_config = {"from_attributes": True}
