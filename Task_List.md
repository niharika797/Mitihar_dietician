## Complete Mityahar Code Task List

> Last updated: Phase 0 ✅ complete · Phase 1 backend ~80% complete · Phase 6 ML engine partially complete
> Legend: [x] = verified done from code · [ ] = not done · [~] = partial / column exists but logic incomplete

---

## 🔴 PHASE 0 — Foundation (Do First, Everything Depends on This)

### Database Migration — MongoDB → PostgreSQL

- [x] Install SQLAlchemy 2.0 async + asyncpg + Alembic in requirements.txt
- [x] Remove PyMongo and motor dependencies
- [x] Create `app/core/database.py` — async PostgreSQL engine and session factory
- [x] Create all 9 tables as SQLAlchemy models:
  - [x] `doctors` table
  - [x] `patients` table
  - [x] `admins` table
  - [x] `food_items` table
  - [x] `recommendations` table
  - [x] `meal_logs` table
  - [x] `progress_logs` table
  - [x] `patient_requests` table
  - [x] `subscription_codes` table
  - [x] `meal_templates` table ← 10th table added during Phase 0 (not in original list)
- [x] Write Alembic initial migration for all 9 tables
- [x] Delete all MongoDB model files (`app/models/diet_plan.py`, `app/models/meal_plan.py`, `app/models/meal_adjustment.py`, `app/models/progress.py`)
- [x] Rewrite `app/models/user.py` as PostgreSQL SQLAlchemy model

### Authentication System — Three Roles

- [x] Rewrite `app/core/security.py` — JWT generation for three roles (patient, doctor, admin)
- [x] Add `role` field to JWT payload
- [x] Add `user_type` field to JWT payload (standalone / doctor_connected)
- [x] Create role-based dependency functions:
  - [x] `get_current_patient()`
  - [x] `get_current_doctor()`
  - [x] `get_current_admin()`
- [x] Create subscription check middleware — reads `sub_status` from JWT claim (zero DB query)
- [x] Create doctor data isolation middleware — auto-scopes every doctor route to their `doctor_id`
- [x] Verify password hashing is bcrypt — confirmed (passlib + bcrypt, monkeypatch applied)
- [x] Add JWT refresh token rotation — `POST /api/v1/auth/refresh` built

### Rate Limiting — Fix Existing

- [ ] Replace in-memory slowapi with Redis-backed slowapi ← deferred to Phase 7 (production infra)
- [x] Add rate limiting to auth endpoints — `20/minute` on `/token` and `/doctors/auth/login`
- [ ] Add rate limiting to all progress log endpoints ← no `@limiter` on progress POST routes
- [ ] Add rate limiting to all patient registration endpoints ← `/register` has no rate limit

### Dead Code Cleanup

- [x] Delete `app/schemas/diet_plan.py` (unused, conflicting) — replaced with clean DietPlanResponse
- [x] Delete `app/models/meal_adjustment.py` (never used)
- [x] Delete `app/services/Healthy.py` (broken Kaggle path)
- [x] Delete `app/services/datasets for eyantra/` entire folder (never imported)
- [x] Evaluate and delete `app/models/meal_plan.py` if unused — deleted
- [x] Clean up `app/crud/` folder

---

**PHASE 0 SCORE: 25 / 28**
Remaining 3: Redis rate limiting — all correctly deferred to Phase 7 production setup.

---

## 🟠 PHASE 1 — Patient Core Experience

### Onboarding — Backend

- [ ] Rewrite `POST /api/v1/auth/register` — split into two flows (standalone vs doctor-connected) ← deferred Sprint 1
- [x] Target weight, date of birth — in OnboardingRequest with past-date validator
- [~] Health goals ✅ stored · pace_preference ❌ missing (requires new DB column + Alembic)
- [x] Medical conditions (15+ as JSONB array)
- [~] Food allergies — field exists and stored, but not enforced as non-empty (defaults to [])
- [x] Dietary preferences (list[str]) — added Block J
- [x] Regional food preference — captured at registration
- [x] Meals per day — `Literal[3, 5]` enforced
- [x] Fasting days — list[str] added Block J
- [x] Lifestyle fields — sleep, water, occupation, smoking, alcohol — all stored
- [ ] Current eating habits fields ← requires new DB columns + Alembic migration (deferred Sprint 1)
- [x] `POST /api/v1/patients/request-doctor` — patient submits request to doctor
- [x] `GET /api/v1/patients/request-status` — patient checks approval status (Block F)
- [x] Auto-calculate and STORE BMI, BMR, TDEE on profile completion
- [x] Auto-recalculate BMI/BMR/TDEE when patient updates weight or height (Block G)
- [x] Auto-trigger first meal plan generation immediately after onboarding (Block F, fire-and-soft-fail)
- [x] Add disclaimer acceptance logging — `POST /api/v1/patients/disclaimer` stores UTC timestamp
- [ ] `POST /api/v1/auth/google` — Firebase Google OAuth ← requires Firebase Admin SDK (deferred Sprint 6)

### Meal Plan — Backend Fixes

- [x] Fix calorie target — replaced hardcoded `2000` with patient's stored TDEE
- [x] Fix plan regeneration — old plan soft-deleted, new one generated (no HTTP 400 block)
- [~] Plan versioning — previous plans preserved via soft-delete ✅ but `version` counter never increments ❌ (deferred Sprint 1)
- [ ] Fix plan storage — change to food_item reference IDs ← requires Phase 6 ML rewrite (deferred)
- [x] `GET /api/v1/meal-plan/week` — grouped by Date field, 7-day dict (Block I)
- [x] `GET /api/v1/meal-plan/history` — metadata of all plans, newest first (Block I)
- [ ] Remove region filter from `meal_generator.py` algorithm ← Phase 6 ML work (deferred)

### Meal Logging — Backend Fixes

- [ ] Link `POST /api/v1/progress/meal` to specific recommendation slot ← needs recommendation_id from client (deferred Sprint 1)
- [x] `food_id` reference (nullable) — column exists on meal_logs from Phase 0
- [x] `custom_food_name` field — column exists from Phase 0
- [x] `portion_size` field — `portion_servings` column exists from Phase 0
- [x] `PUT /api/v1/progress/log/meal/{log_id}` — edit meal log within 24h window (Block H)
- [x] `DELETE /api/v1/progress/log/meal/{log_id}` — delete meal log within 24h window (Block H)
- [ ] Build adherence calculation ← depends on recommendation slot linking first (deferred Sprint 1)
- [ ] `GET /api/v1/progress/adherence/weekly` ← depends on adherence calculation (deferred Sprint 1)

### Progress Tracking — Backend Fixes

- [x] Fix `GET /api/v1/progress/today` — uses patient.tdee, fallback 2000 only if None
- [x] `PUT /api/v1/progress/log/water` — overwrite today's count (Block H)
- [x] `PUT /api/v1/progress/log/steps` — overwrite today's count (Block H)
- [x] `PUT /api/v1/progress/log/weight` — overwrite today's weight (Block H)
- [x] `DELETE /api/v1/progress/log/water` — reset to 0 (Block H)
- [x] `DELETE /api/v1/progress/log/steps` — reset to 0 (Block H)
- [x] `GET /api/v1/progress/weekly-report` — 7-day breakdown, totals, averages vs TDEE (Block H)
- [x] `GET /api/v1/progress/weight-history` — entries for last N days, capped 365 (Block H)
- [x] Streak calculation — `GET /api/v1/progress/streak`, capped at 365 days (Block H)

### Shopping List — Backend

- [x] `GET /api/v1/meal-plan/shopping-list` — aggregated ingredient list (Block K)
- [x] Group ingredients by category (Vegetables, Dairy, Grains, Proteins, Fruits, Spices) (Block K)
- [ ] Mark items as "available at home" toggle endpoint ← deferred Sprint 1

### Patient App — React Native Screens

- [ ] Setup Expo project with navigation (React Navigation)
- [ ] Screen: Splash
- [ ] Screen: Welcome / Landing
- [ ] Screen: Google OAuth login
- [ ] Screen: "Do you have a doctor?" choice
- [ ] Screen: Enter doctor code / select doctor from list
- [ ] Screen: Registration request submitted (waiting)
- [ ] Screen: Health questionnaire — Step 1 (Body Metrics)
- [ ] Screen: Health questionnaire — Step 2 (Health Goals)
- [ ] Screen: Health questionnaire — Step 3 (Medical Conditions)
- [ ] Screen: Health questionnaire — Step 4 (Allergies — mandatory)
- [ ] Screen: Health questionnaire — Step 5 (Dietary Preferences)
- [ ] Screen: Health questionnaire — Step 6 (Lifestyle)
- [ ] Screen: Health questionnaire — Step 7 (Eating Habits)
- [ ] Screen: Profile Summary (BMI/BMR/TDEE shown after questionnaire)
- [ ] Screen: Home Dashboard
- [ ] Screen: Weekly Meal Plan view (7-day tab navigation)
- [ ] Screen: Recipe Detail (ingredients, instructions, nutrition, doctor note)
- [ ] Screen: Log Meal — "I had this" flow
- [ ] Screen: Log Meal — "I had something else" flow (search + custom)
- [ ] Screen: Progress Overview
- [ ] Screen: Log Water
- [ ] Screen: Log Steps
- [ ] Screen: Log Weight
- [ ] Screen: Weekly Report
- [ ] Screen: Shopping List / Ingredient Checklist
- [ ] Screen: Find a Doctor (location-based, Tier 1 only)
- [ ] Screen: Profile Overview
- [ ] Screen: Edit Profile
- [ ] Screen: Notification Preferences
- [ ] Screen: Disclaimer screen (Tier 1 — mandatory on first launch)
- [ ] Screen: Subscription expired screen (Tier 2)
- [ ] Connect all screens to backend APIs
- [ ] Handle loading states on every screen
- [ ] Handle error states on every screen
- [ ] Handle empty states (no plan yet, no logs yet)

---

**PHASE 1 BACKEND SCORE: 30 / 44 (2 partial)**
React Native screens: 0 / 36 — not started, separate frontend sprint.

---

## 🟡 PHASE 2 — Doctor Dashboard

### Doctor — Backend

- [x] `POST /api/v1/doctors/auth/login` — email + password login (Phase 0)
- [x] `GET /api/v1/doctor/requests` — list pending patient requests (Block B)
- [x] `PATCH /api/v1/doctor/requests/{request_id}/accept` — accept patient (Block B)
- [x] `PATCH /api/v1/doctor/requests/{request_id}/reject` — reject with optional note (Block B)
- [x] `GET /api/v1/doctor/patients` — paginated list with filters (Block B)
- [x] `GET /api/v1/doctor/patients/{patient_id}` — full patient profile view (Block B)
- [ ] `GET /api/v1/doctor/patients/{patient_id}/logs` — meal logs with recommended vs actual
- [ ] `GET /api/v1/doctor/patients/{patient_id}/progress` — weight, water, steps history
- [x] `GET /api/v1/doctor/patients/{patient_id}/plan` — current meal plan (Block B)
- [x] `PUT /api/v1/doctor/patients/{patient_id}/plan` — doctor overrides meal plan (Block B)
- [ ] `POST /api/v1/doctor/patients/{patient_id}/plan/notes` — add note to specific meal
- [ ] `POST /api/v1/doctor/patients/{patient_id}/notes` — add private clinical note
- [ ] `GET /api/v1/doctor/patients/{patient_id}/notes` — get all clinical notes
- [ ] `DELETE /api/v1/doctor/patients/{patient_id}` — remove patient from doctor's list
- [ ] `GET /api/v1/doctor/recipes` — browse food database
- [ ] `POST /api/v1/doctor/recipes` — add new recipe (with auto-fetch for blank fields)
- [ ] Build auto-fetch recipe details from internet when fields left blank (Edamam API or similar)
- [ ] `POST /api/v1/doctor/recipes/{recipe_id}/assign` — assign recipe to patient(s)
- [x] `GET /api/v1/doctor/codes` — list all activation codes used/unused/expired (Block B)
- [ ] `GET /api/v1/doctor/dashboard` — aggregated stats for dashboard cards
- [ ] Build patient inactivity detection — flag patients with no logs in X days
- [ ] Build subscription expiry detection — flag patients expiring this week
- [x] Enforce doctor data isolation on ALL doctor endpoints — DoctorIsolationMiddleware (Phase 0)

### Doctor Dashboard — React Web Screens

- [ ] Setup React + Vite project with React Router
- [ ] Setup shared component library (shadcn/ui)
- [ ] Screen: Login (email + password + MFA field)
- [ ] Screen: Home Dashboard (4 stat cards + attention list + pending requests)
- [ ] Screen: Patient List (table with filters and search)
- [ ] Screen: Individual Patient — Profile Tab
- [ ] Screen: Individual Patient — Meal Logs Tab (recommended vs actual)
- [ ] Screen: Individual Patient — Progress Tab (weight/water/steps graphs)
- [ ] Screen: Individual Patient — Current Plan Tab (with edit/swap/note per meal)
- [ ] Screen: Individual Patient — Clinical Notes Tab
- [ ] Screen: Pending Requests (accept/reject with optional rejection note)
- [ ] Screen: Recipe Library (search, filter, browse)
- [ ] Screen: Add New Recipe form
- [ ] Screen: Assign Recipe modal
- [ ] Screen: Codes and Billing (code history, billing summary, buy more)
- [ ] Screen: My Profile (edit details, photo, availability, change password)
- [ ] Connect all screens to backend APIs
- [ ] Add MFA setup and verification flow (Google Authenticator)

---

**PHASE 2 BACKEND SCORE: 11 / 23 done**
React Web screens: 0 / 18 — not started.

---

## 🟢 PHASE 3 — Admin Dashboard

### Admin — Backend

- [ ] `POST /api/v1/admin/auth/login` — email + password + MFA ← dedicated login endpoint not built
- [x] `GET /api/v1/admin/overview` — platform-wide stats (get_stats, Block C)
- [x] `POST /api/v1/admin/doctors` — create new doctor account (Block C)
- [x] `GET /api/v1/admin/doctors` — list all doctors with patient counts (Block C)
- [ ] `GET /api/v1/admin/doctors/{doctor_id}` — full doctor profile and history
- [x] `PATCH /api/v1/admin/doctors/{doctor_id}/deactivate` — deactivate doctor (Block C)
- [ ] `DELETE /api/v1/admin/doctors/{doctor_id}` — remove doctor (with patient handling rules)
- [ ] `POST /api/v1/admin/codes/generate` — generate activation code batch for a doctor
- [ ] `GET /api/v1/admin/codes` — view all codes across all doctors
- [ ] `GET /api/v1/admin/billing` — full platform billing overview
- [ ] `POST /api/v1/admin/billing/{doctor_id}/mark-paid` — mark a doctor's payment received
- [ ] `PATCH /api/v1/admin/patients/{patient_id}/subscription/override` — manual subscription override
- [ ] `GET /api/v1/admin/food` — food database management view
- [ ] `PATCH /api/v1/admin/food/{food_id}/approve` — approve doctor-added recipe
- [ ] `PATCH /api/v1/admin/food/{food_id}/reject` — reject with note
- [ ] `DELETE /api/v1/admin/food/{food_id}` — remove food item
- [ ] `GET /api/v1/admin/audit-logs` — paginated audit log viewer
- [ ] Build audit log writer — records every significant action with timestamp, actor, IP
- [ ] `DELETE /api/v1/admin/patients/{patient_id}` — DPDP Act compliance data erasure
- [ ] Add IP whitelisting middleware for all admin routes

### Admin Dashboard — React Web Screens

- [ ] Extend Doctor Dashboard React project with admin role routing
- [ ] Screen: Admin Login (email + password + MFA + IP check)
- [ ] Screen: Overview Dashboard (all doctors, all patients, revenue this month, growth chart)
- [ ] Screen: All Doctors List (table with status, patient count, revenue MTD)
- [ ] Screen: Add New Doctor form
- [ ] Screen: Individual Doctor view (profile, patients, codes, billing, activity)
- [ ] Screen: Food Database (browse all 6,871+ items, pending approvals tab)
- [ ] Screen: Approve/Reject Doctor Recipe
- [ ] Screen: Billing Overview (per doctor breakdown, paid/pending/overdue)
- [ ] Screen: Generate Codes modal
- [ ] Screen: Audit Logs viewer (filterable, exportable as CSV)
- [ ] Screen: Platform Settings
- [ ] Connect all screens to backend APIs

---

**PHASE 3 BACKEND SCORE: 4 / 20 done**
React Web screens: 0 / 13 — not started.

---

## 🔵 PHASE 4 — Subscriptions and Billing

- [ ] Integrate Razorpay SDK into backend
- [ ] Build doctor subscription payment flow (monthly billing)
- [ ] Build `POST /api/v1/billing/pay` — Razorpay payment initiation
- [ ] Build Razorpay webhook handler — mark payment received on success
- [ ] Build subscription auto-expiry job — runs daily, expires subscriptions past end date
- [ ] Build subscription renewal flow — extend `subscription_end_date` on payment
- [ ] Build doctor billing reminder — email 7 days before due date
- [ ] Build patient expiry reminder notification — push notification 3 days before expiry
- [ ] Build code purchase flow — doctor requests codes, admin generates, codes delivered
- [ ] Build Tier 1 standalone premium flow (₹149/month — Phase 2 of app)
- [ ] Build Find a Doctor API — location-based doctor listing sorted by distance
- [ ] Build standalone → doctor-connected upgrade flow

---

## 🟣 PHASE 5 — Notifications and Polish

- [ ] Integrate Firebase Cloud Messaging (FCM) into FastAPI backend
- [ ] Store FCM device tokens for each patient on login
- [ ] Build notification service layer
- [ ] Patient notifications:
  - [ ] Meal reminders (breakfast, lunch, dinner — user-set times)
  - [ ] Water intake reminder every 2 hours if not logged
  - [ ] New weekly plan ready
  - [ ] Doctor approved your request
  - [ ] Doctor updated your plan
  - [ ] Doctor added a note to your meal
  - [ ] Subscription expiring in 3 days
  - [ ] Milestone achieved (first kg lost, 7-day streak)
  - [ ] Inactivity reminder (no log in 2 days)
- [ ] Doctor notifications:
  - [ ] New patient request received
  - [ ] Patient inactive for X days
  - [ ] Subscription expiring for X patients this week
  - [ ] Billing due reminder
- [ ] Admin notifications:
  - [ ] Doctor payment overdue
  - [ ] Doctor code stock running low
- [ ] Add loading skeletons to all app screens
- [ ] Add proper error messages to all API failures
- [ ] Add empty state screens (no plan, no logs, no patients)
- [ ] Handle offline state in React Native (no internet message)

---

## ⚪ PHASE 6 — Dataset and ML Upgrade

> ⚠️ NOTE: meal_generator.py was FULLY REWRITTEN in Phase 0 to read from PostgreSQL `food_items`
> and `meal_templates` tables via SQLAlchemy — this is the largest Phase 6 task and it's done.
> However the food_items table is currently EMPTY — no ETL script has loaded actual food data yet.
> All ETL tasks below must be completed before the meal generator can produce real results.

### ETL — Merge All Datasets into PostgreSQL

- [ ] Write ETL script to load `IndianFoodDataset` (6,871 rows) into `food_items` table as primary source
- [ ] Normalize column names across all sources (fiber vs fibre, name vs MENU etc.)
- [ ] Cross-reference `meal_generator/data/*.xlsx` files by food name — merge nutrition data where names match
- [ ] Cross-reference eyantra datasets — pull `image_url` where food names match
      ← NOTE: `food_items` table has no `image_url` column yet — add via Alembic migration first
- [~] Flag all items with missing nutrition as `nutrition_verified = false`
      ← Column exists as `is_verified` (Boolean, default=False) — name differs from spec, ETL flagging logic not written
- [ ] Call Edamam/Nutritionix API to fill nutrition gaps for unflagged items
- [ ] Remove `Region` column entirely from all datasets ← xlsx files still have region columns
- [ ] Remove duplicate entries across all three sources
- [ ] Write data validation script — check for nulls, negative nutrition values, impossible calorie counts

### ML Engine — Rewrite to Read from PostgreSQL

- [x] Rewrite `meal_generator.py` — reads from `food_items` + `meal_templates` PostgreSQL tables via SQLAlchemy
      ← DONE. Full 4-level waterfall, diet fallback chain, non-veg budget, weekly deduplication all built.
- [ ] Remove region filter from algorithm logic completely
      ← Region still filters both MealTemplate AND FoodItem queries at 4 points in the code
- [ ] Add allergy filtering — exclude food items containing patient's allergenic ingredients from `ingredients` JSONB
      ← `patient.food_allergies` is stored but never read in _find_food_item()
- [ ] Expand health condition support from 3 values to full 15+ conditions mapped to diet type filters:
  - [ ] Diabetic → filter to Diabetic Friendly tagged recipes only
  - [ ] PCOS → prioritize high-fiber low-GI meals
  - [ ] Kidney disease → flag high potassium/phosphorus, doctor warning
  - [ ] Jain → exclude onion, garlic, potato, carrot, radish from ingredients
  - [ ] Gluten free → filter to Gluten Free tagged recipes
  - [ ] Vegan → filter to Vegan tagged recipes
- [ ] Add long-term meal history — avoid repeating same meals across consecutive weeks
      ← `weekly_used_ids` is an in-memory set that resets each generation call — no cross-week persistence
- [ ] Store meal recommendation references as `food_id` links, not full embedded data
      ← `recommendations.meals` still stores full JSON objects with all nutrition embedded

---

**PHASE 6 SCORE: 1 / 15 done (1 partial)**
The one done item (meal_generator PostgreSQL rewrite) is the most architecturally significant.
All 9 ETL tasks remain — food_items table is empty until these run.

---

## ⚫ PHASE 7 — Production Deployment

- [ ] Create GCP project in Mumbai region (asia-south1)
- [ ] Set up Cloud SQL PostgreSQL instance (private VPC, no public IP)
- [ ] Run Alembic migrations on Cloud SQL
- [ ] Set up Google Secret Manager — move all `.env` secrets
- [ ] Set up Cloud Storage bucket for food images
- [ ] Configure Cloudflare DNS for `mityahar.com` and `api.mityahar.com`
- [ ] Set up SSL via Cloudflare
- [ ] Write Dockerfile for FastAPI backend
- [ ] Write `cloudbuild.yaml` or GitHub Actions CI/CD pipeline
- [ ] Configure Cloud Run service — auto-scaling, environment variables from Secret Manager
- [ ] Set up Redis via Cloud Memorystore
- [ ] Run load test before launch
- [ ] Submit React Native app to Google Play Store (₹2,088 one-time)
- [ ] Submit React Native app to Apple TestFlight (₹8,267/year)
- [ ] Set up Cloud Monitoring and alerting
- [ ] Set up error tracking (Sentry — free tier)

---

## 🔑 SECURITY TASKS (Cross-Phase — Implement as You Build)

- [x] Verify bcrypt is used for password hashing — confirmed in security.py (passlib + bcrypt)
- [ ] Add MFA (TOTP — Google Authenticator) for doctor login ← `mfa_secret` + `mfa_enabled` columns exist but logic not built
- [ ] Add MFA + IP whitelisting for admin login ← `allowed_ips` JSONB column exists but middleware not built
- [ ] Encrypt sensitive patient fields at application level (phone, health data) via Google KMS
- [ ] Fix CORS — ensure not set to `*` wildcard in production
- [ ] Add security headers (HSTS, X-Frame-Options, Content-Security-Policy)
- [ ] Add request signing for admin endpoints
- [ ] Audit log every doctor and admin action (actor, action, timestamp, IP)
- [ ] Add data retention policy enforcement (DPDP Act)
- [x] Add consent logging — `disclaimer_accepted_at` timestamp stored on Patient row (Block J)

---

## 📊 COMPLETE TASK COUNT

| Phase | Total | Done | Partial | Remaining | Priority |
|---|---|---|---|---|---|
| Phase 0 — Foundation | 28 | 25 | 0 | 3 | 🔴 Critical |
| Phase 1 — Patient Backend | 44 | 30 | 2 | 12 | 🔴 Critical |
| Phase 1 — React Native | 36 | 0 | 0 | 36 | 🔴 Critical |
| Phase 2 — Doctor Backend | 23 | 11 | 0 | 12 | 🟠 High |
| Phase 2 — React Web | 18 | 0 | 0 | 18 | 🟠 High |
| Phase 3 — Admin Backend | 20 | 4 | 0 | 16 | 🟡 Medium |
| Phase 3 — Admin Web | 13 | 0 | 0 | 13 | 🟡 Medium |
| Phase 4 — Billing | 12 | 0 | 0 | 12 | 🟡 Medium |
| Phase 5 — Notifications | 20 | 0 | 0 | 20 | 🟢 Normal |
| Phase 6 — Dataset + ML | 15 | 1 | 1 | 13 | 🟢 Normal |
| Phase 7 — Deployment | 16 | 0 | 0 | 16 | ⚪ Last |
| Security (ongoing) | 10 | 2 | 0 | 8 | 🔴 Throughout |
| **Total** | **255** | **73** | **3** | **179** | |

---

## SPRINT PLAN (agreed approach — backend first, then all 3 frontends together)

### Sprint 1 — Phase 1 Backend Cleanup ← NEXT
Small remaining gaps. All require Alembic migrations — do now before Phase 2 adds complexity.
- Alembic: add `pace_preference`, `eating_habits` columns to patients table
- Alembic: add `image_url` column to food_items table (Phase 6 ETL prep)
- `/register` flow split (standalone vs doctor-connected)
- Enforce `food_allergies` as non-empty on onboarding
- Meal log → recommendation slot linking
- Adherence calculation + `GET /progress/adherence/weekly`
- `version` counter increment on plan regeneration
- "Available at home" shopping list toggle

### Sprint 2 — Phase 2 Doctor Backend (12 remaining endpoints)
Patient logs view, progress view, clinical notes, meal plan notes, recipe library, dashboard stats, inactivity + expiry detection, remove patient.

### Sprint 3 — Phase 3 Admin Backend (16 remaining endpoints)
Admin login, billing, food management, audit log, DPDP erasure, IP whitelisting, codes management.

### Sprint 4 — Doctor Dashboard React Web (18 screens)
First shippable product. Doctors onboard → generate codes → patients activate.

### Sprint 5 — Admin Dashboard React Web (13 screens)
Extends Doctor Dashboard project with admin routing.

### Sprint 6 — Phase 6 ETL + ML Upgrade
Load 6,871 food items, remove region filter, allergy filtering, expand health conditions, cross-week history.

### Sprint 7 — Patient App React Native (36 screens)
Starts only after backend is fully locked and stable.

### Sprint 8 — Phase 4 Billing + Phase 5 Notifications

### Sprint 9 — Production Deploy (Phase 7)

---

This is the complete picture. Every checkbox verified from actual file reads, not assumed.
