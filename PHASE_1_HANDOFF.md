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
**IDE:** Google Antigravity (agent-first). Complex multi-file tasks go to Antigravity via a precise prompt. You write the prompts and audit the output — never trust walkthroughs, always read the actual files and run an audit script before declaring a step done.

---

## Phase 0 — COMPLETE

Everything below is already built, tested, and verified. Do not rebuild it.

### Database (12 tables in PostgreSQL — all migrated, alembic check: clean)
`admins`, `doctors`, `patients`, `recommendations`, `meal_logs`, `progress_logs`,
`patient_requests`, `subscription_codes`, `food_items`, `meal_templates`,
`clinical_notes`, `audit_logs`

### ORM models (all in `app/models/db_models.py`)
- **Patient** — 38 cols incl. `bmi`, `bmr`, `tdee`, `pace_preference`, `eating_habits`, `nonveg_meals_per_week`, `subscription_status`, `doctor_id`
- **Doctor** — email, hashed_password, specialization, clinic, `clinical_notes` relationship
- **Admin** — email, hashed_password, `allowed_ips` JSONB
- **Recommendation** — `meals` JSONB, `ingredient_checklist` JSONB, `version` int, `is_active`, `doctor_notes`
- **MealLog** — per-meal logging with `calories_consumed`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`
- **ProgressLog** — one row per patient+date, includes `calorie_adjustment` Numeric (written by Phase 1 Feature 5)
- **PatientRequest** — pending/accepted/rejected connection requests
- **SubscriptionCode** — doctor-generated codes, `is_used`, `used_by_patient_id`, `expires_at`
- **ClinicalNote** — `note_type` (general/dietary/medical/progress), `is_private`, doctor+patient FKs
- **AuditLog** — `actor_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `detail` JSONB, `ip_address`

### Auth system
- JWT always embeds: `sub`, `role`, `user_type`, `sub_status`, `patient_id`/`doctor_id`, `exp`, `iat`, `nbf`
- Three role deps in `app/core/security.py`: `get_current_patient`, `get_current_doctor`, `get_current_admin`
- `get_current_user = get_current_patient` alias in `user_service.py` (backward compat for 5 routers)
- `POST /api/v1/auth/token` — patient login
- `POST /api/v1/auth/doctor/login` — doctor login
- `POST /api/v1/auth/register` — patient register (409 on duplicate email)

### Middleware (`app/core/middleware.py`) — zero DB queries
- `SubscriptionCheckMiddleware` — reads `sub_status` from JWT claim, blocks `/meal-plan`, `/progress`, `/diet-plans` for inactive patients
- `DoctorIsolationMiddleware` — reads `doctor_id` from JWT claim, restricts `/doctor/*`, injects `request.state.doctor_id`

### Diet plan service (`app/services/diet_plan_service.py`)
- Returns `DietPlanResponse` from `app/schemas/diet_plan.py` (NOT the old `models/diet_plan.py` — that file is deleted)
- `store_diet_plan()` — soft-deletes previous active plan, inserts new one with `version + 1`
- `get_diet_plan()` — returns active plan with `version` field populated
- `get_plan_history()` — returns all plans (active + inactive) newest first, no meals payload

### Meal generator (`app/services/meal_generator/meal_generator.py`)
- Slot-based (not recipe-based). MealTemplates define slots, FoodItems fill them.
- 4-level waterfall per slot: region+weekly → no-region+weekly → region → no-region. BETWEEN filter and `daily_used_ids` NEVER dropped.
- Non-veg weekly budget: pre-allocates 3-4 non-veg slots at Lunch/Dinner only (from `patient.nonveg_meals_per_week`). No two non-veg on same day. All other slots Vegetarian.
- Diet fallback chain: Non-Veg → Eggetarian → Veg. `user_diet=` kwarg passed to `_find_food_item` to preserve breakfast-egg exception.
- Slot quality blocklist: chutney/pickle/powder blocked from grain/dal_protein/main_dish/sabzi (LIMIT 5 + `_pick()`).
- Shopping list: pantry staples excluded (`is_pantry_staple=True` in JSONB), names normalized to `.strip().title()`.
- Dataset: 1,963 verified Indian recipes, avg 435 kcal, all below 1,200 kcal, 3,956 pantry staples tagged.

### All current endpoints
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

POST   /api/v1/diet-plans/generate          (3-retry loop, HTTP 503 on all fail)
GET    /api/v1/diet-plans/my-plan
GET    /api/v1/diet-plans/today
PUT    /api/v1/diet-plans/update
DELETE /api/v1/diet-plans/delete
GET    /api/v1/diet-plans/ingredient-checklist
GET    /api/v1/diet-plans/weekly-ingredients

POST   /api/v1/meal-plan/adjust             (versioned — calls store_diet_plan)
GET    /api/v1/meal-plan/week               (7-day dict keyed by date)
GET    /api/v1/meal-plan/history            (plan metadata, no meals payload)
GET    /api/v1/meal-plan/shopping-list      (grouped by category, handles both 'ingredient'/'Ingredient' keys)
POST   /api/v1/meal-plan/shopping-list/toggle  (at_home flag on checklist item)

POST   /api/v1/progress/log/meal
POST   /api/v1/progress/log/water
POST   /api/v1/progress/log/steps
POST   /api/v1/progress/log/weight
POST   /api/v1/progress/log/activity
GET    /api/v1/progress/today               (uses patient.tdee, fallback 2000)
GET    /api/v1/progress/weekly
GET    /api/v1/progress/weight
```

### Known tech debt (do not fix unless blocking Phase 1)
- `ProgressLog.calorie_adjustment` exists and is queried in `/adjust` but **nothing writes it yet** — Day N+1 carry-over is silently 0 until Phase 1 Feature 5 is built
- `/progress/today` falls back to `target=2000` when `patient.tdee=None` (new patients before onboarding)
- `slowapi` is in-memory (not Redis). Fine for dev, fix before multi-worker production
- ~20 dirty `food_items` rows pending Ollama clean pass

---

## Phase 1 — BUILD THIS (in order)

### Feature 1 — Patient onboarding (FIRST — blocks everything else)
New patients register with just email/password/name/gender/height/weight/activity/diet.
Onboarding is a separate step that completes the profile and computes TDEE.

```
POST /api/v1/patients/onboarding
Auth: get_current_patient
Body: {
  date_of_birth: date,
  health_goals: list[str],
  medical_conditions: list[str],
  food_allergies: list[str],
  target_weight_kg: float,
  meals_per_day: int,          (3 or 5)
  sleep_hours: float,
  water_glasses: int,
  occupation: str,
  nonveg_meals_per_week: int   (0-7, default 3)
}
Response: full Patient profile with bmi, bmr, tdee stored on the row
```

On success: calculate BMR/TDEE using existing `calculate_bmr()`/`calculate_tdee()` from `app/services/meal_generator/calculations.py`. Store on `Patient.bmr`, `Patient.tdee`, `Patient.bmi`. This fixes the `/progress/today` fallback-to-2000 issue.

### Feature 2 — Subscription activation
Patient enters a code from their doctor to activate subscription.

```
POST /api/v1/patients/activate
Auth: get_current_patient
Body: { code: str }
```

Logic:
1. Look up `SubscriptionCode` where `code=code` AND `is_used=False` AND `expires_at > now()`
2. Set `code.is_used=True`, `code.used_by_patient_id=patient.id`, `code.used_at=now()`
3. Set `patient.subscription_status="active"`, `patient.doctor_id=code.doctor_id`
4. Set `patient.user_type="doctor_assigned"`
5. Return updated patient profile

Note: `sub_status` in the JWT is stale after this until next login — that's fine, middleware allows on next login.

### Feature 3 — Doctor dashboard
All routes under `/api/v1/doctor/*` — already protected by `DoctorIsolationMiddleware`.
`request.state.doctor_id` is already injected — use it always, never trust a body param for this.

```
GET  /api/v1/doctor/patients                     (list own patients, paginated)
GET  /api/v1/doctor/patients/{patient_id}        (single patient full profile)
GET  /api/v1/doctor/patients/{patient_id}/plan   (their active recommendation)
PUT  /api/v1/doctor/patients/{patient_id}/plan   (override plan + set doctor_notes, generated_by="doctor")
GET  /api/v1/doctor/requests                     (pending PatientRequests)
POST /api/v1/doctor/requests/{id}/accept         (set patient.doctor_id, status="accepted")
POST /api/v1/doctor/requests/{id}/reject         (set rejection_note, status="rejected")
POST /api/v1/doctor/subscription-codes           (generate N codes with expiry date)
GET  /api/v1/doctor/subscription-codes           (list own codes + used_by + used_at)
```

**Data isolation rule — non-negotiable:** Every single query must filter by `doctor_id = request.state.doctor_id`. A doctor must never see another doctor's patients or data. Audit this explicitly after building.

### Feature 4 — Patient-Doctor connection request
Patient can request to connect with a doctor (alternative to subscription code flow).

```
POST /api/v1/patients/request-doctor
Auth: get_current_patient
Body: { doctor_id: int }
```

Creates `PatientRequest(patient_id=current_user.id, doctor_id=body.doctor_id, status="pending")`.
Return 409 if a pending request already exists for this pair.
Doctor accepts/rejects via Feature 3 endpoints.

### Feature 5 — Day N+1 calorie adjustment
After logging meals, calculate surplus/deficit vs TDEE and carry it to the next day.

`ProgressLog.calorie_adjustment` column already exists in DB. Nothing writes it yet.

Logic: when `/progress/log/meal` is called, after inserting the meal log, recalculate the day's total calories consumed. Store `(total_consumed - patient.tdee)` as `ProgressLog.calorie_adjustment` for today's row (positive = overate, negative = under-ate).

`/meal-plan/adjust` already reads `yesterday.calorie_adjustment` and applies it to `target_calories`. So once writing is implemented, the full loop works automatically.

### Feature 6 — Admin panel (basic)
```
POST  /api/v1/admin/doctors                    (create doctor account with hashed password)
GET   /api/v1/admin/doctors                    (list all doctors)
PATCH /api/v1/admin/doctors/{id}/deactivate    (set is_active=False)
GET   /api/v1/admin/stats                      (patient count, active subscriptions, plans generated today)
```

All routes: `Depends(get_current_admin)`.
Write to `AuditLog` on every state-changing action (deactivate, create).

### Feature 7 — Google OAuth (patient login)
```
GET  /api/v1/auth/google              (redirect to Google consent)
GET  /api/v1/auth/google/callback     (exchange code, upsert Patient, return JWT)
```

Use `authlib` or `httpx` for the OAuth flow. On first login: create Patient with `name`/`email` from Google profile, random hashed_password (not usable), `is_active=True`. Return same JWT structure as `/token`.

---

## File locations to know

```
app/core/security.py              — get_current_patient/doctor/admin, create_access_token
app/core/middleware.py            — SubscriptionCheckMiddleware, DoctorIsolationMiddleware (zero-DB)
app/core/database.py              — get_db() AsyncSession dependency
app/models/db_models.py           — ALL ORM models
app/schemas/diet_plan.py          — DietPlanResponse (replaces deleted models/diet_plan.py)
app/schemas/user.py               — UserCreate, UserUpdate, UserResponse
app/schemas/progress.py           — MealLogCreate, WaterLogCreate etc.
app/services/user_service.py      — create_patient, authenticate_patient, get_current_user alias
app/services/diet_plan_service.py — DietPlanService (store/get/update/delete/history)
app/services/meal_generator/      — meal_generator.py (MealGenerator class + singleton)
app/services/meal_generator/calculations.py — calculate_bmr, calculate_tdee, calculate_bmi
alembic/versions/                 — all 7 migrations (clean, no drift)
scripts/                          — audit scripts, tag_pantry_staples.py
journal.txt                       — running project log
PHASE_1_HANDOFF.md                — this file
```

---

## Working rules (non-negotiable)

1. **Never trust Antigravity walkthroughs.** Always read every changed file directly, then run an audit script before declaring done.
2. **Audit script pattern:** Python script that imports changed modules and `assert`s exact behavior. Run it. Fix failures. Rerun until clean.
3. **Alembic after every model change.** `alembic revision --autogenerate -m "description"` → inspect file → `alembic upgrade head`. Check for false-positive GIN index drops and remove them before applying.
4. **No hardcoded values.** Age, TDEE, calorie targets — always derive from the Patient ORM object. Log a warning when fallback fires.
5. **Middleware is zero-DB.** Never add DB queries to middleware. Embed needed claims in JWT at login time.
6. **Doctor isolation is non-negotiable.** Every `/doctor/*` query must filter by `request.state.doctor_id`. Audit explicitly after every doctor feature.
7. **Test command:** `venv\Scripts\uvicorn app.main:app --reload --port 8001`
8. **DB check:** `venv\Scripts\alembic.exe check` must return "No new upgrade operations detected" after every migration.
