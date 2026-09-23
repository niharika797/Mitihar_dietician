# PHASE 1 HANDOFF — Mityahar Dietician API

## How to use this file
Paste the entire contents of this file as your first message in the Phase 1 chat.
Claude will read it, reconstruct full project context, and be ready to continue.

---

## Project

**Name:** Mityahar — AI-powered Indian diet planning app  
**Stack:** FastAPI + PostgreSQL (SQLAlchemy 2.0 async + asyncpg) + Alembic  
**Python:** 3.12 (venv at `venv\Scripts\activate`)  
**Location:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`  
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`  
**IDE:** Google Antigravity (agent-first). Complex multi-file tasks go to Antigravity via a precise prompt. You write the prompts and audit the output — never trust walkthroughs, always read the actual files.

---

## Phase 0 — COMPLETE

Everything below is already built, tested, and verified. Do not rebuild it.

### Database (10 tables in PostgreSQL)
`admins`, `doctors`, `patients`, `recommendations`, `meal_logs`, `progress_logs`,  
`patient_requests`, `subscription_codes`, `food_items`, `meal_templates`

All Alembic migrations are clean. `alembic check` returns "No new upgrade operations detected."

### Auth system
- JWT always embeds: `sub`, `role`, `user_type`, `sub_status`, `patient_id`/`doctor_id`, `exp`, `iat`, `nbf`
- Three role deps: `get_current_patient`, `get_current_doctor`, `get_current_admin` (in `app/core/security.py`)
- `get_current_user = get_current_patient` alias in `user_service.py` (backward compat)
- `POST /api/v1/auth/token` — patient login  
- `POST /api/v1/auth/doctor/login` — doctor login  
- `POST /api/v1/auth/register` — patient register (409 on duplicate email)

### Middleware (zero DB queries per request)
- `SubscriptionCheckMiddleware` — reads `sub_status` from JWT, blocks `/meal-plan`, `/progress`, `/diet-plans` for inactive patients
- `DoctorIsolationMiddleware` — reads `doctor_id` from JWT, restricts `/doctor/*`, injects `request.state.doctor_id`

### Meal generator
Located at `app/services/meal_generator/meal_generator.py`  
Key architecture:
- Slot-based (not recipe-based): MealTemplates define slots per meal_time, FoodItems fill slots
- 4-level waterfall per slot: region+weekly → no-region+weekly → region → no-region. BETWEEN filter and daily_used_ids NEVER dropped
- Non-veg weekly budget: pre-allocates 3-4 non-veg slots at Lunch/Dinner only (from `patient.nonveg_meals_per_week`). No two non-veg on same day. All other slots Vegetarian
- Diet fallback chain: Non-Veg → Eggetarian → Veg. `user_diet=` kwarg passed to preserve breakfast-egg exception
- Slot quality blocklist: chutney/pickle/powder blocked from grain/dal_protein/main_dish/sabzi
- Shopping list: pantry staples excluded (`is_pantry_staple=True` in JSONB), names normalized to `.strip().title()`
- Dataset: 1,963 verified Indian recipes, avg 435 kcal, all below 1,200 kcal

### Current endpoints
```
POST   /api/v1/auth/register
POST   /api/v1/auth/token
POST   /api/v1/auth/refresh
POST   /api/v1/auth/doctor/login
GET    /api/v1/users/me
PUT    /api/v1/users/me
GET    /api/v1/users/bmi
GET    /api/v1/calculations/bmr
GET    /api/v1/calculations/tdee
GET    /api/v1/calculations/bmi
POST   /api/v1/diet-plans/generate
GET    /api/v1/diet-plans/my-plan
GET    /api/v1/diet-plans/today
PUT    /api/v1/diet-plans/update
DELETE /api/v1/diet-plans/delete
GET    /api/v1/diet-plans/ingredient-checklist
GET    /api/v1/diet-plans/weekly-ingredients
POST   /api/v1/meal-plan/adjust
POST   /api/v1/progress/log/meal
POST   /api/v1/progress/log/water
POST   /api/v1/progress/log/steps
POST   /api/v1/progress/log/weight
POST   /api/v1/progress/log/activity
GET    /api/v1/progress/today
GET    /api/v1/progress/weekly
GET    /api/v1/progress/weight
```

### Known tech debt (do not fix unless blocking Phase 1)
- `app/models/diet_plan.py`: old Pydantic `DietPlan` class still used as return type in `diet_plan_service.py`. Replace in Phase 1 when recommendations layer gets proper schemas
- `/progress/today` falls back to `target=2000` when `patient.tdee=None` (new patients before onboarding)
- `slowapi` is in-memory (not Redis). Fine for dev, fix before multi-worker production
- ~20 dirty `food_items` rows pending Ollama clean pass

---

## Phase 1 — BUILD THIS

Work through these features in order. Each one has a dependency on the previous.

### Feature 1 — Patient onboarding (FIRST, blocks everything else)
New patients register with just email/password/name/gender/height/weight/activity/diet.  
Onboarding is a separate step that completes the profile and calculates TDEE.

```
POST /api/v1/patients/onboarding
Auth: get_current_patient
Body: {
  date_of_birth: date,
  health_goals: list[str],           # e.g. ["weight_loss", "muscle_gain"]
  medical_conditions: list[str],     # e.g. ["hypertension"]
  food_allergies: list[str],
  target_weight_kg: float,
  meals_per_day: int,                # 3 or 5
  sleep_hours: float,
  water_glasses: int,
  occupation: str,
  nonveg_meals_per_week: int         # 0-7, default 3
}
Response: full Patient profile with calculated bmi, bmr, tdee stored on row
```

On success: calculate BMR/TDEE using existing `calculate_bmr()`/`calculate_tdee()`, store on `Patient.bmr`, `Patient.tdee`, `Patient.bmi`. This fixes the `/progress/today` fallback-to-2000 issue.

### Feature 2 — Subscription activation
Patient enters a code given by their doctor to activate subscription.

```
POST /api/v1/patients/activate
Auth: get_current_patient
Body: { code: str }
```

Logic:
1. Look up `SubscriptionCode` where `code=code` and `is_used=False` and `expires_at > now()`
2. Set `code.is_used=True`, `code.used_by_patient_id=patient.id`, `code.used_at=now()`
3. Set `patient.subscription_status="active"`, `patient.doctor_id=code.doctor_id`
4. Set `patient.user_type="doctor_assigned"`
5. Return updated patient profile

Note: `sub_status` in the JWT is stale after this until next login. That's fine — middleware will allow access on next login.

### Feature 3 — Doctor dashboard
All routes under `/api/v1/doctor/*` — already protected by `DoctorIsolationMiddleware`.  
`request.state.doctor_id` is already injected — use it, never trust a body param for this.

```
GET  /api/v1/doctor/patients                    — list own patients (paginated)
GET  /api/v1/doctor/patients/{patient_id}       — single patient profile
GET  /api/v1/doctor/patients/{patient_id}/plan  — their active recommendation
PUT  /api/v1/doctor/patients/{patient_id}/plan  — override/edit plan + set doctor_notes
GET  /api/v1/doctor/requests                    — pending PatientRequests
POST /api/v1/doctor/requests/{id}/accept        — accept, set patient.doctor_id
POST /api/v1/doctor/requests/{id}/reject        — reject with rejection_note
POST /api/v1/doctor/subscription-codes          — generate N codes with expiry
GET  /api/v1/doctor/subscription-codes          — list own codes + used status
```

Data isolation rule: every query must filter by `doctor_id = request.state.doctor_id`. A doctor must never see another doctor's patients.

### Feature 4 — Patient-Doctor connection request
Patient can request to connect to a doctor (alternative to subscription code flow).

```
POST /api/v1/patients/request-doctor
Auth: get_current_patient
Body: { doctor_id: int }
```

Creates `PatientRequest(patient_id, doctor_id, status="pending")`.  
Doctor accepts/rejects via Feature 3 endpoints.

### Feature 5 — Day N+1 calorie adjustment
After logging meals for a day, calculate surplus/deficit vs TDEE.  
Redistribute across the next day's plan.

This is a background calculation, not a user-triggered endpoint.  
Trigger: when `/progress/log/meal` is called and the day's total crosses 80% of TDEE, calculate adjustment.  

Store result in `MealLog` (there's a `notes` field) or add a new column — your call.  
The adjustment affects the `target_calories` passed to the generator on the next `/meal-plan/adjust` call.

### Feature 6 — Admin panel (basic)
```
POST /api/v1/admin/doctors          — create doctor account (hashed password)
GET  /api/v1/admin/doctors          — list all doctors
GET  /api/v1/admin/stats            — patient count, active subscriptions, plans generated
PATCH /api/v1/admin/doctors/{id}/deactivate
```

All routes: `Depends(get_current_admin)`.

### Feature 7 — Clean up models/diet_plan.py
Replace the legacy Pydantic `DietPlan` return type in `diet_plan_service.py` with proper `RecommendationResponse` Pydantic schema.  
Delete `app/models/diet_plan.py` after.

---

## File locations to know

```
app/core/security.py         — get_current_patient/doctor/admin, create_access_token
app/core/middleware.py       — SubscriptionCheckMiddleware, DoctorIsolationMiddleware
app/core/database.py         — get_db() AsyncSession dependency
app/models/db_models.py      — ALL ORM models (Patient, Doctor, Admin, Recommendation, etc.)
app/services/user_service.py — create_patient, authenticate_patient, get_current_user alias
app/services/meal_generator/ — meal_generator.py (MealGenerator class + singleton)
alembic/versions/            — all migrations
scripts/                     — audit scripts, tag_pantry_staples.py
journal.txt                  — running project log (update after each phase)
```

---

## Working rules for this project

1. **Never trust Antigravity walkthroughs.** Always read every changed file directly after Antigravity reports completion, then run an audit script before declaring the step done.
2. **Audit script pattern:** write a Python script that imports the changed modules and asserts exact behavior — no unit test framework needed, just `assert` + `print`. Run it. Fix failures. Rerun until clean.
3. **Alembic after every model change.** Run `alembic revision --autogenerate -m "description"`, inspect the generated file, then `alembic upgrade head`. Check for GIN index drops (false positives) and remove them before applying.
4. **No hardcoded values.** Age, TDEE, calorie targets — always derive from the Patient ORM object. Fallback with a constant only as a last resort, and log a warning when it fires.
5. **Middleware is zero-DB.** Never add DB queries to middleware. Embed needed claims in JWT at login time.
6. **Doctor isolation is non-negotiable.** Every `/doctor/*` query must filter by `request.state.doctor_id`. Audit this explicitly after every doctor feature is built.
7. **Test command:** `venv\Scripts\uvicorn app.main:app --reload --port 8001`
