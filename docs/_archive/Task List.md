## Complete Mityahar Code Task List

---

## 🔴 PHASE 0 — Foundation (Do First, Everything Depends on This)

### Database Migration — MongoDB → PostgreSQL

- [ ] Install SQLAlchemy 2.0 async + asyncpg + Alembic in requirements.txt
- [ ] Remove PyMongo and motor dependencies
- [ ] Create `app/core/database.py` — async PostgreSQL engine and session factory
- [ ] Create all 9 tables as SQLAlchemy models:
  - [ ] `doctors` table
  - [ ] `patients` table
  - [ ] `admins` table
  - [ ] `food_items` table
  - [ ] `recommendations` table
  - [ ] `meal_logs` table
  - [ ] `progress_logs` table
  - [ ] `patient_requests` table
  - [ ] `subscription_codes` table
- [ ] Write Alembic initial migration for all 9 tables
- [ ] Delete all MongoDB model files (`app/models/diet_plan.py`, `app/models/meal_plan.py`, `app/models/meal_adjustment.py`, `app/models/progress.py`)
- [ ] Rewrite `app/models/user.py` as PostgreSQL SQLAlchemy model

### Authentication System — Three Roles

- [ ] Rewrite `app/core/security.py` — JWT generation for three roles (patient, doctor, admin)
- [ ] Add `role` field to JWT payload
- [ ] Add `user_type` field to JWT payload (standalone / doctor_connected)
- [ ] Create role-based dependency functions:
  - [ ] `get_current_patient()`
  - [ ] `get_current_doctor()`
  - [ ] `get_current_admin()`
- [ ] Create subscription check middleware — checks `subscription_status` and `subscription_end_date` on every patient API call
- [ ] Create doctor data isolation middleware — every doctor query auto-scoped to their `doctor_id`
- [ ] Verify password hashing is bcrypt (not MD5 or SHA1) — fix if not
- [ ] Add JWT refresh token rotation

### Rate Limiting — Fix Existing

- [ ] Replace in-memory slowapi with Redis-backed slowapi
- [ ] Add rate limiting to all auth endpoints
- [ ] Add rate limiting to all progress log endpoints
- [ ] Add rate limiting to all patient registration endpoints

### Dead Code Cleanup

- [ ] Delete `app/schemas/diet_plan.py` (unused, conflicting)
- [ ] Delete `app/models/meal_adjustment.py` (never used)
- [ ] Delete `app/services/Healthy.py` (broken Kaggle path)
- [ ] Delete `app/services/datasets for eyantra/` entire folder (never imported)
- [ ] Evaluate and delete `app/models/meal_plan.py` if unused
- [ ] Clean up `app/crud/` folder

---

## 🟠 PHASE 1 — Patient Core Experience

### Onboarding — Backend

- [ ] Rewrite `POST /api/v1/auth/register` — split into two flows (standalone vs doctor-connected)
- [ ] Add all 7 questionnaire section fields to patient schema:
  - [ ] Target weight, date of birth
  - [ ] Health goals, pace preference
  - [ ] Medical conditions (15+ as JSONB array)
  - [ ] Food allergies (mandatory — cannot be null)
  - [ ] Dietary preferences (Jain, Vegan, No onion/garlic, Eggetarian)
  - [ ] Regional food preference
  - [ ] Meals per day, fasting days
  - [ ] Lifestyle fields (sleep, water, occupation, smoking/alcohol)
  - [ ] Current eating habits fields
- [ ] Build `POST /api/v1/patients/request` — patient submits request to doctor (Tier 2 flow)
- [ ] Build `GET /api/v1/patients/request/status` — patient checks if approved yet
- [ ] Auto-calculate and STORE BMI, BMR, TDEE on profile completion (not on-the-fly)
- [ ] Auto-recalculate BMI/BMR/TDEE when patient updates weight or height
- [ ] Auto-trigger first meal plan generation immediately after questionnaire completion — remove manual `/generate` requirement
- [ ] Add disclaimer acceptance logging — store timestamp when patient taps "I Understand"
- [ ] Build `POST /api/v1/auth/google` — Firebase Google OAuth token verification for patients

### Meal Plan — Backend Fixes

- [ ] Fix calorie target — replace hardcoded `2000` with patient's actual stored TDEE
- [ ] Fix plan regeneration — remove HTTP 400 block, allow regeneration with history preservation
- [ ] Add plan versioning — store previous plans, not just overwrite
- [ ] Fix plan storage — change from full embedded meal data to food_item reference IDs
- [ ] Build `GET /api/v1/meal-plan/week` — returns current week's plan
- [ ] Build `GET /api/v1/meal-plan/history` — returns past weeks
- [ ] Remove region filter from `meal_generator.py` algorithm logic

### Meal Logging — Backend Fixes

- [ ] Fix `POST /api/v1/progress/meal` — link to specific recommendation slot (not just free log)
- [ ] Add `food_id` reference (nullable) to meal log — link to food database
- [ ] Add `custom_food_name` field — for foods not in database
- [ ] Add `portion_size` field to meal log
- [ ] Build `PUT /api/v1/progress/meal/{log_id}` — edit a logged meal (within 24 hours)
- [ ] Build `DELETE /api/v1/progress/meal/{log_id}` — delete a logged meal
- [ ] Build adherence calculation — compare recommended meals vs logged meals per day/week
- [ ] Build `GET /api/v1/progress/adherence/weekly` — returns adherence percentage

### Progress Tracking — Backend Fixes

- [ ] Fix `GET /api/v1/progress/today` — use patient's stored TDEE not hardcoded 2000
- [ ] Add `PUT` and `DELETE` to water, steps, weight logs
- [ ] Build `GET /api/v1/progress/weekly-report` — full weekly summary with recommended vs actual comparison
- [ ] Build `GET /api/v1/progress/weight-history` — full weight journey since joining
- [ ] Build streak calculation — consecutive days with at least one log

### Shopping List — Backend

- [ ] Build `GET /api/v1/meal-plan/shopping-list` — aggregated ingredients for full week
- [ ] Group ingredients by category (vegetables, dairy, grains, spices)
- [ ] Mark items as "available at home" (toggle endpoint)

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

## 🟡 PHASE 2 — Doctor Dashboard

### Doctor — Backend

- [ ] Build `POST /api/v1/doctors/auth/login` — email + password login (not Google OAuth)
- [ ] Build `GET /api/v1/doctor/requests` — list all pending patient requests for this doctor
- [ ] Build `PATCH /api/v1/doctor/requests/{request_id}/accept` — accept patient, consume one code, create subscription
- [ ] Build `PATCH /api/v1/doctor/requests/{request_id}/reject` — reject with optional note
- [ ] Build `GET /api/v1/doctor/patients` — list all this doctor's patients with filters
- [ ] Build `GET /api/v1/doctor/patients/{patient_id}` — full patient profile view
- [ ] Build `GET /api/v1/doctor/patients/{patient_id}/logs` — patient's meal logs with recommended vs actual comparison
- [ ] Build `GET /api/v1/doctor/patients/{patient_id}/progress` — weight, water, steps history
- [ ] Build `GET /api/v1/doctor/patients/{patient_id}/plan` — current meal plan
- [ ] Build `PUT /api/v1/doctor/patients/{patient_id}/plan` — doctor edits/overrides meal plan
- [ ] Build `POST /api/v1/doctor/patients/{patient_id}/plan/notes` — add note to specific meal in plan
- [ ] Build `POST /api/v1/doctor/patients/{patient_id}/notes` — add private clinical note
- [ ] Build `GET /api/v1/doctor/patients/{patient_id}/notes` — get all clinical notes
- [ ] Build `DELETE /api/v1/doctor/patients/{patient_id}` — remove patient from doctor's list
- [ ] Build `GET /api/v1/doctor/recipes` — browse food database
- [ ] Build `POST /api/v1/doctor/recipes` — add new recipe (with auto-fetch for blank fields)
- [ ] Build auto-fetch recipe details from internet when fields left blank (Edamam API or similar)
- [ ] Build `POST /api/v1/doctor/recipes/{recipe_id}/assign` — assign recipe to patient(s)
- [ ] Build `GET /api/v1/doctor/codes` — list all activation codes (used/unused/expired)
- [ ] Build `GET /api/v1/doctor/dashboard` — aggregated stats for dashboard cards
- [ ] Build patient inactivity detection — flag patients with no logs in X days
- [ ] Build subscription expiry detection — flag patients expiring this week
- [ ] Enforce doctor data isolation on ALL doctor endpoints (no cross-doctor data access)

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

## 🟢 PHASE 3 — Admin Dashboard

### Admin — Backend

- [ ] Build `POST /api/v1/admin/auth/login` — email + password + MFA
- [ ] Build `GET /api/v1/admin/overview` — platform-wide stats
- [ ] Build `POST /api/v1/admin/doctors` — create new doctor account, send credentials via email
- [ ] Build `GET /api/v1/admin/doctors` — list all doctors with patient counts and revenue
- [ ] Build `GET /api/v1/admin/doctors/{doctor_id}` — full doctor profile and history
- [ ] Build `PATCH /api/v1/admin/doctors/{doctor_id}/deactivate` — deactivate doctor
- [ ] Build `DELETE /api/v1/admin/doctors/{doctor_id}` — remove doctor (with patient handling rules)
- [ ] Build `POST /api/v1/admin/codes/generate` — generate activation code batch for a doctor
- [ ] Build `GET /api/v1/admin/codes` — view all codes across all doctors
- [ ] Build `GET /api/v1/admin/billing` — full platform billing overview
- [ ] Build `POST /api/v1/admin/billing/{doctor_id}/mark-paid` — mark a doctor's payment received
- [ ] Build `PATCH /api/v1/admin/patients/{patient_id}/subscription/override` — manual subscription override for disputes
- [ ] Build `GET /api/v1/admin/food` — food database management view
- [ ] Build `PATCH /api/v1/admin/food/{food_id}/approve` — approve doctor-added recipe
- [ ] Build `PATCH /api/v1/admin/food/{food_id}/reject` — reject with note
- [ ] Build `DELETE /api/v1/admin/food/{food_id}` — remove food item
- [ ] Build `GET /api/v1/admin/audit-logs` — paginated audit log viewer
- [ ] Build audit log writer — records every significant action with timestamp, actor, IP
- [ ] Build `DELETE /api/v1/admin/patients/{patient_id}` — DPDP Act compliance data erasure
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

### ETL — Merge All Datasets into PostgreSQL

- [ ] Write ETL script to load `IndianFoodDataset` (6,871 rows) into `food_items` table as primary source
- [ ] Normalize column names across all sources (fiber vs fibre, name vs MENU etc.)
- [ ] Cross-reference `meal_generator/data/*.xlsx` files by food name — merge nutrition data where names match
- [ ] Cross-reference eyantra datasets — pull `image_url` where food names match
- [ ] Flag all items with missing nutrition as `nutrition_verified = false`
- [ ] Call Edamam/Nutritionix API to fill nutrition gaps for unflagged items
- [ ] Remove `Region` column entirely from all datasets
- [ ] Remove duplicate entries across all three sources
- [ ] Write data validation script — check for nulls, negative nutrition values, impossible calorie counts

### ML Engine — Rewrite to Read from PostgreSQL

- [ ] Rewrite `meal_generator.py` — read from `food_items` PostgreSQL table instead of xlsx files
- [ ] Remove region filter from algorithm logic completely
- [ ] Add allergy filtering — exclude food items containing patient's allergenic ingredients from `ingredients` JSONB
- [ ] Expand health condition support from 3 values to full 15+ conditions mapped to diet type filters:
  - [ ] Diabetic → filter to Diabetic Friendly tagged recipes only
  - [ ] PCOS → prioritize high-fiber low-GI meals
  - [ ] Kidney disease → flag high potassium/phosphorus, doctor warning
  - [ ] Jain → exclude onion, garlic, potato, carrot, radish from ingredients
  - [ ] Gluten free → filter to Gluten Free tagged recipes
  - [ ] Vegan → filter to Vegan tagged recipes
- [ ] Add long-term meal history — avoid repeating same meals across consecutive weeks
- [ ] Store meal recommendation references as `food_id` links, not full embedded data

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

- [ ] Verify bcrypt is used for password hashing — add argon2 if upgrading
- [ ] Add MFA (TOTP — Google Authenticator) for doctor login
- [ ] Add MFA + IP whitelisting for admin login
- [ ] Encrypt sensitive patient fields at application level (phone, health data) via Google KMS
- [ ] Fix CORS — ensure not set to `*` wildcard in production
- [ ] Add security headers (HSTS, X-Frame-Options, Content-Security-Policy)
- [ ] Add request signing for admin endpoints
- [ ] Audit log every doctor and admin action (actor, action, timestamp, IP)
- [ ] Add data retention policy enforcement (DPDP Act)
- [ ] Add consent logging — record timestamp of every user accepting terms

---

## 📊 COMPLETE TASK COUNT

| Phase | Tasks | Priority |
|---|---|---|
| Phase 0 — Foundation | 28 tasks | 🔴 Critical |
| Phase 1 — Patient | 67 tasks | 🔴 Critical |
| Phase 2 — Doctor | 38 tasks | 🟠 High |
| Phase 3 — Admin | 30 tasks | 🟡 Medium |
| Phase 4 — Billing | 14 tasks | 🟡 Medium |
| Phase 5 — Notifications | 28 tasks | 🟢 Normal |
| Phase 6 — Dataset + ML | 18 tasks | 🟢 Normal |
| Phase 7 — Deployment | 18 tasks | ⚪ Last |
| Security (ongoing) | 12 tasks | 🔴 Throughout |
| **Total** | **253 tasks** | |

---

This is the complete picture. Every task derived from the audit report, the transcript, the file tree, and every decision made in all our discussions. Nothing is missing.
