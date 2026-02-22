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

class HealthCondition(str, Enum):
    HEALTHY = "Healthy"
    DIABETIC = "Diabetic-Friendly"
    GYM = "Gym-Friendly"

class UserBase(BaseModel):
    email: EmailStr
    name: str
    age: int = Field(..., gt=0)
    gender: str
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    activity_level: ActivityLevel
    diet: DietType
    health_condition: HealthCondition
    diabetes_status: Optional[str] = None  # Allow None
    gym_goal: Optional[str] = None  # Allow None
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
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    age: Optional[int] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    weight: Optional[float] = Field(None, gt=0)
    activity_level: Optional[ActivityLevel] = None
    diet: Optional[DietType] = None
    health_condition: Optional[HealthCondition] = None
    diabetes_status: Optional[str] = None  # Add this if updates can include it
    gym_goal: Optional[str] = None  # Add this if updates can include it
    region: Optional[str] = None

class UserResponse(UserBase):
    id: str
    meal_plan_purchased: bool

    model_config = ConfigDict(from_attributes=True)