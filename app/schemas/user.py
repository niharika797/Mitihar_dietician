from pydantic import BaseModel, EmailStr, validator
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
    NON_VEGETARIAN = "Non Vegetarian"

class HealthCondition(str, Enum):
    HEALTHY = "Healthy"
    DIABETIC = "Diabetic-Friendly"
    GYM = "Gym-Friendly"

class UserBase(BaseModel):
    email: EmailStr
    name: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: ActivityLevel
    diet: DietType
    health_condition: HealthCondition
    diabetes_status: Optional[str] = None  # Allow None
    gym_goal: Optional[str] = None  # Allow None
    region: str


    @validator("diabetes_status", always=True, pre=True)
    def check_diabetes_status(cls, v, values):
        if values.get("health_condition") == HealthCondition.DIABETIC:
            if v not in ["controlled", "uncontrolled"]:
                raise ValueError("If diabetic, diabetes_status must be 'controlled' or 'uncontrolled'")
        return v
    @validator("gym_goal", always=True, pre=True)
    def check_gym_goal(cls, v, values):
        if values.get("health_condition") == HealthCondition.GYM:
            if v not in ["weight_loss", "muscle_gain", "maintenance"]:
                raise ValueError("If gym-friendly, gym_goal must be 'weight_loss', 'muscle_gain', or 'maintenance'")
        return v

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    diet: Optional[DietType] = None
    health_condition: Optional[HealthCondition] = None
    diabetes_status: Optional[str] = None  # Add this if updates can include it
    gym_goal: Optional[str] = None  # Add this if updates can include it
    region: Optional[str] = None

class UserResponse(UserBase):
    id: str
    meal_plan_purchased: bool

    class Config:
        from_attributes = True