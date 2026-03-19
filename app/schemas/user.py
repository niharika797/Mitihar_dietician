from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, Field
from typing import Optional
from enum import Enum


class ActivityLevel(str, Enum):
    SEDENTARY = "S"
    LIGHTLY_ACTIVE = "LA"
    MODERATELY_ACTIVE = "MA"
    VERY_ACTIVE = "VA"
    SUPER_ACTIVE = "SA"


class DietType(str, Enum):
    VEGETARIAN = "Vegetarian"
    NON_VEGETARIAN = "Non-Vegetarian"
    EGGETARIAN = "Eggetarian"


class HealthCondition(str, Enum):
    HEALTHY = "Healthy"
    DIABETIC = "Diabetic-Friendly"
    GYM = "Gym-Friendly"


class UserBase(BaseModel):
    email: EmailStr
    name: str
    age: Optional[int] = Field(None, gt=0)
    gender: str
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    activity_level: ActivityLevel
    diet: DietType
    health_condition: HealthCondition
    diabetes_status: Optional[str] = None
    gym_goal: Optional[str] = None
    region: Optional[str] = None

    @field_validator("diabetes_status", mode="before")
    @classmethod
    def check_diabetes_status(cls, v, info):
        if info.data.get("health_condition") == HealthCondition.DIABETIC:
            if v not in ["controlled", "uncontrolled"]:
                raise ValueError("If diabetic, diabetes_status must be 'controlled' or 'uncontrolled'")
        return v

    @field_validator("gym_goal", mode="before")
    @classmethod
    def check_gym_goal(cls, v, info):
        if info.data.get("health_condition") == HealthCondition.GYM:
            if v not in ["weight_loss", "muscle_gain", "maintenance"]:
                raise ValueError("If gym-friendly, gym_goal must be 'weight_loss', 'muscle_gain', or 'maintenance'")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    doctor_code: Optional[str] = Field(default=None)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Enforce minimum password security policy:
        - At least 8 characters
        - At least one letter
        - At least one digit
        This prevents trivially weak passwords like '12345678' or 'aaaaaaaa'.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    age: Optional[int] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    weight: Optional[float] = Field(None, gt=0)
    activity_level: Optional[ActivityLevel] = None
    diet: Optional[DietType] = None
    health_condition: Optional[HealthCondition] = None
    diabetes_status: Optional[str] = None
    gym_goal: Optional[str] = None
    region: Optional[str] = None

class UserResponse(BaseModel):
    """Response model that maps Patient ORM fields to the API contract."""
    id: int
    email: EmailStr
    name: str
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: str
    diet_type: str
    health_condition: Optional[str] = None
    region: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)