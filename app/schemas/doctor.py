from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class PatientSummary(BaseModel):
    id: int
    name: str
    email: str
    gender: str
    subscription_status: str
    user_type: str
    date_of_birth: Optional[date]
    bmi: Optional[float]
    bmr: Optional[float]
    tdee: Optional[float]
    meals_per_day: int
    model_config = {"from_attributes": True}

class PaginatedPatients(BaseModel):
    patients: list[PatientSummary]
    total: int
    page: int
    page_size: int

class RecommendationDetail(BaseModel):
    id: int
    patient_id: int
    week_start_date: Optional[date]
    meals: list
    ingredient_checklist: list
    is_active: bool
    generated_by: str
    doctor_notes: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class PlanOverrideRequest(BaseModel):
    meals: Optional[list] = None
    doctor_notes: Optional[str] = None

class PatientRequestDetail(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    status: str
    rejection_note: Optional[str]
    requested_at: datetime
    responded_at: Optional[datetime]
    patient: PatientSummary
    model_config = {"from_attributes": True}

class RejectRequest(BaseModel):
    rejection_note: Optional[str] = Field(default=None)

class GenerateCodesRequest(BaseModel):
    count: int = Field(..., ge=1, le=50)
    expires_in_days: int = Field(default=30, ge=1, le=365)

class SubscriptionCodeDetail(BaseModel):
    id: int
    code: str
    is_used: bool
    used_by_patient_id: Optional[int]
    used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}
