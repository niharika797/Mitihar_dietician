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


class DoctorDetailView(DoctorAdminView):
    """Full doctor view with patient count."""
    patient_count: int = 0
    mfa_enabled: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditLogEntry(BaseModel):
    id: int
    actor_id: int
    actor_role: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    detail: dict
    ip_address: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedAuditLogs(BaseModel):
    logs: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


class GenerateCodesAdminRequest(BaseModel):
    doctor_id: int
    count: int = Field(..., ge=1, le=100)
    expires_in_days: int = Field(default=30, ge=1, le=365)


class CodeAdminView(BaseModel):
    id: int
    doctor_id: int
    code: str
    is_used: bool
    used_by_patient_id: Optional[int]
    expires_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class FoodAdminView(BaseModel):
    id: int
    recipe_name: str
    slot_type: str
    diet_type: str
    source: str
    is_verified: bool
    cal_per_serving: float
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminPatientView(BaseModel):
    id: int
    name: str
    email: str
    gender: str
    subscription_status: str
    user_type: str
    doctor_id: Optional[int]
    bmi: Optional[float]
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedAdminPatients(BaseModel):
    patients: list[AdminPatientView]
    total: int
    page: int
    page_size: int
