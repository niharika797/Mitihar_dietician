# MITYAHAR — SPRINT 4 HANDOFF
> Generated: 2026-03-10 | Sprint 3 complete (97/97 tests) | Next: Backend fixes B2/B3 → Patient App (Expo SDK 54)

---

## HOW TO USE THIS FILE
Paste this entire file as your first message in the Sprint 4 chat.

**Session startup procedure (non-negotiable):**
1. Read this file top to bottom.
2. Read the 4 key source files listed in the "Files to Read First" section.
3. Confirm understanding across: (a) what is done, (b) what the two pending fixes are, (c) verification steps, (d) patient app scope.
4. Wait for instruction. Do NOT begin writing any code until told to.

---

## Project Overview

**Name:** Mityahar — AI-powered Indian diet planning app
**Backend:** FastAPI + PostgreSQL (SQLAlchemy 2.0 async + asyncpg) + Alembic
**Backend root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`
**Backend URL:** `http://localhost:8000/api/v1`
**Backend start:** `venv\Scripts\uvicorn app.main:app --reload --port 8000`
**Test suite:** `venv\Scripts\python scripts\test_all_endpoints.py` → **97/97 passing**
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`
**GitHub:** `feature/api-remediation-v0.2` → last commit `66fe95e`

**Frontend root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\mitihar-frontend\apps`
**Frontend start:** `pnpm dev` (port 5173)
**Test credentials:**
- Doctor: `testdoctor@mityahar.com` / `doctor1234`
- Admin: `admin@mityahar.com` / `admin1234`

---

## Non-Negotiable Rules

1. **Never trust memory** — always read actual files from disk before writing any code.
2. **Middleware is zero-DB** — `DoctorIsolationMiddleware` and `SubscriptionCheckMiddleware` read JWT claims only, never touch the DB.
3. **Doctor isolation is absolute** — every `/doctor/*` query must filter by `request.state.doctor_id`.
4. **`db_models.py` is the single source of truth** for all ORM models. Do not create separate model files.
5. **Alembic chain must stay clean** — always verify `down_revision` matches the previous head before writing a migration.
6. **97/97 tests must still pass** after every change. Run the test suite before declaring anything done.
7. **Surgical edits only** — never rewrite a whole file when a targeted edit will do.

---

## Current State (Verified 2026-03-10)

### Backend — 97/97 Tests Passing
All Phase 0-3 backend work is complete. The following is the current Alembic chain (head confirmed):

```
92084b0bc541  food_items_and_templates
4e5124b3e103  add_all_user_tables
cf7a21f007f0  fix_nullable_streak_requestedat
370efc812ae5  add_pace_preference_eating_habits_image
3fb0a727fee2  add_clinical_notes_table
861b9d58abdf  add_calorie_adjustment_to_progress_logs
eb8dbef8dd19  add_audit_logs_table
a1b2c3d4e5f6  add_google_id_to_patients  ← HEAD (applied)
```

### Frontend — Sprint 3 Complete (18 Doctor + 6 Admin pages live)
All dashboard pages wired to real API. No mock data anywhere.
- Doctor dashboard: Overview, Patients, PatientDetail (4 tabs), Requests, Settings, Recipes
- Admin dashboard: AdminOverview, AdminDoctors, AdminPatients, FoodDatabase, Billing, AuditLogs

### DB Tables (12, all applied)
`admins, doctors, food_items, meal_logs, meal_templates, patient_requests, patients,
progress_logs, recommendations, subscription_codes, clinical_notes, audit_logs`

---

## Files to Read First (Before Touching Anything)

Read these 4 files in full before writing any code:

```
app\models\db_models.py            ← FoodItem model — confirm doctor_id is NOT there yet
app\routers\doctor.py              ← POST /doctor/recipes endpoint + RecipeCreateRequest import
app\schemas\doctor.py              ← RecipeCreateRequest schema — confirm no save_to_library yet
alembic\versions\a1b2c3d4e5f6_add_google_id_to_patients.py  ← last migration — need down_revision for new one
```

---

## Pending Backend Fixes

Only **2 fixes remain**. B1 and B4 from the previous task list are already done:

| Fix | Status | Evidence |
|---|---|---|
| B1 — Google OAuth migration (`alembic upgrade head`) | ✅ DONE | `alembic current` = `a1b2c3d4e5f6 (head)`; `google_id` confirmed in `patients` table |
| B2 — `save_to_library` flag on `POST /doctor/recipes` | ❌ TODO | `RecipeCreateRequest` has no `save_to_library` field; FoodItem has no `doctor_id` column (confirmed from DB) |
| B3 — `doctor_id` nullable FK on `food_items` table | ❌ TODO | Verified: `doctor_id` NOT in `FoodItem.__table__.columns` |
| B4 — Refresh token rotation | ✅ DONE | `/auth/refresh` calls `_issue_tokens()` → issues new access+refresh pair; sets new HttpOnly cookie |

---

## Fix B3: Add `doctor_id` to `food_items`

### What to do

**Step 1 — Update `app/models/db_models.py`**

In the `FoodItem` class, add `doctor_id` column after `image_url`:

```python
# ADD after image_url line:
doctor_id           = Column(Integer, ForeignKey("doctors.id"), nullable=True)
# Tracks which doctor submitted this item. NULL for system/ETL food items.
```

Also add the relationship at the bottom of `FoodItem`:
```python
doctor              = relationship("Doctor")
```

**Step 2 — Write new Alembic migration**

Create file: `alembic\versions\b2c3d4e5f6a7_add_doctor_id_to_food_items.py`

```python
"""add_doctor_id_to_food_items

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'food_items',
        sa.Column('doctor_id', sa.Integer(), sa.ForeignKey('doctors.id'), nullable=True)
    )
    op.create_index('idx_fi_doctor', 'food_items', ['doctor_id'])


def downgrade() -> None:
    op.drop_index('idx_fi_doctor', table_name='food_items')
    op.drop_column('food_items', 'doctor_id')
```

**Step 3 — Apply migration**
```cmd
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
venv\Scripts\python -m alembic upgrade head
```

---

## Fix B2: Add `save_to_library` Flag to `POST /doctor/recipes`

### Context
Currently `POST /doctor/recipes` always saves to the `food_items` table with `source="doctor"`, `is_verified=False`.

The `save_to_library` flag gives doctors control:
- `save_to_library=True` (default): saves to food_items table (pending admin approval, reusable)
- `save_to_library=False`: creates a transient food item in-memory — **only** for use in a single assign call; not persisted

For Sprint 4 (patient app), `save_to_library=True` is the normal path. The `False` path is a nice-to-have for the assign flow but can be deferred. **Implement only `True` path for now; if `save_to_library=False` is passed, return HTTP 501 Not Implemented.**

### What to do

**Step 1 — Update `app/schemas/doctor.py`**

In `RecipeCreateRequest`, add:
```python
save_to_library: bool = Field(default=True, description="True = save to food_items pending approval. False = not yet supported.")
```

**Step 2 — Update `POST /doctor/recipes` in `app/routers/doctor.py`**

In the `add_recipe` endpoint, after `doctor: Doctor = Depends(get_current_doctor)`:

```python
# Guard: save_to_library=False not yet implemented
if not body.save_to_library:
    raise HTTPException(status_code=501, detail="save_to_library=False is not yet implemented. Use True to submit for admin approval.")

food = FoodItem(
    ...existing fields...
    doctor_id=doctor.id,   # ← ADD THIS LINE
    source="doctor",
    is_verified=False,
)
```

**Step 3 — Update `FoodItemSummary` schema** to expose `doctor_id`:
```python
doctor_id: Optional[int] = None   # ADD to FoodItemSummary
```

---

## Verification Checklist

After both fixes, run through this checklist in order:

### 1. Migration applied cleanly
```cmd
venv\Scripts\python -m alembic current
# Expected: b2c3d4e5f6a7 (head)

venv\Scripts\python -m alembic check
# Expected: No new upgrade operations detected.
```

### 2. Column exists in DB
```cmd
venv\Scripts\python -c "from app.models.db_models import FoodItem; print([c.name for c in FoodItem.__table__.columns])"
# Expected: [..., 'doctor_id', ...]
```

### 3. Full test suite still passes
```cmd
venv\Scripts\python scripts\test_all_endpoints.py
# Expected: 97/97 passing (no regressions)
```

### 4. Manual smoke test — POST /doctor/recipes
```bash
# Login first, get token
curl -X POST http://localhost:8000/api/v1/auth/doctor/login \
  -d "username=testdoctor@mityahar.com&password=doctor1234"

# Then call POST /doctor/recipes with save_to_library=true
curl -X POST http://localhost:8000/api/v1/doctor/recipes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipe_name": "Test Khichdi B3",
    "slot_type": "grain",
    "cal_per_serving": 185,
    "protein_per_serving": 7,
    "carbs_per_serving": 32,
    "fat_per_serving": 4,
    "fiber_per_serving": 2,
    "diet_type": "Vegetarian",
    "save_to_library": true
  }'
# Expected: 201 Created, response includes "doctor_id": <doctor_id>

# Test save_to_library=false returns 501
curl -X POST http://localhost:8000/api/v1/doctor/recipes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"recipe_name": "X", "slot_type": "grain", "cal_per_serving": 100, "diet_type": "Vegetarian", "save_to_library": false}'
# Expected: 501 Not Implemented
```

### 5. Confirm food item has doctor_id in DB
```cmd
venv\Scripts\python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db')
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT id, recipe_name, doctor_id FROM food_items WHERE source=\'doctor\' ORDER BY created_at DESC LIMIT 3'))
        for row in result.all():
            print(row)

asyncio.run(check())
"
```

---

## Complete API Reference (For Patient App — Sprint 4)

### Auth Endpoints (Patient)
```
POST /api/v1/auth/register          form: email, password, name, gender, height, weight, activity_level, diet, doctor_code?
                                     → {message, user_id, doctor_connected}
POST /api/v1/auth/token             form: username, password → {access_token, refresh_token, token_type}
POST /api/v1/auth/refresh           cookie/body: refresh_token → {access_token}
POST /api/v1/auth/google/verify     body: {id_token} → {access_token, refresh_token, is_new_user}
```

### Patient Onboarding
```
POST /api/v1/patients/onboarding    body: full onboarding data (see schema below)
POST /api/v1/patients/disclaimer    body: {} → stores disclaimer_accepted_at timestamp
POST /api/v1/patients/activate      body: {code} → activates subscription + links to doctor
POST /api/v1/patients/request-doctor body: {doctor_id} → creates PatientRequest
GET  /api/v1/patients/request-status → {status: "pending"|"accepted"|"rejected"|"none"}
```

### Patient Profile
```
GET  /api/v1/users/me               → full patient profile (all fields)
PUT  /api/v1/users/me               body: partial update → auto-recalcs BMI/BMR/TDEE
GET  /api/v1/users/bmi              → {bmi, category}
```

### Meal Plan
```
GET  /api/v1/meal-plan/week         → 7-day plan grouped by date
GET  /api/v1/meal-plan/history      → [{id, week_start_date, version, is_active, created_at}]
GET  /api/v1/meal-plan/shopping-list → grouped by category
POST /api/v1/meal-plan/shopping-list/toggle  body: {ingredient_name} → toggle "have at home"
```

### Progress Logging
```
GET  /api/v1/progress/today         → {tdee, calories_consumed, water, steps, streak}
POST /api/v1/progress/meal          body: {meal_type, calories_consumed, protein_g, carbs_g, fat_g, fiber_g, logged_date?, notes?}
PUT  /api/v1/progress/log/meal/{id} body: partial update (within 24h)
DELETE /api/v1/progress/log/meal/{id}  (within 24h)
PUT  /api/v1/progress/log/water     body: {glasses}
PUT  /api/v1/progress/log/steps     body: {steps}
PUT  /api/v1/progress/log/weight    body: {weight_kg}
DELETE /api/v1/progress/log/water
DELETE /api/v1/progress/log/steps
GET  /api/v1/progress/weekly-report → 7-day breakdown
GET  /api/v1/progress/weight-history?days=30 → [{date, weight_kg}]
GET  /api/v1/progress/streak        → {streak_days, last_logged}
```

### Onboarding Request Body (full schema)
```typescript
{
  date_of_birth: "YYYY-MM-DD",          // must be past date
  gender: "Male" | "Female" | "Other",
  height_cm: number,                     // positive
  weight_kg: number,                     // positive
  activity_level: "S" | "LA" | "MA" | "VA" | "SA",
  diet_type: "Vegetarian" | "Non-Vegetarian" | "Eggetarian",
  region: "North" | "South" | "East" | "West",
  health_condition: string,              // "Healthy" default
  target_weight_kg: number,
  health_goals: string[],               // e.g. ["weight_loss", "muscle_gain"]
  medical_conditions: string[],         // e.g. ["Diabetes", "Hypertension"]
  food_allergies: string[],             // min 1 item; use ["None"] if none
  dietary_preferences: string[],
  meals_per_day: 3 | 5,
  fasting_days: string[],               // e.g. ["Monday", "Thursday"]
  sleep_hours: number,
  water_glasses: number,
  occupation: string,
  smoking: boolean,
  alcohol: boolean,
  nonveg_meals_per_week: number,        // 0-14
  pace_preference: "slow" | "moderate" | "fast",
  eating_habits: string[],              // e.g. ["skips_breakfast"]
}
```

---

## Key Backend Architecture Notes

### JWT Claims Structure
```typescript
// Patient token
{ sub: email, role: "patient", user_type: "standalone"|"doctor_assigned",
  sub_status: "active"|"inactive", patient_id: number }

// Doctor token
{ sub: email, role: "doctor", user_type: "doctor", doctor_id: number }

// Admin token
{ sub: email, role: "admin", user_type: "admin", admin_id: number }
```

### Middleware Stack (top to bottom in main.py)
```
SecurityHeadersMiddleware     ← outermost — HSTS, X-Frame, CSP headers
AdminIPWhitelistMiddleware    ← blocks non-whitelisted IPs on /admin routes
SubscriptionCheckMiddleware   ← 402 on /patients/* if sub_status != "active" (reads JWT only, zero DB)
DoctorIsolationMiddleware     ← injects request.state.doctor_id on /doctor/* (reads JWT only, zero DB)
```

### Token Security (Mobile — Patient App)
```
Mobile patient:
  access_token  → Expo SecureStore (iOS Keychain / Android Keystore)
  refresh_token → Expo SecureStore (NOT HttpOnly cookie — mobile has no browser cookie jar)
  withCredentials: N/A for React Native

Web doctor/admin (existing):
  access_token  → Zustand memory only
  refresh_token → HttpOnly cookie (set by backend, never touched by JS)
```

### Subscription Status Logic
- `standalone` patient: `subscription_status = "inactive"` → can only access `/auth/*` and `/patients/activate`
- `doctor_assigned` patient with active code: `subscription_status = "active"` → full access
- `/progress/*` and `/meal-plan/*` all require `sub_status == "active"` (enforced by middleware)
- Exception: `/patients/onboarding`, `/patients/disclaimer`, `/patients/activate`, `/patients/request-doctor`, `/patients/request-status` are NOT gated by subscription

---

## Technology Stack

### Backend (existing — do not change)
- Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic
- passlib[bcrypt] for passwords, python-jose for JWT, pyotp for TOTP
- slowapi for rate limiting (in-memory — Redis is Phase 7)

### Patient App Stack (Sprint 4 — build this)
| Layer | Choice |
|---|---|
| Framework | Expo SDK 54 (New Architecture — JSI/Fabric) |
| Language | TypeScript strict |
| Routing | Expo Router v4 (file-based, same mental model as Next.js App Router) |
| Styling | NativeWind v4 (Tailwind utility classes in React Native) |
| Server state | TanStack Query v5 (same pattern as web dashboard) |
| Client state | Zustand v5 |
| Forms | React Hook Form + Zod |
| Charts | Victory Native (mobile-optimised) |
| Animations | React Native Reanimated 3 |
| Token storage | Expo SecureStore (iOS Keychain / Android Keystore) |
| HTTP | Axios |
| Push notifications | Expo Notifications (Phase 5 — defer for now) |
| Google OAuth | Expo Auth Session + Google Sign-In |

---

## Patient App Scope (36 Screens)

### Auth (3 screens)
1. Register — email + password form + doctor_code optional field
2. Login — email + password
3. Google OAuth login button (calls `POST /auth/google/verify`)

### Onboarding (8 screens — one per "step")
4. Personal Info — DOB, gender, height, weight
5. Activity Level — 5-option picker (S / LA / MA / VA / SA)
6. Goals — multi-select health goals
7. Medical Conditions — multi-select (15+ options)
8. Allergies — multi-select + "None" sentinel
9. Dietary Preferences — diet type, region, meals/day, fasting days
10. Lifestyle — sleep, water, occupation, smoking, alcohol
11. Disclaimer — text + accept button → `POST /patients/disclaimer`

### Home / Dashboard (4 screens)
12. Home — today's summary (calories, water, steps), streak, quick-log buttons
13. Weekly Overview — 7-day calorie/progress chart
14. Notification Center — placeholder (FCM Phase 5)
15. Doctor Card — shows connected doctor info or "Find a Doctor" CTA

### Meal Plan (6 screens)
16. Today's Plan — list of meals for today from active plan
17. Week View — 7-day calendar grid → tap day to see meals
18. Meal Detail — ingredients list, calories breakdown, doctor notes
19. Plan History — list of past plans with date + version
20. Shopping List — grouped ingredient list with "have at home" toggles
21. Plan Empty State — no plan yet → "Your plan is being prepared" screen

### Meal Logging (3 screens)
22. Log Meal — form (meal_type, calories, macros, notes)
23. Log from Plan — pre-filled form from a planned meal slot
24. Edit/Delete Log — 24h window, confirmation dialog

### Progress (5 screens)
25. Progress Hub — today's water/steps/weight quick-log buttons
26. Water Log — glasses counter with +/- buttons
27. Steps Log — number input
28. Weight Log — numeric input + today's entry display
29. Progress Charts — weight history line chart, weekly calorie trend bar chart

### Doctor Connection (3 screens)
30. Subscription / Activate — enter subscription code field → `POST /patients/activate`
31. Request Doctor — browse/enter doctor ID → `POST /patients/request-doctor`
32. Connection Status — pending / accepted / rejected state with poll

### Profile & Settings (4 screens)
33. Profile Edit — update name, weight, height, preferences → `PUT /users/me`
34. Notification Preferences — placeholder (FCM Phase 5)
35. Account — logout button, delete account (calls `/auth/logout`)
36. About / Disclaimer — legal text + app version

---

## Design System (Verdant — same as web dashboard)

```
Brand green:   #1E7C45 (brand-600), #23924F (brand-500), #34B164 (brand-400)
               #DCFCE7 (brand-100), #F0FDF4 (brand-50)
Neutral:       Slate — #111827, #374151, #6B7280, #D1D5DB, #E5E7EB, #F3F4F6, #F9FAFB
Semantic:      #DC2626 error, #F59E0B warning, #2563EB info
Font:          Inter (load via expo-font or @expo-google-fonts/inter)
```

---

## Known Tech Debt (Do Not Fix in Sprint 4)

- `Set-Cookie secure=False` in `auth.py` — change to `True` before HTTPS deploy
- slowapi in-memory — resets on server restart, broken under multiple workers (Phase 7: Redis)
- `ProgressLog.total_calories_consumed` column never written
- `MealLog.food_id` / `custom_food_name` rarely populated (slot linking deferred)
- All Gemini free-tier keys quota-exhausted — `POST /doctor/recipes/estimate` falls back to local DB only
- No monetary billing table — Billing shows code usage only (Razorpay Phase 4)

---

## Sprint Status

| Sprint | Scope | Status |
|---|---|---|
| Sprint 0 | DB schema, migrations, models | ✅ Done |
| Sprint 1 | Patient + Doctor + Admin backend, ETL, allergy filtering | ✅ Done |
| Sprint 2 | Rate limits, MFA TOTP, IP whitelist, mark-paid, food_allergies fix | ✅ Done — 97/97 |
| Sprint 3 | Doctor Dashboard + Admin Dashboard (React+Vite) — 18+6 pages | ✅ Done |
| **Sprint 4** | **Backend fixes B2+B3 → Patient App (Expo SDK 54, 36 screens)** | 🔲 **Start here** |
| Sprint 5 | Phase 4 Billing (Razorpay) + Phase 5 FCM | 🔲 Queued |
| Sprint 6 | Phase 6 ML improvements | 🔲 Queued |
| Sprint 7 | Phase 7 Production Deploy (GCP + Cloud Run + CI/CD) | 🔲 Queued |

---

## First Steps for Sprint 4 Chat

```
STEP 1 — READ FILES (mandatory before any code)
  Read: app\models\db_models.py         ← confirm FoodItem has no doctor_id
  Read: app\routers\doctor.py            ← see POST /doctor/recipes endpoint
  Read: app\schemas\doctor.py            ← see RecipeCreateRequest
  Read: alembic\versions\a1b2c3d4e5f6_add_google_id_to_patients.py  ← get down_revision chain

STEP 2 — IMPLEMENT B3 (migration + model)
  Write migration: alembic\versions\b2c3d4e5f6a7_add_doctor_id_to_food_items.py
  Edit db_models.py: add doctor_id column + relationship to FoodItem
  Run: venv\Scripts\python -m alembic upgrade head

STEP 3 — IMPLEMENT B2 (schema + endpoint)
  Edit schemas\doctor.py: add save_to_library field to RecipeCreateRequest
                           add doctor_id field to FoodItemSummary
  Edit routers\doctor.py: guard save_to_library=False with 501, set food.doctor_id=doctor.id

STEP 4 — VERIFY
  Run: venv\Scripts\python scripts\test_all_endpoints.py → must be 97/97
  Smoke test POST /doctor/recipes with save_to_library=true → check doctor_id in response
  Smoke test POST /doctor/recipes with save_to_library=false → check 501 response
  Run: venv\Scripts\python -m alembic check → must say "No new upgrade operations detected"

STEP 5 — ONLY AFTER VERIFIED: Begin Patient App scaffold
  Expo SDK 54, NativeWind v4, Expo Router v4, TanStack Query v5
  Build auth screens first, verify token storage in SecureStore, then proceed screen by screen
```
