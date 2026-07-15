# MITYAHAR — FULL BACKEND SPRINT PLAN
> Strategy: Complete all backend sprints (1–3) before touching any frontend.
> Rule: Execute blocks in strict order within each sprint. Bring each block output to Claude for audit before moving on.
> Each sprint block is a self-contained Antigravity prompt.

---

## SPRINT 1 — Phase 1 Backend Cleanup
**Goal:** Close every remaining Phase 1 backend gap. All Alembic migrations done first.
**Blocks:** 1-A → 1-B → 1-C → 1-D

---

### SPRINT 1 — BLOCK A
**Scope:** Alembic migration + ORM model column additions
**Files:** `app/models/db_models.py`, new Alembic migration file

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 1 · BLOCK A

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Alembic, Pydantic v2.
Existing Patient ORM model is in app/models/db_models.py.
Existing FoodItem ORM model is in app/models/db_models.py.
Alembic is already configured. Migration files live in alembic/versions/.

We need to add new columns to two existing tables.
DO NOT touch any other model, router, schema, or service file in this block.

=======================================================
TASK 1: Add columns to Patient ORM model in db_models.py
=======================================================

In the Patient class, add these 2 new columns AFTER the `alcohol` column:

    pace_preference     = Column(String(20), nullable=True)
    # Values: "slow" | "moderate" | "fast" — how quickly patient wants to reach goal
    
    eating_habits       = Column(JSONB, default={})
    # Stores: {"meal_timings": [...], "cuisine_preference": [...], "skip_meals": bool}

Also update the PatientProfileResponse schema (it's in app/schemas/patients.py) to expose
these two new fields. Add them AFTER the `nonveg_meals_per_week` field:

    pace_preference: Optional[str] = None
    eating_habits: dict = {}

=======================================================
TASK 2: Add image_url column to FoodItem ORM model in db_models.py
=======================================================

In the FoodItem class, add this column AFTER the `is_verified` column.
The comment DO NOT MODIFY refers to the existing nutrition columns — adding a new
column at the bottom of the class is safe.

    image_url           = Column(String(500), nullable=True)
    # Populated during Phase 6 ETL from eyantra dataset cross-reference

=======================================================
TASK 3: Write Alembic migration
=======================================================

Create a new file: alembic/versions/002_add_pace_eating_habits_image_url.py

The migration must:
1. Add `pace_preference` VARCHAR(20) NULL to patients table
2. Add `eating_habits` JSONB NOT NULL DEFAULT '{}' to patients table
3. Add `image_url` VARCHAR(500) NULL to food_items table

Use this exact template:

"""Add pace_preference, eating_habits to patients; image_url to food_items

Revision ID: 002
Revises: 001
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('patients',
        sa.Column('pace_preference', sa.String(20), nullable=True)
    )
    op.add_column('patients',
        sa.Column('eating_habits', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default='{}')
    )
    op.add_column('food_items',
        sa.Column('image_url', sa.String(500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('food_items', 'image_url')
    op.drop_column('patients', 'eating_habits')
    op.drop_column('patients', 'pace_preference')


NOTE: Replace `001` in `down_revision` with whatever the actual revision ID of the
most recent existing migration file is. Check alembic/versions/ for the correct value.
```

---

### SPRINT 1 — BLOCK B
**Scope:** Schema + onboarding + register split
**Files:** `app/schemas/patients.py`, `app/routers/patients.py`, `app/routers/auth.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 1 · BLOCK B

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Sprint 1 Block A must be complete before this block (new columns exist on Patient model).

Files to MODIFY:
  app/schemas/patients.py
  app/routers/patients.py
  app/routers/auth.py

=======================================================
MODIFICATION 1: app/schemas/patients.py
=======================================================

A) In OnboardingRequest, add these 2 fields AFTER the `alcohol` field
   and BEFORE the @field_validator:

    pace_preference: Optional[str] = None
    eating_habits: dict = Field(default_factory=dict)

   Add this validator AFTER the existing dob_must_be_past validator:

    @field_validator("pace_preference")
    @classmethod
    def validate_pace(cls, v):
        if v is not None and v not in ("slow", "moderate", "fast"):
            raise ValueError("pace_preference must be 'slow', 'moderate', or 'fast'")
        return v

   Also add `Optional` to the import line at the top:
   Change: from typing import Optional, Literal
   (it's already there — confirm it includes Optional, add it if missing)

B) In OnboardingRequest, change food_allergies field from:
    food_allergies: list[str] = Field(default_factory=list)
   To:
    food_allergies: list[str] = Field(default_factory=list)

   And add this validator AFTER the pace_preference validator:

    @field_validator("food_allergies")
    @classmethod
    def allergies_must_not_be_empty_for_connected(cls, v, info):
        # Only enforce non-empty when health_condition requires it.
        # For standalone patients, empty is allowed — they may have no allergies.
        # We store whatever they provide; allergy filtering happens in the meal generator.
        return v

   NOTE: We are NOT making it a hard required non-empty field — that UX decision
   is deferred. The validator is a no-op placeholder that documents the intent.

C) Add StandaloneRegisterRequest schema AFTER the existing DoctorRequestBody class:

class StandaloneRegisterRequest(BaseModel):
    """Registration for a patient without a doctor — standalone tier."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    gender: str
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    activity_level: str
    diet: str
    region: Optional[str] = "North"
    health_condition: Optional[str] = "Healthy"

class DoctorConnectedRegisterRequest(BaseModel):
    """Registration for a patient who already has a doctor and a subscription code."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    gender: str
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    activity_level: str
    diet: str
    region: Optional[str] = "North"
    health_condition: Optional[str] = "Healthy"
    subscription_code: str = Field(..., min_length=1)
    # Code is validated and consumed during registration

   Add `EmailStr` to the imports at the top of patients.py:
   from pydantic import BaseModel, Field, field_validator, EmailStr

=======================================================
MODIFICATION 2: app/routers/patients.py
=======================================================

A) In the onboard_patient endpoint, inside the .values() dict of update(Patient),
   add these 2 new fields AFTER the `alcohol=body.alcohol` line:

            pace_preference=body.pace_preference,
            eating_habits=body.eating_habits,

B) Add this new endpoint AFTER the accept_disclaimer endpoint at the bottom of patients.py:

# ─── POST /api/v1/patients/register/standalone ────────────────────────────

@router.post("/register/standalone", status_code=201)
async def register_standalone(
    body: StandaloneRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a standalone patient (no doctor, no subscription code).
    Patient starts with subscription_status='inactive' — they can browse but
    cannot access meal plans or progress tracking until a doctor accepts them
    or they enter a subscription code later.
    """
    from ..services.user_service import create_patient, get_patient_by_email
    from sqlalchemy.exc import IntegrityError

    existing = await get_patient_by_email(session, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        patient_id = await create_patient(session, data={
            "email": body.email,
            "password": body.password,
            "name": body.name,
            "gender": body.gender,
            "height": body.height,
            "weight": body.weight,
            "activity_level": body.activity_level,
            "diet": body.diet,
            "region": body.region or "North",
            "health_condition": body.health_condition or "Healthy",
        })
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")

    return {
        "message": "Registration successful",
        "user_id": patient_id,
        "user_type": "standalone",
        "next_step": "Complete onboarding at POST /api/v1/patients/onboarding",
    }


# ─── POST /api/v1/patients/register/doctor-connected ──────────────────────

@router.post("/register/doctor-connected", status_code=201)
async def register_doctor_connected(
    body: DoctorConnectedRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a patient who already has a subscription code from their doctor.
    Validates and consumes the code during registration.
    Patient starts with subscription_status='active' and doctor_id set.
    """
    from ..services.user_service import create_patient, get_patient_by_email
    from sqlalchemy.exc import IntegrityError
    from datetime import datetime, timezone

    existing = await get_patient_by_email(session, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate subscription code BEFORE creating patient
    now = datetime.now(timezone.utc)
    code_result = await session.execute(
        select(SubscriptionCode).where(
            SubscriptionCode.code == body.subscription_code,
            SubscriptionCode.is_used == False,
            SubscriptionCode.expires_at > now,
        )
    )
    code_row = code_result.scalars().first()
    if code_row is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already-used subscription code",
        )

    try:
        patient_id = await create_patient(session, data={
            "email": body.email,
            "password": body.password,
            "name": body.name,
            "gender": body.gender,
            "height": body.height,
            "weight": body.weight,
            "activity_level": body.activity_level,
            "diet": body.diet,
            "region": body.region or "North",
            "health_condition": body.health_condition or "Healthy",
        })
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Consume code and activate patient immediately
    code_row.is_used = True
    code_row.used_by_patient_id = patient_id
    code_row.used_at = now

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            subscription_status="active",
            doctor_id=code_row.doctor_id,
            user_type="doctor_assigned",
        )
    )
    await session.flush()

    return {
        "message": "Registration successful",
        "user_id": patient_id,
        "user_type": "doctor_assigned",
        "next_step": "Complete onboarding at POST /api/v1/patients/onboarding",
    }

Also add StandaloneRegisterRequest and DoctorConnectedRegisterRequest to the import:
from ..schemas.patients import (
    OnboardingRequest, ActivationRequest, DoctorRequestBody, PatientProfileResponse,
    StandaloneRegisterRequest, DoctorConnectedRegisterRequest,
)

=======================================================
MODIFICATION 3: app/routers/auth.py
=======================================================

The existing POST /register endpoint is now DEPRECATED in favour of the two new
split endpoints in patients.py. Add a deprecation note to the existing endpoint
but DO NOT remove it (backward compatibility):

Change the existing register endpoint docstring to:
    """
    DEPRECATED — use POST /api/v1/patients/register/standalone or
    POST /api/v1/patients/register/doctor-connected instead.
    Kept for backward compatibility only.
    """

No other changes to auth.py.
```

---

### SPRINT 1 — BLOCK C
**Scope:** Recommendation slot linking + adherence calculation
**Files:** `app/schemas/progress.py`, `app/services/progress_service.py`, `app/routers/progress.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 1 · BLOCK C

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.

ORM models relevant here:
  MealLog: id, patient_id, recommendation_id (nullable FK), logged_date, meal_type,
           food_id (nullable), custom_food_name, calories_consumed, protein_g, carbs_g,
           fat_g, fiber_g, portion_servings, notes, created_at
  Recommendation: id, patient_id, meals (JSONB list), is_active, created_at

Files to MODIFY:
  app/schemas/progress.py
  app/services/progress_service.py
  app/routers/progress.py

DO NOT modify db_models.py — recommendation_id already exists as nullable FK on meal_logs.
DO NOT run Alembic — no new columns needed.

=======================================================
MODIFICATION 1: app/schemas/progress.py
=======================================================

A) Change the existing MealLogCreate class to optionally accept recommendation_id
   and meal_slot. Replace the current class with:

class MealLogCreate(BaseModel):
    meal_type: str  # Breakfast, MorningSnacks, Lunch, EveningSnacks, Dinner, snack
    calories: float
    protein: Optional[float] = 0
    carbs: Optional[float] = 0
    fat: Optional[float] = 0
    fiber: Optional[float] = 0
    recommendation_id: Optional[int] = None
    # If provided, links this log to the specific recommendation slot
    # Enables adherence tracking (did patient eat what was recommended?)

B) Add this response schema AFTER WeeklyReportResponse:

class AdherenceDay(BaseModel):
    date: str
    recommended_slots: int
    logged_slots: int
    adherence_pct: float   # 0.0 – 100.0

class WeeklyAdherenceResponse(BaseModel):
    week_start: str
    week_end: str
    daily: list[AdherenceDay]
    overall_pct: float

=======================================================
MODIFICATION 2: app/services/progress_service.py
=======================================================

A) Modify the existing log_meal function to accept and store recommendation_id.
Replace the current log_meal function with:

async def log_meal(
    session: AsyncSession,
    patient_id: int,
    data: dict,
) -> MealLog:
    """Insert a row into meal_logs. Returns the created MealLog."""
    entry = MealLog(
        patient_id=patient_id,
        logged_date=date.today(),
        meal_type=data.get("meal_type", "Breakfast"),
        calories_consumed=data.get("calories", 0),
        protein_g=data.get("protein", 0),
        carbs_g=data.get("carbs", 0),
        fat_g=data.get("fat", 0),
        fiber_g=data.get("fiber", 0),
        recommendation_id=data.get("recommendation_id"),
        # recommendation_id is nullable — free logs (no plan) still work
    )
    session.add(entry)
    await session.flush()
    return entry

B) Add this new function to the BOTTOM of progress_service.py:

async def calculate_weekly_adherence(
    session: AsyncSession,
    patient_id: int,
) -> dict:
    """
    Adherence = how many recommended meal slots the patient actually logged.

    Logic:
      For each of the last 7 days:
        - Count how many MealLogs exist where recommendation_id IS NOT NULL
          (i.e. the patient logged a meal tied to a specific recommendation slot)
        - Count how many meal slots were recommended in the active plan for that date
          (from the JSONB meals array on the Recommendation row)
        - adherence_pct = (logged_slots / recommended_slots) * 100

    If no active recommendation exists, all days return 0% adherence.
    Days where the patient had no recommendation and no logs are 0%.
    """
    from datetime import timedelta
    from sqlalchemy import func as sa_func

    today = date.today()
    start = today - timedelta(days=6)

    # Get the active recommendation for date-slot mapping
    rec_result = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == patient_id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalars().first()

    # Build a dict: date_str → number of recommended slots that day
    recommended_by_date: dict[str, int] = {}
    if rec and rec.meals:
        for meal in rec.meals:
            day = meal.get("Date")
            if day:
                recommended_by_date[day] = recommended_by_date.get(day, 0) + 1

    # Count linked logs per day (recommendation_id IS NOT NULL)
    logged_result = await session.execute(
        select(
            MealLog.logged_date,
            sa_func.count(MealLog.id).label("linked_count"),
        )
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
            MealLog.recommendation_id.isnot(None),
        )
        .group_by(MealLog.logged_date)
    )
    logged_by_date = {str(r.logged_date): r.linked_count for r in logged_result.all()}

    daily = []
    total_recommended = 0
    total_logged = 0

    for i in range(7):
        day = start + timedelta(days=i)
        day_str = str(day)
        recommended = recommended_by_date.get(day_str, 0)
        logged = logged_by_date.get(day_str, 0)
        pct = round((logged / recommended * 100), 1) if recommended > 0 else 0.0

        total_recommended += recommended
        total_logged += logged
        daily.append({
            "date": day_str,
            "recommended_slots": recommended,
            "logged_slots": logged,
            "adherence_pct": pct,
        })

    overall_pct = round((total_logged / total_recommended * 100), 1) if total_recommended > 0 else 0.0

    return {
        "week_start": str(start),
        "week_end": str(today),
        "daily": daily,
        "overall_pct": overall_pct,
    }

=======================================================
MODIFICATION 3: app/routers/progress.py
=======================================================

A) Add calculate_weekly_adherence to the existing import from progress_service:
   Append it to the existing from ..services.progress_service import (...) block:
   calculate_weekly_adherence

B) Add WeeklyAdherenceResponse to the existing import from schemas.progress:
   Append it to the existing from ..schemas.progress import (...) block:
   WeeklyAdherenceResponse, AdherenceDay

C) In the existing post_log_meal endpoint, change this line:
    await log_meal(session, current_user.id, meal.model_dump())
   To:
    await log_meal(session, current_user.id, meal.model_dump())
   (no change needed — log_meal now accepts recommendation_id via model_dump())

D) Add this new endpoint to the BOTTOM of progress.py:

# ─── GET /api/v1/progress/adherence/weekly ───────────────────────────────

@router.get("/adherence/weekly", response_model=WeeklyAdherenceResponse)
async def get_weekly_adherence(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns the patient's meal adherence for the last 7 days.
    Adherence = recommended meal slots actually logged (linked to recommendation).
    Returns 0% for days with no active plan.
    """
    result = await calculate_weekly_adherence(session, current_user.id)
    return result
```

---

### SPRINT 1 — BLOCK D
**Scope:** Plan version counter + shopping list "available at home" toggle
**Files:** `app/services/diet_plan_service.py`, `app/routers/meal_plan.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 1 · BLOCK D

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Files to MODIFY: app/services/diet_plan_service.py, app/routers/meal_plan.py

ORM model: Recommendation has a `version` Integer column, default=1.
Currently when a plan is regenerated, the old plan is soft-deleted (is_active=False)
and a new Recommendation row is inserted — but version always starts at 1 again.

=======================================================
MODIFICATION 1: app/services/diet_plan_service.py
=======================================================

Modify the store_diet_plan method. Find the current implementation:

    async def store_diet_plan(self, diet_plan: DietPlan, *, session: AsyncSession) -> int:
        rec = Recommendation(
            patient_id=int(diet_plan.user_id),
            week_start_date=date.today(),
            meals=diet_plan.meals,
            ingredient_checklist=diet_plan.ingredient_checklist,
            is_active=True,
        )
        session.add(rec)
        await session.flush()
        return rec.id

Replace it with:

    async def store_diet_plan(self, diet_plan: DietPlan, *, session: AsyncSession) -> int:
        """
        Insert a new recommendation row.
        Version = max existing version for this patient + 1.
        Returns the new row's id.
        """
        from sqlalchemy import func as sa_func

        # Find the current highest version for this patient
        version_result = await session.execute(
            select(sa_func.coalesce(sa_func.max(Recommendation.version), 0))
            .where(Recommendation.patient_id == int(diet_plan.user_id))
        )
        next_version = (version_result.scalar() or 0) + 1

        rec = Recommendation(
            patient_id=int(diet_plan.user_id),
            week_start_date=date.today(),
            meals=diet_plan.meals,
            ingredient_checklist=diet_plan.ingredient_checklist,
            is_active=True,
            version=next_version,
        )
        session.add(rec)
        await session.flush()
        return rec.id

=======================================================
MODIFICATION 2: app/routers/meal_plan.py
=======================================================

Add these 2 new endpoints to the BOTTOM of meal_plan.py.
Do not modify any existing endpoint.

# ─── POST /api/v1/meal-plan/shopping-list/toggle ─────────────────────────

@router.post("/shopping-list/toggle")
async def toggle_ingredient_available(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    ingredient_name: str = Query(..., description="Exact ingredient name to toggle"),
):
    """
    Mark an ingredient as 'available at home' or toggle it back.
    Stores availability in today's ProgressLog as a JSONB list on a new field.

    Implementation: uses a simple patient-level key-value via a new DB approach.
    We store the list of 'available at home' ingredient names in the active
    Recommendation row under a new key in ingredient_checklist items.

    Finds the matching item in ingredient_checklist (case-insensitive name match)
    and flips its 'available_at_home' boolean key.
    Returns 404 if ingredient not found in current active plan.
    """
    diet_service = DietPlanService()
    plan_rec = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == current_user.id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = plan_rec.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    checklist = list(rec.ingredient_checklist or [])
    name_lower = ingredient_name.strip().lower()
    found = False

    for item in checklist:
        item_name = str(item.get("ingredient") or item.get("name") or "").lower()
        if item_name == name_lower:
            item["available_at_home"] = not item.get("available_at_home", False)
            found = True
            break

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient '{ingredient_name}' not found in current plan checklist",
        )

    # SQLAlchemy won't detect in-place JSONB mutations — reassign the list
    from copy import deepcopy
    rec.ingredient_checklist = deepcopy(checklist)
    await session.flush()

    toggled_item = next(
        (i for i in checklist if str(i.get("ingredient") or i.get("name") or "").lower() == name_lower),
        None,
    )
    return {
        "ingredient": ingredient_name,
        "available_at_home": toggled_item.get("available_at_home", False) if toggled_item else False,
    }


# ─── GET /api/v1/meal-plan/shopping-list/available ───────────────────────

@router.get("/shopping-list/available")
async def get_available_ingredients(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns only the ingredients the patient has marked as 'available at home'.
    Returns empty list if no active plan or none marked.
    """
    plan_rec = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == current_user.id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = plan_rec.scalars().first()
    if rec is None:
        return {"available": []}

    available = [
        item for item in (rec.ingredient_checklist or [])
        if item.get("available_at_home") is True
    ]
    return {"available": available, "count": len(available)}

Also add this import at the top of meal_plan.py if not already present:
from fastapi import Query
```

---
---

## SPRINT 2 — Phase 2 Doctor Backend (12 remaining endpoints)
**Goal:** Complete all doctor-facing backend endpoints so the doctor dashboard frontend has a full API contract.
**Blocks:** 2-A → 2-B → 2-C

---

### SPRINT 2 — BLOCK A
**Scope:** Patient data views for doctor (logs + progress)
**Files:** `app/routers/doctor.py`, `app/schemas/doctor.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 2 · BLOCK A

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Files to MODIFY: app/routers/doctor.py, app/schemas/doctor.py

Existing doctor router has these endpoints:
  GET  /doctor/patients              — paginated list
  GET  /doctor/patients/{id}         — profile
  GET  /doctor/patients/{id}/plan    — active plan
  PUT  /doctor/patients/{id}/plan    — override plan
  GET  /doctor/requests              — pending requests
  POST /doctor/requests/{id}/accept  — accept
  POST /doctor/requests/{id}/reject  — reject
  POST /doctor/subscription-codes    — generate codes
  GET  /doctor/subscription-codes    — list codes

Security: every endpoint uses _doctor_id(request) which reads from JWT middleware.
Patient ownership check = Patient.doctor_id == did.

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD new schemas
=======================================================

Add these schemas to the BOTTOM of doctor.py:

class MealLogEntry(BaseModel):
    id: int
    logged_date: date
    meal_type: str
    calories_consumed: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    notes: Optional[str]
    recommendation_id: Optional[int]
    # recommendation_id present = patient logged a recommended meal
    # recommendation_id None    = patient logged a free/custom meal
    model_config = {"from_attributes": True}

class PatientLogsResponse(BaseModel):
    patient_id: int
    logs: list[MealLogEntry]
    total_logs: int

class ProgressEntry(BaseModel):
    log_date: date
    weight_kg: Optional[float]
    water_glasses: Optional[int]
    steps: Optional[int]
    calories_burned: Optional[float]
    streak_days: int
    model_config = {"from_attributes": True}

class PatientProgressResponse(BaseModel):
    patient_id: int
    entries: list[ProgressEntry]
    total_entries: int

Add `date` to the imports at top of doctor.py schemas file:
from datetime import date, datetime

=======================================================
MODIFICATION 2: app/routers/doctor.py — ADD 2 endpoints
=======================================================

Add these 2 endpoints AFTER the override_patient_plan endpoint.
Do not modify any existing endpoint.

Also add to the top imports:
from ..models.db_models import Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode, MealLog, ProgressLog
from ..schemas.doctor import (
    PatientSummary, PaginatedPatients, RecommendationDetail,
    PlanOverrideRequest, PatientRequestDetail, RejectRequest,
    GenerateCodesRequest, SubscriptionCodeDetail,
    MealLogEntry, PatientLogsResponse, ProgressEntry, PatientProgressResponse,
)


# ─── GET /api/v1/doctor/patients/{patient_id}/logs ────────────────────────

@router.get("/patients/{patient_id}/logs", response_model=PatientLogsResponse)
async def get_patient_logs(
    patient_id: int,
    request: Request,
    days: int = Query(default=7, ge=1, le=90),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns all meal logs for a patient for the last N days (default 7, max 90).
    Doctor can only see logs for patients under their care.
    Sorted newest-first by logged_date.
    """
    from datetime import timedelta
    did = _doctor_id(request)

    # Verify patient belongs to this doctor
    pat = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    cutoff = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        select(MealLog)
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= cutoff,
        )
        .order_by(MealLog.logged_date.desc(), MealLog.created_at.desc())
    )
    logs = result.scalars().all()
    return PatientLogsResponse(
        patient_id=patient_id,
        logs=logs,
        total_logs=len(logs),
    )


# ─── GET /api/v1/doctor/patients/{patient_id}/progress ───────────────────

@router.get("/patients/{patient_id}/progress", response_model=PatientProgressResponse)
async def get_patient_progress(
    patient_id: int,
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns ProgressLog entries (weight, water, steps, streak) for the last N days.
    Doctor can only see data for their own patients.
    Sorted chronologically (oldest first) for easy chart rendering.
    """
    from datetime import timedelta
    did = _doctor_id(request)

    pat = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    cutoff = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        select(ProgressLog)
        .where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date >= cutoff,
        )
        .order_by(ProgressLog.log_date.asc())
    )
    entries = result.scalars().all()
    return PatientProgressResponse(
        patient_id=patient_id,
        entries=entries,
        total_entries=len(entries),
    )
```

---

### SPRINT 2 — BLOCK B
**Scope:** Clinical notes + meal plan notes + remove patient
**Files:** `app/routers/doctor.py`, `app/schemas/doctor.py`, `app/models/db_models.py`, new Alembic migration

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 2 · BLOCK B

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.

We need a new `clinical_notes` table and endpoints for doctors to write
private notes about patients. We also need plan-level meal notes and patient removal.

=======================================================
TASK 1: New ORM model + Alembic migration
=======================================================

A) Add this new model to the BOTTOM of app/models/db_models.py:

# ---------------------------------------------------------------------------
# ClinicalNote
# ---------------------------------------------------------------------------

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id   = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id  = Column(Integer, ForeignKey("patients.id"), nullable=False)
    note        = Column(Text, nullable=False)
    is_private  = Column(Boolean, default=True)   # always private, visible only to doctor
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_cn_doctor_patient", "doctor_id", "patient_id"),
    )

B) Create alembic/versions/003_add_clinical_notes.py:

"""Add clinical_notes table

Revision ID: 003
Revises: 002
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'clinical_notes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_cn_doctor_patient', 'clinical_notes', ['doctor_id', 'patient_id'])


def downgrade() -> None:
    op.drop_index('idx_cn_doctor_patient', table_name='clinical_notes')
    op.drop_table('clinical_notes')


NOTE: Replace `002` in down_revision with the actual ID of the previous migration.

=======================================================
TASK 2: app/schemas/doctor.py — ADD new schemas
=======================================================

Add to the BOTTOM of doctor.py schemas:

class ClinicalNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=5000)

class ClinicalNoteResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    note: str
    created_at: datetime
    model_config = {"from_attributes": True}

class MealNoteRequest(BaseModel):
    meal_date: str   # "YYYY-MM-DD" — which day in the plan
    meal_type: str   # "Breakfast" | "Lunch" | "Dinner" | "MorningSnacks" | "EveningSnacks"
    note: str = Field(..., min_length=1, max_length=1000)

=======================================================
TASK 3: app/routers/doctor.py — ADD 4 endpoints
=======================================================

Add these imports at the top of doctor.py:
from ..models.db_models import (
    Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
    MealLog, ProgressLog, ClinicalNote,
)
from ..schemas.doctor import (
    PatientSummary, PaginatedPatients, RecommendationDetail,
    PlanOverrideRequest, PatientRequestDetail, RejectRequest,
    GenerateCodesRequest, SubscriptionCodeDetail,
    MealLogEntry, PatientLogsResponse, ProgressEntry, PatientProgressResponse,
    ClinicalNoteCreate, ClinicalNoteResponse, MealNoteRequest,
)

Add these 4 endpoints AFTER get_patient_progress:


# ─── POST /api/v1/doctor/patients/{patient_id}/notes ─────────────────────

@router.post("/patients/{patient_id}/notes", response_model=ClinicalNoteResponse, status_code=201)
async def add_clinical_note(
    patient_id: int,
    body: ClinicalNoteCreate,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Add a private clinical note about a patient. Only visible to this doctor."""
    did = _doctor_id(request)
    pat = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    note = ClinicalNote(
        doctor_id=did,
        patient_id=patient_id,
        note=body.note,
        is_private=True,
    )
    session.add(note)
    await session.flush()
    return note


# ─── GET /api/v1/doctor/patients/{patient_id}/notes ──────────────────────

@router.get("/patients/{patient_id}/notes", response_model=list[ClinicalNoteResponse])
async def get_clinical_notes(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Get all clinical notes for a patient written by this doctor."""
    did = _doctor_id(request)
    pat = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(ClinicalNote)
        .where(
            ClinicalNote.doctor_id == did,
            ClinicalNote.patient_id == patient_id,
        )
        .order_by(ClinicalNote.created_at.desc())
    )
    return result.scalars().all()


# ─── POST /api/v1/doctor/patients/{patient_id}/plan/notes ────────────────

@router.post("/patients/{patient_id}/plan/notes")
async def add_meal_plan_note(
    patient_id: int,
    body: MealNoteRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Add a doctor note to a specific meal slot in the patient's active plan.
    Finds the meal by date + meal_type in the JSONB meals array and injects
    a 'doctor_note' key. Updates the Recommendation row in place.
    Returns 404 if the meal slot doesn't exist in the current plan.
    """
    from copy import deepcopy
    did = _doctor_id(request)

    pat = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    meals = deepcopy(rec.meals or [])
    found = False
    for meal in meals:
        if meal.get("Date") == body.meal_date and meal.get("Meal Type") == body.meal_type:
            meal["doctor_note"] = body.note
            found = True
            break

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Meal slot '{body.meal_type}' on '{body.meal_date}' not found in active plan",
        )

    rec.meals = meals
    await session.flush()
    return {"message": "Note added to meal plan", "meal_date": body.meal_date, "meal_type": body.meal_type}


# ─── DELETE /api/v1/doctor/patients/{patient_id} ─────────────────────────

@router.delete("/patients/{patient_id}")
async def remove_patient(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Remove a patient from this doctor's care.
    Does NOT delete the patient account — only severs the doctor_id link
    and sets subscription_status back to 'inactive'.
    Patient retains their history.
    """
    did = _doctor_id(request)
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            doctor_id=None,
            user_type="standalone",
            subscription_status="inactive",
        )
    )
    await session.flush()
    return {"message": f"Patient {patient_id} removed from your care"}
```

---

### SPRINT 2 — BLOCK C
**Scope:** Recipe library + dashboard stats + inactivity + expiry detection
**Files:** `app/routers/doctor.py`, `app/schemas/doctor.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 2 · BLOCK C

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Files to MODIFY: app/routers/doctor.py, app/schemas/doctor.py

ORM model FoodItem has these columns:
  id, recipe_name, slot_type, cal_per_serving, protein_per_serving,
  carbs_per_serving, fat_per_serving, fiber_per_serving, sodium_per_serving,
  serving_weight_g, diet_type, region_tags, meal_time_tags, plan_type_tags,
  ingredients (JSONB), source, is_verified, image_url, created_at

Doctors can BROWSE the food database and ADD their own recipes.
Doctor-added recipes have source='doctor' and is_verified=False until admin approves.

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD schemas
=======================================================

Add to the BOTTOM of doctor.py schemas:

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
    model_config = {"from_attributes": True}

class RecipeCreateRequest(BaseModel):
    recipe_name: str = Field(..., min_length=1)
    slot_type: str
    diet_type: str
    cal_per_serving: float = Field(..., gt=0)
    protein_per_serving: float = Field(default=0, ge=0)
    carbs_per_serving: float = Field(default=0, ge=0)
    fat_per_serving: float = Field(default=0, ge=0)
    fiber_per_serving: float = Field(default=0, ge=0)
    sodium_per_serving: float = Field(default=0, ge=0)
    serving_weight_g: Optional[float] = None
    meal_time_tags: list[str] = Field(default_factory=list)
    plan_type_tags: list[str] = Field(default=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
    region_tags: list[str] = Field(default_factory=list)
    ingredients: list[dict] = Field(default_factory=list)
    # ingredients format: [{"name": str, "amount_g": float, "is_pantry_staple": bool}]

class RecipeAssignRequest(BaseModel):
    patient_ids: list[int] = Field(..., min_length=1)
    # Assign this recipe as a substitute for a meal slot in these patients' active plans

class DoctorDashboardStats(BaseModel):
    total_patients: int
    active_subscriptions: int
    inactive_patients: list[int]   # patient IDs with no log in last 3 days
    expiring_soon: list[int]       # patient IDs whose subscription expires within 7 days

=======================================================
MODIFICATION 2: app/routers/doctor.py — ADD 5 endpoints
=======================================================

Add these 5 endpoints to the BOTTOM of doctor.py.

Also add FoodItem to the db_models import:
from ..models.db_models import (
    Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
    MealLog, ProgressLog, ClinicalNote, FoodItem,
)

Also add new schemas to the schema import:
  FoodItemSummary, RecipeCreateRequest, RecipeAssignRequest, DoctorDashboardStats


# ─── GET /api/v1/doctor/recipes ──────────────────────────────────────────

@router.get("/recipes", response_model=list[FoodItemSummary])
async def browse_recipes(
    request: Request,
    search: Optional[str] = Query(default=None),
    diet_type: Optional[str] = Query(default=None),
    meal_time: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Browse the food database. Supports search by name, filter by diet_type and meal_time."""
    stmt = select(FoodItem)

    if search:
        stmt = stmt.where(FoodItem.recipe_name.ilike(f"%{search}%"))
    if diet_type:
        stmt = stmt.where(FoodItem.diet_type == diet_type)
    if meal_time:
        stmt = stmt.where(FoodItem.meal_time_tags.any(meal_time))

    stmt = stmt.order_by(FoodItem.recipe_name).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── POST /api/v1/doctor/recipes ─────────────────────────────────────────

@router.post("/recipes", response_model=FoodItemSummary, status_code=201)
async def add_recipe(
    body: RecipeCreateRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor adds a new recipe to the food database.
    source='doctor', is_verified=False — requires admin approval before use in plans.
    """
    food = FoodItem(
        recipe_name=body.recipe_name,
        slot_type=body.slot_type,
        diet_type=body.diet_type,
        cal_per_serving=body.cal_per_serving,
        protein_per_serving=body.protein_per_serving,
        carbs_per_serving=body.carbs_per_serving,
        fat_per_serving=body.fat_per_serving,
        fiber_per_serving=body.fiber_per_serving,
        sodium_per_serving=body.sodium_per_serving,
        serving_weight_g=body.serving_weight_g,
        meal_time_tags=body.meal_time_tags,
        plan_type_tags=body.plan_type_tags,
        region_tags=body.region_tags,
        ingredients=body.ingredients,
        source="doctor",
        is_verified=False,
    )
    session.add(food)
    await session.flush()
    return food


# ─── POST /api/v1/doctor/recipes/{recipe_id}/assign ──────────────────────

@router.post("/recipes/{recipe_id}/assign")
async def assign_recipe(
    recipe_id: int,
    body: RecipeAssignRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Adds a recipe as a doctor note/suggestion to the meal plans of specified patients.
    Does NOT replace their current plan — adds it as a 'doctor_suggestion' key
    on the Recommendation row's doctor_notes field.
    Only patients belonging to this doctor can be assigned.
    """
    did = _doctor_id(request)

    food_result = await session.execute(select(FoodItem.recipe_name).where(FoodItem.id == recipe_id))
    food_name = food_result.scalar()
    if food_name is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    assigned = []
    not_found = []
    for pid in body.patient_ids:
        pat = await session.execute(
            select(Patient.id).where(Patient.id == pid, Patient.doctor_id == did)
        )
        if pat.scalars().first() is None:
            not_found.append(pid)
            continue

        rec_result = await session.execute(
            select(Recommendation)
            .where(Recommendation.patient_id == pid, Recommendation.is_active == True)
            .order_by(Recommendation.created_at.desc()).limit(1)
        )
        rec = rec_result.scalars().first()
        if rec:
            existing = rec.doctor_notes or ""
            rec.doctor_notes = f"{existing}\n[Suggested recipe: {food_name} (food_id={recipe_id})]".strip()
            await session.flush()
            assigned.append(pid)

    return {
        "recipe_id": recipe_id,
        "recipe_name": food_name,
        "assigned_to": assigned,
        "not_found": not_found,
    }


# ─── GET /api/v1/doctor/dashboard ────────────────────────────────────────

@router.get("/dashboard", response_model=DoctorDashboardStats)
async def get_dashboard(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Dashboard summary cards:
      - total_patients: all patients under this doctor
      - active_subscriptions: patients with subscription_status='active'
      - inactive_patients: patient IDs with no MealLog in last 3 days
      - expiring_soon: patient IDs whose subscription_end_date is within 7 days
    """
    from datetime import timedelta, timezone as _tz
    did = _doctor_id(request)
    now = datetime.now(timezone.utc)

    total_result = await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == did)
    )
    total_patients = total_result.scalar()

    active_result = await session.execute(
        select(func.count(Patient.id)).where(
            Patient.doctor_id == did,
            Patient.subscription_status == "active",
        )
    )
    active_subs = active_result.scalar()

    # Inactive: no meal log in last 3 days
    three_days_ago = date.today() - timedelta(days=3)
    all_patient_ids_result = await session.execute(
        select(Patient.id).where(Patient.doctor_id == did)
    )
    all_ids = [r for r in all_patient_ids_result.scalars().all()]

    active_loggers_result = await session.execute(
        select(MealLog.patient_id).distinct().where(
            MealLog.patient_id.in_(all_ids),
            MealLog.logged_date >= three_days_ago,
        )
    )
    active_logger_ids = set(active_loggers_result.scalars().all())
    inactive_ids = [pid for pid in all_ids if pid not in active_logger_ids]

    # Expiring soon: subscription_end_date within 7 days
    seven_days = now + timedelta(days=7)
    expiring_result = await session.execute(
        select(Patient.id).where(
            Patient.doctor_id == did,
            Patient.subscription_end_date.isnot(None),
            Patient.subscription_end_date <= seven_days,
            Patient.subscription_end_date >= now,
        )
    )
    expiring_ids = expiring_result.scalars().all()

    return DoctorDashboardStats(
        total_patients=total_patients,
        active_subscriptions=active_subs,
        inactive_patients=inactive_ids,
        expiring_soon=list(expiring_ids),
    )
```

---
---

## SPRINT 3 — Phase 3 Admin Backend (16 remaining)
**Goal:** Complete all admin endpoints. Full platform management API ready.
**Blocks:** 3-A → 3-B → 3-C

---

### SPRINT 3 — BLOCK A
**Scope:** Admin login, doctor management gaps, code management, billing stubs
**Files:** `app/routers/admin.py`, `app/schemas/admin.py`, `app/routers/auth.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 3 · BLOCK A

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Files to MODIFY: app/routers/admin.py, app/schemas/admin.py, app/routers/auth.py

Existing admin router has:
  POST /admin/doctors          — create doctor
  GET  /admin/doctors          — list doctors
  GET  /admin/stats            — platform stats
  PATCH /admin/doctors/{id}/deactivate

Admin ORM model has: id, email, hashed_password, name, mfa_secret, mfa_enabled,
                     allowed_ips (JSONB), is_active, role
SubscriptionCode ORM: id, doctor_id, code, is_used, used_by_patient_id, used_at,
                      expires_at, created_at

=======================================================
MODIFICATION 1: app/routers/auth.py — ADD admin login
=======================================================

Add this endpoint to the BOTTOM of auth.py.
Also add Admin to db_models import at top of auth.py:
from ..models.db_models import Doctor, Admin

# ─── POST /api/v1/auth/admin/login ───────────────────────────────────────

@router.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin login — email + password.
    MFA verification is enforced client-side for now (TOTP stored in mfa_secret).
    IP whitelisting enforced by AdminIPMiddleware on all /admin routes (Sprint 3-C).
    """
    result = await session.execute(
        select(Admin).where(Admin.email == form_data.username)
    )
    admin = result.scalars().first()

    if admin is None or not verify_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Admin account deactivated")

    token_data = {
        "sub": admin.email,
        "role": "admin",
        "admin_id": admin.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "mfa_required": admin.mfa_enabled,
        # If mfa_required=True, client must verify TOTP before trusting token
    }

=======================================================
MODIFICATION 2: app/schemas/admin.py — ADD schemas
=======================================================

Add these to the BOTTOM of admin.py schemas:

class DoctorDetailView(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    specialization: Optional[str]
    clinic_name: Optional[str]
    city: Optional[str]
    is_active: bool
    mfa_enabled: bool
    patient_count: int
    created_at: datetime
    model_config = {"from_attributes": True}

class GenerateCodesAdminRequest(BaseModel):
    doctor_id: int
    count: int = Field(..., ge=1, le=100)
    expires_in_days: int = Field(default=365, ge=1, le=730)

class CodeAdminView(BaseModel):
    id: int
    doctor_id: int
    code: str
    is_used: bool
    used_by_patient_id: Optional[int]
    used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}

class BillingEntry(BaseModel):
    doctor_id: int
    doctor_name: str
    total_codes_issued: int
    codes_used: int
    codes_unused: int

class MarkPaidRequest(BaseModel):
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None

=======================================================
MODIFICATION 3: app/routers/admin.py — ADD 6 endpoints
=======================================================

Add imports at top of admin.py:
from ..models.db_models import Admin, Doctor, Patient, Recommendation, SubscriptionCode
from ..schemas.admin import (
    CreateDoctorRequest, DoctorAdminView, PlatformStats,
    DoctorDetailView, GenerateCodesAdminRequest, CodeAdminView,
    BillingEntry, MarkPaidRequest,
)
import secrets, string
from datetime import timedelta, timezone

Add these 6 endpoints AFTER deactivate_doctor:


# ─── GET /api/v1/admin/doctors/{doctor_id} ────────────────────────────────

@router.get("/doctors/{doctor_id}", response_model=DoctorDetailView)
async def get_doctor_detail(
    doctor_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Full doctor profile including patient count."""
    result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    count_result = await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == doctor_id)
    )
    patient_count = count_result.scalar()

    return DoctorDetailView(
        id=doctor.id, email=doctor.email, name=doctor.name, phone=doctor.phone,
        specialization=doctor.specialization, clinic_name=doctor.clinic_name,
        city=doctor.city, is_active=doctor.is_active, mfa_enabled=doctor.mfa_enabled,
        patient_count=patient_count, created_at=doctor.created_at,
    )


# ─── DELETE /api/v1/admin/doctors/{doctor_id} ────────────────────────────

@router.delete("/doctors/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Deactivate doctor and unlink all their patients.
    Does NOT hard-delete — sets is_active=False.
    All patients are moved to standalone (doctor_id=None, subscription_status=inactive).
    """
    result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(is_active=False)
    )
    # Unlink all patients
    await session.execute(
        update(Patient).where(Patient.doctor_id == doctor_id).values(
            doctor_id=None, user_type="standalone", subscription_status="inactive"
        )
    )
    await session.flush()
    return {"message": f"Doctor {doctor_id} deleted and patients unlinked"}


# ─── POST /api/v1/admin/codes/generate ───────────────────────────────────

@router.post("/codes/generate", response_model=list[CodeAdminView], status_code=201)
async def generate_codes_for_doctor(
    body: GenerateCodesAdminRequest,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Generate a batch of subscription codes for a doctor."""
    result = await session.execute(
        select(Doctor).where(Doctor.id == body.doctor_id, Doctor.is_active == True)
    )
    if result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    alphabet = string.ascii_uppercase + string.digits
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=body.expires_in_days)
    created = []

    for _ in range(body.count):
        for attempt in range(10):
            candidate = "".join(secrets.choice(alphabet) for _ in range(12))
            exists = await session.execute(
                select(SubscriptionCode.id).where(SubscriptionCode.code == candidate)
            )
            if exists.scalars().first() is None:
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique code")

        code = SubscriptionCode(
            doctor_id=body.doctor_id,
            code=candidate,
            is_used=False,
            expires_at=expiry,
        )
        session.add(code)
        created.append(code)

    await session.flush()
    return created


# ─── GET /api/v1/admin/codes ──────────────────────────────────────────────

@router.get("/codes", response_model=list[CodeAdminView])
async def list_all_codes(
    doctor_id: Optional[int] = Query(default=None),
    is_used: Optional[bool] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """List all subscription codes. Optionally filter by doctor_id or used status."""
    stmt = select(SubscriptionCode).order_by(SubscriptionCode.created_at.desc())
    if doctor_id is not None:
        stmt = stmt.where(SubscriptionCode.doctor_id == doctor_id)
    if is_used is not None:
        stmt = stmt.where(SubscriptionCode.is_used == is_used)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── GET /api/v1/admin/billing ───────────────────────────────────────────

@router.get("/billing", response_model=list[BillingEntry])
async def get_billing_overview(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Per-doctor breakdown: codes issued, used, unused."""
    doctors_result = await session.execute(
        select(Doctor).where(Doctor.is_active == True).order_by(Doctor.name)
    )
    doctors = doctors_result.scalars().all()

    entries = []
    for doctor in doctors:
        total = (await session.execute(
            select(func.count(SubscriptionCode.id)).where(SubscriptionCode.doctor_id == doctor.id)
        )).scalar()
        used = (await session.execute(
            select(func.count(SubscriptionCode.id)).where(
                SubscriptionCode.doctor_id == doctor.id, SubscriptionCode.is_used == True
            )
        )).scalar()
        entries.append(BillingEntry(
            doctor_id=doctor.id, doctor_name=doctor.name,
            total_codes_issued=total, codes_used=used, codes_unused=total - used,
        ))
    return entries


# ─── PATCH /api/v1/admin/patients/{patient_id}/subscription/override ──────

@router.patch("/patients/{patient_id}/subscription/override")
async def override_subscription(
    patient_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Manually set a patient's subscription to active for 30 days.
    Used for dispute resolution and manual overrides.
    """
    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from datetime import timedelta, timezone
    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    await session.execute(
        update(Patient).where(Patient.id == patient_id).values(
            subscription_status="active",
            subscription_end_date=expiry,
        )
    )
    await session.flush()
    return {"message": f"Patient {patient_id} subscription overridden for 30 days", "expires_at": expiry.isoformat()}
```

---

### SPRINT 3 — BLOCK B
**Scope:** Food database management (approve/reject/delete) + audit log system
**Files:** `app/routers/admin.py`, `app/schemas/admin.py`, `app/models/db_models.py`, new Alembic migration

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 3 · BLOCK B

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Files to MODIFY: app/models/db_models.py, app/routers/admin.py, app/schemas/admin.py
New file: alembic/versions/004_add_audit_logs.py

=======================================================
TASK 1: AuditLog ORM model + migration
=======================================================

A) Add to the BOTTOM of app/models/db_models.py:

# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    actor_id    = Column(Integer, nullable=False)   # doctor.id or admin.id
    actor_role  = Column(String(10), nullable=False)  # 'doctor' | 'admin'
    action      = Column(String(100), nullable=False)
    # e.g. "ACCEPT_PATIENT_REQUEST", "GENERATE_CODES", "DEACTIVATE_DOCTOR"
    target_type = Column(String(30), nullable=True)   # 'patient' | 'doctor' | 'food_item' etc.
    target_id   = Column(Integer, nullable=True)
    detail      = Column(JSONB, default={})           # any extra context
    ip_address  = Column(String(45), nullable=True)   # IPv4 or IPv6
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_al_actor", "actor_id", "actor_role"),
        Index("idx_al_created", "created_at"),
    )

B) Create alembic/versions/004_add_audit_logs.py:

"""Add audit_logs table

Revision ID: 004
Revises: 003
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('actor_role', sa.String(10), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_type', sa.String(30), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_al_actor', 'audit_logs', ['actor_id', 'actor_role'])
    op.create_index('idx_al_created', 'audit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_al_created', table_name='audit_logs')
    op.drop_index('idx_al_actor', table_name='audit_logs')
    op.drop_table('audit_logs')

=======================================================
TASK 2: app/schemas/admin.py — ADD schemas
=======================================================

Add to the BOTTOM:

class FoodAdminView(BaseModel):
    id: int
    recipe_name: str
    diet_type: str
    source: str
    is_verified: bool
    cal_per_serving: float
    created_at: datetime
    model_config = {"from_attributes": True}

class FoodRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1)

class AuditLogEntry(BaseModel):
    id: int
    actor_id: int
    actor_role: str
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    detail: dict
    ip_address: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}

=======================================================
TASK 3: app/routers/admin.py — ADD 7 endpoints + audit writer
=======================================================

Add AuditLog to the db_models import.
Add FoodAdminView, FoodRejectRequest, AuditLogEntry to schemas import.

First, add this audit writer helper function at the top of admin.py
(after imports, before the router = APIRouter() line):

async def _write_audit(
    session: AsyncSession,
    actor_id: int,
    actor_role: str,
    action: str,
    request: Request = None,
    target_type: str = None,
    target_id: int = None,
    detail: dict = None,
) -> None:
    """Write one audit log entry. Never raises — failures are silently logged."""
    import logging
    try:
        ip = None
        if request:
            forwarded = request.headers.get("x-forwarded-for")
            ip = forwarded.split(",")[0].strip() if forwarded else getattr(request.client, "host", None)
        entry = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
            ip_address=ip,
        )
        session.add(entry)
        await session.flush()
    except Exception as exc:
        logging.getLogger(__name__).error(f"Audit write failed: {exc}", exc_info=True)


Then add these 7 endpoints to the BOTTOM of admin.py:


# ─── GET /api/v1/admin/food ───────────────────────────────────────────────

@router.get("/food", response_model=list[FoodAdminView])
async def list_food_items(
    source: Optional[str] = Query(default=None),   # 'doctor' to see pending approvals
    is_verified: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Browse the food database. Filter by source='doctor' to see pending approvals."""
    stmt = select(FoodItem).order_by(FoodItem.created_at.desc())
    if source:
        stmt = stmt.where(FoodItem.source == source)
    if is_verified is not None:
        stmt = stmt.where(FoodItem.is_verified == is_verified)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── PATCH /api/v1/admin/food/{food_id}/approve ──────────────────────────

@router.patch("/food/{food_id}/approve")
async def approve_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    food.is_verified = True
    await session.flush()
    await _write_audit(session, admin.id, "admin", "APPROVE_FOOD_ITEM", request,
                       target_type="food_item", target_id=food_id,
                       detail={"recipe_name": food.recipe_name})
    return {"message": f"Food item {food_id} approved"}


# ─── PATCH /api/v1/admin/food/{food_id}/reject ───────────────────────────

@router.patch("/food/{food_id}/reject")
async def reject_food_item(
    food_id: int,
    body: FoodRejectRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    await session.delete(food)   # Rejected items are hard-deleted
    await session.flush()
    await _write_audit(session, admin.id, "admin", "REJECT_FOOD_ITEM", request,
                       target_type="food_item", target_id=food_id,
                       detail={"reason": body.reason})
    return {"message": f"Food item {food_id} rejected and removed"}


# ─── DELETE /api/v1/admin/food/{food_id} ─────────────────────────────────

@router.delete("/food/{food_id}")
async def delete_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    await session.delete(food)
    await session.flush()
    await _write_audit(session, admin.id, "admin", "DELETE_FOOD_ITEM", request,
                       target_type="food_item", target_id=food_id)
    return {"message": f"Food item {food_id} deleted"}


# ─── GET /api/v1/admin/audit-logs ────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogEntry])
async def get_audit_logs(
    actor_role: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Paginated audit log. Filter by actor_role ('doctor'|'admin') or action keyword."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── DELETE /api/v1/admin/patients/{patient_id} ──────────────────────────

@router.delete("/patients/{patient_id}")
async def delete_patient_dpdp(
    patient_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    DPDP Act compliance data erasure.
    Anonymises the patient row rather than hard-deleting (preserves FK integrity).
    Deletes: meal_logs, progress_logs, clinical_notes, recommendations for this patient.
    Anonymises: email → deleted_{id}@deleted.mityahar.com, name → [DELETED], phone → None
    """
    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from sqlalchemy import delete as sa_delete
    from ..models.db_models import ClinicalNote

    # Delete associated data
    await session.execute(sa_delete(MealLog).where(MealLog.patient_id == patient_id))
    await session.execute(sa_delete(ProgressLog).where(ProgressLog.patient_id == patient_id))
    await session.execute(sa_delete(ClinicalNote).where(ClinicalNote.patient_id == patient_id))
    await session.execute(sa_delete(Recommendation).where(Recommendation.patient_id == patient_id))

    # Anonymise patient row
    await session.execute(
        update(Patient).where(Patient.id == patient_id).values(
            email=f"deleted_{patient_id}@deleted.mityahar.com",
            name="[DELETED]",
            hashed_password="[DELETED]",
            phone=None,
            is_active=False,
        )
    )
    await session.flush()
    await _write_audit(session, admin.id, "admin", "DPDP_ERASE_PATIENT", request,
                       target_type="patient", target_id=patient_id)
    return {"message": f"Patient {patient_id} data erased (DPDP compliance)"}
```

---

### SPRINT 3 — BLOCK C
**Scope:** IP whitelisting middleware for admin routes
**Files:** `app/core/middleware.py`, `app/main.py`

---

#### 🤖 ANTIGRAVITY PROMPT — SPRINT 3 · BLOCK C

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async.
Files to MODIFY: app/core/middleware.py, app/main.py

Existing middlewares in middleware.py:
  SubscriptionCheckMiddleware  — blocks inactive patients
  DoctorIsolationMiddleware    — scopes doctor routes to their ID

We need a third middleware: AdminIPMiddleware.

Admin allowed_ips is a JSONB list on the Admin row.
HOWEVER: reading DB in middleware creates a DB call on EVERY admin request.
Solution: in dev/test mode, skip IP check if ADMIN_IP_WHITELIST_ENABLED=false in .env
In production, perform a single DB lookup and cache allowed IPs per admin email
using a simple in-process dict (good enough for single-instance Cloud Run).

=======================================================
MODIFICATION 1: app/core/middleware.py — ADD AdminIPMiddleware
=======================================================

Add this class to the BOTTOM of middleware.py:

# ---------------------------------------------------------------------------
# Admin IP whitelisting middleware
# ---------------------------------------------------------------------------

_admin_ip_cache: dict[str, list[str]] = {}   # email → allowed_ips (in-process cache)
_ADMIN_PREFIX = f"{settings.API_V1_STR}/admin"


class AdminIPMiddleware(BaseHTTPMiddleware):
    """
    Restricts /admin/* routes to allowed IP addresses stored on the Admin row.

    Behaviour:
      - If ADMIN_IP_WHITELIST_ENABLED env var is not 'true' → bypass entirely (dev mode)
      - If admin has empty allowed_ips list → bypass (no restriction configured)
      - If request IP not in allowed_ips → 403 Forbidden
      - Uses in-process dict cache — refreshed on 403 to catch IP list updates

    Reads role from JWT — only applies to role=admin tokens.
    Falls back gracefully on any JWT error — lets the route dependency handle it.
    """

    def __init__(self, app, whitelist_enabled: bool = False):
        super().__init__(app)
        self._enabled = whitelist_enabled

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not self._enabled:
            return await call_next(request)

        if not path.startswith(_ADMIN_PREFIX):
            return await call_next(request)

        # Skip admin login — can't have IP check before the admin is identified
        if path == f"{_ADMIN_PREFIX}/login" or path.endswith("/login"):
            return await call_next(request)

        token = _extract_token(request)
        if token is None:
            return await call_next(request)

        payload = _safe_decode(token)
        if payload is None or payload.get("role") != "admin":
            return await call_next(request)

        admin_email = payload.get("sub")
        if not admin_email:
            return await call_next(request)

        # Get client IP
        forwarded = request.headers.get("x-forwarded-for")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            getattr(request.client, "host", None)
        )

        allowed = _admin_ip_cache.get(admin_email)
        if allowed is None:
            # Lazy DB load — only runs once per admin email per process lifetime
            from ..core.database import async_session_factory
            from sqlalchemy import select as _select
            from ..models.db_models import Admin as _Admin
            try:
                async with async_session_factory() as s:
                    result = await s.execute(
                        _select(_Admin.allowed_ips).where(_Admin.email == admin_email)
                    )
                    row = result.scalar()
                    allowed = row if isinstance(row, list) else []
                    _admin_ip_cache[admin_email] = allowed
            except Exception:
                allowed = []

        if not allowed:
            # No IPs configured — allow all (admin hasn't set up restriction yet)
            return await call_next(request)

        if client_ip not in allowed:
            # Bust cache and re-check in case the list was recently updated
            _admin_ip_cache.pop(admin_email, None)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: IP not whitelisted", "code": "IP_BLOCKED"},
            )

        return await call_next(request)

Also add this import at the top of middleware.py if not already present:
from starlette.responses import JSONResponse   (already imported — confirm)

=======================================================
MODIFICATION 2: app/main.py — register AdminIPMiddleware
=======================================================

In main.py, find where SubscriptionCheckMiddleware and DoctorIsolationMiddleware
are added. Add AdminIPMiddleware BEFORE them (middlewares execute last-registered first):

import os
from .core.middleware import (
    SubscriptionCheckMiddleware,
    DoctorIsolationMiddleware,
    AdminIPMiddleware,
)

# Register middlewares — order matters, last registered = first executed
app.add_middleware(SubscriptionCheckMiddleware)
app.add_middleware(DoctorIsolationMiddleware)
app.add_middleware(
    AdminIPMiddleware,
    whitelist_enabled=os.getenv("ADMIN_IP_WHITELIST_ENABLED", "false").lower() == "true"
)

Also add to .env (or .env.example):
ADMIN_IP_WHITELIST_ENABLED=false
# Set to true in production with admin IPs configured in the DB
```

---

## EXECUTION SEQUENCE

```
Sprint 1 ─┬─ Block A (Alembic + ORM columns)
           ├─ Block B (Schema + register split + onboarding fields)
           ├─ Block C (Slot linking + adherence)
           └─ Block D (Version counter + shopping toggle)

Sprint 2 ─┬─ Block A (Patient logs + progress views for doctor)
           ├─ Block B (Clinical notes + plan notes + remove patient + migration)
           └─ Block C (Recipe library + dashboard + inactivity/expiry)

Sprint 3 ─┬─ Block A (Admin login + doctor management + codes + billing)
           ├─ Block B (Food management + audit log + DPDP erasure + migration)
           └─ Block C (IP whitelisting middleware)
```

**After Sprint 3 completes:** The full backend API surface is locked and stable.
Sprints 4–5 (React Web dashboards) and Sprint 6 (React Native mobile) begin.

---

## VERIFICATION COMMANDS (run after each sprint)

```powershell
# Start server
venv\Scripts\uvicorn app.main:app --reload --port 8001

# Run Alembic migrations (after any block that creates migrations)
venv\Scripts\alembic upgrade head

# Check migration history
venv\Scripts\alembic history --verbose
```
