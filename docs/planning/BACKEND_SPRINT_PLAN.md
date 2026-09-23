# MITYAHAR — COMPLETE BACKEND SPRINT PLAN
## Sprints 1, 2, 3 — Full Antigravity Prompts

> Rule: Execute blocks in strict order within each sprint. Paste each block into Antigravity, bring output back to Claude for audit before moving to the next block.

---

# ═══════════════════════════════════════════════════════════
# SPRINT 1 — Phase 1 Backend Cleanup
# 4 Blocks: L → M → N → O
# ═══════════════════════════════════════════════════════════

## BLOCK L — New DB Columns + Alembic Migration
**Files:** `app/models/db_models.py` (MODIFY), new Alembic migration file
**Why first:** Every other Sprint 1 block depends on these columns existing.

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK L

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Alembic is configured and 4 migration files already exist.
Latest migration revision: cf7a21f007f0

TASK 1: app/models/db_models.py — ADD 2 columns to Patient class
=========================================================
The Patient class currently ends with:
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

Add these 2 columns BEFORE the created_at line:
    pace_preference = Column(String(20), nullable=True)
    # valid values: "slow" | "moderate" | "fast" — patient's preferred weight-loss pace
    eating_habits   = Column(JSONB, default=[])
    # e.g. ["skips_breakfast", "late_night_eating", "irregular_meals"]

TASK 2: app/models/db_models.py — ADD 1 column to FoodItem class
=========================================================
The FoodItem class currently has:
    is_verified  = Column(Boolean, nullable=False, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

Add this column BEFORE the created_at line:
    image_url = Column(String(500), nullable=True)
    # URL to food image — populated by ETL script in Phase 6

TASK 3: Generate Alembic migration
=========================================================
Run this command in the project root (where alembic.ini is):
    alembic revision --autogenerate -m "add_pace_preference_eating_habits_image_url"

Then open the generated file in alembic/versions/ and verify the upgrade() function contains:
  - op.add_column('patients', sa.Column('pace_preference', sa.String(length=20), nullable=True))
  - op.add_column('patients', sa.Column('eating_habits', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
  - op.add_column('food_items', sa.Column('image_url', sa.String(length=500), nullable=True))

If the autogenerate did NOT produce these columns, manually add them.
The downgrade() function must have the matching op.drop_column() calls.

Then run:
    alembic upgrade head

Confirm output ends with: Running upgrade cf7a21f007f0 -> <new_revision_id>
```

---

### 🔍 CLAUDE AUDIT — BLOCK L
- [ ] `pace_preference` added to Patient before `created_at`
- [ ] `eating_habits` added to Patient before `created_at`
- [ ] `image_url` added to FoodItem before `created_at`
- [ ] Migration file contains all 3 `op.add_column` calls
- [ ] Migration `down_revision` = `'cf7a21f007f0'`
- [ ] `alembic upgrade head` ran without errors

---
---

## BLOCK M — Onboarding Fields + Register Flow Split
**Files:** `app/schemas/patients.py`, `app/schemas/user.py`, `app/routers/patients.py`, `app/routers/auth.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK M

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
The Patient ORM model now has: pace_preference (String, nullable), eating_habits (JSONB, default=[])
These columns were just added via Alembic — do NOT run another migration.

=======================================================
MODIFICATION 1: app/schemas/patients.py
=======================================================
In OnboardingRequest class, add these 2 fields AFTER the alcohol field
and BEFORE the @field_validator:

    pace_preference: Optional[str] = Field(default=None)
    # "slow" | "moderate" | "fast"
    eating_habits: list[str] = Field(default_factory=list)
    # e.g. ["skips_breakfast", "late_night_eating", "irregular_meals"]

Also CHANGE the food_allergies field from:
    food_allergies: list[str] = Field(default_factory=list)
To:
    food_allergies: list[str] = Field(default_factory=list, min_length=1)
    # mandatory — patient must list at least one allergy or "None"

Also ADD these 2 fields to PatientProfileResponse class
(after the nonveg_meals_per_week field):
    pace_preference: Optional[str] = None
    eating_habits: list = []

Add `Optional` to the imports at top of file if not already present:
    from typing import Optional, Literal

=======================================================
MODIFICATION 2: app/schemas/user.py
=======================================================
In UserCreate class, add this optional field after the password field:
    doctor_code: Optional[str] = Field(default=None)
    # If provided, patient connects to a doctor immediately on registration.
    # The code must be a valid, unused SubscriptionCode.

Add Optional to imports if not already present.

=======================================================
MODIFICATION 3: app/routers/patients.py
=======================================================
In the onboard_patient endpoint, inside the session.execute(update(Patient).values(...)) call,
add these 2 fields to the existing .values() dict:
    pace_preference=body.pace_preference,
    eating_habits=body.eating_habits,

Also REMOVE the min_length=1 enforcement for food_allergies at the router level
if any exists — validation is now handled by the Pydantic schema.

=======================================================
MODIFICATION 4: app/routers/auth.py
=======================================================
Modify the register endpoint to handle optional doctor_code.
Replace the entire register endpoint with:

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a new patient.
    If doctor_code is provided: validates it, consumes it, and links patient to doctor immediately.
    If no doctor_code: standalone patient with inactive subscription.
    """
    from ..models.db_models import SubscriptionCode, Patient as PatientModel
    from datetime import datetime, timezone as _tz
    from sqlalchemy import update as sa_update

    data = user_data.model_dump()
    doctor_code = data.pop("doctor_code", None)

    try:
        patient_id = await create_patient(session, data=data)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If a doctor code was provided, validate and consume it immediately
    if doctor_code:
        now = datetime.now(_tz.utc)
        code_result = await session.execute(
            select(SubscriptionCode).where(
                SubscriptionCode.code == doctor_code,
                SubscriptionCode.is_used == False,
                SubscriptionCode.expires_at > now,
            )
        )
        code_row = code_result.scalars().first()

        if code_row is None:
            # Registration succeeded but code is invalid — do not roll back.
            # Return success with a warning. Patient can activate later via /activate.
            return {
                "message": "Registered successfully. Doctor code was invalid or expired — activate manually via /patients/activate.",
                "user_id": patient_id,
                "doctor_connected": False,
            }

        # Consume code and activate
        code_row.is_used = True
        code_row.used_by_patient_id = patient_id
        code_row.used_at = now

        await session.execute(
            sa_update(PatientModel)
            .where(PatientModel.id == patient_id)
            .values(
                doctor_id=code_row.doctor_id,
                user_type="doctor_assigned",
                subscription_status="active",
            )
        )
        await session.flush()
        return {
            "message": "Registered and connected to doctor successfully.",
            "user_id": patient_id,
            "doctor_connected": True,
        }

    return {
        "message": "User registered successfully",
        "user_id": patient_id,
        "doctor_connected": False,
    }

Keep all existing imports at the top of auth.py unchanged.
The new imports (SubscriptionCode, Patient, datetime, sa_update) are inline inside the function.
```

---

### 🔍 CLAUDE AUDIT — BLOCK M
- [ ] `pace_preference: Optional[str]` with `default=None` in OnboardingRequest
- [ ] `eating_habits: list[str]` with `default_factory=list` in OnboardingRequest
- [ ] `food_allergies` now has `min_length=1` — enforced at schema level
- [ ] Both new fields added to `.values()` in onboard_patient
- [ ] `PatientProfileResponse` includes `pace_preference` and `eating_habits`
- [ ] `UserCreate` has `doctor_code: Optional[str] = None`
- [ ] register endpoint: invalid code does NOT roll back registration — returns warning
- [ ] register endpoint: valid code sets `user_type="doctor_assigned"`, `subscription_status="active"`, `doctor_id`
- [ ] All inline imports inside the function body — no new top-level imports in auth.py

---
---

## BLOCK N — Meal Log Slot Linking + Adherence
**Files:** `app/schemas/progress.py`, `app/services/progress_service.py`, `app/routers/progress.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK N

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
ORM models — MealLog has: recommendation_id (Integer FK, nullable=True), meal_type, logged_date, calories_consumed etc.
ORM models — Recommendation has: id, patient_id, meals (JSONB list), is_active, week_start_date.

meal_logs.recommendation_id column already exists in the DB.
DO NOT run Alembic — no new columns needed.

=======================================================
MODIFICATION 1: app/schemas/progress.py
=======================================================
In MealLogCreate class, add this optional field after fiber:
    recommendation_id: Optional[int] = Field(default=None)
    # ID of the recommendation this meal was taken from. Null for custom meals.

=======================================================
MODIFICATION 2: app/services/progress_service.py
=======================================================
CHANGE the existing log_meal function from:

async def log_meal(session, patient_id, data) -> None:
    entry = MealLog(
        patient_id=patient_id,
        logged_date=date.today(),
        meal_type=data.get("meal_type", "Breakfast"),
        calories_consumed=data.get("calories", 0),
        protein_g=data.get("protein", 0),
        carbs_g=data.get("carbs", 0),
        fat_g=data.get("fat", 0),
        fiber_g=data.get("fiber", 0),
    )
    session.add(entry)
    await session.flush()

TO:

async def log_meal(session, patient_id, data) -> MealLog:
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
        recommendation_id=data.get("recommendation_id"),  # nullable — None for custom meals
    )
    session.add(entry)
    await session.flush()
    return entry

ADD this function AFTER log_meal:

async def calculate_adherence(
    session: AsyncSession,
    patient_id: int,
    days: int = 7,
) -> dict:
    """
    Adherence = (meal slots logged / meal slots recommended) * 100 for each day.

    Logic:
      - For each day in the last N days, count distinct meal_types in meal_logs
        where recommendation_id IS NOT NULL (i.e., patient logged a recommended meal).
      - Compare against the patient's meals_per_day setting.
      - Return day-by-day breakdown and overall weekly percentage.
    """
    from sqlalchemy import func as sa_func, case
    today = date.today()
    start = today - timedelta(days=days - 1)

    # Get patient's meals_per_day target
    patient_result = await session.execute(
        select(Patient.meals_per_day, Patient.id).where(Patient.id == patient_id)
    )
    patient_row = patient_result.first()
    meals_per_day_target = patient_row.meals_per_day if patient_row else 5

    # Count logged recommended meals per day
    result = await session.execute(
        select(
            MealLog.logged_date,
            sa_func.count(sa_func.distinct(MealLog.meal_type)).label("logged_slots"),
        )
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
            MealLog.recommendation_id.isnot(None),  # only recommended meals count
        )
        .group_by(MealLog.logged_date)
        .order_by(MealLog.logged_date)
    )
    logged_by_day = {str(r.logged_date): int(r.logged_slots) for r in result.all()}

    daily = []
    total_logged = 0
    total_possible = 0

    for i in range(days):
        day = start + timedelta(days=i)
        day_str = str(day)
        logged = logged_by_day.get(day_str, 0)
        possible = meals_per_day_target
        pct = round((logged / possible) * 100, 1) if possible > 0 else 0.0
        total_logged += logged
        total_possible += possible
        daily.append({
            "date": day_str,
            "logged_slots": logged,
            "target_slots": possible,
            "adherence_pct": pct,
        })

    overall_pct = round((total_logged / total_possible) * 100, 1) if total_possible > 0 else 0.0
    return {
        "period_days": days,
        "week_start": str(start),
        "week_end": str(today),
        "overall_adherence_pct": overall_pct,
        "daily": daily,
    }

Also add Patient to the imports at the top of progress_service.py:
Change:
    from ..models.db_models import MealLog, ProgressLog
To:
    from ..models.db_models import MealLog, ProgressLog, Patient

=======================================================
MODIFICATION 3: app/routers/progress.py
=======================================================
Step 1 — Add calculate_adherence to the existing import from progress_service:
    from ..services.progress_service import (
        ..., calculate_and_store_streak, calculate_adherence,
    )

Step 2 — Modify the existing post_log_meal endpoint body to pass recommendation_id:
Inside the log_meal call, change:
    await log_meal(session, current_user.id, meal.model_dump())
To:
    await log_meal(session, current_user.id, meal.model_dump())
(No change needed — model_dump() already includes recommendation_id)

Step 3 — Add this endpoint to the BOTTOM of progress.py:

# ─── GET /api/v1/progress/adherence/weekly ───────────────────────────────

@router.get("/adherence/weekly")
async def get_weekly_adherence(
    days: int = 7,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns adherence percentage for the last N days (default 7, max 30).
    Adherence = recommended meal slots actually logged / total recommended slots.
    Only meals logged with a recommendation_id count as 'adhered'.
    Custom meals (recommendation_id=None) do not count for adherence.
    """
    days = min(max(days, 1), 30)
    result = await calculate_adherence(session, current_user.id, days)
    return result
```

---

### 🔍 CLAUDE AUDIT — BLOCK N
- [ ] `MealLogCreate.recommendation_id: Optional[int] = None`
- [ ] `log_meal()` now passes `recommendation_id=data.get("recommendation_id")`
- [ ] `log_meal()` returns the created `MealLog` object
- [ ] `calculate_adherence()` only counts meals WHERE `recommendation_id IS NOT NULL`
- [ ] `calculate_adherence()` uses `meals_per_day` from Patient row — not hardcoded
- [ ] `Patient` added to db_models import in progress_service.py
- [ ] `days` clamped to `[1, 30]` in the router endpoint
- [ ] `calculate_adherence` added to router's import from progress_service

---
---

## BLOCK O — Plan Versioning + Shopping Toggle
**Files:** `app/services/diet_plan_service.py`, `app/routers/meal_plan.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK O

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
ORM model: Recommendation has a `version` Integer column (default=1).
Current behaviour: old plan is soft-deleted (is_active=False), new plan is inserted with version=1 always.
Required behaviour: new plan version = previous plan version + 1.

Files to MODIFY:
  app/services/diet_plan_service.py
  app/routers/meal_plan.py

=======================================================
MODIFICATION 1: app/services/diet_plan_service.py
=======================================================
In the store_diet_plan method, REPLACE the current body:

    async def store_diet_plan(self, diet_plan: DietPlan, *, session: AsyncSession) -> int:
        """Insert a new recommendation row and return its id."""
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

WITH:

    async def store_diet_plan(self, diet_plan: DietPlan, *, session: AsyncSession) -> int:
        """
        Soft-delete any existing active plan, then insert a new one.
        New plan version = previous version + 1 (so version history is trackable).
        Returns the new recommendation id.
        """
        # Find current active plan to read its version before soft-deleting
        existing_result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == int(diet_plan.user_id),
                Recommendation.is_active == True,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        existing = existing_result.scalars().first()

        next_version = 1
        if existing is not None:
            next_version = (existing.version or 1) + 1
            existing.is_active = False  # soft-delete previous plan
            await session.flush()

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
Add this endpoint to the BOTTOM of meal_plan.py.
Do not modify any existing endpoint.

# ─── POST /api/v1/meal-plan/shopping-list/toggle ─────────────────────────

@router.post("/shopping-list/toggle")
async def toggle_ingredient_at_home(
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    ingredient_name: str = Query(..., min_length=1),
    at_home: bool = Query(...),
):
    """
    Mark an ingredient as 'available at home' or 'need to buy'.
    Stores the toggle state on the active Recommendation's ingredient_checklist JSONB.

    Each checklist item gets an 'at_home' boolean field.
    Matching is case-insensitive on ingredient name.

    Returns 404 if no active plan.
    Returns 404 if the ingredient is not found in the checklist.
    """
    rec_result = await session.execute(
        select(Recommendation)
        .where(
            Recommendation.patient_id == current_user.id,
            Recommendation.is_active == True,
        )
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active meal plan found")

    checklist = list(rec.ingredient_checklist or [])
    search = ingredient_name.strip().lower()
    found = False

    updated_checklist = []
    for item in checklist:
        name = str(item.get("ingredient") or item.get("name") or "").lower()
        if name == search:
            item = dict(item)      # copy — JSONB items are read-only dicts
            item["at_home"] = at_home
            found = True
        updated_checklist.append(item)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient '{ingredient_name}' not found in checklist",
        )

    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(ingredient_checklist=updated_checklist)
    )
    await session.flush()
    return {
        "ingredient": ingredient_name,
        "at_home": at_home,
        "message": f"Marked as {'available at home' if at_home else 'need to buy'}",
    }

Add to the top-level imports of meal_plan.py (after the existing imports):
    from fastapi import Query
(Only if Query is not already imported)
```

---

### 🔍 CLAUDE AUDIT — BLOCK O
- [ ] `store_diet_plan` reads `existing.version` before soft-deleting
- [ ] `next_version = (existing.version or 1) + 1` — handles None version safely
- [ ] Soft-delete happens via `existing.is_active = False` + `session.flush()` before insert
- [ ] New plan inserted with `version=next_version`
- [ ] `/shopping-list/toggle` matches case-insensitively (`name == search` after `.lower()`)
- [ ] JSONB item copied with `dict(item)` before mutating — immutable dict safety
- [ ] Uses `sa_update` with `values(ingredient_checklist=updated_checklist)` — not setattr
- [ ] Returns 404 for both no plan and ingredient not found

---

# ═══════════════════════════════════════════════════════════
# SPRINT 2 — Phase 2 Doctor Backend (12 remaining endpoints)
# 5 Blocks: P → Q → R → S → T
# ═══════════════════════════════════════════════════════════

## BLOCK P — ClinicalNote DB Model + Alembic Migration
**Files:** `app/models/db_models.py`, new Alembic migration
**Why first:** Blocks R depends on this table existing.

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK P

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async.
Latest Alembic revision: the one generated in Sprint 1 Block L (pace_preference migration).

TASK 1: app/models/db_models.py — ADD ClinicalNote model
=========================================================
Add this new model class to the BOTTOM of db_models.py, after the SubscriptionCode class.
Do NOT modify any existing class.

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id   = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id  = Column(Integer, ForeignKey("patients.id"), nullable=False)
    note_type   = Column(String(20), nullable=False, default="general")
    # "general" | "dietary" | "medical" | "progress"
    content     = Column(Text, nullable=False)
    is_private  = Column(Boolean, default=True)   # True = doctor-only, False = visible to patient
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor      = relationship("Doctor")
    patient     = relationship("Patient")

    __table_args__ = (
        Index("idx_cn_doctor_patient", "doctor_id", "patient_id"),
    )

Also add ClinicalNote to the Doctor model's relationships section:
    clinical_notes = relationship("ClinicalNote", back_populates=None, foreign_keys="ClinicalNote.doctor_id")

TASK 2: Generate and run Alembic migration
=========================================================
Run:
    alembic revision --autogenerate -m "add_clinical_notes_table"

Verify upgrade() contains:
    op.create_table('clinical_notes', ...)
    with columns: id, doctor_id, patient_id, note_type, content, is_private, created_at, updated_at
    with foreign keys to doctors.id and patients.id
    with composite index on (doctor_id, patient_id)

Then run:
    alembic upgrade head
```

---

### 🔍 CLAUDE AUDIT — BLOCK P
- [ ] `ClinicalNote` model added at bottom of db_models.py
- [ ] `note_type` has valid default `"general"`
- [ ] `is_private` defaults to `True` — notes are doctor-only by default
- [ ] Composite index `idx_cn_doctor_patient` on `(doctor_id, patient_id)`
- [ ] Migration `down_revision` points to the Sprint 1 Block L revision id
- [ ] Migration creates `clinical_notes` table with all 8 columns

---
---

## BLOCK Q — Doctor Patient Data Endpoints
**Files:** `app/schemas/doctor.py` (MODIFY), `app/routers/doctor.py` (MODIFY)
**Adds:** patient logs view, patient progress view, remove patient endpoint

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK Q

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Existing doctor.py imports:
    from ..models.db_models import Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode
Existing doctor.py helper: _doctor_id(request) — extracts doctor_id from request.state

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD 3 new response schemas
=======================================================
Add these classes to the BOTTOM of doctor.py schemas file.
Do not touch existing classes.

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

=======================================================
MODIFICATION 2: app/routers/doctor.py — ADD 3 endpoints
=======================================================

Step 1 — Extend the existing imports line from:
    from ..models.db_models import (
        Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
    )
To:
    from ..models.db_models import (
        Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
        MealLog, ProgressLog,
    )

Step 2 — Extend schemas import to include new schemas:
    from ..schemas.doctor import (
        PatientSummary, PaginatedPatients, RecommendationDetail,
        PlanOverrideRequest, PatientRequestDetail, RejectRequest,
        GenerateCodesRequest, SubscriptionCodeDetail,
        MealLogEntry, PatientProgressEntry, PatientLogsResponse, PatientProgressResponse,
    )

Step 3 — Add these 3 endpoints AFTER the override_patient_plan endpoint.
Do not modify any existing endpoint.

# ─── GET /api/v1/doctor/patients/{patient_id}/logs ────────────────────────

@router.get("/patients/{patient_id}/logs", response_model=PatientLogsResponse)
async def get_patient_logs(
    patient_id: int,
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor views a patient's meal logs for the last N days.
    Only returns logs for patients belonging to this doctor.
    """
    did = _doctor_id(request)

    # Ownership check
    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from datetime import timedelta
    start = date.today() - timedelta(days=days - 1)

    result = await session.execute(
        select(MealLog)
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
        )
        .order_by(MealLog.logged_date.desc(), MealLog.created_at.desc())
    )
    logs = result.scalars().all()
    return PatientLogsResponse(patient_id=patient_id, period_days=days, meal_logs=logs)


# ─── GET /api/v1/doctor/patients/{patient_id}/progress ───────────────────

@router.get("/patients/{patient_id}/progress", response_model=PatientProgressResponse)
async def get_patient_progress(
    patient_id: int,
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor views a patient's weight/water/steps history for the last N days.
    """
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from datetime import timedelta
    start = date.today() - timedelta(days=days - 1)

    result = await session.execute(
        select(ProgressLog)
        .where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date >= start,
        )
        .order_by(ProgressLog.log_date.asc())
    )
    progress = result.scalars().all()
    return PatientProgressResponse(patient_id=patient_id, period_days=days, progress_logs=progress)


# ─── DELETE /api/v1/doctor/patients/{patient_id} ─────────────────────────

@router.delete("/patients/{patient_id}")
async def remove_patient(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor removes a patient from their list.
    Patient's account is NOT deleted — they become standalone (doctor_id=None).
    Subscription is set to inactive since they no longer have a doctor.
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
    return {"message": f"Patient {patient_id} removed from your list", "patient_id": patient_id}
```

---

### 🔍 CLAUDE AUDIT — BLOCK Q
- [ ] All 3 new endpoints verify `Patient.doctor_id == did` — no cross-doctor access
- [ ] `/logs` `days` clamped to `[1, 30]`
- [ ] `/progress` `days` clamped to `[1, 90]`
- [ ] `DELETE /patients/{id}` sets `doctor_id=None`, `user_type="standalone"`, `subscription_status="inactive"`
- [ ] Patient record NOT deleted — account preserved
- [ ] `MealLog` and `ProgressLog` added to db_models import in doctor.py

---
---

## BLOCK R — Clinical Notes + Meal Plan Notes
**Files:** `app/schemas/doctor.py`, `app/routers/doctor.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK R

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
The clinical_notes table was created in Block P.
ORM model ClinicalNote: id, doctor_id, patient_id, note_type, content, is_private, created_at, updated_at
Existing doctor.py helpers: _doctor_id(request)

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD 3 schemas
=======================================================
Add these classes to the BOTTOM of schemas/doctor.py:

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

=======================================================
MODIFICATION 2: app/routers/doctor.py
=======================================================

Step 1 — Add ClinicalNote to the db_models import:
    from ..models.db_models import (
        Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
        MealLog, ProgressLog, ClinicalNote,
    )

Step 2 — Add new schemas to the schemas import:
    ClinicalNoteCreate, ClinicalNoteResponse, MealPlanNoteRequest

Step 3 — Add these 3 endpoints to the BOTTOM of doctor.py:

# ─── POST /api/v1/doctor/patients/{patient_id}/notes ─────────────────────

@router.post("/patients/{patient_id}/notes", response_model=ClinicalNoteResponse, status_code=201)
async def add_clinical_note(
    patient_id: int,
    body: ClinicalNoteCreate,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Add a private clinical note for a patient."""
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    note = ClinicalNote(
        doctor_id=did,
        patient_id=patient_id,
        note_type=body.note_type,
        content=body.content,
        is_private=body.is_private,
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

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(ClinicalNote)
        .where(ClinicalNote.doctor_id == did, ClinicalNote.patient_id == patient_id)
        .order_by(ClinicalNote.created_at.desc())
    )
    return result.scalars().all()


# ─── POST /api/v1/doctor/patients/{patient_id}/plan/notes ────────────────

@router.post("/patients/{patient_id}/plan/notes")
async def add_meal_plan_note(
    patient_id: int,
    body: MealPlanNoteRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Add a doctor note to a specific meal in the patient's active plan.
    Finds the matching meal by date + meal_type and injects a 'doctor_note' field.
    Returns 404 if no active plan or if the specific meal is not found.
    """
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    meals = list(rec.meals or [])
    found = False
    updated_meals = []
    for meal in meals:
        meal = dict(meal)  # copy — JSONB dicts are immutable
        if meal.get("Date") == body.meal_date and meal.get("Meal Type") == body.meal_type:
            meal["doctor_note"] = body.note
            found = True
        updated_meals.append(meal)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Meal '{body.meal_type}' on '{body.meal_date}' not found in plan",
        )

    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(meals=updated_meals)
    )
    await session.flush()
    return {"message": "Note added to meal", "meal_date": body.meal_date, "meal_type": body.meal_type}
```

---

### 🔍 CLAUDE AUDIT — BLOCK R
- [ ] All 3 endpoints verify `Patient.doctor_id == did` — ownership check before any action
- [ ] `ClinicalNote` created with `doctor_id=did` (from middleware) — not from request body
- [ ] Meal plan note: JSONB `dict(meal)` copy before mutation
- [ ] Meal plan note: uses `sa_update` + `.values(meals=updated_meals)` — not setattr
- [ ] `is_private` defaults to `True` in schema
- [ ] `GET /notes` filters by BOTH `doctor_id=did` AND `patient_id` — no cross-doctor leakage

---
---

## BLOCK S — Doctor Recipe Library
**Files:** `app/schemas/doctor.py`, `app/routers/doctor.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK S

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
FoodItem ORM model columns: id, recipe_name, slot_type, cal_per_serving, protein_per_serving,
  carbs_per_serving, fat_per_serving, fiber_per_serving, diet_type, region_tags, meal_time_tags,
  plan_type_tags, ingredients (JSONB), source, is_verified, image_url, created_at

Doctor-added recipes: source="doctor", is_verified=False (pending admin approval).

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD recipe schemas
=======================================================
Add these classes to the BOTTOM of schemas/doctor.py:

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

class RecipeAssignRequest(BaseModel):
    patient_ids: list[int] = Field(..., min_length=1)
    meal_type: str = Field(..., description="Breakfast | MorningSnacks | Lunch | EveningSnacks | Dinner")
    meal_date: str = Field(..., description="Date string e.g. '2026-03-15'")
    note: Optional[str] = None

=======================================================
MODIFICATION 2: app/routers/doctor.py
=======================================================

Step 1 — Add FoodItem to the db_models import:
    from ..models.db_models import (
        Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
        MealLog, ProgressLog, ClinicalNote, FoodItem,
    )

Step 2 — Add new schemas to import:
    FoodItemSummary, RecipeCreateRequest, RecipeAssignRequest

Step 3 — Add these 3 endpoints to the BOTTOM of doctor.py:

# ─── GET /api/v1/doctor/recipes ───────────────────────────────────────────

@router.get("/recipes", response_model=list[FoodItemSummary])
async def browse_recipes(
    request: Request,
    diet_type: Optional[str] = Query(default=None),
    meal_time: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Browse the food database. Supports optional filters and pagination."""
    stmt = select(FoodItem).where(FoodItem.is_verified == True)

    if diet_type:
        stmt = stmt.where(FoodItem.diet_type == diet_type)
    if meal_time:
        stmt = stmt.where(FoodItem.meal_time_tags.any(meal_time))
    if search:
        stmt = stmt.where(FoodItem.recipe_name.ilike(f"%{search}%"))

    offset = (page - 1) * page_size
    stmt = stmt.order_by(FoodItem.recipe_name).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    return result.scalars().all()


# ─── POST /api/v1/doctor/recipes ──────────────────────────────────────────

@router.post("/recipes", response_model=FoodItemSummary, status_code=201)
async def add_recipe(
    body: RecipeCreateRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor adds a new recipe to the food database.
    Saved with source='doctor', is_verified=False (pending admin approval).
    Once admin approves it (PATCH /admin/food/{id}/approve), it becomes available to all patients.
    """
    food = FoodItem(
        recipe_name=body.recipe_name,
        slot_type=body.slot_type,
        cal_per_serving=body.cal_per_serving,
        protein_per_serving=body.protein_per_serving,
        carbs_per_serving=body.carbs_per_serving,
        fat_per_serving=body.fat_per_serving,
        fiber_per_serving=body.fiber_per_serving,
        diet_type=body.diet_type,
        meal_time_tags=body.meal_time_tags,
        plan_type_tags=body.plan_type_tags,
        ingredients=body.ingredients,
        region_tags=body.region_tags,
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
    Inject a specific food item into specified patients' active meal plans.
    Adds the recipe as a new meal slot on the given date and meal_type.
    Only works for patients belonging to this doctor.
    Returns a summary of how many plans were updated.
    """
    did = _doctor_id(request)

    # Verify food item exists
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == recipe_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build the meal object to inject
    new_meal = {
        "Date": body.meal_date,
        "Meal Type": body.meal_type,
        "Menu Names": food.recipe_name,
        "Diet Type": food.diet_type,
        "Total Calories": float(food.cal_per_serving),
        "Total Protein": float(food.protein_per_serving),
        "Total Carbs": float(food.carbs_per_serving),
        "Total Fat": float(food.fat_per_serving),
        "Total Fiber": float(food.fiber_per_serving),
        "doctor_note": body.note or "",
        "food_id": recipe_id,
    }

    updated_count = 0
    failed_ids = []

    for pid in body.patient_ids:
        # Ownership check per patient
        owner = await session.execute(
            select(Patient.id).where(Patient.id == pid, Patient.doctor_id == did)
        )
        if owner.scalars().first() is None:
            failed_ids.append(pid)
            continue

        rec_result = await session.execute(
            select(Recommendation)
            .where(Recommendation.patient_id == pid, Recommendation.is_active == True)
            .order_by(Recommendation.created_at.desc())
        )
        rec = rec_result.scalars().first()
        if rec is None:
            failed_ids.append(pid)
            continue

        updated_meals = list(rec.meals or []) + [new_meal]
        from sqlalchemy import update as sa_update
        await session.execute(
            sa_update(Recommendation)
            .where(Recommendation.id == rec.id)
            .values(meals=updated_meals)
        )
        updated_count += 1

    await session.flush()
    return {
        "message": f"Recipe assigned to {updated_count} patient(s)",
        "updated_count": updated_count,
        "failed_patient_ids": failed_ids,
    }
```

---

### 🔍 CLAUDE AUDIT — BLOCK S
- [ ] `GET /recipes` only returns `is_verified=True` items — doctor-added unverified items don't show in browse
- [ ] `POST /recipes` sets `source="doctor"`, `is_verified=False`
- [ ] `/assign` verifies `Patient.doctor_id == did` per patient in the list — no cross-doctor
- [ ] `/assign` skips patients with no active plan (adds to `failed_ids`, does not raise)
- [ ] New meal object injected includes `food_id` field — linkage preserved
- [ ] `search` filter uses `ilike` — case-insensitive

---
---

## BLOCK T — Doctor Dashboard Stats + Inactivity + Expiry Detection
**Files:** `app/schemas/doctor.py`, `app/routers/doctor.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK T

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Existing doctor.py helper: _doctor_id(request)
ORM models available: Doctor, Patient, MealLog, ProgressLog, Recommendation, SubscriptionCode

=======================================================
MODIFICATION 1: app/schemas/doctor.py — ADD dashboard schema
=======================================================
Add this class to the BOTTOM of schemas/doctor.py:

class DoctorDashboardStats(BaseModel):
    total_patients: int
    active_patients: int          # subscription_status == "active"
    pending_requests: int         # PatientRequest with status == "pending"
    plans_generated_this_week: int
    inactive_patients: list[dict] # patients with no logs in last 7 days
    expiring_soon: list[dict]     # patients whose subscription_end_date is within 7 days

=======================================================
MODIFICATION 2: app/routers/doctor.py — ADD 1 endpoint
=======================================================
Add this endpoint to the BOTTOM of doctor.py:

# ─── GET /api/v1/doctor/dashboard ─────────────────────────────────────────

@router.get("/dashboard", response_model=DoctorDashboardStats)
async def get_dashboard(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Aggregated stats for the doctor's home dashboard.
    Includes: patient counts, pending requests, plans this week,
    inactive patients (no logs 7+ days), expiring subscriptions (next 7 days).
    """
    from datetime import timedelta
    did = _doctor_id(request)
    today = date.today()
    seven_days_ago = today - timedelta(days=7)
    seven_days_ahead = today + timedelta(days=7)

    # Total patients
    total = (await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == did)
    )).scalar() or 0

    # Active patients
    active = (await session.execute(
        select(func.count(Patient.id)).where(
            Patient.doctor_id == did,
            Patient.subscription_status == "active",
        )
    )).scalar() or 0

    # Pending requests
    pending = (await session.execute(
        select(func.count(PatientRequest.id)).where(
            PatientRequest.doctor_id == did,
            PatientRequest.status == "pending",
        )
    )).scalar() or 0

    # Plans generated this week
    week_start = today - timedelta(days=today.weekday())
    plans_this_week = (await session.execute(
        select(func.count(Recommendation.id))
        .join(Patient, Recommendation.patient_id == Patient.id)
        .where(
            Patient.doctor_id == did,
            Recommendation.week_start_date >= week_start,
        )
    )).scalar() or 0

    # Inactive patients — no meal log in the last 7 days
    # Get all patient IDs for this doctor who logged at least once in 7 days
    active_patients_result = await session.execute(
        select(MealLog.patient_id)
        .join(Patient, MealLog.patient_id == Patient.id)
        .where(
            Patient.doctor_id == did,
            MealLog.logged_date >= seven_days_ago,
        )
        .distinct()
    )
    active_patient_ids = {row[0] for row in active_patients_result.all()}

    # All patients for this doctor
    all_patients_result = await session.execute(
        select(Patient).where(Patient.doctor_id == did)
    )
    all_patients = all_patients_result.scalars().all()

    inactive_patients = [
        {"patient_id": p.id, "name": p.name, "email": p.email}
        for p in all_patients
        if p.id not in active_patient_ids
    ]

    # Expiring soon — subscription_end_date within next 7 days
    expiring_result = await session.execute(
        select(Patient).where(
            Patient.doctor_id == did,
            Patient.subscription_status == "active",
            Patient.subscription_end_date.isnot(None),
            Patient.subscription_end_date <= seven_days_ahead,
        )
    )
    expiring_patients = expiring_result.scalars().all()
    expiring_soon = [
        {
            "patient_id": p.id,
            "name": p.name,
            "subscription_end_date": p.subscription_end_date.isoformat() if p.subscription_end_date else None,
        }
        for p in expiring_patients
    ]

    return DoctorDashboardStats(
        total_patients=total,
        active_patients=active,
        pending_requests=pending,
        plans_generated_this_week=plans_this_week,
        inactive_patients=inactive_patients,
        expiring_soon=expiring_soon,
    )

Add DoctorDashboardStats to the schemas import line in doctor.py.
```

---

### 🔍 CLAUDE AUDIT — BLOCK T
- [ ] All queries filter by `Patient.doctor_id == did` — no cross-doctor data
- [ ] `inactive_patients` uses set subtraction — not a correlated subquery
- [ ] `expiring_soon` checks `subscription_end_date <= seven_days_ahead` AND `is not None`
- [ ] `plans_generated_this_week` uses a JOIN on Patient to scope to this doctor's patients
- [ ] All `.scalar()` calls have `or 0` fallback — no None arithmetic

---

# ═══════════════════════════════════════════════════════════
# SPRINT 3 — Phase 3 Admin Backend (16 remaining endpoints)
# 4 Blocks: U → V → W → X
# ═══════════════════════════════════════════════════════════

## BLOCK U — AuditLog DB Model + Admin Login + Doctor Management
**Files:** `app/models/db_models.py`, new Alembic migration, `app/routers/auth.py`, `app/routers/admin.py`, `app/schemas/admin.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK U

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Latest Alembic revision: the clinical_notes migration from Sprint 2 Block P.
Existing admin router: POST /doctors, GET /doctors, GET /stats, PATCH /doctors/{id}/deactivate
Admin auth currently uses get_current_admin dep (standard OAuth2 bearer via /auth/token equivalent).
The Admin ORM model has: mfa_secret, mfa_enabled (Boolean), allowed_ips (JSONB) columns already.

=======================================================
TASK 1: app/models/db_models.py — ADD AuditLog model
=======================================================
Add this class to the BOTTOM of db_models.py, after ClinicalNote:

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    actor_id    = Column(Integer, nullable=False)   # doctor.id or admin.id
    actor_role  = Column(String(10), nullable=False)  # "doctor" | "admin"
    action      = Column(String(100), nullable=False)  # e.g. "accept_request", "deactivate_doctor"
    entity_type = Column(String(50), nullable=True)   # e.g. "patient", "doctor", "recipe"
    entity_id   = Column(Integer, nullable=True)      # ID of the affected record
    detail      = Column(JSONB, default={})           # any extra context
    ip_address  = Column(String(45), nullable=True)   # IPv4 or IPv6
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_al_actor", "actor_id", "actor_role"),
        Index("idx_al_created", "created_at"),
    )

=======================================================
TASK 2: Generate and run Alembic migration
=========================================================
Run:
    alembic revision --autogenerate -m "add_audit_logs_table"

Verify upgrade() creates the audit_logs table with all 9 columns and 2 indexes.
Then run:
    alembic upgrade head

=======================================================
TASK 3: app/services/audit_service.py — CREATE new file
=========================================================
Create a new file at app/services/audit_service.py with this content:

"""
Audit log service — write-only, fire-and-forget.
All writes are wrapped in try/except so audit failures never break the main request.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.db_models import AuditLog

_log = logging.getLogger(__name__)


async def log_action(
    session: AsyncSession,
    *,
    actor_id: int,
    actor_role: str,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    detail: dict = None,
    ip_address: str = None,
) -> None:
    """
    Write an audit log entry. Never raises — failures are logged and swallowed.
    Call this AFTER the main operation has succeeded and session.flush() has run.
    """
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail or {},
            ip_address=ip_address,
        )
        session.add(entry)
        await session.flush()
    except Exception as exc:
        _log.error(f"Audit log failed: {exc}", exc_info=True)

=======================================================
TASK 4: app/routers/auth.py — ADD admin login endpoint
=========================================================
Add this endpoint to the BOTTOM of auth.py (after the doctor_login endpoint):

@router.post("/admin/login")
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin login — email + password. Returns JWT with role=admin.
    MFA verification is checked client-side for now (full TOTP in security sprint).
    """
    from ..models.db_models import Admin as AdminModel
    result = await session.execute(
        select(AdminModel).where(AdminModel.email == form_data.username)
    )
    admin = result.scalars().first()

    if admin is None or not verify_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token_data = {
        "sub": admin.email,
        "role": "admin",
        "user_type": "admin",
        "admin_id": admin.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

=======================================================
TASK 5: app/schemas/admin.py — ADD 3 new schemas
=========================================================
Add these classes to the BOTTOM of schemas/admin.py:

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

=======================================================
TASK 6: app/routers/admin.py — ADD 3 endpoints + update existing
=========================================================

Step 1 — Add to imports:
    from ..models.db_models import Admin, Doctor, Patient, Recommendation, SubscriptionCode, AuditLog
    from ..schemas.admin import CreateDoctorRequest, DoctorAdminView, PlatformStats, DoctorDetailView, AuditLogEntry, PaginatedAuditLogs
    from ..services.audit_service import log_action

Step 2 — Add these 3 new endpoints to the BOTTOM of admin.py:

# ─── GET /api/v1/admin/doctors/{doctor_id} ────────────────────────────────

@router.get("/doctors/{doctor_id}", response_model=DoctorDetailView)
async def get_doctor_detail(
    doctor_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Full doctor profile including patient count."""
    doctor_result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doctor_result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    patient_count = (await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == doctor_id)
    )).scalar() or 0

    view = DoctorDetailView.model_validate(doctor)
    view.patient_count = patient_count
    return view


# ─── DELETE /api/v1/admin/doctors/{doctor_id} ─────────────────────────────

@router.delete("/doctors/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Remove a doctor. All their patients are set to standalone + inactive.
    The doctor row is soft-deleted (is_active=False, not physical delete).
    Action is audit-logged.
    """
    from fastapi import Request
    doctor_result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doctor_result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Disconnect all patients
    await session.execute(
        update(Patient)
        .where(Patient.doctor_id == doctor_id)
        .values(doctor_id=None, user_type="standalone", subscription_status="inactive")
    )

    # Soft-delete the doctor
    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(is_active=False)
    )
    await session.flush()

    await log_action(
        session,
        actor_id=admin.id,
        actor_role="admin",
        action="delete_doctor",
        entity_type="doctor",
        entity_id=doctor_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": f"Doctor {doctor_id} deleted and patients disconnected"}


# ─── GET /api/v1/admin/audit-logs ─────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedAuditLogs)
async def get_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    actor_role: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Paginated audit log viewer with optional filters."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_stmt = select(func.count(AuditLog.id))

    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
        count_stmt = count_stmt.where(AuditLog.actor_role == actor_role)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
        count_stmt = count_stmt.where(AuditLog.action.ilike(f"%{action}%"))

    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    result = await session.execute(stmt.offset(offset).limit(page_size))
    logs = result.scalars().all()
    return PaginatedAuditLogs(logs=logs, total=total, page=page, page_size=page_size)

Add to admin.py top-level imports: from typing import Optional
Add to admin.py top-level imports: from fastapi import Query, Request
```

---

### 🔍 CLAUDE AUDIT — BLOCK U
- [ ] `AuditLog` model has `idx_al_actor` and `idx_al_created` indexes
- [ ] `log_action()` wrapped in `try/except` — never raises
- [ ] `POST /auth/admin/login` returns JWT with `role="admin"` and `admin_id`
- [ ] `DELETE /admin/doctors/{id}` soft-deletes doctor (`is_active=False`) — not physical delete
- [ ] Patients disconnected BEFORE doctor soft-delete — correct order
- [ ] Audit log written AFTER `session.flush()` — not before
- [ ] `/audit-logs` `action` filter uses `ilike` — case-insensitive
- [ ] `DoctorDetailView` extends `DoctorAdminView` — no duplicate field definitions

---
---

## BLOCK V — Admin Codes + Subscription Override + Food Management
**Files:** `app/schemas/admin.py`, `app/routers/admin.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK V

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Existing admin.py imports include: AuditLog, log_action, SubscriptionCode, FoodItem (add if missing)
SubscriptionCode ORM: id, doctor_id, code, is_used, used_by_patient_id, expires_at, created_at
FoodItem ORM: id, recipe_name, is_verified, source, slot_type, diet_type, meal_time_tags, plan_type_tags

=======================================================
MODIFICATION 1: app/schemas/admin.py — ADD 3 schemas
=======================================================
Add to BOTTOM of schemas/admin.py:

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

=======================================================
MODIFICATION 2: app/routers/admin.py — ADD 7 endpoints
=======================================================
Add FoodItem and SubscriptionCode to the db_models import if not already there.
Add GenerateCodesAdminRequest, CodeAdminView, FoodAdminView to the schemas import.

Add these 7 endpoints to the BOTTOM of admin.py:

import secrets, string

def _gen_code(length: int = 12) -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))


# ─── POST /api/v1/admin/codes/generate ───────────────────────────────────

@router.post("/codes/generate", response_model=list[CodeAdminView], status_code=201)
async def admin_generate_codes(
    body: GenerateCodesAdminRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Generate a batch of subscription codes for a specific doctor."""
    from datetime import timezone, timedelta

    doctor_result = await session.execute(select(Doctor).where(Doctor.id == body.doctor_id))
    if doctor_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=body.expires_in_days)
    created = []

    for _ in range(body.count):
        for _ in range(10):
            candidate = _gen_code()
            exists = (await session.execute(
                select(SubscriptionCode.id).where(SubscriptionCode.code == candidate)
            )).scalars().first()
            if exists is None:
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
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="generate_codes", entity_type="doctor",
                     entity_id=body.doctor_id, detail={"count": body.count})
    return created


# ─── GET /api/v1/admin/codes ──────────────────────────────────────────────

@router.get("/codes", response_model=list[CodeAdminView])
async def list_all_codes(
    doctor_id: Optional[int] = Query(default=None),
    is_used: Optional[bool] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """View all subscription codes. Optional filter by doctor or used status."""
    stmt = select(SubscriptionCode).order_by(SubscriptionCode.created_at.desc())
    if doctor_id:
        stmt = stmt.where(SubscriptionCode.doctor_id == doctor_id)
    if is_used is not None:
        stmt = stmt.where(SubscriptionCode.is_used == is_used)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── PATCH /api/v1/admin/patients/{patient_id}/subscription/override ──────

@router.patch("/patients/{patient_id}/subscription/override")
async def override_subscription(
    patient_id: int,
    status: str = Query(..., description="active | inactive"),
    days: int = Query(default=30, ge=1, le=365),
    request: Request = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Manually override a patient's subscription status.
    Used for dispute resolution or manual activation.
    """
    from datetime import timezone, timedelta
    if status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'inactive'")

    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    new_end = datetime.now(timezone.utc) + timedelta(days=days) if status == "active" else None

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(subscription_status=status, subscription_end_date=new_end)
    )
    await session.flush()

    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="override_subscription", entity_type="patient",
                     entity_id=patient_id, detail={"status": status, "days": days})
    return {"patient_id": patient_id, "subscription_status": status, "end_date": new_end.isoformat() if new_end else None}


# ─── GET /api/v1/admin/food ───────────────────────────────────────────────

@router.get("/food", response_model=list[FoodAdminView])
async def list_food_items(
    source: Optional[str] = Query(default=None, description="manual | doctor"),
    is_verified: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Food database management view. Filter by source and verified status."""
    stmt = select(FoodItem).order_by(FoodItem.created_at.desc())
    if source:
        stmt = stmt.where(FoodItem.source == source)
    if is_verified is not None:
        stmt = stmt.where(FoodItem.is_verified == is_verified)
    offset = (page - 1) * page_size
    result = await session.execute(stmt.offset(offset).limit(page_size))
    return result.scalars().all()


# ─── PATCH /api/v1/admin/food/{food_id}/approve ───────────────────────────

@router.patch("/food/{food_id}/approve")
async def approve_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Approve a doctor-submitted recipe. Makes it available for meal generation."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    if food.is_verified:
        raise HTTPException(status_code=400, detail="Already verified")

    await session.execute(
        update(FoodItem).where(FoodItem.id == food_id).values(is_verified=True)
    )
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="approve_food", entity_type="food_item", entity_id=food_id)
    return {"message": f"Food item {food_id} approved", "recipe_name": food.recipe_name}


# ─── PATCH /api/v1/admin/food/{food_id}/reject ────────────────────────────

@router.patch("/food/{food_id}/reject")
async def reject_food_item(
    food_id: int,
    request: Request,
    reason: Optional[str] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Reject and soft-delete a doctor-submitted recipe."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    # Soft-delete by marking source as "rejected" — preserves row for audit
    await session.execute(
        update(FoodItem).where(FoodItem.id == food_id).values(source="rejected")
    )
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="reject_food", entity_type="food_item", entity_id=food_id,
                     detail={"reason": reason})
    return {"message": f"Food item {food_id} rejected"}


# ─── DELETE /api/v1/admin/food/{food_id} ─────────────────────────────────

@router.delete("/food/{food_id}")
async def delete_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Permanently delete a food item from the database."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    await session.delete(food)
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="delete_food", entity_type="food_item", entity_id=food_id)
    return {"message": f"Food item {food_id} permanently deleted"}
```

---

### 🔍 CLAUDE AUDIT — BLOCK V
- [ ] `admin_generate_codes` verifies doctor exists before generating
- [ ] Code generation retries 10x on collision, raises 500 after 10 failures
- [ ] `approve_food` raises 400 if already verified — idempotent guard
- [ ] `reject_food` soft-deletes by setting `source="rejected"` — row preserved for audit
- [ ] Every state-changing endpoint calls `log_action()` after `session.flush()`
- [ ] `GET /food` returns results from ALL sources (manual + doctor + rejected) — admin sees everything
- [ ] `override_subscription` sets `subscription_end_date=None` when status is "inactive"

---
---

## BLOCK W — DPDP Data Erasure + IP Whitelisting Middleware + Billing Overview
**Files:** `app/routers/admin.py`, `app/core/middleware.py`

---

### 🤖 ANTIGRAVITY PROMPT — BLOCK W

```
CONTEXT
=======
Project: Mityahar FastAPI backend. Python 3.12, SQLAlchemy 2.0 async, Pydantic v2.
Admin ORM model has: allowed_ips = Column(JSONB, default=[])
  — if allowed_ips is empty list [], IP whitelisting is DISABLED (any IP allowed)
  — if allowed_ips has values, only those IPs may access /admin routes
app/core/middleware.py has SubscriptionCheckMiddleware and DoctorIsolationMiddleware already.
main.py already adds both middlewares via app.add_middleware().

=======================================================
TASK 1: app/core/middleware.py — ADD AdminIPWhitelistMiddleware
=========================================================
Add this new class to the BOTTOM of middleware.py, after DoctorIsolationMiddleware.
Do not modify any existing middleware.

class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Checks the requesting IP against the admin's allowed_ips list (stored in DB).
    Only fires on /admin routes.
    If no admin JWT present, skips check (route dep will reject unauthenticated).
    If allowed_ips is empty on the admin row, all IPs are allowed (dev/staging mode).

    NOTE: This middleware makes ONE DB query per admin request.
    Switch to a Redis cache if admin traffic is high.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        admin_prefix = f"{settings.API_V1_STR}/admin"

        # Only enforce on admin routes
        if not path.startswith(admin_prefix):
            return await call_next(request)

        # Skip the login endpoint itself
        if path == f"{settings.API_V1_STR}/auth/admin/login":
            return await call_next(request)

        token = _extract_token(request)
        if token is None:
            return await call_next(request)  # let route dep produce 401

        payload = _safe_decode(token)
        if payload is None or payload.get("role") != "admin":
            return await call_next(request)

        # Import here to avoid circular imports
        from ..models.db_models import Admin as AdminModel
        from ..core.database import AsyncSessionLocal

        admin_email = payload.get("sub")
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select as sa_select
                result = await session.execute(
                    sa_select(AdminModel.allowed_ips).where(AdminModel.email == admin_email)
                )
                row = result.first()
        except Exception:
            # DB error — fail open (log and allow) so admin isn't locked out
            return await call_next(request)

        if row is None:
            return JSONResponse(status_code=403, content={"detail": "Admin not found"})

        allowed_ips = row[0] or []

        # Empty list = whitelist disabled
        if not allowed_ips:
            return await call_next(request)

        client_ip = request.client.host if request.client else None
        if client_ip not in allowed_ips:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "IP address not whitelisted",
                    "code": "IP_NOT_ALLOWED",
                },
            )

        return await call_next(request)

=======================================================
TASK 2: app/main.py — REGISTER the new middleware
=========================================================
Add this import at the top of main.py alongside the existing middleware imports:
    from .core.middleware import SubscriptionCheckMiddleware, DoctorIsolationMiddleware, AdminIPWhitelistMiddleware

Add the new middleware registration AFTER the DoctorIsolationMiddleware line:
    app.add_middleware(AdminIPWhitelistMiddleware)

The order in main.py should be (outermost first):
    app.add_middleware(AdminIPWhitelistMiddleware)
    app.add_middleware(DoctorIsolationMiddleware)
    app.add_middleware(SubscriptionCheckMiddleware)
    app.add_middleware(CORSMiddleware, ...)

=======================================================
TASK 3: app/routers/admin.py — ADD billing overview + DPDP erasure endpoints
=========================================================
Add these 2 endpoints to the BOTTOM of admin.py:

# ─── GET /api/v1/admin/billing ────────────────────────────────────────────

@router.get("/billing")
async def get_billing_overview(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Platform-wide billing overview.
    Revenue is computed from subscription codes consumed (each code = 1 patient subscription).
    Does not integrate Razorpay (Phase 4) — this is a derived view over existing data.
    """
    # Total codes issued
    total_issued = (await session.execute(
        select(func.count(SubscriptionCode.id))
    )).scalar() or 0

    # Total codes consumed (= active subscriptions ever created)
    total_consumed = (await session.execute(
        select(func.count(SubscriptionCode.id)).where(SubscriptionCode.is_used == True)
    )).scalar() or 0

    # Currently active subscriptions
    active_now = (await session.execute(
        select(func.count(Patient.id)).where(Patient.subscription_status == "active")
    )).scalar() or 0

    # Per-doctor breakdown
    doctor_breakdown_result = await session.execute(
        select(
            Doctor.id,
            Doctor.name,
            Doctor.email,
            func.count(SubscriptionCode.id).label("total_codes"),
            func.sum(
                func.cast(SubscriptionCode.is_used, Integer)
            ).label("used_codes"),
        )
        .join(SubscriptionCode, Doctor.id == SubscriptionCode.doctor_id, isouter=True)
        .group_by(Doctor.id, Doctor.name, Doctor.email)
        .order_by(func.count(SubscriptionCode.id).desc())
    )

    breakdown = [
        {
            "doctor_id": row.id,
            "name": row.name,
            "email": row.email,
            "total_codes_issued": row.total_codes or 0,
            "codes_consumed": int(row.used_codes or 0),
        }
        for row in doctor_breakdown_result.all()
    ]

    return {
        "platform_totals": {
            "total_codes_issued": total_issued,
            "total_codes_consumed": total_consumed,
            "active_subscriptions_now": active_now,
        },
        "by_doctor": breakdown,
    }


# ─── DELETE /api/v1/admin/patients/{patient_id} ───────────────────────────

@router.delete("/patients/{patient_id}")
async def erase_patient_data(
    patient_id: int,
    request: Request,
    confirm: bool = Query(..., description="Must be true to execute erasure"),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    DPDP Act compliance data erasure.
    Anonymises patient PII — does NOT delete the row (preserves aggregate stats).
    Deletes all meal_logs and progress_logs for this patient.
    Requires confirm=true query param to prevent accidental erasure.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Add ?confirm=true to confirm erasure. This action is irreversible.",
        )

    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    import uuid
    anon_suffix = str(uuid.uuid4())[:8]

    # Anonymise PII
    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            email=f"deleted_{anon_suffix}@erased.invalid",
            name=f"Deleted User {anon_suffix}",
            phone=None,
            hashed_password="ERASED",
            date_of_birth=None,
            health_goals=[],
            medical_conditions=[],
            food_allergies=[],
            dietary_preferences=[],
            fasting_days=[],
            eating_habits=[],
            occupation=None,
            is_active=False,
        )
    )

    # Delete logs
    from sqlalchemy import delete as sa_delete
    from ..models.db_models import MealLog as MealLogModel, ProgressLog as ProgressLogModel
    await session.execute(sa_delete(MealLogModel).where(MealLogModel.patient_id == patient_id))
    await session.execute(sa_delete(ProgressLogModel).where(ProgressLogModel.patient_id == patient_id))
    await session.flush()

    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="dpdp_erasure", entity_type="patient", entity_id=patient_id,
                     ip_address=request.client.host if request.client else None)

    return {"message": f"Patient {patient_id} data erased in compliance with DPDP Act"}

Add to admin.py top-level imports if missing:
    from sqlalchemy import Integer
    from sqlalchemy.orm import joinedload
```

---

### 🔍 CLAUDE AUDIT — BLOCK W
- [ ] `AdminIPWhitelistMiddleware` skips `/auth/admin/login` — admin can always log in
- [ ] Empty `allowed_ips = []` means whitelist DISABLED — all IPs allowed
- [ ] DB error in IP check fails OPEN (returns `call_next`) — admin not locked out
- [ ] Middleware order in main.py: Admin IP → Doctor ISO → Subscription → CORS
- [ ] DPDP erasure requires `confirm=true` query param — no accidental deletion
- [ ] DPDP anonymises row — does NOT physically delete patient row (aggregate stats preserved)
- [ ] Logs (meal_logs, progress_logs) ARE physically deleted
- [ ] Billing overview uses `isouter=True` join — doctors with zero codes still appear
- [ ] Audit log written for both erasure and billing-adjacent actions

---

# ═══════════════════════════════════════════════════════════
# EXECUTION SUMMARY
# ═══════════════════════════════════════════════════════════

## Sprint 1 — Phase 1 Cleanup
```
Block L → Block M → Block N → Block O
```
Estimated: 1 session (all small, no new tables except adding 3 columns)

## Sprint 2 — Phase 2 Doctor Backend
```
Block P → Block Q → Block R → Block S → Block T
```
Estimated: 2 sessions (Block P has a new table; Block S+T are substantial)

## Sprint 3 — Phase 3 Admin Backend
```
Block U → Block V → Block W
```
Estimated: 2 sessions (Block U has new table + 6 tasks; Block W has middleware)

---

## POST SPRINT 3 — What's left before frontend
After all 3 backend sprints, the only remaining backend items are:
1. Phase 6 ETL (load food data into DB) — can run in parallel with frontend
2. Phase 4 Billing (Razorpay) — post-launch
3. Phase 5 Notifications (FCM) — post-launch
4. Firebase Google OAuth — Sprint 6 (patient app)

**The backend is fully API-complete for all 3 frontends after Sprint 3.**

---

## AUDIT RULE
After each block: paste output to Claude before running next block.
Claude reads the actual modified files — not the diff — and verifies every checklist item.
