from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import date, datetime

class OnboardingRequest(BaseModel):
    date_of_birth: date
    gender: str
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity_level: str = Field(default="LA")
    diet_type: str = Field(default="Vegetarian")
    region: str = Field(default="North")
    health_condition: str = Field(default="Healthy")
    health_goals: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    meals_per_day: int = Field(default=3)
    fasting_days: list[str] = Field(default_factory=list)
    sleep_hours: float = Field(default=7.0)
    water_glasses: int = Field(default=8)
    occupation: Optional[str] = None
    smoking: bool = False
    alcohol: bool = False
    nonveg_meals_per_week: int = 0
    pace_preference: str = Field(default="moderate")
    eating_habits: list[str] = Field(default_factory=list)
    target_weight_kg: Optional[float] = None

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
    pace_preference: Optional[str] = None
    eating_habits: list = []
    bmi: Optional[float]
    bmr: Optional[float]
    tdee: Optional[float]
    is_active: bool
    # Onboarding completion gate — used by login to skip re-onboarding
    disclaimer_accepted_at: Optional[datetime] = None
    # Subscription expiry date
    subscription_end_date: Optional[datetime] = None
    # Token 1 — subscription identifier shown to doctor
    token_1: Optional[str] = None
    token_1_active: bool = False
    token_1_expiry: Optional[datetime] = None
    renewal_requested: bool = False
    renewal_requested_at: Optional[datetime] = None
    expiring_soon: bool = False

    model_config = {"from_attributes": True}


class PublicDoctorResponse(BaseModel):
    """Public-safe doctor profile returned to patients browsing the directory."""
    id: int
    name: str
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    experience_years: Optional[int] = 0
    fee_per_month: Optional[int] = 0
    rating: Optional[float] = 0.0
    review_count: Optional[int] = 0
    is_accepting: bool = True

    model_config = ConfigDict(from_attributes=True)

class ActivationResponse(BaseModel):
    patient: PatientProfileResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
