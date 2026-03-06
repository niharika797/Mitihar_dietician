from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class CreateDoctorRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    city: Optional[str] = None

class DoctorAdminView(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    specialization: Optional[str]
    clinic_name: Optional[str]
    city: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class PlatformStats(BaseModel):
    total_patients: int
    active_subscriptions: int
    total_doctors: int
    total_plans_generated: int
