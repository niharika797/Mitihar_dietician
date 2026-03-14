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

class MealLogEntry(BaseModel):
    id: int
    logged_date: date
    meal_type: str
    calories_consumed: float
    protein_g: float
    carbs_g: float
    fat_g: float
    recommendation_id: Optional[int]
    custom_food_name: Optional[str]
    notes: Optional[str]
    model_config = {"from_attributes": True}

class PatientProgressEntry(BaseModel):
    log_date: date
    weight_kg: Optional[float]
    water_glasses: Optional[int]
    steps: Optional[int]
    streak_days: int
    model_config = {"from_attributes": True}

class PatientLogsResponse(BaseModel):
    patient_id: int
    period_days: int
    meal_logs: list[MealLogEntry]

class PatientProgressResponse(BaseModel):
    patient_id: int
    period_days: int
    progress_logs: list[PatientProgressEntry]


class ClinicalNoteCreate(BaseModel):
    content: str = Field(..., min_length=1)
    note_type: str = Field(default="general")
    # "general" | "dietary" | "medical" | "progress"
    is_private: bool = True


class ClinicalNoteResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    note_type: str
    content: str
    is_private: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MealPlanNoteRequest(BaseModel):
    meal_date: str = Field(..., description="Date string matching meal's 'Date' key e.g. '2026-03-10'")
    meal_type: str = Field(..., description="e.g. 'Breakfast', 'Lunch'")
    note: str = Field(..., min_length=1)


class FoodItemSummary(BaseModel):
    id: int
    recipe_name: str
    slot_type: str
    cal_per_serving: float
    protein_per_serving: float
    carbs_per_serving: float
    fat_per_serving: float
    fiber_per_serving: float
    diet_type: str
    meal_time_tags: list[str]
    plan_type_tags: list[str]
    source: str
    is_verified: bool
    image_url: Optional[str]
    doctor_id: Optional[int] = None
    model_config = {"from_attributes": True}


class RecipeCreateRequest(BaseModel):
    recipe_name: str = Field(..., min_length=2)
    slot_type: str = Field(..., description="grain | dal_protein | main_dish | sabzi | beverage | snack | fruit | egg_dish")
    cal_per_serving: float = Field(..., gt=0)
    protein_per_serving: float = Field(default=0.0, ge=0)
    carbs_per_serving: float = Field(default=0.0, ge=0)
    fat_per_serving: float = Field(default=0.0, ge=0)
    fiber_per_serving: float = Field(default=0.0, ge=0)
    diet_type: str = Field(..., description="Vegetarian | Non-Vegetarian | Eggetarian")
    meal_time_tags: list[str] = Field(default_factory=list)
    plan_type_tags: list[str] = Field(default=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
    ingredients: list[dict] = Field(default_factory=list)
    # [{"name": "Onion", "amount_g": 50}]
    region_tags: list[str] = Field(default_factory=list)
    save_to_library: bool = Field(default=True, description="True = save to food_items pending approval. False = not yet supported.")


class RecipeAssignRequest(BaseModel):
    patient_ids: list[int] = Field(..., min_length=1)
    meal_type: str = Field(..., description="Breakfast | MorningSnacks | Lunch | EveningSnacks | Dinner")
    meal_date: str = Field(..., description="Date string e.g. '2026-03-15'")
    note: Optional[str] = None


class DoctorDashboardStats(BaseModel):
    total_patients: int
    active_patients: int          # subscription_status == "active"
    pending_requests: int         # PatientRequest with status == "pending"
    plans_generated_this_week: int
    inactive_patients: list[dict] # patients with no logs in last 7 days
    expiring_soon: list[dict]     # patients whose subscription_end_date is within 7 days
