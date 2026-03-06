from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date

class OnboardingRequest(BaseModel):
    date_of_birth: date
    health_goals: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)
    target_weight_kg: float = Field(..., gt=0)
    meals_per_day: Literal[3, 5]
    sleep_hours: float = Field(..., gt=0, le=24)
    water_glasses: int = Field(default=8, ge=0)
    occupation: str
    nonveg_meals_per_week: int = Field(default=3, ge=0, le=7)
    dietary_preferences: list[str] = Field(default_factory=list)
    fasting_days: list[str] = Field(default_factory=list)
    smoking: bool = False
    alcohol: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def dob_must_be_past(cls, v):
        if v >= date.today():
            raise ValueError("date_of_birth must be a past date")
        return v

class ActivationRequest(BaseModel):
    code: str = Field(..., min_length=1)

class DoctorRequestBody(BaseModel):
    doctor_id: int = Field(..., gt=0)

class PatientProfileResponse(BaseModel):
    id: int
    email: str
    name: str
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: str
    diet_type: str
    region: str
    user_type: str
    subscription_status: str
    doctor_id: Optional[int]
    date_of_birth: Optional[date]
    health_goals: list
    medical_conditions: list
    food_allergies: list
    dietary_preferences: list
    target_weight_kg: Optional[float]
    meals_per_day: int
    sleep_hours: Optional[float]
    water_glasses: int
    occupation: Optional[str]
    nonveg_meals_per_week: int
    bmi: Optional[float]
    bmr: Optional[float]
    tdee: Optional[float]
    is_active: bool

    model_config = {"from_attributes": True}
