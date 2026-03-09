## Complete Mityahar Code Task List

> Last audited: 2026-03-08 — Sprint 2 complete, 95/95 tests passing
> Legend: [x] = verified done from code · [ ] = not done · [~] = partial / logic incomplete

---

## 🔴 PHASE 0 — Foundation

### Database & Models
- [x] SQLAlchemy 2.0 async + asyncpg + Alembic installed
- [x] PyMongo / motor removed
- [x] `app/core/database.py` — async engine + session factory
- [x] All 10 DB tables as SQLAlchemy models:
  - [x] `doctors`, `patients`, `admins`, `food_items`, `recommendations`
  - [x] `meal_logs`, `progress_logs`, `patient_requests`, `subscription_codes`, `meal_templates`
- [x] Alembic initial migration for all tables
- [x] Dead MongoDB model files deleted
- [x] `pace_preference` + `eating_habits` columns on `patients` ← confirmed: onboarding writes both

### Auth System
- [x] `app/core/security.py` — JWT for 3 roles (patient / doctor / admin)
- [x] `role`, `user_type` fields in JWT payload
- [x] `get_current_patient()`, `get_current_doctor()`, `get_current_admin()` dependencies
- [x] SubscriptionCheck middleware — reads `sub_status` from JWT (zero DB query)
- [x] DoctorIsolationMiddleware — auto-scopes every doctor route to `doctor_id`
- [x] bcrypt password hashing (passlib + monkeypatch applied)
- [x] `POST /api/v1/auth/refresh` — JWT refresh token rotation

### Rate Limiting
- [x] `20/minute` on `/token` and `/doctor/login`
- [x] Rate limiting on `POST /auth/register` ← `@limiter.limit("10/minute")` added in Sprint 2
- [x] Rate limiting on all 5 progress log POST endpoints ← added in Sprint 2
- [ ] Redis-backed slowapi ← deferred to Phase 7

### Dead Code Cleanup
- [x] Deleted: `app/schemas/diet_plan.py`, `app/models/meal_adjustment.py`
- [x] Deleted: `app/services/Healthy.py`, `app/services/datasets for eyantra/`
- [x] Deleted: `app/models/meal_plan.py`, cleaned `app/crud/`

---

**PHASE 0 SCORE: 27 / 28** — 1 remaining: Redis (deferred to Phase 7).

---

## 🟠 PHASE 1 — Patient Core Experience

### Auth
- [x] `POST /api/v1/auth/register` — dual flow: standalone (no code) + doctor-connected (with code)
- [x] `POST /api/v1/auth/token` — patient login, JWT + refresh
- [x] `POST /api/v1/auth/doctor/login` — doctor login, JWT + refresh
- [x] `POST /api/v1/auth/admin/login` — admin login, JWT + refresh
- [x] `POST /api/v1/auth/google/verify` — Google ID token verification, patient upsert, links existing accounts
- [ ] Firebase Cloud Messaging device token storage on login ← Phase 5

### Onboarding
- [x] `POST /api/v1/patients/onboarding` — stores all fields + calculates BMI/BMR/TDEE
  - [x] Target weight, date of birth (past-date validator)
  - [x] Health goals, medical conditions (15+)
  - [x] Dietary preferences, regional preference, meals per day, fasting days
  - [x] Lifestyle fields: sleep, water, occupation, smoking, alcohol
  - [x] pace_preference + eating_habits ← columns exist, written at onboarding
  - [x] nonveg_meals_per_week
  - [x] food_allergies — `Field(..., min_length=1)` enforced ← fixed in Sprint 2
- [x] Auto-calculate + store BMI, BMR, TDEE on onboarding
- [x] Auto-recalculate BMI/BMR/TDEE when patient updates weight or height (`PUT /users/me`)
- [x] Auto-trigger first meal plan generation after onboarding (fire-and-soft-fail)
- [x] `POST /api/v1/patients/disclaimer` — stores `disclaimer_accepted_at` UTC timestamp

### Patient Subscription & Doctor Connection
- [x] `POST /api/v1/patients/activate` — patient enters subscription code, links to doctor
- [x] `POST /api/v1/patients/request-doctor` — patient requests connection (alternative to code)
- [x] `GET /api/v1/patients/request-status` — patient polls approval status

### Meal Plan
- [x] `GET /api/v1/meal-plan/week` — 7-day plan grouped by date
- [x] `GET /api/v1/meal-plan/history` — metadata of all plans, newest first
- [x] Fix calorie target — uses patient's stored TDEE (not hardcoded 2000)
- [x] Plan regeneration — old plan soft-deleted, new one created
- [x] Plan versioning — soft-delete ✅ + version counter increments in `diet_plan_service.store_diet_plan()` ✅
- [ ] Fix plan storage — store `food_id` references, not full embedded JSON ← Phase 6 ML work

### Meal Logging
- [x] `POST /api/v1/progress/meal` — log a meal
- [x] `PUT /api/v1/progress/log/meal/{log_id}` — edit meal log within 24h window
- [x] `DELETE /api/v1/progress/log/meal/{log_id}` — delete meal log within 24h window
- [x] `food_id` reference (nullable) + `custom_food_name` + `portion_servings` columns exist
- [ ] Link meal log to specific recommendation slot ← deferred Sprint 3+
- [ ] `GET /api/v1/progress/adherence/weekly` ← depends on slot linking

### Progress Tracking
- [x] `GET /api/v1/progress/today` — uses patient.tdee, fallback 2000 only if None
- [x] `PUT /api/v1/progress/log/water` — overwrite today's count
- [x] `PUT /api/v1/progress/log/steps` — overwrite today's count
- [x] `PUT /api/v1/progress/log/weight` — overwrite today's weight
- [x] `DELETE /api/v1/progress/log/water` + `DELETE /api/v1/progress/log/steps` — reset to 0
- [x] `GET /api/v1/progress/weekly-report` — 7-day breakdown, totals, averages vs TDEE
- [x] `GET /api/v1/progress/weight-history` — last N days, capped 365
- [x] `GET /api/v1/progress/streak` — consecutive logging days

### Shopping List
- [x] `GET /api/v1/meal-plan/shopping-list` — aggregated + grouped by category
- [x] `POST /api/v1/meal-plan/shopping-list/toggle` — mark item as "available at home"

### Profile
- [x] `GET /api/v1/users/me` — current user profile
- [x] `PUT /api/v1/users/me` — update profile, auto-recalculates BMI/BMR/TDEE
- [x] `GET /api/v1/users/bmi` — current BMI

---

**PHASE 1 BACKEND SCORE: 40 / 42**
Remaining 2: FCM token storage (Phase 5), slot linking + adherence (deferred).

**Expo (React Native) screens: 0 / 36** — Sprint 5, not started.

---

## 🟡 PHASE 2 — Doctor Dashboard

### Doctor Backend
- [x] `POST /api/v1/auth/doctor/login` — JWT with role=doctor
  - [x] MFA fork: `mfa_enabled=False` → full JWT; `mfa_enabled=True` → partial 5-min token ← Sprint 2
- [x] `POST /api/v1/auth/doctor/mfa-login` — step-2: partial token + TOTP code → full JWT ← Sprint 2
- [x] `POST /api/v1/auth/doctor/mfa-setup` — generate secret, return otpauth:// URI for QR ← Sprint 2
- [x] `POST /api/v1/auth/doctor/mfa-confirm` — verify first live code, set mfa_enabled=True ← Sprint 2
- [x] `POST /api/v1/auth/doctor/mfa-disable` — disable MFA (requires valid TOTP) ← Sprint 2
- [x] `GET /api/v1/doctor/requests` — pending patient requests
- [x] `POST /api/v1/doctor/requests/{id}/accept` — accept patient
- [x] `POST /api/v1/doctor/requests/{id}/reject` — reject with optional note
- [x] `GET /api/v1/doctor/patients` — paginated list with total count
- [x] `GET /api/v1/doctor/patients/{patient_id}` — full patient profile
- [x] `GET /api/v1/doctor/patients/{patient_id}/logs` — meal logs for last N days
- [x] `GET /api/v1/doctor/patients/{patient_id}/progress` — weight/water/steps history
- [x] `GET /api/v1/doctor/patients/{patient_id}/plan` — current active meal plan
- [x] `PUT /api/v1/doctor/patients/{patient_id}/plan` — doctor overrides entire plan
- [x] `POST /api/v1/doctor/patients/{patient_id}/plan/notes` — inject note into specific meal slot
- [x] `POST /api/v1/doctor/patients/{patient_id}/notes` — add private clinical note
- [x] `GET /api/v1/doctor/patients/{patient_id}/notes` — list all clinical notes
- [x] `DELETE /api/v1/doctor/patients/{patient_id}` — remove patient (becomes standalone)
- [x] `GET /api/v1/doctor/recipes` — browse food DB (filter by diet, meal_time, search, paginated)
- [x] `POST /api/v1/doctor/recipes` — add new recipe (source='doctor', pending admin approval)
- [x] `POST /api/v1/doctor/recipes/{id}/assign` — inject recipe into patient plan(s)
- [x] `POST /api/v1/doctor/subscription-codes` — generate codes with expiry
- [x] `GET /api/v1/doctor/subscription-codes` — list all codes for this doctor
- [x] `GET /api/v1/doctor/dashboard` — stats: total/active patients, pending requests, etc.
- [x] Doctor data isolation — DoctorIsolationMiddleware enforced on all endpoints
- [ ] Auto-fetch recipe nutrition from Edamam API ← optional, deferred

---

**PHASE 2 BACKEND SCORE: 25 / 26** — 1 remaining: Edamam auto-fetch (optional).

**Next.js 15 Web screens: 0 / 18** — Sprint 3, not started.

---

## 🟢 PHASE 3 — Admin Dashboard

### Admin Backend
- [x] `POST /api/v1/auth/admin/login` — email + password, JWT with role=admin
  - [x] MFA fork: `mfa_enabled=False` → full JWT; `mfa_enabled=True` → partial 5-min token ← Sprint 2
- [x] `POST /api/v1/auth/admin/mfa-login` — step-2: partial token + TOTP code → full JWT ← Sprint 2
- [x] `POST /api/v1/auth/admin/mfa-setup` — generate secret, return otpauth:// URI for QR ← Sprint 2
- [x] `POST /api/v1/auth/admin/mfa-confirm` — verify first live code, set mfa_enabled=True ← Sprint 2
- [x] `POST /api/v1/auth/admin/mfa-disable` — disable MFA (requires valid TOTP) ← Sprint 2
- [x] `GET /api/v1/admin/stats` — total patients, active subscriptions, total doctors, active plans
- [x] `POST /api/v1/admin/doctors` — create doctor account
- [x] `GET /api/v1/admin/doctors` — list all doctors
- [x] `GET /api/v1/admin/doctors/{doctor_id}` — full profile + patient count
- [x] `PATCH /api/v1/admin/doctors/{doctor_id}/deactivate` — deactivate doctor
- [x] `DELETE /api/v1/admin/doctors/{doctor_id}` — soft-delete doctor, disconnect all patients
- [x] `POST /api/v1/admin/codes/generate` — generate code batch for a doctor, audit-logged
- [x] `GET /api/v1/admin/codes` — all codes, filterable by doctor + used status
- [x] `GET /api/v1/admin/billing` — platform-wide: total codes, used, per-doctor breakdown
- [x] `POST /api/v1/admin/billing/{doctor_id}/mark-paid` — audit-log entry, no new table ← Sprint 2
- [x] `PATCH /api/v1/admin/patients/{patient_id}/subscription/override` — manual override, audit-logged
- [x] `GET /api/v1/admin/food` — food DB view, filterable, paginated
- [x] `PATCH /api/v1/admin/food/{food_id}/approve` — approve doctor recipe
- [x] `PATCH /api/v1/admin/food/{food_id}/reject` — soft-delete
- [x] `DELETE /api/v1/admin/food/{food_id}` — hard delete food item
- [x] `GET /api/v1/admin/audit-logs` — paginated, filterable by role + action
- [x] Audit log writer — `log_action()` in `audit_service.py`
- [x] `DELETE /api/v1/admin/patients/{patient_id}` — DPDP Act right-to-erasure
- [x] IP whitelisting middleware — `AdminIPWhitelistMiddleware` in `middleware.py` ← Sprint 2
      Reads `allowed_ips` JSONB from Admin row. Empty list = whitelisting disabled (any IP allowed).

---

**PHASE 3 BACKEND SCORE: 23 / 23** ✅ COMPLETE

**Next.js 15 Web screens: 0 / 13** — Sprint 4, not started.

---

## 🔵 PHASE 4 — Subscriptions and Billing

- [ ] Integrate Razorpay SDK into backend
- [ ] `POST /api/v1/billing/pay` — Razorpay payment initiation
- [ ] Razorpay webhook handler — mark payment received on success
- [ ] Subscription auto-expiry job — daily cron, expires subscriptions past end_date
- [ ] Subscription renewal flow — extend `subscription_end_date` on payment
- [ ] Doctor billing reminder — email 7 days before due date
- [ ] Patient expiry reminder — push notification 3 days before expiry
- [ ] Code purchase flow — doctor requests codes, admin generates, codes delivered
- [ ] Tier 1 standalone premium flow (₹149/month)
- [ ] Find a Doctor API — location-based listing sorted by distance
- [ ] Standalone → doctor-connected upgrade flow

---

## 🟣 PHASE 5 — Notifications

- [ ] FCM integration into FastAPI
- [ ] Store FCM device tokens per patient on login
- [ ] Notification service layer
- [ ] Patient notifications: meal reminders, water reminder, new plan ready, doctor accepted/updated/noted, sub expiry, milestone, inactivity
- [ ] Doctor notifications: new request, patient inactive, subs expiring, billing due
- [ ] Admin notifications: payment overdue, code stock low
- [ ] Loading skeletons on all app screens
- [ ] Proper error messages on all API failures
- [ ] Empty state screens (no plan, no logs, no patients)
- [ ] Offline state handling in React Native

---

## ⚪ PHASE 6 — Dataset and ML

### ETL Status (from live DB audit 2026-03-08: 2,116 rows total)
- [x] `seed_food_items.py` — 184 hand-curated excel rows loaded (`is_verified=True`)
- [x] `seed_6k_recipes.py` — 1,930 rows from IndianFoodDatasetCSV.csv with USDA nutrition
- [x] `fix_6k_calories.py` — cup-density bug fixed
- [x] `clean_recipe_names.py` — regex cleaning applied
- [x] `ai_clean_recipe_names.py` — Gemini + Ollama pass applied
- [x] `tag_pantry_staples.py` — pantry staple tags on ingredients JSONB
- [x] `seed_meal_templates.py` — 180 templates (5 meal times × 4 regions × 3 diets × 3 plan types)
- [ ] Add `image_url` column to `food_items` via Alembic + cross-reference eyantra dataset ← optional
- [ ] `scripts/data_validation.py` — check for nulls, negative nutrition, impossible calories

### Meal Generator — Remaining Improvements
- [x] Allergy filtering — `_is_allergenic()` checks `ingredients` JSONB. Normalises allergens to
      lowercase frozenset. Handles "None" sentinel. Both callers updated. Done Sprint 1.
- [ ] Remove region filter from algorithm — still filters `FoodItem.region_tags.any(region)` at
      Level 1; reduces food variety unnecessarily
- [ ] Expand health condition support from 3 to 15+ conditions (PCOS, Jain, Kidney, Gluten-free, Vegan)
- [ ] Cross-week meal history — `weekly_used_ids` is in-memory, resets on each `generate_meal_plan()` call
- [ ] Store meal plans as `food_id` links instead of full embedded JSON

---

**PHASE 6 SCORE: 8 / 13** — ETL fully done + allergy filtering done, 5 ML improvements remain.

---

## ⚫ PHASE 7 — Production Deployment

- [ ] GCP project — Mumbai region (asia-south1)
- [ ] Cloud SQL PostgreSQL (private VPC, no public IP)
- [ ] Alembic migrations on Cloud SQL
- [ ] Google Secret Manager — move all `.env` secrets
- [ ] Cloud Storage bucket for food images
- [ ] Cloudflare DNS for `mityahar.com` + `api.mityahar.com`
- [ ] SSL via Cloudflare
- [ ] Dockerfile for FastAPI backend
- [ ] `cloudbuild.yaml` or GitHub Actions CI/CD
- [ ] Cloud Run — auto-scaling, env vars from Secret Manager
- [ ] Redis via Cloud Memorystore (replaces in-memory slowapi)
- [ ] Load test before launch
- [ ] Google Play Store submission (₹2,088 one-time)
- [ ] Apple TestFlight (₹8,267/year)
- [ ] Cloud Monitoring + alerting
- [ ] Sentry error tracking (free tier)

---

## 🔑 SECURITY (Cross-Phase)

- [x] bcrypt password hashing — confirmed in security.py
- [x] Consent logging — `disclaimer_accepted_at` timestamp stored on Patient row
- [x] Audit log writer — `log_action()` called from all mutating admin routes
- [x] MFA (TOTP — Google Authenticator) for **doctor login** ← Sprint 2
      `app/services/mfa_service.py` — `generate_mfa_secret()`, `get_totp_uri()`, `verify_totp()`
      Setup → Confirm → Login step-2 flow implemented. Backward-compatible: mfa_enabled=False unchanged.
- [x] MFA (TOTP) for **admin login** ← Sprint 2 — same pattern as doctor
- [x] IP whitelisting middleware for admin routes ← Sprint 2
      `AdminIPWhitelistMiddleware` in `middleware.py`, mounted in `main.py`.
      DB query only fires on authenticated /admin requests. Empty allowed_ips = disabled.
- [x] Rate limit `POST /auth/register` ← Sprint 2 (10/minute)
- [x] Rate limit progress log POST endpoints ← Sprint 2 (30-60/minute each)
- [ ] HttpOnly cookie for refresh tokens (web frontends) ← Sprint 3 — small backend change required
- [ ] Encrypt sensitive patient fields at application level (phone, health data) via Google KMS
- [ ] Fix CORS — not `*` wildcard in production
- [ ] Security headers (HSTS, X-Frame-Options, CSP)
- [ ] Data retention policy enforcement (DPDP Act) ← erasure endpoint exists, scheduled purge not built

---

## 🖥️ FRONTEND ARCHITECTURE (decided 2026-03-08)

### Monorepo Structure
```
mityahar-frontend/
├── apps/
│   ├── admin/          # Next.js 15 (App Router)
│   ├── doctor/         # Next.js 15 (App Router)
│   └── patient/        # Expo SDK 54 (New Architecture)
├── packages/
│   ├── api-client/     # Auto-generated TS client from FastAPI /openapi.json
│   ├── types/          # Shared Zod schemas + TypeScript interfaces
│   └── ui/             # Shared shadcn/ui primitives (web only)
├── turbo.json
└── pnpm-workspace.yaml
```

### Admin Dashboard — Next.js 15
| Layer | Choice | Reason |
|---|---|---|
| Framework | Next.js 15 App Router | Edge middleware JWT validation, opinionated structure |
| Language | TypeScript strict | Mirror Pydantic type safety end-to-end |
| Styling | Tailwind CSS v4 + shadcn/ui | Owned components, no vendor lock-in |
| Server state | TanStack Query v5 | Caching, background refetch, optimistic updates |
| Client state | Zustand v5 | Auth tokens (in-memory), UI flags |
| Forms | React Hook Form + Zod | Mirrors Pydantic schemas, zero runtime cost |
| Charts | Recharts | Billing, doctor stats, food DB metrics |
| HTTP | Axios | Interceptors for silent token refresh |
| Token storage | Zustand (memory) + HttpOnly cookie | Best XSS + CSRF protection |
| **Screens** | **0 / 13** | Sprint 4 |

### Doctor Dashboard — Next.js 15
| Layer | Choice | Reason |
|---|---|---|
| Framework | Next.js 15 App Router | Same stack as admin, 80% shared config |
| Language | TypeScript strict | — |
| Styling | Tailwind CSS v4 + shadcn/ui | — |
| Server state | TanStack Query v5 | Patient list, meal logs, progress charts |
| Client state | Zustand v5 | — |
| Forms | React Hook Form + Zod | — |
| Charts | Recharts | Patient weight history, adherence, calorie trends |
| HTTP | Axios | — |
| Token storage | Zustand (memory) + HttpOnly cookie | — |
| **Screens** | **0 / 18** | Sprint 3 |

### Patient App — Expo SDK 54
| Layer | Choice | Reason |
|---|---|---|
| Framework | Expo SDK 54 (New Architecture) | JSI/Fabric, OTA updates via EAS, no bridge bottleneck |
| Language | TypeScript strict | — |
| Styling | NativeWind v4 | Tailwind utility classes in React Native |
| Routing | Expo Router v4 | File-based, same mental model as Next.js App Router |
| Server state | TanStack Query v5 | Same pattern as web — no new concepts |
| Client state | Zustand v5 | Same pattern as web |
| Forms | React Hook Form + Zod | — |
| Charts | Victory Native | Mobile-optimised, smooth animations |
| Animations | React Native Reanimated 3 | Progress bars, meal log transitions |
| Push notifications | Expo Notifications | Phase 5 — meal reminders, sub expiry |
| Token storage | Expo SecureStore | iOS Keychain / Android Keystore hardware-backed |
| HTTP | Axios | — |
| **Screens** | **0 / 36** | Sprint 5 |

### Token Security Architecture
```
Web (Admin + Doctor):
  Login → access_token in Zustand (memory only, gone on tab close)
          refresh_token in HttpOnly + Secure + SameSite=Strict cookie
  Refresh → silent POST /auth/refresh on 401 → new access_token → back in Zustand
  Requires: FastAPI backend change — Set-Cookie header on login endpoints (Sprint 3)

Mobile (Patient):
  Login → access_token + refresh_token in Expo SecureStore
          (maps to iOS Keychain / Android Keystore — not localStorage, not AsyncStorage)
```

---

## 📊 ACCURATE TASK COUNT (2026-03-08, post-Sprint-2)

| Area | Total | Done | Remaining |
|---|---|---|---|
| Phase 0 — Foundation | 28 | 27 | 1 (Redis) |
| Phase 1 — Patient Backend | 42 | 40 | 2 (FCM, slot linking) |
| Phase 1 — Expo (Patient App) | 36 | 0 | 36 |
| Phase 2 — Doctor Backend | 26 | 25 | 1 (Edamam optional) |
| Phase 2 — Next.js (Doctor Web) | 18 | 0 | 18 |
| Phase 3 — Admin Backend | 23 | 23 | 0 ✅ |
| Phase 3 — Next.js (Admin Web) | 13 | 0 | 13 |
| Phase 4 — Billing | 11 | 0 | 11 |
| Phase 5 — Notifications | 20 | 0 | 20 |
| Phase 6 — Dataset + ML | 13 | 8 | 5 |
| Phase 7 — Deployment | 16 | 0 | 16 |
| Security (cross-phase) | 12 | 8 | 4 |
| **Total** | **258** | **131** | **127** |

---

## 🚀 SPRINT STATUS

| Sprint | Scope | Status |
|---|---|---|
| Sprint 0 | DB schema, migrations, models | ✅ Done |
| Sprint 1 | Patient + Doctor + Admin backend, ETL, allergy filtering | ✅ Done |
| **Sprint 2** | **Rate limits, MFA (TOTP), IP whitelist, mark-paid, food_allergies fix** | ✅ **Done — 95/95 tests** |
| Sprint 3 | Doctor Dashboard — Next.js 15 (18 screens) | 🔲 Next |
| Sprint 4 | Admin Dashboard — Next.js 15 (13 screens) | 🔲 Queued |
| Sprint 5 | Patient App — Expo SDK 54 (36 screens) | 🔲 Queued |
| Sprint 6 | Phase 4 Billing (Razorpay) + Phase 5 Notifications (FCM) | 🔲 Queued |
| Sprint 7 | ML quality improvements (Phase 6 Tier 3) | 🔲 Queued |
| Sprint 8 | Phase 7 Production Deploy (GCP, Cloud Run, CI/CD) | 🔲 Queued |

### Sprint 3 Prerequisites (before starting Doctor Dashboard)
- [ ] Add `Set-Cookie` (HttpOnly) for refresh_token on `/auth/doctor/login` endpoint
- [ ] Add `CORS_ORIGINS` entry for `http://localhost:3001` in `.env`
- [ ] Scaffold monorepo: `pnpm init`, `turbo.json`, `apps/doctor/` with Next.js 15
- [ ] Generate TypeScript API client from `GET /openapi.json` using `openapi-typescript`
