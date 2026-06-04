from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime
from typing import Literal, Optional

class MealLogCreate(BaseModel):
    meal_type: Literal["Breakfast", "Lunch", "Dinner"]
    calories: float    = Field(..., ge=0, le=5000)
    protein:  Optional[float] = Field(default=0, ge=0, le=500)
    carbs:    Optional[float] = Field(default=0, ge=0, le=500)
    fat:      Optional[float] = Field(default=0, ge=0, le=500)
    fiber:    Optional[float] = Field(default=0, ge=0, le=200)
    recommendation_id: Optional[int] = Field(default=None)
    # ID of the recommendation this meal was taken from. Null for custom meals.

class WaterLogCreate(BaseModel):
    glasses: int = Field(..., ge=0, le=50)

class StepsLogCreate(BaseModel):
    steps: int = Field(..., ge=0, le=100_000)

class WeightLogCreate(BaseModel):
    weight: float = Field(..., gt=0, le=500)

class ActivityLogCreate(BaseModel):
    steps: int = Field(..., ge=0, le=100_000)
    calories_burned: Optional[float] = Field(default=0, ge=0, le=10_000)
    activity_type: Optional[str] = Field(default="Walking", max_length=100)

class MealLogUpdate(BaseModel):
    meal_type: Optional[Literal["Breakfast", "Lunch", "Dinner"]] = None
    calories: Optional[float] = Field(default=None, ge=0, le=5000)
    protein: Optional[float] = Field(default=None, ge=0, le=500)
    carbs: Optional[float] = Field(default=None, ge=0, le=500)
    fat: Optional[float] = Field(default=None, ge=0, le=500)
    fiber: Optional[float] = Field(default=None, ge=0, le=200)
    notes: Optional[str] = Field(default=None, max_length=1000)

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
