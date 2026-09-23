# MITYAHAR — PHASE 2 HANDOFF
> Generated: 2026-03-07 | Phase 0 + Phase 1: COMPLETE | Next: Frontend + Pre-Prod

## How to use this file
Paste the entire contents as your first message in any new chat.
Claude will read it, reconstruct full project context, and be ready to continue.

---

## Project

**Name:** Mityahar — AI-powered Indian diet planning app  
**Stack:** FastAPI + PostgreSQL (SQLAlchemy 2.0 async + asyncpg) + Alembic  
**Python:** 3.12 (venv at `venv\Scripts\activate`)  
**Location:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`  
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`  
**IDE:** Google Antigravity (agent-first). Complex multi-file tasks go to Antigravity via a precise prompt. You write the prompts and audit the output — never trust walkthroughs, always read the actual files and run an audit script before declaring a step done.  
**Frontend (planned):** React Native

---

## Architecture Overview

### Auth — Three-role JWT system
Every JWT embeds: `sub` (email), `role`, `user_type`, `sub_status`, `patient_id` OR `doctor_id` OR `admin_id`, `exp`, `iat`, `nbf`

| Role | Login endpoint | JWT role claim | Key dep |
|---|---|---|---|
| Patient | `POST /auth/token` | `patient` | `get_current_patient` |
| Doctor | `POST /auth/doctor/login` | `doctor` | `get_current_doctor` |
| Admin | `POST /auth/admin/login` | `admin` | `get_current_admin` |

### Middleware Stack (`app/core/middleware.py`) — all zero-DB except AdminIPWhitelist
1. **`AdminIPWhitelistMiddleware`** — fires on `/admin/*` only. Reads `Admin.allowed_ips` from DB. If `allowed_ips=[]`, whitelisting is disabled (allow all IPs).
2. **`DoctorIsolationMiddleware`** — fires on `/doctor/*`. Reads `doctor_id` from JWT claim, injects `request.state.doctor_id`. Zero DB.
3. **`SubscriptionCheckMiddleware`** — fires on `/meal-plan`, `/progress`, `/diet-plans`. Reads `sub_status` from JWT. Blocks inactive patients with HTTP 402. Zero DB.

### Doctor isolation rule — NON-NEGOTIABLE
Every single `/doctor/*` query must filter by `request.state.doctor_id`. Never trust a body param for doctor_id. This is injected by middleware, not derived from request body.

### Meal generator architecture
- Slot-based (not recipe-based). `MealTemplate` defines slots, `FoodItem` fills them.
- 4-level waterfall per slot: region+weekly → no-region+weekly → region+BETWEEN → no-region+BETWEEN. BETWEEN filter never dropped.
- Non-veg weekly budget: pre-allocates 3-4 slots at Lunch/Dinner only from `patient.nonveg_meals_per_week`. No two non-veg on same day.
- Diet fallback chain: Non-Veg → Eggetarian → Veg. `user_diet=` kwarg passed for breakfast-egg exception.
- Slot quality blocklist: chutney/pickle/powder blocked from grain/dal_protein/main_dish/sabzi (LIMIT 5 + `_pick()`).
- Pantry staples: `is_pantry_staple=True` items excluded from shopping list (3,956 tagged).
- Ingredient normalization: `.strip().title()` before grouping.

### Calorie adjustment loop — fully wired
1. `POST /progress/log/meal` — after insert, if today's calories ≥ 80% of TDEE → calls `calculate_and_store_calorie_adjustment()`
2. `calculate_and_store_calorie_adjustment()` — writes `tdee - today_calories` to `ProgressLog.calorie_adjustment`
3. `POST /meal-plan/adjust` — reads yesterday's `calorie_adjustment`, applies to `target_calories`

### Plan versioning
`store_diet_plan()` soft-deletes previous active plan (sets `is_active=False`), inserts new with `version = previous_version + 1`. `/adjust` calls `store_diet_plan`, so every adjustment increments version.

---

## Database — 12 Tables

### Migration chain (8 migrations, alembic check: PENDING `a1b2c3d4e5f6`)
```
92084b0bc541  food_items + meal_templates
  → 4e5124b3e103  all user tables (doctors, admins, patients, recommendations, meal_logs, progress_logs, patient_requests, subscription_codes)
    → cf7a21f007f0  fix nullable (streak_days, requested_at)
      → 861b9d58abdf  add calorie_adjustment to progress_logs
        → 370efc812ae5  add pace_preference, eating_habits, image_url
          → 3fb0a727fee2  add clinical_notes table
            → eb8dbef8dd19  add audit_logs table
              → a1b2c3d4e5f6  add google_id to patients  ← PENDING (run when DB is up)
```

**⚠️ ACTION REQUIRED:** Run `venv\Scripts\alembic.exe upgrade head` when DB is running to apply the `google_id` migration.

### All 12 tables + key columns

**`patients`** — 38 cols  
`id, email, hashed_password, name, phone, date_of_birth, gender, height_cm, weight_kg, activity_level (S/LA/MA/VA/SA), diet_type, region, health_condition, bmi, bmr, tdee, target_weight_kg, health_goals (JSONB), medical_conditions (JSONB), food_allergies (JSONB), dietary_preferences (JSONB), meals_per_day, fasting_days (JSONB), sleep_hours, water_glasses, occupation, smoking, alcohol, user_type (standalone|doctor_assigned), doctor_id (FK), subscription_status (active|inactive), subscription_end_date, disclaimer_accepted_at, nonveg_meals_per_week, role, is_active, google_id (nullable unique), pace_preference (slow|moderate|fast), eating_habits (JSONB)`

**`doctors`**  
`id, email, hashed_password, name, phone, specialization, clinic_name, clinic_address, city, mfa_secret, mfa_enabled, is_active, role`

**`admins`**  
`id, email, hashed_password, name, mfa_secret, mfa_enabled, allowed_ips (JSONB), is_active, role`

**`recommendations`**  
`id, patient_id (FK), week_start_date, week_number, meals (JSONB), ingredient_checklist (JSONB), is_active, generated_by (system|doctor), doctor_notes, version`

**`meal_logs`**  
`id, patient_id (FK), recommendation_id (FK nullable), logged_date, meal_type, food_id (FK nullable), custom_food_name, calories_consumed, protein_g, carbs_g, fat_g, fiber_g, portion_servings, notes`

**`progress_logs`** — one row per patient+date (unique constraint)  
`id, patient_id (FK), log_date, weight_kg, water_glasses, steps, calories_burned, total_calories_consumed, protein_pct, carbs_pct, fat_pct, streak_days, calorie_adjustment`

**`patient_requests`**  
`id, patient_id (FK), doctor_id (FK), status (pending|accepted|rejected), rejection_note, requested_at, responded_at`

**`subscription_codes`**  
`id, doctor_id (FK), code (unique 12-char), is_used, used_by_patient_id (FK nullable), used_at, expires_at`

**`clinical_notes`**  
`id, doctor_id (FK), patient_id (FK), note_type (general|dietary|medical|progress), content, is_private`

**`audit_logs`**  
`id, actor_id, actor_role (doctor|admin), action, entity_type, entity_id, detail (JSONB), ip_address`

**`food_items`**  
`id, recipe_name, slot_type, cal_per_serving, protein_per_serving, carbs_per_serving, fat_per_serving, fiber_per_serving, sodium_per_serving, serving_weight_g, diet_type, region_tags (ARRAY), meal_time_tags (ARRAY), plan_type_tags (ARRAY), ingredients (JSONB), source (manual|doctor|rejected), is_verified, image_url`

**`meal_templates`**  
`id, meal_time, region, diet_type, plan_type, slots (JSONB)` — unique on (meal_time, region, diet_type, plan_type)

---

## Complete Endpoint Inventory (84 endpoints)

### Auth (`/api/v1/auth/`)
```
POST   /auth/register                    patient register — body: email,password,name,gender,height,weight,activity_level,diet,health_condition,region + optional doctor_code
POST   /auth/token                       patient login — form: username,password
POST   /auth/refresh                     refresh JWT — body: {refresh_token}
POST   /auth/doctor/login                doctor login — form: username,password
POST   /auth/admin/login                 admin login — form: username,password
POST   /auth/google/verify               Google Sign-In — body: {id_token} — returns access_token,refresh_token,is_new_user
```

### Users (`/api/v1/users/`) — patient_token
```
GET    /users/me                         full patient profile
PUT    /users/me                         update profile fields
GET    /users/bmi                        current BMI
```

### Calculations (`/api/v1/calculations/`) — patient_token
```
GET    /calculations/bmr                 Basal Metabolic Rate
GET    /calculations/tdee                Total Daily Energy Expenditure
GET    /calculations/bmi                 Body Mass Index
```

### Patients (`/api/v1/patients/`) — patient_token
```
POST   /patients/onboarding              complete profile + computes+stores BMI/BMR/TDEE + auto-generates first diet plan (soft-fail)
POST   /patients/activate                enter subscription code → link to doctor → sub_status=active
POST   /patients/request-doctor          request connection to a doctor (409 on duplicate pending)
GET    /patients/request-status          poll most recent request status
POST   /patients/disclaimer              accept disclaimer — stores UTC timestamp
```

### Diet Plans (`/api/v1/diet-plans/`) — patient_token, subscription required
```
POST   /diet-plans/generate              generate 7-day plan — 3 internal retries, 503 if all fail
GET    /diet-plans/my-plan               active plan with version number
GET    /diet-plans/today                 today's meals only
PUT    /diet-plans/update                update doctor_notes or plan content (in-place, no version bump)
DELETE /diet-plans/delete                soft-delete active plan
GET    /diet-plans/ingredient-checklist  pantry-staple-excluded checklist
GET    /diet-plans/weekly-ingredients    full week ingredient list
```

### Meal Plan (`/api/v1/meal-plan/`) — patient_token, subscription required
```
POST   /meal-plan/adjust                 adjust plan (applies yesterday's calorie_adjustment, version++)
GET    /meal-plan/week                   7-day dict keyed by date string
GET    /meal-plan/history                plan metadata list, newest first, no meals payload
GET    /meal-plan/shopping-list          grouped by category, handles 'ingredient'/'Ingredient' key variants
POST   /meal-plan/shopping-list/toggle   toggle at_home flag on a checklist item
```

### Progress (`/api/v1/progress/`) — patient_token, subscription required
```
POST   /progress/log/meal                log meal — triggers calorie_adjustment if ≥80% TDEE
PUT    /progress/log/meal/{id}           edit meal log (24-hour window only)
DELETE /progress/log/meal/{id}           delete meal log (24-hour window only)
POST   /progress/log/water               add water glasses (cumulative)
PUT    /progress/log/water               overwrite today's water count
DELETE /progress/log/water               reset water to 0
POST   /progress/log/steps               add steps (cumulative)
PUT    /progress/log/steps               overwrite today's step count
DELETE /progress/log/steps               reset steps to 0
POST   /progress/log/weight              log today's weight
PUT    /progress/log/weight              overwrite today's weight
POST   /progress/log/activity            log steps + calories_burned + activity_type
GET    /progress/weight                  current weight from patient profile
GET    /progress/today                   calories/water/steps vs targets (uses real TDEE, fallback 2000)
GET    /progress/weekly                  daily calorie totals last 7 days
GET    /progress/weekly-report           full 7-day: macros + water + steps vs TDEE
GET    /progress/weight-history          weight entries for last N days (?days=30)
GET    /progress/streak                  consecutive logging days — stores on ProgressLog
GET    /progress/adherence/weekly        adherence % — only recommended meals (with recommendation_id) count
```

### Doctor (`/api/v1/doctor/`) — doctor_token, DoctorIsolationMiddleware injects request.state.doctor_id
```
GET    /doctor/dashboard                 stats: totals, pending, inactive patients, expiring subscriptions
GET    /doctor/patients                  paginated list — only this doctor's patients
GET    /doctor/patients/{id}             single patient full profile
GET    /doctor/patients/{id}/plan        patient's active plan
PUT    /doctor/patients/{id}/plan        override plan meals/doctor_notes, sets generated_by="doctor"
POST   /doctor/patients/{id}/plan/notes  inject doctor_note into specific meal slot by date+meal_type
GET    /doctor/patients/{id}/logs        meal logs last N days (?days=7)
GET    /doctor/patients/{id}/progress    weight/water/steps history (?days=30)
POST   /doctor/patients/{id}/notes       add clinical note (note_type: general|dietary|medical|progress)
GET    /doctor/patients/{id}/notes       list clinical notes — doctor sees only own notes
DELETE /doctor/patients/{id}             remove patient → standalone + inactive (account NOT deleted)
GET    /doctor/requests                  pending PatientRequests
POST   /doctor/requests/{id}/accept      accept → patient.doctor_id set, sub_status=active
POST   /doctor/requests/{id}/reject      reject → stores rejection_note
POST   /doctor/subscription-codes        generate N codes (collision-safe, 12-char alphanumeric)
GET    /doctor/subscription-codes        list own codes + is_used + used_by + used_at
GET    /doctor/recipes                   browse verified food items (?diet_type, ?meal_time, ?search)
POST   /doctor/recipes                   add recipe → source="doctor", is_verified=False (pending admin approval)
POST   /doctor/recipes/{id}/assign       inject recipe into multiple patients' active plans
```

### Admin (`/api/v1/admin/`) — admin_token, AdminIPWhitelistMiddleware
```
POST   /admin/doctors                    create doctor with hashed password (409 on duplicate email)
GET    /admin/doctors                    list all doctors
GET    /admin/doctors/{id}               doctor detail + patient count
PATCH  /admin/doctors/{id}/deactivate    set is_active=False
DELETE /admin/doctors/{id}               soft-delete + disconnect all patients (set standalone+inactive)
GET    /admin/stats                      total_patients, active_subscriptions, total_doctors, total_plans
POST   /admin/codes/generate             generate codes for any doctor (collision-safe)
GET    /admin/codes                      all codes (?doctor_id, ?is_used)
PATCH  /admin/patients/{id}/subscription/override   manual status override (?status=active&days=30)
GET    /admin/food                       food database (?source, ?is_verified, paginated)
PATCH  /admin/food/{id}/approve          approve doctor recipe → is_verified=True
PATCH  /admin/food/{id}/reject           soft-delete: sets source="rejected"
DELETE /admin/food/{id}                  hard-delete food item
GET    /admin/audit-logs                 paginated audit log (?actor_role, ?action)
GET    /admin/billing                    codes issued/used per doctor breakdown
DELETE /admin/patients/{id}              DPDP erasure — anonymise PII + hard-delete logs
```

---

## File Map
```
app/
  core/
    config.py         Settings — SECRET_KEY, GOOGLE_CLIENT_ID, CORS_ORIGINS etc.
    database.py       AsyncSession + AsyncSessionLocal + get_db()
    exceptions.py     Custom HTTPExceptions
    limiter.py        slowapi in-memory (TODO: Redis before multi-worker deploy)
    middleware.py     AdminIPWhitelistMiddleware, DoctorIsolationMiddleware, SubscriptionCheckMiddleware
    security.py       create_access_token, verify_password, get_password_hash, get_current_patient/doctor/admin

  models/
    db_models.py      ALL 12 ORM models in one file — do not split

  routers/
    auth.py           register, token, refresh, doctor/login, admin/login, google/verify
    users.py          /users/* (me, update, bmi)
    calculations.py   /calculations/* (bmr, tdee, bmi)
    patients.py       /patients/* (onboarding, activate, request-doctor, request-status, disclaimer)
    diet_plans.py     /diet-plans/*
    meal_plan.py      /meal-plan/*
    progress.py       /progress/*
    doctor.py         /doctor/* (778 lines — all doctor endpoints)
    admin.py          /admin/* (545 lines — all admin endpoints)

  schemas/
    user.py           UserCreate, UserUpdate, UserResponse, ActivityLevel, DietType, HealthCondition
    patients.py       OnboardingRequest, ActivationRequest, DoctorRequestBody, PatientProfileResponse
    doctor.py         PatientSummary, RecommendationDetail, ClinicalNoteCreate, RecipeCreateRequest, DoctorDashboardStats etc.
    admin.py          CreateDoctorRequest, DoctorAdminView, PlatformStats, AuditLogEntry, FoodAdminView etc.
    progress.py       MealLogCreate, WaterLogCreate, StepsLogCreate, WeightLogCreate, MealLogResponse etc.
    diet_plan.py      DietPlanResponse (replaces deleted models/diet_plan.py)

  services/
    user_service.py           create_patient, authenticate_patient, get_patient_by_email, get_current_user (alias)
    diet_plan_service.py      DietPlanService — store/get/update/delete/get_plan_history
    progress_service.py       log_meal/water/steps/weight/activity, get_today_summary, get_weekly_summary,
                              calculate_and_store_calorie_adjustment, calculate_and_store_streak,
                              calculate_adherence, get_weekly_report, update_meal_log, delete_meal_log
    audit_service.py          log_action() — fire-and-forget AuditLog writer

    meal_generator/
      meal_generator.py       MealGenerator class + singleton `meal_generator`
      calculations.py         calculate_bmr(), calculate_tdee(), calculate_bmi()

alembic/versions/             8 migration files — see chain above
scripts/
  audit_step6.py              Step 6 audit (15 checks)
  audit_meal_fixes.py         Meal plan fixes audit (10 checks)
  audit_google_oauth.py       Google OAuth audit (21 checks — all passing)
  tag_pantry_staples.py       Tags is_pantry_staple=True on 3,956 ingredients
  TESTING_PROMPT_FOR_ANTIGRAVITY.md  Full 84-endpoint testing prompt

.env
  SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, CORS_ORIGINS,
  GEMINI_API_KEY_1..4, GOOGLE_CLIENT_ID (Web OAuth Client ID from Google Console)

requirements.txt
  fastapi, google-auth, uvicorn, pydantic, python-jose[cryptography], passlib[bcrypt],
  bcrypt==4.0.1, python-multipart, pydantic[email], pydantic-settings, pandas, numpy,
  scikit-learn, openpyxl, pytest, httpx, python-dotenv, slowapi, sqlalchemy,
  asyncpg, greenlet, alembic, psycopg2-binary
```

---

## Google OAuth — Setup Status
- `google-auth` library installed ✅
- `GOOGLE_CLIENT_ID` in `.env` ✅ (Web application client — `753328753529-...`)
- `Patient.google_id` column in ORM ✅
- Migration `a1b2c3d4e5f6` written ✅ — **PENDING `alembic upgrade head`**
- `POST /auth/google/verify` endpoint live ✅

**React Native integration:**
- Install: `@react-native-google-signin/google-signin`
- Configure with `webClientId` = same Client ID as `GOOGLE_CLIENT_ID` in `.env`
- Call `GoogleSignin.getTokens()` → send `idToken` to `POST /auth/google/verify`
- Check `is_new_user` in response → if `true`, navigate to onboarding screen
- Android OAuth Client ID needed when testing on emulator/device (get SHA-1 from `./gradlew signingReport`)
- iOS OAuth Client ID needed when building for iOS (use Bundle ID)

---

## Known Tech Debt — Do Not Fix Unless Blocking

| Item | Impact | When to fix |
|---|---|---|
| `alembic upgrade head` not yet run | `google_id` column missing from DB | Before first Google Sign-In test |
| `slowapi` in-memory (not Redis) | Rate limits reset on server restart, breaks multi-worker | Before production deploy |
| ~20 dirty `food_items` rows | Minor data quality issue | Ollama clean pass, not urgent |
| `/progress/today` fallback to 2000 when `patient.tdee=None` | New patients before onboarding | Logs warning, acceptable |
| `ProgressLog.total_calories_consumed` never written | Unused column | Future analytics sprint |
| `MealLog.food_id` / `custom_food_name` rarely populated | Partial feature | Future food tracking sprint |

---

## What's Next — Phase 2

### 1. Pre-Prod Prep (before any real users)
- Run `alembic upgrade head` (google_id column)
- Switch `slowapi` from in-memory to Redis storage
- Set up real `SECRET_KEY` (32-byte random hex, not the dev key)
- Configure `CORS_ORIGINS` for production domain
- Set up admin account via direct DB insert or a seed script
- Set `allowed_ips` on Admin row if IP whitelisting needed

### 2. React Native Frontend
- Google Sign-In SDK setup (`@react-native-google-signin/google-signin`)
- Android OAuth Client ID (SHA-1 fingerprint from keystore)
- iOS OAuth Client ID (Bundle ID)
- Auth flow: login → store JWT → attach as Bearer header on all requests
- Onboarding screen (show when `is_new_user=true` from `/auth/google/verify`)
- Check `subscription_status` after login — if inactive, show subscription/code entry screen
- Key flows to build: dashboard, meal plan view, meal logging, progress tracking, shopping list, doctor request

### 3. Dataset Clean Pass
- ~20 dirty `food_items` rows need Ollama clean pass
- `is_verified=True` rows only — verify no garbage calorie values remain

### 4. Future Features (Phase 3+)
- Push notifications (meal reminders, streak alerts)
- Admin MFA / TOTP enforcement
- Image upload for food items (`image_url` column exists, ETL script not built)
- Doctor MFA setup endpoint
- Patient-visible clinical notes (currently all `is_private=True`)
- `total_calories_consumed` writer on `ProgressLog`
- Subscription expiry auto-deactivation job

---

## Working Rules — Non-Negotiable

1. **Never trust Antigravity walkthroughs.** Always read every changed file directly, then run an audit script before declaring done.
2. **Audit script pattern.** Python script that imports changed modules and asserts exact behavior. Run it. Fix failures. Rerun until clean.
3. **Alembic after every model change.** `alembic revision --autogenerate -m "description"` → inspect file → `alembic upgrade head`. Check for false-positive GIN index drops.
4. **No hardcoded values.** Age, TDEE, calorie targets — always derive from Patient ORM object. Log a warning when fallback fires.
5. **Middleware is zero-DB.** Never add DB queries to SubscriptionCheckMiddleware or DoctorIsolationMiddleware. AdminIPWhitelistMiddleware may query DB on `/admin/*` only.
6. **Doctor isolation is non-negotiable.** Every `/doctor/*` query must filter by `request.state.doctor_id`. Never trust a body param for this.
7. **Test command:** `venv\Scripts\uvicorn app.main:app --reload --port 8001`
8. **DB check:** `venv\Scripts\alembic.exe check` must return "No new upgrade operations detected" after every migration.
9. **Each phase gets its own chat.** Don't let context get polluted by 10 sessions of history.
