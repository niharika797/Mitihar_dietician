from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserInDB(BaseModel):
    id: str
    email: EmailStr
    name: str
    hashed_password: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    diet: str
    meal_plan_purchased: bool
    created_at: datetime
    updated_at: datetime
    health_condition: Optional[str]=None
    region: Optional[str]=None

class User(BaseModel):
    email: EmailStr
    name: str
    password: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    diet: str
    meal_plan_purchased: bool = False
    health_condition: Optional[str]=None
    region: Optional[str]=None