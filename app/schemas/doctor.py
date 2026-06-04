from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal, Optional
from datetime import date, datetime

class PatientSummary(BaseModel):
    id: int
    name: str
    email: str
    gender: str
    subscription_status: str
    user_type: str
    date_of_birth: Optional[date]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    target_weight_kg: Optional[float]
    bmi: Optional[float]
    bmr: Optional[float]
    tdee: Optional[float]
    activity_level: Optional[str]
    diet_type: Optional[str]
    health_condition: Optional[str]
    health_goals: list[str] = []
    medical_conditions: list[str] = []
    food_allergies: list[str] = []
    meals_per_day: int
    # Token 1 fields
    token_1: Optional[str] = None
    token_1_active: bool = False
    token_1_expiry: Optional[datetime] = None
    renewal_requested: bool = False
    renewal_requested_at: Optional[datetime] = None
    expiring_soon: bool = False
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
    meals:        Optional[list[dict]] = None  # typed to dict; long-term goal: list[MealSlot]
    doctor_notes: Optional[str] = Field(default=None, max_length=2000)

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
    rejection_note: Optional[str] = Field(default=None, max_length=1000)

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
    content:   str = Field(..., min_length=1, max_length=5000)
    note_type: Literal["general", "dietary", "medical", "progress"] = "general"
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
    # Pydantic parses and validates '2026-03-10' automatically; handler converts back to str
    meal_date: date
    meal_type: Literal["Breakfast", "Lunch", "Dinner"]
    note: str = Field(..., min_length=1, max_length=1000)


class FoodItemSummary(BaseModel):
    id: int
    recipe_name: str
    slot_type: str
    cal_per_serving: float
    protein_per_serving: float
    carbs_per_serving: float
    fat_per_serving: float
    fiber_per_serving: float
    serving_weight_g: Optional[float] = None
    sodium_per_serving: Optional[float] = None
    diet_type: str
    meal_time_tags: list[str]
    plan_type_tags: list[str]
    source: str
    is_verified: bool
    image_url: Optional[str]
    doctor_id: Optional[int] = None
    model_config = {"from_attributes": True}


# Typed ingredient item — prevents arbitrary JSON injection into meal JSONB / AI prompts
class IngredientItem(BaseModel):
    name:     str = Field(..., min_length=1, max_length=100)
    quantity: str = Field(..., min_length=1, max_length=50)
    unit:     str = Field(..., min_length=1, max_length=20)


# Bounded tag list: max 10 tags, each max 50 chars
_BoundedTag = Annotated[str, Field(max_length=50)]
BoundedTagList = Annotated[list[_BoundedTag], Field(max_length=10)]


class RecipeCreateRequest(BaseModel):
    recipe_name:       str = Field(..., min_length=2, max_length=200)
    slot_type:         Literal[
        "grain", "dal_protein", "main_dish", "sabzi",
        "beverage", "snack_item", "fruit", "egg_dish"
    ]
    cal_per_serving:   float = Field(..., gt=0, le=5000)
    protein_per_serving: float = Field(default=0.0, ge=0, le=500)
    carbs_per_serving:   float = Field(default=0.0, ge=0, le=500)
    fat_per_serving:     float = Field(default=0.0, ge=0, le=500)
    fiber_per_serving:   float = Field(default=0.0, ge=0, le=200)
    diet_type:         Literal["Vegetarian", "Non-Vegetarian", "Eggetarian"]
    meal_time_tags:    BoundedTagList = Field(default_factory=list)
    plan_type_tags:    BoundedTagList = Field(default=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
    serving_weight_g:  float = Field(..., gt=0, le=10000)
    sodium_per_serving: Optional[float] = Field(default=None, ge=0, le=10000)
    ingredients:       Annotated[list[IngredientItem], Field(max_length=50)] = Field(default_factory=list)
    region_tags:       BoundedTagList = Field(default_factory=list)
    submit_to_global: bool = Field(
        default=False,
        description=(
            "False (default) = save to doctor's personal library only. "
            "True = also submit for admin approval to add to the global dataset used by all doctors."
        ),
    )


_VALID_SLOT_TYPES = Literal[
    "accompaniment", "beverage", "dal_protein", "grain",
    "main_dish", "one_pot", "sabzi", "snack_item",
]


class AddCustomDishRequest(BaseModel):
    recipe_name: str = Field(..., min_length=1, max_length=200)
    calories:    float = Field(..., gt=0, le=5000)
    protein:     float = Field(default=0.0, ge=0, le=500)
    carbs:       float = Field(default=0.0, ge=0, le=500)
    fat:         float = Field(default=0.0, ge=0, le=500)
    fiber:       float = Field(default=0.0, ge=0, le=200)
    diet_type:   str = "Vegetarian"
    slot_type:   _VALID_SLOT_TYPES = "main_dish"  # type: ignore[assignment]
    add_to_library:   bool = False
    serving_weight_g: Optional[float] = Field(default=None, gt=0, le=10000)


class DishAction(str, Enum):
    swap   = "swap"
    remove = "remove"
    add    = "add"


class CustomDishBody(BaseModel):
    recipe_name: str   = Field(..., min_length=1, max_length=200)
    calories:    float = Field(..., gt=0, le=5000)
    protein:     float = Field(default=0.0, ge=0, le=500)
    carbs:       float = Field(default=0.0, ge=0, le=500)
    fat:         float = Field(default=0.0, ge=0, le=500)
    fiber:       float = Field(default=0.0, ge=0, le=200)


class PatchDishRequest(BaseModel):
    action:              DishAction
    replacement_food_id: Optional[int]           = None  # existing food_items record
    custom_dish:         Optional[CustomDishBody] = None  # free-text dish
    flag_for_database:   bool                     = False  # True + custom_dish → submitted_for_review
    slot_type:           Optional[str]            = None  # passed through to new dish if custom


class RecipeAssignRequest(BaseModel):
    patient_ids: list[int] = Field(..., min_length=1)
    meal_type:   Literal["Breakfast", "Lunch", "Dinner"]
    meal_date:   date  # Pydantic parses '2026-03-15'; handler uses str(body.meal_date)
    note:        Optional[str] = Field(default=None, max_length=500)


class PatientVisitResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    token_2: str
    cycle_start: datetime
    cycle_expiry: datetime
    last_charged_at: Optional[datetime]
    visit_counter: int
    created_at: datetime
    model_config = {"from_attributes": True}


class RecordVisitResponse(BaseModel):
    charged: bool
    visit_counter: int
    last_charged_at: Optional[datetime]
    message: str


class RenewalApproveResponse(BaseModel):
    message: str
    token_1: str
    token_2: str
    token_1_expiry: datetime


class BulkRenewalResponse(BaseModel):
    approved_count: int
    patient_ids: list[int]


class PendingRenewalItem(BaseModel):
    patient_id: int
    patient_name: str
    patient_email: str
    token_1: Optional[str]
    renewal_requested_at: Optional[datetime]
    token_1_expiry: Optional[datetime]


class DoctorDashboardStats(BaseModel):
    total_patients: int
    active_patients: int
    pending_requests: int
    plans_generated_this_week: int
    inactive_patients: list[dict]
    expiring_soon: list[dict]


# ── Visit verification schemas ─────────────────────────────────────────────

class RecordVisitRequest(BaseModel):
    token_2: str = Field(..., min_length=5, max_length=100, description="Token 2 shown by the patient on their app")


class FlagVisitRequest(BaseModel):
    doctor_note: Optional[str] = Field(None, max_length=1000, description="Optional note for the patient about this flagged visit")


class PendingVisitApprovalResponse(BaseModel):
    id: int
    doctor_id: int
    visit_date: datetime
    doctor_note: Optional[str]
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Visit data on patient summary ─────────────────────────────────────────

class PatientSummaryWithVisit(PatientSummary):
    """PatientSummary extended with the latest visit cycle data."""
    token_2: Optional[str] = None
    visits_this_cycle: int = 0
    cycle_expiry: Optional[datetime] = None
    last_visit_at: Optional[datetime] = None
