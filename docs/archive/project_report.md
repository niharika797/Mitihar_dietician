# Mityahar — Technical Intelligence Report

> Generated June 3, 2026. Based on exhaustive codebase exploration (Session 14 state).

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [How It Works — End-to-End Execution](#2-how-it-works--end-to-end-execution)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Data — Schema, Storage, Flow](#5-data--schema-storage-flow)
6. [Key Features](#6-key-features)
7. [Entry Points & Interfaces](#7-entry-points--interfaces)
8. [Configuration & Deployment](#8-configuration--deployment)
9. [Current State](#9-current-state)
10. [Strengths & Risks](#10-strengths--risks)

---

## 1. What It Is

**Mityahar** (Sanskrit: "balanced diet") is an AI-powered dietetics platform that automates personalized meal planning for Indian patients under the guidance of licensed dieticians.

### Problem Solved

Manual dietician workflows are labor-intensive: a doctor sees dozens of patients, hand-writes or re-uses template diets, and has no feedback loop on what patients actually eat. Mityahar replaces the template-diet model with:

1. A **personalized meal generator** that selects from 2,141 verified recipes against each patient's biometrics, conditions, and regional cuisine preferences
2. A **doctor dashboard** where dieticians supervise multiple patients, override AI recommendations, and track compliance
3. A **patient mobile app** that delivers the day's meals, captures logs, and drives habit-forming streaks

### Who Uses It

| Role | Interface | Primary Job |
|------|-----------|-------------|
| **Patient** | iOS/Android mobile app | View daily meals, log food/water/weight, rate dishes |
| **Doctor** | Web dashboard (React) | Manage patient roster, review plans, override dishes, add notes |
| **Admin** | Web dashboard (different shell) | Platform operations, doctor management, billing, audit logs |

### Maturity

14 development sessions (February–June 2026). Core platform is functional and testable end-to-end. Production gaps exist: medical condition filtering is not yet live in the generator, doctor meal overrides are not wired end-to-end, and the nutritional data layer (ingredient-level nutrition) was just built in Session 14. The system is pre-launch; it is not yet in production with real patients.

---

## 2. How It Works — End-to-End Execution

### Startup Sequence

When `uvicorn app.main:app --reload --port 8001` runs:

1. **Lifespan hook fires** (`app/main.py`)
   - Checks `COOKIE_SECURE` (warns if `False` on non-localhost)
   - Initializes Firebase Admin SDK from credentials file
   - Starts APScheduler with two cron jobs:
     - `01:00 UTC` — marks patients within 4 days of expiry (`expiring_soon=True`)
     - `01:05 UTC` — deactivates patients whose `token_1_expiry` has passed

2. **Middleware stack attaches** (LIFO — last registered executes first on inbound requests):
   ```
   Inbound: SecurityHeaders → CORS → SubscriptionCheck → DoctorIsolation → AdminIPWhitelist → Router
   Outbound: Router → AdminIPWhitelist → DoctorIsolation → SubscriptionCheck → CORS → SecurityHeaders
   ```

3. **9 routers mount** at `/api/v1/*` (auth, users, diet_plans, calculations, progress, meal_plan, patients, doctor, admin)

4. **Rate limiter** wires via `slowapi` (in-memory; production requires Redis)

---

### Patient Journey: Registration → First Meal Plan

**Step 1 — Registration** (`POST /api/v1/auth/register`)

Patient submits email + password. System:
- Hashes password with bcrypt
- Creates `Patient` row (no subscription yet)
- Reserves the subscription code (`SubscriptionCode` status: `AVAILABLE → RESERVED`)
- Returns access + refresh JWT pair

**Step 2 — Onboarding** (`POST /api/v1/patients/onboarding`)

8-step flow on mobile (device storage persists state across app kills). Final submit sends:
- Personal: name, DOB, gender, phone, region (North/South/East/West)
- Biometrics: height, weight, activity level
- Preferences: diet type (Veg/Non-Veg/Eggetarian), allergies, eating habits
- Goals: weight loss, muscle gain, etc.
- Medical conditions: diabetes, hypertension, PCOS, etc.
- Lifestyle: sleep hours, occupation, fasting preferences

Backend calculates and stores: `BMI`, `BMR` (Mifflin-St Jeor), `TDEE` (BMR × activity multiplier).

**Step 3 — Disclaimer** (`POST /api/v1/patients/disclaimer`)

One-click acceptance. Unlocks subscription code entry.

**Step 4 — Subscription Activation** (`POST /api/v1/patients/activate`)

Patient enters 6-character code from doctor. System:
- Verifies code exists and is in `RESERVED` state
- Marks code `CONSUMED` (one-time use)
- Generates `token_1` string (e.g. `TKN1-PAT-00142`)
- Sets `token_1_expiry = now + 30 days`
- Creates `PatientVisit` row for billing tracking
- `SubscriptionCheckMiddleware` now passes this patient through on diet routes

**Step 5 — Meal Plan Generation** (`POST /api/v1/diet-plans/generate` or auto on activation)

`MealGenerator.generate_meal_plan(user_data, session)` runs:

1. Loads patient TDEE; checks for `PatientMealConfig` split override (default: 25% breakfast / 35% lunch / 25% dinner / 15% buffer)
2. Computes `effective_tdee = TDEE × 0.85` (buffer absorbs passive snacking)
3. Loads food_ids used in last 2 plans to avoid repetition
4. For each of 7 days × 3 slots (Breakfast/Lunch/Dinner):
   - Queries `MealTemplate` for slot configurations matching diet_type + region + plan_type
   - Selects `FoodItem` records matching that slot, filtered by diet_type/region, excluding recent food_ids
   - Fallback: Gemini 2.5-flash-lite call for unrecognized foods
   - Fallback of fallback: random safe default
5. Builds `meals[]` JSONB: each entry contains `slot_type`, `food_id`, per-dish macros, ingredient names with proportional labels
6. Stores result as `Recommendation` row (soft-deletes prior active plan, increments version)
7. Returns full plan to patient app

**Step 6 — Daily Use (Patient App)**

Patient opens app → Home tab shows today's 3 meals from the active plan.
- Taps a meal → `meal-detail.tsx` shows per-dish cards (name, macros, expandable ingredients)
- Rates dish (👍/👎) → `POST /api/v1/progress/rating` → stores `MealRating` row
- Logs meal → `POST /api/v1/progress/meal` → stores `MealLog` row
- Logs water, steps, weight → `PUT /api/v1/progress/water|steps|weight`

---

### Doctor Journey: Dashboard → Patient Supervision

Doctor logs in via web dashboard (React + Vite):
- MFA required (TOTP via authenticator app)
- `DoctorIsolationMiddleware` restricts all `/api/v1/doctor/*` calls to their own patient roster (reads `patient_id` FK on PatientRequest without a DB hit — zero-DB middleware enforced via JWT claims)

Doctor workflow:
1. **Requests** — reviews pending connection requests; accepts/rejects
2. **Generate subscription codes** — creates `SubscriptionCode` entries (`AVAILABLE`) for new patients
3. **Patient detail** — 7-tab view: Overview, Plan, Activity, Notes, Progress, Visits, Renewals
4. **Plan override** — can view current 7-day plan; (Session 16 target) replace individual dishes
5. **Clinical notes** — attach public/private notes per patient
6. **Renewals** — reviews patients approaching expiry; renews subscriptions

---

### Admin Journey: Platform Operations

Admin logs in from the same web URL with `/admin/*` routing. `AdminIPWhitelistMiddleware` checks the request IP against `Admin.allowed_ips` JSONB column (single DB read).

Admin capabilities:
- Doctor onboarding/deactivation
- Patient list with search/pagination
- Annual billing: consultation fee pool, royalty split per doctor (2% model, Indian financial year Apr 1)
- Audit log trail (every action logged with actor_id, IP, entity, detail JSONB)
- Food database editor (verified recipe management)
- IP whitelist management

---

## 3. Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│                                                          │
│  ┌──────────────────┐     ┌──────────────────────────┐  │
│  │  Patient Mobile  │     │  Web Dashboard           │  │
│  │  (Expo RN)       │     │  (React + Vite)          │  │
│  │  36 screens      │     │  Doctor Shell + Admin    │  │
│  │  Expo Router     │     │  Shell, React Router v7  │  │
│  └────────┬─────────┘     └────────────┬─────────────┘  │
└───────────┼─────────────────────────────┼───────────────┘
            │ REST/JSON + JWT             │ REST/JSON + JWT
            ▼                             ▼
┌───────────────────────────────────────────────────────────┐
│                    BACKEND API                            │
│                  FastAPI + asyncpg                        │
│                                                          │
│  SecurityHeaders → CORS → SubscriptionCheck →            │
│  DoctorIsolation → AdminIPWhitelist                       │
│                                                          │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐        │
│  │ auth   │ │ doctor │ │ admin    │ │ patients │        │
│  │ users  │ │ diet   │ │ meal_plan│ │ progress │  ...   │
│  └────────┘ └────────┘ └──────────┘ └──────────┘        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              SERVICES LAYER                      │   │
│  │  MealGenerator | DietPlanService | TokenService  │   │
│  │  MFAService | NotificationService | AuditService │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              MODELS (SQLAlchemy 2.0)             │   │
│  │  Patient | Doctor | Admin | FoodItem | ...       │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────┘
                            │ asyncpg
                            ▼
┌───────────────────────────────────────────────────────────┐
│                    DATA LAYER                             │
│            PostgreSQL 15 (Docker)                         │
│  16+ tables | 2,141 recipes | 18,248 ingredient rows      │
└───────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     Firebase FCM     Gemini API      llama.cpp
   (push notifs)  (dish rename,   (local nutrition
                  meal fallback)   estimation)
```

### Component Responsibilities

| Component | Responsibility | Isolation |
|-----------|---------------|-----------|
| **Middleware stack** | Auth enforcement, CORS, rate limiting, IP whitelist | Stateless except AdminIPWhitelist (1 DB read) |
| **Routers** | HTTP contract — validate input, call services, serialize output | Thin layer, no business logic |
| **Services** | Business logic — meal generation, token lifecycle, notifications | Pure functions + async DB sessions |
| **Models** | ORM mapping, relationship definitions | SQLAlchemy declarative, no logic |
| **Schemas** | Pydantic request/response validation | Separate from ORM models |
| **Cron jobs** | Background lifecycle management | APScheduler in-process |
| **Scripts** | Data seeding, auditing, batch operations | One-off CLI, not part of app runtime |

### Middleware Stack Detail

Every inbound request traverses these layers in order:

1. **SecurityHeadersMiddleware** — attaches `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, CSP built from `CORS_ORIGINS`
2. **CORSMiddleware** — preflight handling; `allow_credentials=True`; configurable origins
3. **SubscriptionCheckMiddleware** — zero-DB: decodes JWT, checks `subscription_active` claim; blocks diet generation routes for inactive patients
4. **DoctorIsolationMiddleware** — zero-DB: for `/api/v1/doctor/*`, verifies that `patient_id` in path belongs to the requesting doctor's roster (JWT claim check)
5. **AdminIPWhitelistMiddleware** — 1 DB read: for `/api/v1/admin/*`, queries `Admin.allowed_ips` JSONB; rejects non-whitelisted IPs

The LIFO registration order means the innermost middleware (AdminIPWhitelist) is registered last but fires first on outbound, last on inbound. This ensures the most expensive check (DB read) only runs when all cheaper checks have passed.

---

## 4. Tech Stack

### Backend

| Technology | Role | Notes |
|------------|------|-------|
| **Python 3.10+** | Runtime | |
| **FastAPI** | Web framework | Async-native, auto OpenAPI docs |
| **SQLAlchemy 2.0** | ORM | Fully async (AsyncSession) |
| **asyncpg** | PostgreSQL driver | High-performance async |
| **Alembic** | Schema migrations | 17 versions tracked |
| **Pydantic v2** | Request/response validation | pydantic-settings for config |
| **python-jose** | JWT creation/validation | HS256 algorithm |
| **passlib + bcrypt** | Password hashing | bcrypt==4.0.1 pinned |
| **pyotp** | TOTP MFA | Doctor and admin only |
| **firebase-admin** | Push notifications | FCM via service account |
| **APScheduler** | Background cron jobs | In-process (not Celery) |
| **slowapi** | Rate limiting | In-memory dev; needs Redis in prod |
| **google-auth** | Google OAuth | Patient registration flow |
| **pandas + numpy** | Data scripts | Used in seeding/auditing scripts only |
| **scikit-learn** | Data scripts | Ditto |
| **uvicorn** | ASGI server | `--reload` for dev |

### Frontend (Web Dashboard)

| Technology | Role |
|------------|------|
| **React 18.3.1** | UI framework |
| **Vite 6.3.5** | Build tool + dev server |
| **TypeScript 5.7.2** | Type safety |
| **React Router 7.13.0** | Client-side routing |
| **TanStack Query 5.62.3** | Server state (data fetching, caching) |
| **Zustand 5.0.2** | Client state |
| **Radix UI** | 19 headless UI components (Dialog, Select, Tabs, etc.) |
| **Tailwind CSS 4.1.12** | Utility styling |
| **React Hook Form 7.55.0** | Form state |
| **Zod 3.24.1** | Schema validation |
| **Recharts 2.15.2** | Charts (weight, calories, macros) |
| **Axios 1.7.9** | HTTP client |

### Mobile App (Patient)

| Technology | Role |
|------------|------|
| **Expo ~55.0.6** | React Native toolchain + deployment |
| **React Native 0.83.2** | Mobile runtime |
| **React 19.2.0** | UI framework (latest) |
| **Expo Router ~55.0.5** | File-based routing |
| **TanStack Query 5.67.3** | Server state |
| **Zustand 5.0.3** | Client state |
| **NativeWind 4.1.23** | Tailwind for React Native |
| **Expo SecureStore** | Encrypted token storage |
| **React Hook Form + Zod** | Form validation |
| **Expo Notifications** | FCM push notification handling |
| **Expo Local Authentication** | Biometric lock (optional) |

### External Services

| Service | Purpose |
|---------|---------|
| **PostgreSQL 15** | Primary datastore (Docker) |
| **Firebase FCM** | Push notifications to patient devices |
| **Google Gemini 2.5-flash-lite** | Fallback meal suggestions; batch dish renaming |
| **Google OAuth** | Patient SSO registration |
| **USDA FoodData Central** | Source of 6,000+ recipes (seeded; not live query) |
| **llama.cpp (local)** | LLM-estimated ingredient nutrition (offline, used in seeding only) |

---

## 5. Data — Schema, Storage, Flow

### Core Tables

#### Patient (`patients`)
Central entity. Stores everything about a patient's account, biometrics, health profile, and subscription state.

Key columns:
- `id`, `email`, `password_hash`, `google_id`
- Biometrics: `height_cm`, `weight_kg`, `bmi`, `bmr`, `tdee`
- Health: `diet_type`, `region`, `health_goals[]`, `medical_conditions[]`, `allergies[]`
- Subscription: `token_1` (string), `token_1_active` (bool), `token_1_expiry` (timestamp), `expiring_soon` (bool)
- App: `fcm_token`, `notification_preferences` (JSONB)
- Security: `password_changed_at`, `failed_login_attempts`, `locked_until`

#### FoodItem (`food_items`)
Recipe catalog. 2,141 rows loaded from USDA + seeding.

Key columns:
- `name`, `slot_type` (breakfast/grain/dal/sabzi/main_dish/dessert)
- Per-serving nutrition: `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sodium_mg`
- `ingredients` (JSONB): raw ingredient list from USDA (names, amounts)
- `diet_type`, `region_tags`, `plan_type_tags` (JSONB arrays)
- `is_verified` (bool): soft quality flag
- `doctor_id` (FK): doctor-created custom recipes
- `nutrition_source`: manual / estimated_llm / verified_ifct

#### Recommendation (`recommendations`)
Stores the generated 7-day meal plan per patient.

Key columns:
- `patient_id` (FK)
- `meals` (JSONB): array of 21 meal objects (7 days × 3 slots)
  - Each meal: `{day, slot_type, dishes: [{food_id, name, calories, protein_g, carbs_g, fat_g, fiber_g, ingredients}]}`
- `ingredient_checklist` (JSONB): flat ingredient list for shopping
- `used_food_ids` (JSONB): food IDs used (for cross-week variety)
- `version` (int): auto-incremented on regeneration
- `is_active` (bool): soft-delete on regeneration

#### Doctor (`doctors`)
Doctor account + professional profile.

Key columns:
- `email`, `password_hash`, `name`, `clinic_address`, `experience_years`
- `consultation_fee`, `rating`, `review_count`
- MFA: `mfa_secret`, `mfa_enabled`
- Security: `failed_login_attempts`, `locked_until`

#### Ingredients (`ingredients`) — Session 14
Master ingredient table with per-100g nutrition.

Key columns:
- `name` (unique), `name_normalized`
- `calories_per_100g`, `protein_per_100g`, `carbs_per_100g`, `fat_per_100g`, `fiber_per_100g`
- `unit_weight_g` (typical unit weight)
- `nutrition_source`: manual / estimated_llm / verified_ifct
- Current state: 950 rows, 846 with LLM-estimated nutrition (89.2%)

#### RecipeIngredients (`recipe_ingredients`) — Session 14
Junction table linking FoodItems to Ingredients.

Key columns:
- `recipe_id` (FK → food_items.id)
- `ingredient_id` (FK → ingredients.id)
- `quantity_g` (CHECK > 0)
- 18,248 rows populated

#### PatientVisit (`patient_visits`)
Billing tracker for doctor-patient consultations.

Key columns:
- `patient_id`, `doctor_id`
- `token_2` (visit billing token)
- `visit_counter` (increments on visits with >15-day gap — billable)
- `current_period_start`, `current_period_end`

### Data Flow: Meal Plan Generation

```
Patient biometrics (Patient row)
    │
    ▼
MealGenerator
    ├── TDEE × 0.85 = effective_tdee
    ├── PatientMealConfig.meal_split_override (or default 25/35/25/15)
    ├── Last 2 Recommendation.used_food_ids (variety)
    │
    ├── For each day (7) × slot (3):
    │       MealTemplate → slot configuration
    │       FoodItem query (diet_type, region, slot_type, NOT IN recent_ids)
    │       ↓ miss → Gemini API call
    │       ↓ miss → random safe default
    │
    └── Output: Recommendation (JSONB meals, ingredient_checklist, used_food_ids)
```

### Data Flow: Patient Progress

```
MealLog ─────┐
ProgressLog──┤──► progress_service.get_today_progress() ──► Home tab summary
MealRating───┘

ProgressLog.weight_kg ──► progress_service.get_weight_history() ──► Charts
```

### Data Flow: Subscription

```
Doctor generates SubscriptionCode (AVAILABLE)
    │
    ▼
Patient registers → code.status = RESERVED (patient_id attached)
    │
    ▼
Patient activates → code.status = CONSUMED
                 → Patient.token_1 = "TKN1-PAT-XXXXX"
                 → Patient.token_1_expiry = now + 30 days
                 → PatientVisit created (billing clock starts)
    │
    ▼
Cron 01:00 UTC → expiring_soon = True (within 4 days)
Cron 01:05 UTC → token_1_active = False (past expiry)
```

### Notable Data Design Choices

**JSONB everywhere for flexibility**: `meals`, `ingredients`, `health_goals`, `medical_conditions`, `allowed_ips`, `notification_preferences` — all JSONB. Fast to query with GIN indexes but harder to enforce referential integrity.

**Soft deletes**: Plans are never deleted; `is_active=False` on regeneration. Full version history retained.

**Cross-week variety via used_food_ids**: Generator loads food IDs from the last 2 plans and excludes them from selection. Simple but effective diversity mechanism.

**Recommendation_id null issue**: `MealRating` has a composite upsert key of `(patient_id, food_item_id, recommendation_id)`. Since `recommendation_id` is NULL on all current meals, PostgreSQL treats `NULL != NULL`, meaning each rating tap creates a new row instead of upserting. Known issue, targeted for Session 16.

---

## 6. Key Features

### Personalized Meal Plan Generation

The generator selects from 2,141 recipes against:
- Caloric target (TDEE × 0.85, split across 3 meals)
- Diet type (Veg/Non-Veg/Eggetarian)
- Regional cuisine (North/South/East/West Indian)
- Recency exclusion (avoids food IDs from last 2 active plans)
- Doctor-level per-patient TDEE split override
- (Planned, Session 18) Medical condition tag filtering (avoid_X / prefer_X)

Output is stored as JSONB in `Recommendation`, giving the app a complete snapshot including ingredient names with proportional labels (not gram weights — a deliberate UX decision).

### 3-State Subscription Code Lifecycle

AVAILABLE → RESERVED (at patient registration) → CONSUMED (at activation). The RESERVED state prevents race conditions where two patients claim the same code simultaneously. The system enforces that only the patient who reserved the code can activate it.

### Token-Based Subscription + Visit Billing

`token_1` governs patient access (30-day rolling window). `token_2` (PatientVisit) tracks billable consultations: a visit is only charged if the gap since the last visit exceeds 15 days, preventing double-billing on frequent check-ins.

### 5-Layer Security Middleware

Stateless authentication + authorization enforced before any route handler executes. DoctorIsolation middleware is zero-DB — it validates patient roster membership from JWT claims alone, eliminating a DB read on every doctor API call.

### MFA for Doctors and Admins

TOTP via pyotp. Doctors and admins scan a QR code to link their authenticator app on first login. Subsequent logins require a 6-digit token in addition to password. Patients use standard JWT (no MFA).

### Cross-Platform Meal Rating + RL Foundation

Patients rate individual dishes (👍/👎) per food item. `DoctorMealOverride` captures the patient context snapshot at the moment a doctor replaces an AI meal (biometrics, conditions, which dish was replaced, what it was replaced with). Together, these form the training signal for a planned contextual bandit recommendation engine (RL Roadmap documented in `docs/RL_Roadmap.md`).

### Offline-Resilient Mobile Onboarding

8-step onboarding state persists to device storage at each step. If the app is killed mid-flow (low memory, phone call, etc.), the patient resumes from the last completed step. The backend only receives the onboarding payload on final submission.

### Admin Billing (Indian Financial Year)

Annual consultation billing uses Apr 1 as year boundary (Indian financial year). Royalty pool is calculated at 2% of gross consultation fees. Per-doctor royalty assignments support differential tiers. The admin billing page shows both pool-level and per-doctor breakdowns.

---

## 7. Entry Points & Interfaces

### REST API (`/api/v1/*`)

Total: ~80 endpoints across 9 routers.

#### Auth (`/api/v1/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Patient registration |
| POST | `/token` | Form-data login (patient) |
| POST | `/refresh` | Refresh access token |
| POST | `/doctor/login` | Doctor login (JSON) |
| POST | `/admin/login` | Admin login (JSON) |
| POST | `/doctor/mfa/verify` | Verify TOTP token |
| GET | `/google` | Initiate Google OAuth |
| POST | `/google/verify` | Exchange Google token |
| POST | `/logout` | Clear refresh cookie |
| POST | `/password-reset/request` | Send reset email |
| POST | `/password-reset/confirm` | Set new password |

#### Patients (`/api/v1/patients`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/onboarding` | Submit onboarding data (8 fields) |
| POST | `/disclaimer` | Accept disclaimer |
| POST | `/activate` | Activate subscription code |
| GET | `/doctors` | List active doctors (for "Find a Doctor") |
| POST | `/doctor-request` | Send connection request |
| GET | `/doctor-request/status` | Check request status |

#### Diet Plans (`/api/v1/diet-plans`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/my-plan` | Get active 7-day plan |
| POST | `/regenerate` | Request fresh plan generation |
| GET | `/history` | Past plan versions (last 10) |
| PUT | `/update` | Partial plan update |

#### Progress (`/api/v1/progress`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/meal` | Log a meal |
| PUT | `/meal/{log_id}` | Update meal log |
| DELETE | `/meal/{log_id}` | Remove meal log |
| PUT | `/water` | Log water intake |
| PUT | `/steps` | Log step count |
| PUT | `/weight` | Log weight |
| GET | `/today` | Today's aggregated progress |
| GET | `/weekly-report` | 7-day summary |
| GET | `/weight-history` | Historical weight |
| GET | `/streak` | Streak count |
| POST | `/rating` | Rate a dish (👍/👎) |

#### Doctor (`/api/v1/doctor`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/requests` | Pending connection requests |
| POST | `/requests/{id}/accept` | Accept patient |
| POST | `/requests/{id}/reject` | Reject patient |
| GET | `/patients` | Patient roster |
| GET | `/patients/{id}` | Patient detail |
| GET | `/patients/{id}/logs` | Meal/progress logs |
| GET/PUT | `/patients/{id}/plan` | View/update plan |
| GET/POST | `/patients/{id}/notes` | Clinical notes |
| GET | `/patients/{id}/visits` | Billing records |
| GET/POST | `/recipes` | Recipe list / create |
| PUT/DELETE | `/recipes/{id}` | Update / delete recipe |
| GET/POST | `/subscription-codes` | Generate codes |
| GET | `/dashboard` | Stats (total patients, expiring soon) |
| GET | `/pending-renewals` | Patients near expiry |

#### Admin (`/api/v1/admin`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/doctors` | All doctors + status |
| PATCH | `/doctors/{id}/status` | Activate/deactivate doctor |
| GET | `/patients` | All patients (paginated) |
| DELETE | `/patients/{id}` | Soft delete patient |
| DELETE | `/patients/{id}/hard` | Hard delete (dev only) |
| GET | `/consultations/annual` | Billing report |
| GET | `/audit-logs` | Audit trail |
| GET/PUT | `/settings` | Platform config (IP whitelist) |

#### Calculations (`/api/v1/calculations`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/bmi` | Calculate BMI from query params |

### Scheduled Jobs (APScheduler)

| Schedule | Function | Action |
|----------|----------|--------|
| `01:00 UTC daily` | `_flag_expiring_patients` | Set `expiring_soon=True` for patients expiring within 4 days |
| `01:05 UTC daily` | `_deactivate_expired_patients` | Set `token_1_active=False` for past-expiry patients |

### Web Dashboard Surfaces

- **Doctor shell** (`/doctor/*`): Overview, Patients list, Patient detail (7-tab), Requests, Recipes, Settings
- **Admin shell** (`/admin/*`): Overview, Patients, Doctors, Annual Billing, Audit Logs, Food Database, Settings
- **Login page**: Single route, role-differentiated (doctor/admin), MFA modal

### Mobile App Surfaces (36 screens)

8-step onboarding → tabbed main app (Home, Meals, Progress, Profile) → deep routes (meal-detail, week-view, shopping-list, log screens, doctor activation, find-doctor, profile settings).

### CLI / Scripts (run manually)

```bash
python -m scripts.seed_admin
python -m scripts.seed_food_items
python -m scripts.seed_6k_recipes
python -m scripts.seed_ingredients_names
python -m scripts.seed_ingredient_nutrition   # requires llama-server running
python -m scripts.seed_recipe_ingredients
python -m scripts.rename_dishes_gemini        # --dry-run supported; checkpointed
```

---

## 8. Configuration & Deployment

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@localhost:5432/mityahar_db` |
| `SECRET_KEY` | ✅ | Min 32 chars; used for JWT signing (HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | Default: 15 |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | ✅ | Default: 10080 (7 days) |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins |
| `GEMINI_API_KEY_1` | ✅ | Gemini API key (only KEY_1 is used) |
| `COOKIE_SECURE` | ✅ | `False` dev, `True` prod (HTTPS) |
| `GOOGLE_CLIENT_ID` | optional | Google OAuth for patients |
| `GOOGLE_CLIENT_SECRET` | optional | |
| `GOOGLE_REDIRECT_URI` | optional | |
| `USDA_API_KEY` | optional | Used only in `seed_6k_recipes.py` |
| `ADMIN_SEED_EMAIL/PASSWORD/NAME` | optional | Used only in `seed_admin.py` |
| `ALLOW_HARD_DELETE` | optional | Default `False`; `True` for dev only |
| `REQUIRE_EMAIL_VERIFICATION` | optional | Default `False`; set `True` for prod |
| `REDIS_URL` | optional | Required for multi-worker production |
| Firebase credentials | ✅ | `credentials/firebase_service_account.json` |

### Infrastructure Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Python | 3.10+ | virtualenv recommended |
| PostgreSQL | 15 | Via Docker or managed service |
| Docker | Required for dev DB | `docker-compose up -d` |
| Node.js | For frontend | pnpm recommended |
| Expo CLI | For mobile | `pnpm start` in `mitihar-patient-app/` |
| Firebase project | For FCM | Service account JSON required |
| Gemini API | Active | `GEMINI_API_KEY_1` |
| llama.cpp (optional) | C:\llama\ | Only needed to re-run nutrition seeding |

### Running the System

```bash
# 1. Start database
docker-compose up -d

# 2. Activate virtualenv (Windows)
venv\Scripts\activate

# 3. Run migrations
alembic upgrade head

# 4. Seed data (first time)
python -m scripts.seed_admin
python -m scripts.seed_food_items
python -m scripts.seed_6k_recipes

# 5. Start backend
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

# 6. Start web dashboard
cd mitihar-frontend/apps && pnpm dev    # http://localhost:5173

# 7. Start mobile app
cd mitihar-patient-app && pnpm start   # Expo Metro, scan QR
```

### Mobile App Network Configuration

`EXPO_PUBLIC_API_URL` must be set to the dev machine's LAN IP (e.g. `http://192.168.1.x:8001/api/v1`). Not `localhost` — Android emulators use `10.0.2.2` as host alias, but physical devices require the real IP. A static local IP in the router avoids changing this frequently.

### API Documentation

FastAPI auto-generates OpenAPI docs:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

---

## 9. Current State

### What Works (Verified)

- Full auth flow: registration, login, Google OAuth, MFA, refresh token rotation, login lockout, password reset
- 3-state subscription code lifecycle (AVAILABLE → RESERVED → CONSUMED)
- Patient onboarding (8 steps, device-persistent)
- Meal plan generation (7 days × 3 meals, per-dish food_ids, per-dish ingredients, cross-week variety)
- Meal detail UI (per-dish cards, expandable ingredients, proportional labels)
- Meal rating (fixed in Session 13: reads `dishes[i].food_id`, not null legacy field)
- Progress logging (meal, water, steps, weight, streak)
- Doctor dashboard (patient roster, 7-tab detail, clinical notes, subscription codes)
- Admin dashboard (billing with 2% royalty, audit logs, doctor management)
- 5-layer middleware (security, CORS, subscription check, doctor isolation, admin IP whitelist)
- Next Visit card on patient home (Session 12)
- Ingredient master table (950 entries, 89.2% with LLM nutrition)
- Recipe-ingredients junction table (18,248 rows linked)

### In Progress / Incomplete

| Item | Status | Target Session |
|------|--------|---------------|
| Medical condition filtering in generator | Logic missing (UI ready) | Session 18 |
| Doctor meal override recording endpoint | `DoctorMealOverride.chosen_food_id` null; food_id now in `dishes[]` but not yet wired | Session 16 |
| Individual dish editing by doctor | No endpoint yet | Session 16 |
| Quantity-based shopping list | Names only (gram quantities unrealistic from batch entry) | Session 13–14 |
| Recipe nutrition recalculation from ingredients | Ingredient data ready; rollup pipeline not built | Session 15 |
| `recommendation_id` on MealRating | Currently null; causes rating dedup to fail | Session 16 |
| Dish rename script | 440/2137 done (22%), checkpointed | Ongoing |
| `plan_type_tags` | All recipes tagged identically; useless for filtering | Session 18 |
| PlanTab.tsx (Sprint 5 rewrite) | Unverified; `patientMealsPerDay` prop may have TypeScript errors | Immediate check needed |
| Billing.tsx legacy labels | `royalty_pool_6pct` / `royalty_per_member_2pct` label names; values correct (2%) | Minor |

### Known Data Issues

- Ingredient gram quantities from USDA batch seeding are unrealistic (e.g., very large or small quantities for several recipes); not yet corrected
- FoodItem ID 2924 (Arabic Vegetable): 560g curry leaves — unusual but within validation bounds
- FoodItem ID 2674 (Drumstick Buttermilk Curry): `slot_type='grain'` should be `'sabzi'`
- 3 food items with "Gm " prefix ingredient names

---

## 10. Strengths & Risks

### Strengths

**Well-structured async backend.** FastAPI + SQLAlchemy 2.0 async is the right stack for this domain. No sync DB calls block the event loop; proper `AsyncSession` usage throughout. The middleware stack is well-designed — zero-DB subscription and doctor isolation checks scale without any per-request DB overhead.

**Clear separation of concerns.** Routers are thin (validate → call service → serialize). Business logic lives in services. No business logic in models. The meal generator is an isolated service with a clean interface.

**Robust auth model.** Short-lived access tokens (15 min), HttpOnly refresh cookies, MFA for privileged roles, `password_changed_at` for session invalidation on password change, login lockout with `failed_login_attempts`, Google OAuth supported. Security was audited and hardened in prior sessions.

**RL-ready data model.** `DoctorMealOverride` (patient context snapshot), `MealRating` (dish feedback), and the ingredient-level nutrition layer are all building blocks for the planned contextual bandit recommendation engine. The schema was designed with the feedback loop in mind.

**Good seeding and tooling.** 43 scripts covering seeding, auditing, cleanup, and batch operations. The dish rename script is checkpointed (idempotent re-runs). The nutrition estimation script ran locally via llama.cpp with no external API dependency.

**Honest documentation.** BUILD_TRACKER.md is a running session-by-session log with explicit P1/P2 known issues, locked decisions, and architectural reasons. CLAUDE.md is accurate and useful. This is unusual quality for a solo project.

### Risks

**Medical condition filtering is inactive.** The UI surfaces 13 conditions at onboarding. The database tags the conditions. But the generator does not yet apply `avoid_X` / `prefer_X` filters. A patient with celiac disease currently receives the same plan as one without. This is a **clinical safety gap** for a healthcare product; it must be resolved before any patient with a medical condition uses the system.

**Ingredient gram quantities are unrealistic.** The 18,248 recipe-ingredient rows were derived from USDA JSONB data that was never normalized. Shopping list quantities and any future per-ingredient nutrition rollup will be inaccurate until this is cleaned. This is flagged P1 in BUILD_TRACKER.

**In-memory rate limiter.** `slowapi` is initialized without Redis. Under multi-worker deployment, rate limit counters reset per worker. A sustained attack from a single IP bypasses limiting if requests hit different workers. Acceptable for single-process dev; unacceptable for production.

**APScheduler in-process.** Cron jobs run inside the Uvicorn process. If the process dies or restarts, jobs don't run on schedule. Under autoscaling or multiple workers, jobs run N times (once per worker). Production requires an external scheduler (Celery Beat, pg_cron, or a managed cron service).

**Recommendation_id null on all MealRatings.** The upsert key for `MealRating` is `(patient_id, food_item_id, recommendation_id)`. Since `recommendation_id` is NULL for all current records and PostgreSQL treats `NULL != NULL`, every tap of 👍/👎 inserts a new row. The rating system produces no reliable signal until this is fixed. This also means the RL feedback loop is currently non-functional.

**JSONB for everything.** `meals`, `ingredients`, `medical_conditions`, `health_goals`, `allowed_ips` — heavy JSONB usage gives flexibility but makes schema enforcement impossible at the DB level. A bug that stores malformed JSON silently passes until runtime. Some of these should be relational (medical_conditions with proper FK join table would enable reliable filtering).

**Single Gemini API project.** Four `GEMINI_API_KEY_*` env vars exist but only `KEY_1` is used; rotating keys doesn't help because quota is per project, not per key. Under high generation load (many patients regenerating simultaneously), Gemini rate limits will cascade. The fallback to random defaults is a silent degradation.

**PlanTab.tsx unverified.** The Sprint 5 rewrite was never confirmed to work. TypeScript errors around `patientMealsPerDay` may exist in the doctor dashboard's most important patient interaction surface.

**No integration test suite for the API.** There's a `tests/full_backend_test.py` that requires a live DB, but no CI pipeline, no contract tests for API shape, and no automated E2E tests. The `contract/` directory exists but its contents weren't confirmed in this audit. Any refactor of schemas or response shapes can silently break frontend clients.

**Dish rename script at 22%.** 1,697 of 2,141 recipes still have raw USDA-style names (e.g., "Barley, pearled, cooked"). Patient-facing dish names are sourced from `FoodItem.name`; until the rename is complete, a significant portion of displayed recipes will show technical names rather than localized Indian dish names.

---

## Appendix: File Metrics

| Subsystem | Approx. LOC |
|-----------|-------------|
| Backend routers | ~5,831 |
| Backend models (ORM) | ~650 |
| Backend services | ~900 |
| Backend core (middleware, security, config) | ~600 |
| Alembic migrations | ~700 |
| Frontend (web dashboard) | ~2,500 |
| Mobile app | ~3,000 |
| Scripts (43 files) | ~3,500 |
| **Total** | **~17,700** |

| Artifact | Count |
|----------|-------|
| Database tables | 16+ |
| API endpoints | ~80 |
| Alembic migrations | 17 |
| Recipes (FoodItem rows) | 2,141 |
| Ingredient master rows | 950 |
| Recipe-ingredient links | 18,248 |
| Documentation files | 48+ |
| Python scripts | 43 |
| Mobile screens | 36 |
