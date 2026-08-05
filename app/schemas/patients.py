from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Annotated, Optional, Literal
from datetime import date, datetime
from .user import ActivityLevel, DietType, HealthCondition

# Bounded list type: max 20 items, each item max 100 chars.
# Prevents DoS via oversized payloads and prompt-injection via unbounded strings.
# Uses explicit Annotated constraints; enforced by field_validator below as defence-in-depth.
_BoundedStr = Annotated[str, Field(max_length=100)]
BoundedStrList = Annotated[list[_BoundedStr], Field(max_length=20)]

class OnboardingRequest(BaseModel):
    date_of_birth:        date
    # T4-5: use enums/Literals — reject any value not in the allowed set
    gender:               Literal["Male", "Female", "Other"]
    height_cm:            float          = Field(..., gt=0)
    weight_kg:            float          = Field(..., gt=0)
    activity_level:       ActivityLevel  = ActivityLevel.LIGHTLY_ACTIVE
    diet_type:            DietType       = DietType.VEGETARIAN
    region:               Literal["North", "South", "East", "West"] = "North"
    health_condition:     HealthCondition = HealthCondition.HEALTHY
    # T4-6: bounded list fields — cap item count and per-item length
    health_goals:         BoundedStrList = Field(default_factory=list)
    medical_conditions:   BoundedStrList = Field(default_factory=list)
    food_allergies:       BoundedStrList = Field(default_factory=list)
    dietary_preferences:  BoundedStrList = Field(default_factory=list)
    fasting_days:         BoundedStrList = Field(default_factory=list)
    eating_habits:        BoundedStrList = Field(default_factory=list)
    # T4-7: numeric bounds
    meals_per_day:        int            = Field(default=3,   ge=1, le=10)
    sleep_hours:          float          = Field(default=7.0, ge=0, le=24)
    water_glasses:        int            = Field(default=8,   ge=0, le=30)
    nonveg_meals_per_week: int           = Field(default=0,   ge=0, le=21)
    target_weight_kg:     Optional[float] = Field(default=None, gt=0, le=500)
    occupation:           Optional[str]  = Field(default=None, max_length=100)
    # T4-5: enum for pace_preference
    pace_preference:      Literal["slow", "moderate", "fast"] = "moderate"
    smoking:              bool = False
    alcohol:              bool = False

    @field_validator("occupation", mode="before")
    @classmethod
    def strip_occupation(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("date_of_birth")
    @classmethod
    def dob_must_be_past(cls, v):
        if v >= date.today():
            raise ValueError("date_of_birth must be a past date")
        return v

    @field_validator(
        "health_goals", "medical_conditions", "food_allergies",
        "dietary_preferences", "fasting_days", "eating_habits",
        mode="before"
    )
    @classmethod
    def validate_bounded_list(cls, v):
        """Defence-in-depth: explicitly enforce list size and item length."""
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("Must be a list")
        if len(v) > 20:
            raise ValueError("List must contain at most 20 items")
        for item in v:
            if isinstance(item, str) and len(item) > 100:
                raise ValueError("Each item must be at most 100 characters")
        return v

class ActivationRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1)

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


class RespondVisitRequest(BaseModel):
    """Patient's response to a doctor-flagged visit.

    Approving is a billing event — it can increment PatientVisit.visit_counter,
    which is what revenue is summed from — so the action is an explicit literal
    rather than a bool, to keep the intent unambiguous at the call site.
    """
    action: Literal["approve", "reject"]
