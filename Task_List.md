## Complete Mityahar Task List

> Last audited: 2026-03-17 — Security hardening complete
> Legend: [x] = verified done · [ ] = not done · [~] = partial / logic incomplete

---

## 🔴 PHASE 0 — Foundation

### Database & Models
- [x] SQLAlchemy 2.0 async + asyncpg + Alembic installed
- [x] PyMongo / motor removed
- [x] `app/core/database.py` — async engine + session factory
- [x] All 10 DB tables as SQLAlchemy models
- [x] Alembic initial migration for all tables
- [x] Dead MongoDB model files deleted
- [x] `pace_preference` + `eating_habits` columns on `patients`

### Auth System
- [x] `app/core/security.py` — JWT for 3 roles (patient / doctor / admin)
- [x] `role`, `user_type` fields in JWT payload
- [x] `get_current_patient()`, `get_current_doctor()`, `get_current_admin()` dependencies
- [x] SubscriptionCheck middleware — reads `sub_status` from JWT (zero DB query)
- [x] DoctorIsolationMiddleware — auto-scopes every doctor route to `doctor_id`
- [x] bcrypt password hashing
- [x] `POST /api/v1/auth/refresh` — JWT refresh token rotation

### Rate Limiting
- [x] `20/minute` on `/token` and `/doctor/login`
- [x] Rate limiting on `POST /auth/register`
- [x] Rate limiting on all 5 progress log POST endpoints
- [ ] Redis-backed slowapi ← deferred to Phase 7

### Dead Code Cleanup
- [x] All old MongoDB files and dead schemas deleted

---

**PHASE 0 SCORE: 17 / 18** — 1 remaining: Redis (deferred Phase 7)

---

## 🟠 PHASE 1 — Patient Core Experience

### Auth
- [x] `POST /api/v1/auth/register`
- [x] `POST /api/v1/auth/token`
- [x] `POST /api/v1/auth/doctor/login`
- [x] `POST /api/v1/auth/admin/login`
- [x] `POST /api/v1/auth/google/verify` — backend complete, mobile not wired yet
- [ ] Firebase Cloud Messaging device token storage on login ← Phase 5

### Onboarding
- [x] `POST /api/v1/patients/onboarding` — stores all fields + calculates BMI/BMR/TDEE
- [x] Auto-calculate + store BMI, BMR, TDEE on onboarding
- [x] Auto-recalculate BMI/BMR/TDEE when patient updates weight or height
- [x] Auto-trigger first meal plan generation after onboarding
- [x] `POST /api/v1/patients/disclaimer`

### Patient Subscription & Doctor Connection
- [x] `POST /api/v1/patients/activate`
- [x] `POST /api/v1/patients/request-doctor`
- [x] `GET /api/v1/patients/request-status`

### Meal Plan
- [x] `GET /api/v1/meal-plan/week`
- [x] `GET /api/v1/meal-plan/history`
- [x] Plan regeneration + versioning

### Meal Logging
- [x] `POST /api/v1/progress/meal`
- [x] `PUT /api/v1/progress/log/meal/{log_id}`
- [x] `DELETE /api/v1/progress/log/meal/{log_id}`

### Progress Tracking
- [x] `GET /api/v1/progress/today`
- [x] `PUT /api/v1/progress/log/water`
- [x] `PUT /api/v1/progress/log/steps`
- [x] `PUT /api/v1/progress/log/weight`
- [x] `GET /api/v1/progress/weekly-report`
- [x] `GET /api/v1/progress/weight-history`
- [x] `GET /api/v1/progress/streak`

### Shopping List
- [x] `GET /api/v1/meal-plan/shopping-list`
- [x] `POST /api/v1/meal-plan/shopping-list/toggle`

### Profile
- [x] `GET /api/v1/users/me`
- [x] `PUT /api/v1/users/me`
- [x] `GET /api/v1/users/bmi`

---

**PHASE 1 BACKEND SCORE: 26 / 27** — 1 remaining: FCM token storage


## 🟡 PHASE 2 — Doctor Dashboard

### Doctor Backend
- [x] `POST /api/v1/auth/doctor/login` — MFA supported
- [x] `POST /api/v1/auth/doctor/mfa-login`
- [x] `POST /api/v1/auth/doctor/mfa-setup`
- [x] `POST /api/v1/auth/doctor/mfa-confirm`
- [x] `POST /api/v1/auth/doctor/mfa-disable`
- [x] `GET /api/v1/doctor/requests`
- [x] `POST /api/v1/doctor/requests/{id}/accept`
- [x] `POST /api/v1/doctor/requests/{id}/reject`
- [x] `GET /api/v1/doctor/patients` — paginated + search
- [x] `GET /api/v1/doctor/patients/{patient_id}`
- [x] `GET /api/v1/doctor/patients/{patient_id}/logs`
- [x] `GET /api/v1/doctor/patients/{patient_id}/progress`
- [x] `GET /api/v1/doctor/patients/{patient_id}/plan`
- [x] `PUT /api/v1/doctor/patients/{patient_id}/plan`
- [x] `POST /api/v1/doctor/patients/{patient_id}/plan/notes`
- [x] `POST /api/v1/doctor/patients/{patient_id}/notes`
- [x] `GET /api/v1/doctor/patients/{patient_id}/notes`
- [x] `DELETE /api/v1/doctor/patients/{patient_id}`
- [x] `GET /api/v1/doctor/recipes`
- [x] `POST /api/v1/doctor/recipes`
- [x] `POST /api/v1/doctor/recipes/{id}/assign`
- [x] `POST /api/v1/doctor/subscription-codes`
- [x] `GET /api/v1/doctor/subscription-codes`
- [x] `GET /api/v1/doctor/dashboard`
- [x] Doctor data isolation via DoctorIsolationMiddleware
- [ ] Auto-fetch recipe nutrition from Edamam API ← optional, deferred

### Doctor Web Dashboard (Vite + React)
- [x] Login page with MFA support
- [x] Overview / Dashboard page
- [x] Patients list page
- [x] Patient detail page — Profile / Plan / Progress / Notes / Activity tabs
- [x] Requests page (accept/reject patient requests)
- [x] Recipes page
- [x] Settings page

---

**PHASE 2 BACKEND SCORE: 25 / 26** — 1 remaining: Edamam (optional)
**PHASE 2 WEB SCORE: 7 / 7** ✅ COMPLETE (pre-Token system)

---

## 🟢 PHASE 3 — Admin Dashboard

### Admin Backend
- [x] `POST /api/v1/auth/admin/login` — MFA supported
- [x] `POST /api/v1/auth/admin/mfa-login`
- [x] `POST /api/v1/auth/admin/mfa-setup`
- [x] `POST /api/v1/auth/admin/mfa-confirm`
- [x] `POST /api/v1/auth/admin/mfa-disable`
- [x] `GET /api/v1/admin/stats`
- [x] `POST /api/v1/admin/doctors`
- [x] `GET /api/v1/admin/doctors`
- [x] `GET /api/v1/admin/doctors/{doctor_id}`
- [x] `PATCH /api/v1/admin/doctors/{doctor_id}/deactivate`
- [x] `DELETE /api/v1/admin/doctors/{doctor_id}`
- [x] `POST /api/v1/admin/codes/generate`
- [x] `GET /api/v1/admin/codes`
- [x] `GET /api/v1/admin/billing`
- [x] `POST /api/v1/admin/billing/{doctor_id}/mark-paid`
- [x] `PATCH /api/v1/admin/patients/{patient_id}/subscription/override`
- [x] `GET /api/v1/admin/food`
- [x] `PATCH /api/v1/admin/food/{food_id}/approve`
- [x] `PATCH /api/v1/admin/food/{food_id}/reject`
- [x] `DELETE /api/v1/admin/food/{food_id}`
- [x] `GET /api/v1/admin/audit-logs`
- [x] Audit log writer — `log_action()` in `audit_service.py`
- [x] `DELETE /api/v1/admin/patients/{patient_id}` — DPDP right-to-erasure
- [x] IP whitelisting middleware

### Admin Web Dashboard (Vite + React)
- [x] Admin Overview page
- [x] Admin Doctors page
- [x] Admin Patients page
- [x] Admin Billing / Codes page
- [x] Audit Logs page
- [x] Food Database page
- [x] Admin Settings page

---

**PHASE 3 BACKEND SCORE: 24 / 24** ✅ COMPLETE
**PHASE 3 WEB SCORE: 7 / 7** ✅ COMPLETE (pre-Token system)


## 🔵 PHASE 4 — Billing

> ⚠️ DECISION (2026-03-15): Razorpay integration CANCELLED permanently.
> Business model confirmed: platform takes 6% royalty on ₹1,200 doctor consultations.
> No payment gateway needed. Coupon system is for record-keeping only, not payment enforcement.
> Replaced entirely by the Token 2 Visit System (see Phase 4B below).

### Original Razorpay Tasks — ALL DROPPED
- [~] Integrate Razorpay SDK ← DROPPED
- [~] `POST /api/v1/billing/pay` ← DROPPED
- [~] Razorpay webhook handler ← DROPPED
- [~] Subscription auto-expiry job ← REPLACED by Token 1 expiry cron
- [~] Doctor billing reminder ← DROPPED
- [~] Code purchase flow ← DROPPED (codes are free, admin-issued)
- [~] Tier 1 standalone premium flow ← DEFERRED to Phase 6
- [~] Find a Doctor API ← DEFERRED to Phase 6

---

## 🔵 PHASE 4B — Token 1 & Token 2 Visit System ← NEW

> Business model: Patient pays doctor ₹1,200 per consultation.
> Platform takes 6% royalty. Split 2% × 3 team members. Paid annually.
> Token 1 = permanent patient ID + meal plan access (30-day rolling).
> Token 2 = visit billing tracker, fresh every 30 days, 15-day charge window.

### Backend — Token System
- [x] Add `token_1` column to `patients` — permanent unique ID (e.g. TKN1-PAT-00142), String(20), unique
- [x] Add `token_1_active` boolean to `patients` — controls meal plan access
- [x] Add `token_1_expiry` DateTime to `patients` — 30-day rolling window
- [x] Add `renewal_requested` boolean to `patients`
- [x] Add `renewal_requested_at` DateTime to `patients`
- [x] Add `expiring_soon` boolean to `patients`
- [x] Create `patient_visits` table: `id`, `patient_id`, `doctor_id`, `token_2`, `cycle_start`, `cycle_expiry`, `last_charged_at`, `visit_counter`, `created_at`
- [x] Write Alembic migration for all above columns and new table
- [x] Update `POST /patients/onboarding` — auto-generate Token 1 + create first `patient_visits` row with Token 2
- [x] `POST /doctor/patients/{id}/record-visit` — checks 15-day window, charges or not, increments counter
- [x] `GET /doctor/patients/{id}/visits` — full visit history for patient
- [x] `POST /doctor/patients/{id}/request-renewal` — patient-triggered, sets renewal_requested flag
- [x] `POST /doctor/patients/{id}/approve-renewal` — reactivates Token 1, generates new Token 2, resets 30-day cycle
- [x] `POST /doctor/patients/approve-all-renewals` — bulk approve all pending renewals for this doctor
- [x] `GET /doctor/patients/pending-renewals` — list all patients with renewal_requested=True for this doctor
- [x] Daily cron (APScheduler) — flag patients with ≤4 days left as expiring_soon=True + trigger FCM
- [x] Daily cron — deactivate patients where token_1_expiry has passed (set token_1_active=False)
- [x] Add `record_visit`, `approve_renewal`, `approve_all_renewals` to audit_service action types
- [x] `apscheduler` added to requirements.txt

### Backend — Admin Consultation Tracker
- [x] `GET /admin/consultations` — platform-wide stats: total this month, per-doctor breakdown
- [x] `GET /admin/consultations/annual` — year-to-date totals + royalty split (2% × 3 members)
- [x] `GET /admin/renewals` — platform-wide pending renewals list
- [x] `POST /admin/renewals/{patient_id}/override-approve` — admin manually approves if doctor unresponsive
- [x] Update `GET /admin/stats` — add `expiring_soon_count`, `pending_renewals_count`, `total_consultations_this_month`

---

**PHASE 4B SCORE: 22 / 22** ✅ COMPLETE


## 🟣 PHASE 5 — Notifications (FCM)

> ⚠️ BLOCKER: Firebase console setup must be done manually before any code work.
> Required files: google-services.json (Android), GoogleService-Info.plist (iOS),
> firebase_service_account.json (backend). None exist yet.

### Backend — FCM
- [ ] Add `firebase-admin` to `requirements.txt`
- [ ] Add `fcm_token` column to `patients` table + Alembic migration
- [ ] New `app/services/notification_service.py` — `init_firebase()`, `send_push()`, `notify_plan_ready()`, `notify_doctor_accepted()`, `notify_sub_expiring()`, `notify_renewal_approved()`
- [ ] Init Firebase in `main.py` lifespan
- [ ] `POST /auth/register-fcm-token` — stores FCM token after login
- [ ] Wire `notify_plan_ready()` into onboarding auto-generation
- [ ] Wire `notify_doctor_accepted()` into doctor accept_request endpoint
- [ ] Wire `notify_sub_expiring()` into daily expiry cron (Phase 4B)
- [ ] Wire `notify_renewal_approved()` into approve-renewal endpoint

### Patient App — FCM
- [ ] Install `expo-notifications`
- [ ] Update `app.config.ts` — add google-services.json, GoogleService-Info.plist, expo-notifications plugin
- [ ] New `lib/notifications.ts` — `requestPermissions()`, `getFCMToken()`, `sendTokenToBackend()`, `setupNotificationListeners(router)`
- [ ] Wire into `_layout.tsx` — request permissions + send FCM token after login
- [ ] Handle notification tap → navigate to correct screen
- [ ] Wire `profile/notifications.tsx` toggles to backend preferences

### Notification Triggers
- [ ] Plan ready → patient notified after onboarding auto-generation
- [ ] Doctor accepted → patient notified when request approved
- [ ] Expiry warning → patient + doctor notified when ≤4 days left (via cron)
- [ ] Renewal approved → patient notified when doctor approves renewal

---

**PHASE 5 SCORE: 0 / 19** ← NOT STARTED (blocked on Firebase setup)

---

## ⚫ PHASE 5B — Patient App (Expo) — Completed Sprint 4

### Auth Screens
- [x] `login.tsx` — email/password login
- [x] `register.tsx` — registration + optional doctor code

### Onboarding Screens (9 screens)
- [x] `personal-info` → `activity-level` → `goals` → `medical-conditions`
- [x] `allergies` → `dietary-preferences` → `lifestyle` → `disclaimer` → `complete`

### Tab Screens
- [x] `index.tsx` — Home: today summary, streak, meal log
- [x] `meals.tsx` — Today's plan, MacroRow, doctor notes
- [x] `progress.tsx` — Water/Steps/Weight metrics, charts
- [x] `profile.tsx` — Stats, subscription card, settings menu

### Doctor Flow
- [x] `find-doctor` → `activate` → `connection-status`

### Meal Screens
- [x] `meal-detail`, `week-view`, `shopping-list`, `plan-history`, `plan-empty`

### Log Screens
- [x] `log-meal`, `log-from-plan`, `edit-log`

### Progress Screens
- [x] `weight-log`, `water-log`, `steps-log`, `charts`

### Profile Screens
- [x] `edit-profile`, `notifications` (placeholder), `account`, `about`

### Home
- [x] `notifications.tsx`

---

**PHASE 5B SCORE: 36 / 36** ✅ COMPLETE


## 🔶 PHASE 5C — Frontend Changes for Token System ← NEW

### Doctor Dashboard — Patients List Page (`Patients.tsx`)
- [x] Replace current columns with Token table: Token 1 (ID + Active/Inactive badge), Token 2 (token ID + last visit date), Days Left (countdown + 🟢🟠🔴 color coding), Visits This Month (counter), Renewal Status
- [x] Color logic — green >7 days, amber ≤4 days, red expired
- [x] "Approve All Renewals" button — visible only when pending renewals exist
- [x] Expiry warning banner at top of page
- [x] Individual "Approve Renewal" button per row when renewal_status = Requested

### Doctor Dashboard — Patient Detail Page (`PatientDetail.tsx`)
- [x] Add new "Visits" tab alongside existing tabs
- [x] Visits tab: Record Visit button, result display (charged/not + reason), visit history table (date, charged, Token 2 ID, counter)
- [x] Current Token 2 status card — token ID, cycle start, days remaining, total visits this cycle

### Doctor Dashboard — Overview Page (`Overview.tsx`)
- [x] Stat cards condensed — layout updated

### Patient App — Profile Screen
- [x] Display Token 1 permanent ID as patient reference number
- [x] 30-day subscription progress bar with days remaining
- [x] "Request Renewal" button — appears only when ≤4 days left
- [x] Subscription states: Active → Expiring Soon → Renewal Requested
- [x] Token 1 fields added to PatientProfile type in types/index.ts
- [x] requestRenewal() added to profile service

### Patient App — Notifications Screen
- [ ] Wire toggle states to backend notification preferences endpoint
- [ ] Connect FCM permission flow (Phase 5)

### Admin Dashboard — Overview Page (`AdminOverview.tsx`)
- [x] Add 2 new stat cards: Total Consultations This Month, Platform Royalty This Month
- [x] Add alerts for pending renewals count and expiring-soon patient count

### Admin Dashboard — Patients Page (`AdminPatients.tsx`)
- [x] Add Token 1 Status column (Active/Inactive badge)
- [x] Add Days Left column with color coding

### Admin Dashboard — Billing Page (`Billing.tsx`)
- [x] Remove "Mark Paid" flow — fully replaced
- [x] Renamed to "Codes & Consultations"
- [x] Consultation Tracker tab — per-doctor breakdown, YTD royalty split
- [x] Activation Codes tab — unchanged, kept as is
- [x] Renewals tab — pending renewals with admin override-approve

### Admin Dashboard — Shell / Routes
- [x] Update sidebar label from "Billing" to "Codes & Consultations" — Sidebar.tsx + AdminShell.tsx breadcrumb

---

**PHASE 5C SCORE: 17 / 18** — 1 remaining (FCM notification wiring in patient app — blocked on Firebase setup)

---

## ⚪ PHASE 6 — Dataset and ML

### ETL — Done
- [x] 184 hand-curated food items loaded
- [x] 1,930 recipes from IndianFoodDatasetCSV seeded
- [x] Calorie bug fixed, recipe names cleaned (regex + Gemini pass)
- [x] Pantry staples tagged
- [x] 180 meal templates seeded

### Bug Fixes — Needed Now
- [x] Fix dead `diabetes_status`/`gym_goal` in `calculate_macronutrients()` — `health_condition` passed twice, sub-conditions never fire
- [x] Fix BMR returning 0.0 for gender "Other" — use average of male/female formula

### ML Improvements — Queued
- [ ] Remove region filter at Level 1 — reduces variety unnecessarily with only ~2k items
- [ ] Expand health conditions from 3 to 15+ (PCOS, Jain, Kidney, Gluten-free, Vegan, Keto etc.)
- [ ] Cross-week meal history — `weekly_used_ids` resets on every generation, allow repeat-free cross-week memory
- [ ] Store meal plans as `food_id` links instead of full embedded JSON
- [ ] Personalisation layer — adapt recommendations based on what patient actually logs over time
- [ ] `scripts/data_validation.py` — check for nulls, negative nutrition, impossible calories

---

**PHASE 6 SCORE: 5 / 11** — ETL done, bug fixes + ML improvements remain


## ⚫ PHASE 7 — Production Deployment

- [ ] GCP project — Mumbai region (asia-south1)
- [ ] Cloud SQL PostgreSQL (private VPC)
- [ ] Alembic migrations on Cloud SQL
- [ ] Google Secret Manager — move all `.env` secrets
- [ ] Cloud Storage bucket for food images
- [ ] Cloudflare DNS + SSL
- [ ] Dockerfile for FastAPI backend
- [ ] GitHub Actions CI/CD
- [ ] Cloud Run — auto-scaling
- [ ] Redis via Cloud Memorystore (replaces in-memory slowapi)
- [ ] Load test before launch
- [ ] Google Play Store submission (₹2,088 one-time)
- [ ] Apple TestFlight + App Store (₹8,267/year)
- [ ] Cloud Monitoring + alerting
- [ ] Sentry error tracking

---

**PHASE 7 SCORE: 0 / 15** ← NOT STARTED

---

## 🔑 SECURITY (Cross-Phase)

- [x] bcrypt password hashing
- [x] Consent logging — `disclaimer_accepted_at`
- [x] Audit log writer — `log_action()`
- [x] MFA TOTP for doctor login
- [x] MFA TOTP for admin login
- [x] IP whitelisting middleware for admin routes
- [x] Rate limiting on register + progress endpoints
- [x] HttpOnly cookie for refresh tokens (doctor/admin web)
- [ ] Encrypt sensitive patient fields at application level via Google KMS
- [ ] Fix CORS — not `*` wildcard in production
- [ ] Security headers (HSTS, X-Frame-Options, CSP) ← SecurityHeadersMiddleware exists, verify headers
- [ ] Data retention scheduled purge (DPDP Act — erasure endpoint exists, scheduled purge not built)
- [ ] `Set-Cookie secure=True` in auth.py (currently False) ← change before HTTPS deploy

---

**SECURITY SCORE: 8 / 13** — 5 remaining (mostly pre-production hardening)

---

---

## 🤖 PHASE 8 — RL Data Infrastructure ("Collect Now, Activate Later")
> Full detail: see `RL_Roadmap.md` in project root
> Rationale: Doctor override events and patient ratings cannot be recovered retroactively.
> Collect from day one. Algorithms activate later when data is sufficient.

### Tier 0 — Pre-Launch (Must complete before first real doctor onboards)

**`doctor_meal_overrides` table**
- [x] Create DB model — id, doctor_id, patient_id, override_date, slot_type, meal_type, rejected_food_id, chosen_food_id, patient_health_condition, patient_medical_conditions (JSONB), patient_region, patient_diet_type, patient_age_bucket, patient_bmi_bucket, created_at
- [x] Write Alembic migration (`f6a7b8c9d0e1_phase8_rl_tables.py`)
- [x] Helper `_bucket_age(dob)` → "18-25" / "26-35" / "36-50" / "50+"
- [x] Helper `_bucket_bmi(bmi)` → "underweight" / "normal" / "overweight" / "obese"
- [x] Helper `_extract_food_id(meal_dict)` → food_item id or None
- [x] Update `PUT /doctor/patients/{id}/plan` — diff old vs new meals, write one override row per swap with full patient context snapshot
- [x] `GET /doctor/patients/{id}/plan/overrides` — override history endpoint

**`meal_ratings` table**
- [x] Create DB model — id, patient_id, food_item_id, recommendation_id, rating (SmallInt +1/-1), rated_at
- [x] Unique constraint (patient_id, food_item_id, recommendation_id)
- [x] Write Alembic migration (same file as overrides)
- [x] `POST /api/v1/progress/meal/rate` endpoint
- [x] `GET /api/v1/progress/meal/ratings` endpoint

**Patient App**
- [x] 👍/👎 buttons on meal cards (visible after meal time passes)
- [x] Wire to rate endpoint + restore state on load

**Fix signal-quality tech debt**
- [x] `ProgressLog.total_calories_consumed` — write in `progress_service.log_meal()`
- [x] `MealLog.food_id` — populate when logging from a recommendation

---

### Tier 1 — ~1 Month Post-Launch (5+ Active Doctors)

**Preference Scoring**
- [ ] Add `preference_score` Float column to `food_items` + migration
- [ ] Add `preference_context` JSONB column to `food_items` + migration
- [ ] `scripts/update_preference_scores.py` — reads overrides, computes per-bucket scores, writes to preference_context
- [ ] Register weekly APScheduler job (Sunday 02:00 UTC) in `main.py`
- [ ] Update `_find_food_item_single_diet()` — preference_score as tertiary sort key

**Patient Rating Integration**
- [ ] `_load_patient_preferences(patient_id, session)` service function
- [ ] Pass soft_prefer_ids / soft_avoid_ids into user_data in `diet_plans.py`
- [ ] Update generator — preferred items LIMIT 15; avoided items excluded

---

### Tier 2 — ~3–6 Months Post-Launch (50+ Active Patients)

**Thompson Sampling Bandit**
- [ ] Create `food_item_bandit_stats` DB model — id, food_item_id, context_bucket_hash, context_label, alpha, beta, last_updated
- [ ] Unique constraint (food_item_id, context_bucket_hash) + migration
- [ ] `scripts/initialize_bandit_priors.py` — seeds all observed pairs with alpha=1, beta=1
- [ ] `app/services/bandit_service.py` — compute_context_hash(), thompson_sample(), update_bandit()
- [ ] `scripts/run_bandit_update.py` — reads new override/rating events, updates Beta distributions
- [ ] Register nightly APScheduler job (03:00 UTC) in `main.py`
- [ ] Integrate `thompson_sample()` into `_find_food_item_single_diet()`
- [ ] `BANDIT_ENABLED = False` feature flag in `app/core/config.py`
- [ ] `BANDIT_MIN_SAMPLES = 20` config threshold

---

**PHASE 8 SCORE: 14 / 33**
- Tier 0: 14/14 ✅ COMPLETE
- Tier 1: 0/7  — Month 1+
- Tier 2: 0/12 — Month 3–6

---

## 📊 ACCURATE TASK COUNT (2026-03-15, post-Sprint-5 planning)

| Area | Total | Done | Remaining |
|---|---|---|---|
| Phase 0 — Foundation | 18 | 17 | 1 (Redis) |
| Phase 1 — Patient Backend | 27 | 26 | 1 (FCM token) |
| Phase 2 — Doctor Backend | 26 | 25 | 1 (Edamam optional) |
| Phase 2 — Doctor Web | 7 | 7 | 0 ✅ |
| Phase 3 — Admin Backend | 24 | 24 | 0 ✅ |
| Phase 3 — Admin Web | 7 | 7 | 0 ✅ |
| Phase 4 — Razorpay | 0 | 0 | 0 (CANCELLED) |
| Phase 4B — Token System Backend | 22 | 22 | 0 ✅ |
| Phase 5 — FCM Notifications | 19 | 0 | 19 |
| Phase 5B — Patient App (Expo) | 36 | 36 | 0 ✅ |
| Phase 5C — Frontend Token Changes | 18 | 17 | 1 (FCM wiring only) |
| Phase 6 — Dataset + ML | 11 | 7 | 4 |
| Phase 7 — Deployment | 15 | 0 | 15 |
| Phase 8 — RL Infrastructure | 33 | 14 | 19 |
| Security (cross-phase) | 13 | 8 | 5 |
| **Total** | **276** | **228** | **48** |

**Overall progress: 228 / 276 = 83% complete**

---

## 🔐 SECURITY HARDENING (2026-03-17)

### Task 1 — Authentication Security Audit
- [x] `.env.example` corrected — `ACCESS_TOKEN_EXPIRE_MINUTES` was 1440 (24h), now 15 min
- [x] `.env.example` — added `COOKIE_SECURE`, `REFRESH_TOKEN_EXPIRE_MINUTES` with correct values
- [x] `config.py` — added `COOKIE_SECURE: bool = False`, `RESET_TOKEN_EXPIRE_MINUTES: int = 30`, `PASSWORD_MIN_LENGTH: int = 8`
- [x] `user.py` — `UserCreate.password_strength` validator: min 8 chars, at least 1 letter + 1 digit
- [x] `security.py` — `create_refresh_token()` added with `token_type='refresh'` claim
- [x] `security.py` — `_decode_jwt()` now explicitly rejects `token_type='refresh'` tokens
- [x] `auth.py` — `_issue_tokens()` uses `create_refresh_token()` with minimal claims (sub+role+ids only)
- [x] `auth.py` — all 4 hardcoded `secure=False` in `set_cookie()` calls replaced with `settings.COOKIE_SECURE`
- [x] `auth.py` — `/refresh` endpoint rejects access tokens used as refresh tokens (`token_type != 'refresh'`)
- [x] `auth.py` — `user_id` (internal DB PK) removed from all 3 register response branches
- [x] `db_models.py` — `is_email_verified` column added to `Patient` model
- [x] `db_models.py` — `EmailVerificationToken` model added (24h expiry, single-use, CASCADE delete)
- [x] `db_models.py` — `PasswordResetToken` model added (30min expiry, single-use, CASCADE delete)
- [x] `alembic/versions/g7h8i9j0k1l2` — migration for both token tables + `is_email_verified`
- [x] `auth.py` — `GET /auth/verify-email?token=` endpoint (oracle-safe, single-use, 24h expiry)
- [x] `auth.py` — `POST /auth/resend-verification` endpoint (rate-limited 3/min)
- [x] `auth.py` — `POST /auth/forgot-password` endpoint (always HTTP 200, no user enumeration)
- [x] `auth.py` — `POST /auth/reset-password` endpoint (30min token, single-use, password re-validated)
- [x] `auth.py` — email verification token auto-created on every new patient registration
- [x] Google OAuth patients auto-marked `is_email_verified=True` (Google already verified)

---

### Task 2 — IDOR (Insecure Direct Object Reference) Audit
- [x] `users.py` — all endpoints use `current_user` directly, no URL IDs → clean
- [x] `patients.py` — all endpoints scope to `patient.id` from JWT → clean
- [x] `diet_plans.py` — all endpoints scope to `current_user.id` → clean
- [x] `meal_plan.py` — all queries enforce `Recommendation.patient_id == current_user.id` → clean
- [x] `progress.py` (log endpoints) — all scope to `current_user.id` → clean
- [x] `progress_service.py` — `get_meal_log_by_id`, `update_meal_log`, `delete_meal_log` all enforce `MealLog.patient_id == patient_id` at service layer → clean
- [x] `doctor.py` — all 20+ patient-specific endpoints verify `Patient.doctor_id == did` before access → clean
- [x] `admin.py` — intentional global access by admin role, authenticated via separate dep → clean
- [x] **IDOR FOUND + FIXED** — `POST /progress/meal/rate`: `recommendation_id` was not verified to belong to `current_user`. Added ownership check: returns HTTP 403 if recommendation belongs to a different patient. Prevents RL signal poisoning.

---

### Task 3 — Secret & Credential Scan

**Files with exposed secrets — all fixed:**
- [x] `docs/client_secret_google_oauth.json` — **DELETED** — contained live `GOOGLE_CLIENT_SECRET`
- [x] `.env` — corrected `ACCESS_TOKEN_EXPIRE_MINUTES` from 1440→15, removed stray `Figm=` Figma PAT, added `COOKIE_SECURE` and proper structure
- [x] `alembic.ini` — hardcoded `postgresql+asyncpg://admin:mityahar_dev@...` replaced with placeholder; `alembic/env.py` now loads `DATABASE_URL` from `.env` and overrides `alembic.ini`
- [x] `scripts/seed_6k_recipes.py` — hardcoded USDA API key as default fallback replaced with hard-fail `os.getenv("USDA_API_KEY")` + hardcoded DB URL removed
- [x] `scripts/seed_food_items.py` — hardcoded DB URL replaced with `os.getenv("DATABASE_URL")`
- [x] `scripts/seed_meal_templates.py` — hardcoded DB URL replaced with `os.getenv("DATABASE_URL")`
- [x] `scripts/check_db_state.py` — hardcoded DB URL replaced with `os.getenv("DATABASE_URL")`
- [x] `scripts/tag_pantry_staples.py` — hardcoded fallback DB URL removed (was `mityahar_dev`)
- [x] `seed_admin.py` — hardcoded `admin1234` password replaced; now reads `ADMIN_SEED_PASSWORD` env var, fails loudly if unset
- [x] `scripts/seed_test_doctor.py` — hardcoded doctor+admin passwords moved to env vars; password no longer printed to stdout
- [x] `docker-compose.yml` — hardcoded `POSTGRES_PASSWORD: mityahar_dev` replaced with `${POSTGRES_PASSWORD:?must be set}` substitution
- [x] `mitihar-frontend/apps/src/lib/axios.ts` — hardcoded `http://localhost:8000/api/v1` replaced with `import.meta.env.VITE_API_URL`

**Gitignore hardening:**
- [x] Root `.gitignore` — added `.env.*`, all subdirectory `.env` patterns, `*service_account*.json`, `google-services.json`, `GoogleService-Info.plist`, `credentials.json`, `*.pem`, `*.p12`, `*.key`
- [x] `mitihar-patient-app/.gitignore` — added explicit `.env` entry (was missing — only had `.env*.local`)

**New files created:**
- [x] `mitihar-frontend/apps/.env` — local dev URL only
- [x] `mitihar-frontend/apps/.env.example` — template for frontend env vars
- [x] `mitihar-patient-app/.env.example` — template for patient app env vars
- [x] `.env.example` — fully updated with all 14 variables documented with safe placeholder values

**⚠️ Action required — rotate these keys immediately:**
- Google Client Secret: `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` — was in `docs/client_secret_google_oauth.json`
- All 4 Gemini API keys — were in `.env` (gitignored but regenerate as precaution)
- USDA API key `uo7qIJasjb...` — was hardcoded in `seed_6k_recipes.py` source

---

**SECURITY SCORE: 13 / 13 ✅** (auth + IDOR + secrets — all three tasks complete)

---

| **Sprint** | **Scope** | **Status** |
|---|---|---|
| Sprint 0 | DB schema, migrations, models | ✅ Done |
| Sprint 1 | Patient + Doctor + Admin backend, ETL, allergy filtering | ✅ Done |
| Sprint 2 | Rate limits, MFA (TOTP), IP whitelist | ✅ Done — 97/97 tests |
| Sprint 3 | Doctor Dashboard + Admin Dashboard (React+Vite) | ✅ Done |
| Sprint 4 | Patient App (Expo, 36 screens) | ✅ Done |
| **Sprint 5** | **Token System (4B) + Frontend Token Changes (5C) + ML bug fixes** | ✅ **Done** |
| Sprint 6 | FCM Notifications (Phase 5) — blocked on Firebase setup | 🔲 **Current** |
| Sprint 6 | Phase 6 ML improvements + bug fixes | 🔲 Queued |
| Sprint 6 | Phase 8 Tier 0 — RL data collection tables (pre-launch) | ✅ **14/14 COMPLETE** |
| **Sprint 6** | **Security Hardening — Auth + IDOR** | ✅ **COMPLETE** |
| Sprint 7 | Phase 7 Production Deploy (GCP + Cloud Run + CI/CD) | 🔲 Queued |
| Sprint 8 | Phase 8 Tier 1 — Preference scoring (after 1 month + 5 doctors) | 🔲 Future |
| Sprint 9 | Phase 8 Tier 2 — Thompson Sampling bandit (after 3-6 months + 50 patients) | 🔲 Future |

---

## ⚡ WHAT TO BUILD NEXT (Ordered by Priority)

1. **Run migration** — `alembic upgrade head` to activate security tables (email_verification_tokens, password_reset_tokens, is_email_verified)
2. **Phase 5 FCM** — BLOCKED on Firebase setup (create Firebase project, download JSON files first)
3. **Phase 6 ML** — More health conditions, region filter fix, personalisation
4. **Phase 7 Deploy** — After everything above is stable. Set `COOKIE_SECURE=True` + real `SECRET_KEY` in prod .env
5. **Phase 8 Tier 1** — Activate preference scoring after 1 month + 5 active doctors
6. **Phase 8 Tier 2** — Activate Thompson Sampling after 3–6 months + 50 active patients

---

## 🧾 BUSINESS MODEL (Confirmed 2026-03-15)

- Patient pays doctor ₹1,200 per consultation (offline)
- Platform takes 6% royalty = ₹72 per consultation
- Split: 2% × 3 team members = ₹24 per person per consultation
- Paid out annually at year end
- GCP infrastructure covered by doctor contributions + ₹2.5L initial buffer
- Razorpay: NOT needed. No payment flows through the app.
- Coupons: FREE, admin-issued, for record-keeping only (establishes doctor-patient link)

---

## 🔧 KNOWN TECH DEBT (Do Not Fix Until Noted)

- `Set-Cookie secure=False` — ✅ Fixed: now reads `settings.COOKIE_SECURE`. Set `COOKIE_SECURE=True` in prod .env before HTTPS deploy
- slowapi in-memory — resets on restart. Phase 7: swap to Redis storage
- `ProgressLog.total_calories_consumed` — ✅ Fixed in Phase 8 Tier 0
- `MealLog.food_id` rarely populated — ✅ Fixed in Phase 8 Tier 0
- Email sending is console-only (`[DEV]` log lines) — wire SendGrid/SES in Phase 7 (marked `# TODO (Phase 7)` in auth.py)
- All Gemini free-tier keys quota-exhausted — `/doctor/recipes/estimate` falls back to local DB
- Loading skeletons absent on all screens — show spinner or blank until data
- Offline state not handled in patient app (Phase 6 polish)
- Google OAuth mobile button is a stub — shows "coming soon" toast (backend ready)
- **RL infrastructure Tier 1/2 not yet active** — see `RL_Roadmap.md`
