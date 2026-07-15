# Mitihar API Audit Report

Date: 2026-04-30  
Auditor: Claude Code — read-only  
Model: claude-sonnet-4-6  
Branch: feature/api-remediation-v0.2

---

## Executive Summary

| Layer | Status | Summary |
|-------|--------|---------|
| Auth | ✅ Healthy | JWT role enforcement solid; bcrypt truncation fixed; MFA available for doctor/admin; lockout implemented; refresh tokens structurally distinct from access tokens |
| Routes | ⚠️ Warnings | All 9 routers have auth dependencies; two unprotected surface areas and one deprecated Gemini model version flagged |
| Middleware | ⚠️ Warning | Stack order correct and zero-DB for sub-check/isolation; one fail-open behavior in admin IP whitelist |
| Meal Pipeline | ✅ Healthy | Generator queries PostgreSQL exclusively; no file-based loading; markdown dataset files are documentation only |
| Fire-and-Forget | ℹ️ Info | Firebase silently disabled if credentials missing (by design); audit log misleadingly labeled "fire-and-forget" but is actually awaited |

---

## Phase 1 — Route Inventory

`get_current_user` is an alias for `get_current_patient` (`app/services/user_service.py:27`). All "patient" routes effectively enforce `get_current_patient`.

### Auth (`/api/v1/auth`)

| Method | Path | Auth Dependency | Request Schema | Response Schema | Notes |
|--------|------|-----------------|----------------|-----------------|-------|
| POST | /register | **None (public)** | `UserCreate` | `dict` | Rate-limited 3/hour; GDPR + age-18 check |
| POST | /token | **None (public)** | `OAuth2PasswordRequestForm` | `{access_token, refresh_token}` | Patient login; rate-limited 5/15min |
| POST | /admin/login | **None (public)** | `OAuth2PasswordRequestForm` | `{access_token}` or partial MFA | Rate-limited 10/min |
| POST | /admin/mfa-login | **None (public)** | `MFALoginRequest` | `{access_token, refresh_token}` | Step-2 of admin MFA |
| POST | /admin/mfa-setup | `get_current_admin` | None | `{totp_uri}` | Stores secret, not yet enabled |
| POST | /admin/mfa-confirm | `get_current_admin` | `MFAConfirmRequest` | msg | Sets `mfa_enabled=True` |
| POST | /admin/mfa-disable | `get_current_admin` | `MFAConfirmRequest` | msg | Requires valid TOTP code |
| POST | /doctor/login | **None (public)** | `OAuth2PasswordRequestForm` | `{access_token}` or partial MFA | Rate-limited 10/min |
| POST | /doctor/mfa-login | **None (public)** | `MFALoginRequest` | `{access_token, refresh_token}` | Step-2 of doctor MFA |
| POST | /doctor/mfa-setup | `get_current_doctor` | None | `{totp_uri}` | |
| POST | /doctor/mfa-confirm | `get_current_doctor` | `MFAConfirmRequest` | msg | |
| POST | /doctor/mfa-disable | `get_current_doctor` | `MFAConfirmRequest` | msg | |
| POST | /refresh | **None (public)** | optional body `{refresh_token}` | `{access_token}` | Cookie-first; body fallback for mobile |
| POST | /logout | **None (by design)** | None | msg | See Note 1 below |
| POST | /google/verify | **None (public)** | `GoogleTokenRequest` | `{access_token, ...}` | Rate-limited 20/min; GDPR gate on new users |
| GET | /verify-email | **None (public)** | `?token=` | msg | One-time token link |
| POST | /resend-verification | `get_current_patient` | None | msg | Rate-limited 3/min |
| POST | /forgot-password | **None (public)** | `ForgotPasswordRequest` | msg | Always HTTP 200 (anti-enumeration) |
| POST | /reset-password | **None (public)** | `ResetPasswordRequest` | msg | Single-use token; 30-min expiry |
| POST | /register-fcm-token | `get_current_patient` | `FCMTokenRequest` | msg | Clears token if body is null |

**Note 1 — /logout has no auth dependency by design** (`auth.py:890`). It reads the Authorization header manually to identify the actor, then deletes the cookie. Any unauthenticated request returns HTTP 200 "Logged out successfully". This is intentional (handles expired access tokens) but means the endpoint leaks no information and cannot be misused beyond wasting an audit log entry.

### Users (`/api/v1/users`)

| Method | Path | Auth Dependency | Request Schema | Notes |
|--------|------|-----------------|----------------|-------|
| GET | /me | `get_current_user` | None | Rate-limited 100/min |
| GET | /bmi | `get_current_user` | None | **NOT subscription-gated** (see Risk R-2) |
| PUT | /me | `get_current_user` | `UserUpdate` | Triggers synchronous plan regen (see Risk R-3) |
| GET | /me/notification-preferences | `get_current_user` | None | |
| POST | /me/notification-preferences | `get_current_user` | `NotificationPreferencesBody` | |
| DELETE | /me | `get_current_user` | `DeleteAccountRequest` | Password required; Google OAuth rejected |

### Diet Plans (`/api/v1/diet-plans`) — subscription-gated by middleware

| Method | Path | Auth Dependency | Notes |
|--------|------|-----------------|-------|
| GET | /my-plan | `get_current_user` | Returns existing plan + regenerates checklist on-the-fly if missing |
| GET | /today | `get_current_user` | Filters to today's date |
| POST | /generate | `get_current_user` | Rate-limited 10/hour; 3-retry loop; 503 on exhaustion |
| PUT | /update | `get_current_user` | `DietPlan` body |
| DELETE | /delete | `get_current_user` | |
| GET | /ingredient-checklist | `get_current_user` | Returns `[]` if no plan |
| GET | /weekly-ingredients | `get_current_user` | Returns `[]` if no plan |

### Calculations (`/api/v1/calculations`) — **NOT subscription-gated**

| Method | Path | Auth Dependency | Notes |
|--------|------|-----------------|-------|
| GET | /bmr | `get_current_user` | Derives age from `date_of_birth`; fallback 30 |
| GET | /tdee | `get_current_user` | |
| GET | /bmi | `get_current_user` | |

See Risk R-2: these endpoints are accessible to inactive-subscription patients.

### Progress (`/api/v1/progress`) — subscription-gated by middleware

| Method | Path | Auth Dependency | Notes |
|--------|------|-----------------|-------|
| POST | /log/meal | `get_current_user` | Rate-limited 60/min; triggers calorie adjustment if ≥80% TDEE |
| POST | /log/water | `get_current_user` | Rate-limited 30/min |
| POST | /log/steps | `get_current_user` | Rate-limited 30/min |
| POST | /log/weight | `get_current_user` | Rate-limited 30/min; triggers **synchronous** plan regen (see Risk R-3) |
| POST | /log/activity | `get_current_user` | Rate-limited 30/min |
| GET | /weight | `get_current_user` | |
| GET | /today | `get_current_user` | |
| GET | /weekly | `get_current_user` | |
| PUT | /log/meal/{log_id} | `get_current_user` | `MealLogUpdate`; 24h edit window |
| DELETE | /log/meal/{log_id} | `get_current_user` | 24h delete window |
| PUT | /log/water | `get_current_user` | Overwrites today's count |
| PUT | /log/steps | `get_current_user` | Overwrites today's count |
| PUT | /log/weight | `get_current_user` | Overwrites today's weight; triggers sync plan regen |
| DELETE | /log/water | `get_current_user` | Resets to 0 |
| DELETE | /log/steps | `get_current_user` | Resets to 0 |
| POST | /meal/rate | `get_current_user` | Rate-limited 120/min; IDOR check on `recommendation_id` |
| GET | /meal/ratings | `get_current_user` | Last 500 ratings |
| GET | /weight-history | `get_current_user` | `?days=` capped at 365 |
| GET | /weekly-report | `get_current_user` | |
| GET | /streak | `get_current_user` | |
| GET | /adherence/weekly | `get_current_user` | `?days=` capped at 30 |

### Meal Plan (`/api/v1/meal-plan`) — subscription-gated by middleware

| Method | Path | Auth Dependency | Notes |
|--------|------|-----------------|-------|
| POST | /adjust | `get_current_user` | Rate-limited 10/hour; calorie floor 800 kcal |
| GET | /week | `get_current_user` | 404 if no plan (replaced prior silent `{}`) |
| GET | /history | `get_current_user` | `?limit=` capped at 50 |
| GET | /shopping-list | `get_current_user` | Keyword-based categorization |
| POST | /shopping-list/toggle | `get_current_user` | Query params: `ingredient_name`, `at_home` |

### Patients (`/api/v1/patients`) — subscription-gated (except onboarding exclusions)

| Method | Path | Auth Dependency | Notes |
|--------|------|-----------------|-------|
| POST | /onboarding | `get_current_patient` | Rate-limited 100/min; plan gen via background task; idempotent |
| POST | /activate | `get_current_patient` | `.with_for_update()` on code — TOCTOU protected |
| POST | /request-doctor | `get_current_patient` | Duplicate pending request check |
| GET | /request-status | `get_current_patient` | Most recent request for patient |
| GET | /doctors | `get_current_patient` | Public doctor directory; rate-limited 100/min |
| GET | /my-visit | `get_current_patient` | Token 2 + cycle info |
| POST | /disclaimer | `get_current_patient` | Idempotent; stores UTC timestamp |
| POST | /request-renewal | `get_current_patient` | Patient-facing renewal; 409 if no doctor linked |

### Doctor (`/api/v1/doctor`) — DoctorIsolationMiddleware + `get_current_doctor`

| Method | Path | Notes |
|--------|------|-------|
| GET | /patients | Rate-limited 100/min; doctor_id from middleware |
| GET | /patients/{patient_id} | Ownership via doctor_id claim |
| GET | /patients/{patient_id}/plan | 404 if no active recommendation |
| PUT | /patients/{patient_id}/plan | Writes `DoctorMealOverride` per changed slot |
| GET | /patients/{patient_id}/plan/overrides | Override audit trail; last 100 |
| POST | /patients/{patient_id}/plan/notes | Injects note into JSONB meals array |
| GET | /requests | Pending requests only |
| POST | /requests/{request_id}/accept | Activates subscription; fires FCM notify |
| POST | /requests/{request_id}/reject | `RejectRequest` body with rejection note |
| POST | /subscription-codes | Collision-safe code gen |
| GET | /subscription-codes | Own codes only |
| GET | /patients/{patient_id}/logs | `?days=` 1–30 |
| GET | /patients/{patient_id}/progress | `?days=` 1–90 |
| DELETE | /patients/{patient_id} | Makes patient standalone, subscription→inactive |
| POST | /patients/{patient_id}/notes | `ClinicalNoteCreate` |
| GET | /patients/{patient_id}/notes | Own notes only |
| GET | /recipes | Verified global or personal library (`?my_library=true`) |
| POST | /recipes | Adds to personal library; optional global submission |
| POST | /recipes/{recipe_id}/assign | Multi-patient plan injection |
| POST | /recipes/estimate | Local lookup → **gemini-2.0-flash** fallback (see Risk R-4) |
| POST | /recipes/lookup | Key-rotating Gemini; uses `gemini-2.5-flash-lite` |
| GET | /dashboard | Rate-limited 100/min; 5 aggregated stat queries |
| POST | /patients/{patient_id}/record-visit | Token 2 verification; charging rules applied |
| POST | /patients/{patient_id}/flag-visit | Creates `PendingVisitApproval` record |
| GET | /patients/{patient_id}/visits | All visit cycles, newest first |
| POST | /patients/{patient_id}/request-renewal | Sets `renewal_requested=True` |
| POST | /patients/{patient_id}/approve-renewal | New Token 2; new 30-day cycle |
| POST | /patients/approve-all-renewals | Bulk renewal; audit logged |
| GET | /pending-renewals | Outside `/patients/{id}/` to avoid int path conflict |

### Admin (`/api/v1/admin`) — AdminIPWhitelistMiddleware + `get_current_admin`

| Method | Path | Notes |
|--------|------|-------|
| POST | /doctors | Creates doctor; audit logged |
| GET | /doctors | All doctors, newest first |
| GET | /stats | Platform-wide counts |
| GET | /patients | Paginated; optional name/email search |
| PATCH | /doctors/{doctor_id}/deactivate | Soft-disable |
| GET | /doctors/{doctor_id} | Profile + patient count |
| DELETE | /doctors/{doctor_id} | Soft-delete + disconnect patients |
| GET | /audit-logs | Paginated; filterable by role/action |
| POST | /codes/generate | Batch subscription code generation |
| GET | /codes | All codes; filterable by doctor/used status |
| PATCH | /patients/{patient_id}/subscription/override | Manual activation; `?status=&days=` |
| GET | /food | Food DB view; filterable by source/verified |
| PATCH | /food/{food_id}/approve | Sets `is_verified=True` |
| PATCH | /food/{food_id}/reject | Soft-delete via `source="rejected"` |
| DELETE | /food/{food_id} | **Permanent** physical delete |
| GET | /billing | Code usage breakdown per doctor |
| DELETE | /patients/{patient_id} | DPDP anonymization (keeps row for stats) |
| DELETE | /patients/{patient_id}/hard-delete | **Physical delete** — gated by `ALLOW_HARD_DELETE` env var |
| POST | /billing/{doctor_id}/mark-paid | Stored as audit log only (no billing table yet) |
| GET | /consultations | Monthly revenue per doctor at ₹1,500/visit; 2% royalty |
| GET | /consultations/annual | FY totals (Apr 1 – Mar 31); tier assignment; **legacy field names** (see Risk R-7) |
| GET | /renewals | Patients with `renewal_requested=True` |
| POST | /renewals/{patient_id}/override-approve | Admin bypasses doctor; new Token 2 |

**Root endpoint:**

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | / | **None (public)** | Health/welcome message only |

---

## Phase 2 — Middleware Chain Verification

### Registration order and execution order

Starlette processes `add_middleware()` in LIFO order. The registration order in `app/main.py:168–179` is:

```
add_middleware(AdminIPWhitelistMiddleware)    # registered 1st → innermost
add_middleware(DoctorIsolationMiddleware)     # registered 2nd
add_middleware(SubscriptionCheckMiddleware)   # registered 3rd
add_middleware(CORSMiddleware, ...)           # registered 4th
add_middleware(SecurityHeadersMiddleware)     # registered 5th
add_middleware(RequestIDMiddleware)           # registered 6th → outermost
```

Effective execution order (request path, outermost first):

```
RequestIDMiddleware → SecurityHeadersMiddleware → CORSMiddleware →
SubscriptionCheckMiddleware → DoctorIsolationMiddleware → AdminIPWhitelistMiddleware →
[route handler]
```

### Per-middleware analysis

**RequestIDMiddleware** (`main.py:30–36`)  
Reads `X-Request-ID` header or generates UUID. Injects into `request.state`. Attached to every response. No security function. Zero-DB.

**SecurityHeadersMiddleware** (`middleware.py:154–210`)  
Adds `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy` (built from `CORS_ORIGINS`), `Permissions-Policy` to every response. Zero-DB. Outermost security layer.

**CORSMiddleware** (FastAPI built-in)  
Configured with `settings.CORS_ORIGINS` (defaults to `["http://localhost:3000"]`). Allows `GET, POST, PUT, PATCH, DELETE, OPTIONS` and headers `Content-Type, Authorization, Cookie`. Handles preflight. Zero-DB.

**SubscriptionCheckMiddleware** (`middleware.py:66–107`)  
- Reads `sub_status` claim from JWT. **Confirmed zero-DB** — no session or DB call.
- Blocks inactive patients (HTTP 402) on these prefixes only: `/api/v1/meal-plan`, `/api/v1/progress`, `/api/v1/diet-plans`, `/api/v1/patients`
- Always passes `/api/v1/auth` routes through.
- Always passes three onboarding exclusions: `/patients/onboarding`, `/patients/disclaimer`, `/patients/activate`
- **Gap: `/api/v1/users` and `/api/v1/calculations` are not in `_SUBSCRIPTION_PREFIXES`** — inactive patients can access profile info and nutritional calculations. (See Risk R-2.)
- If token is absent, passes through (route dep produces 401).

**DoctorIsolationMiddleware** (`middleware.py:114–147`)  
- Only fires on `/api/v1/doctor/*` paths.
- Reads `doctor_id` claim from JWT. **Confirmed zero-DB**.
- Rejects non-doctor roles with HTTP 403 before route handler runs.
- Injects `request.state.doctor_id` for handler use.
- Route handlers call `_doctor_id(request)` to read from state; raises 403 if absent.

**AdminIPWhitelistMiddleware** (`middleware.py:221–289`)  
- Only fires on `/api/v1/admin/*` paths.
- Reads `admin_id` from JWT, then queries `Admin.allowed_ips` from DB. **Single DB read per admin request.**
- If `allowed_ips` is empty/None, whitelisting is disabled (any IP allowed).
- Non-admin role token on admin path → HTTP 403.
- **Risk: if DB query raises any exception, the middleware logs a warning and `allows` the request through** (`middleware.py:282–286`). A DB outage disables admin IP filtering silently. (See Risk R-1.)

### Bypass analysis

- **No sub-apps mounted** — all routes go through `app.include_router(...)`, all middleware applies uniformly.
- **Background tasks** (plan generation in `patients.py:194`) run after the response is sent. They use their own `AsyncSessionLocal` session, completely separate from the request session. Middleware does not apply to background task execution.
- **Cron jobs** (`main.py:40–147`) run on APScheduler inside the lifespan context. They own their sessions. Middleware is not involved.
- **`/api/v1/auth/google/verify`** creates new patient accounts from Google OAuth. It correctly gates `gdpr_consent` on first-time signups (`auth.py:664`). Existing patients can sign in via Google without GDPR being re-checked (they already consented at registration).

---

## Phase 3 — Live Connection Tests

Live tests executed against server running at `http://localhost:8001` with PostgreSQL container `mityahar_postgres` (Docker). No patients exist in the current dev DB (`total_patients: 0`), so patient-role tests (#7–9) were replaced with equivalent cross-role tests.

### Planned test results

| # | Endpoint | Method | Token Used | Actual HTTP | Actual Body | Result |
|---|----------|--------|-----------|-------------|-------------|--------|
| 1 | /api/v1/auth/admin/login (wrong creds) | POST | — | **401** | `{"detail":"Incorrect email or password"}` | ✅ PASS |
| 2 | /api/v1/admin/stats | GET | Admin | **200** | `{"total_patients":0,"total_doctors":71,...}` | ✅ PASS |
| 3 | /api/v1/admin/doctors | GET | Admin | **200** | Array of 71 doctors | ✅ PASS |
| 4 | /api/v1/admin/stats (doctor token) | GET | Doctor | **403** | `{"detail":"Admin access required"}` | ✅ PASS |
| 5 | /api/v1/doctor/patients | GET | Doctor | **200** | `{"patients":[],"total":0}` | ✅ PASS |
| 6 | /api/v1/doctor/patients (admin token) | GET | Admin | **403** | `{"detail":"Doctor role required"}` | ✅ PASS |
| 7 | /api/v1/calculations/bmr (doctor token) | GET | Doctor | **403** | `{"detail":"Patient role required"}` | ✅ PASS (role enforcement confirmed; no patient in DB) |
| 8 | Patient inactive-subscription tests | — | — | — | — | ⏭️ SKIP — No patient in DB |
| 9 | /api/v1/progress/today (inactive sub) | — | — | — | — | ⏭️ SKIP — No patient in DB |
| 10 | /api/v1/doctor/dashboard | GET | Doctor | **200** | `{"total_patients":0,"active_patients":0,...}` | ✅ PASS |

### Additional live tests

| Test | Endpoint | HTTP | Body | Result |
|------|----------|------|------|--------|
| Unauthenticated → admin route | GET /admin/stats | **401** | `{"detail":"Not authenticated"}` | ✅ PASS |
| Unauthenticated → doctor route | GET /doctor/patients | **401** | `{"detail":"Authentication required"}` | ✅ PASS |
| Refresh token used as access token | GET /doctor/patients | **401** | `{"detail":"Refresh token cannot be used for API access"}` | ✅ PASS — T1-7 safeguard confirmed |
| Cookie path-scoping (refresh token) | GET /doctor/dashboard | **401** | `{"detail":"Authentication required"}` | ✅ PASS — HttpOnly cookie not sent outside `/api/v1/auth` |
| POST /auth/refresh (via cookie) | POST /auth/refresh | **200** | New access token | ✅ PASS — Refresh flow works |
| GET /auth/verify-email?token=invalid | GET /auth/verify-email | **400** | `{"detail":"Verification link is invalid..."}` | ✅ PASS — Not 401; correctly public |
| GET /admin/audit-logs | GET /admin/audit-logs | **200** | `{"logs":[],"total":0}` | ✅ PASS |
| Rate limit: forgot-password (5/min) | POST /auth/forgot-password | 200 ×4 | Anti-enumeration 200 on all | ✅ PASS — Limit not exceeded in 4 calls; `5/minute` set at `auth.py:1118` |
| Security headers present | GET / | 200 | Headers confirmed in response | ✅ PASS — see below |

### Security headers observed on live server

All headers confirmed present on root (`/`) response:

```
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
content-security-policy: default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; ...
permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), accelerometer=()
x-request-id: <uuid>
```

**New finding from live test (see Risk R-12):** The CSP allows `'unsafe-inline'` for both `script-src` and `style-src`, and uses `connect-src 'self' *` (wildcard connect). The `'unsafe-inline'` directive undermines the XSS protection that CSP is meant to provide.

**Mutating / external-call routes (skip per audit rules):**

- `POST /api/v1/diet-plans/generate` — ⏭️ SKIP — MUTATING (DB + plan write)
- `POST /api/v1/patients/onboarding` — ⏭️ SKIP — MUTATING
- `POST /api/v1/doctor/requests/{id}/accept` — ⏭️ SKIP — EXTERNAL CALL (FCM)
- `POST /api/v1/doctor/patients/{id}/approve-renewal` — ⏭️ SKIP — EXTERNAL CALL (FCM)
- All `DELETE` routes — ⏭️ SKIP — MUTATING

---

## Phase 4 — Fire-and-Forget Service Probe

### `audit_service.log_action` (`app/services/audit_service.py`)

- **Is there a log on failure?** Yes — `_log.error(f"Audit log failed: {exc}", exc_info=True)` at line 41.
- **Does any caller await the result and check it?** Every caller `await`s `log_action(...)` but none check a return value (the function returns `None`). The `try/except` in `log_action` swallows all errors silently after logging.
- **Labeling discrepancy**: The docstring says "fire-and-forget" but the function is `await`ed inline in the same request session. It is better described as "never-raises" or "error-tolerant". This means audit failures do not block the parent operation (good), but the function does consume a slot in the request's DB transaction lifecycle (not truly detached).

### `notification_service.*` (`app/services/notification_service.py`)

- **`notify_plan_ready`** — synchronous call, no `await`. Called inside `_generate_plan_background` (a separate event loop). Has internal `try/except` via `send_push`.
- **`notify_doctor_accepted`** — called in `doctor.py:462–466` inside `try/except: pass` block. Never blocks `accept_request`.
- **`notify_sub_expiring`** — called in `main.py:88–90` inside `try/except: pass` block. Never blocks the cron.
- **`notify_renewal_approved`** — called in `doctor.py:1503–1507` inside `try/except: pass`. Never blocks `approve_renewal`.
- **All callers check for log on failure?** `send_push` logs `_log.warning(...)` on any FCM exception (line 98). The outer `try/except: pass` at call sites silences any exception that escapes `send_push`.

### `init_firebase()` at startup (`notification_service.py:30–57`)

- Called once from `main.py:138` in the lifespan context.
- If `FIREBASE_SERVICE_ACCOUNT_PATH` file is not found: **logs warning**, sets `_firebase_app = None` — app continues.
- If `firebase_admin.initialize_app()` raises: **logs error**, leaves `_firebase_app = None` — app continues.
- All `notify_*` functions call `send_push` which checks `if _firebase_app is None: return False` (line 80). Notifications silently no-op when Firebase is not initialized.
- **Conclusion**: Firebase failure at startup is fully silent (no HTTP error, no crash). Push notifications are disabled but the API remains fully functional.

---

## Phase 5 — Meal Dataset Status

### How datasets are loaded

The `MealGenerator` class (`app/services/meal_generator/meal_generator.py`) **does not load any markdown or CSV files at runtime**. It queries exclusively from PostgreSQL:

- `MealTemplate` table → slot structure per meal time/region/diet/plan-type
- `FoodItem` table → individual food items matching slot criteria

The markdown files in `app/graphify-out/converted/` are **graphify analysis output** (documentation snapshots generated by the `/graphify` tool). They are not imported or referenced by any Python module.

### Are "new" variant files wired in?

No. `Breakfast_new_25408bcd.md`, `Lunch_new_f6408e14.md`, `Dinner_new_51fc9d6e.md` exist in the `app/graphify-out/converted/` directory but are not referenced anywhere in the Python codebase. They are graphify documentation artifacts.

### Is there a fallback if a file is missing?

Not applicable — the generator doesn't load files. If the PostgreSQL `food_items` or `meal_templates` tables are empty, the generator logs warnings per missing slot (`"No template found for {db_meal_time}"`) and skips that meal slot. The plan would have fewer than 35 meals, which would fail the `_validate_generated_plan` check in `diet_plans.py:184` and trigger a retry.

### Muskmelon smoothie with zero nutritional values

Located in:
- `app/graphify-out/converted/Morning_Snack (1)_d3d3d6ab.md:11` (documentation file — not runtime)
- Source CSV `IndianFoodDatasetCSV.csv` rows 2766–2767 (raw dataset)

**Runtime impact**: If the Muskmelon smoothie was seeded into the `food_items` table with `cal_per_serving=0`, the meal generator at `meal_generator.py:410–412` checks `if float(food_item.cal_per_serving) > 0` and sets `factor=1.0` as fallback. The item would enter a meal plan with zero calorie/macro contribution — a silent nutritional accounting error. **Cannot verify whether this item is in the live DB without running a query.**

---

## Phase 6 — Known Risk Flags Verification

### In-memory rate limiter

**File**: `app/core/limiter.py:1–22` and `app/main.py:152`

- `app/core/limiter.py` contains a proper Redis-conditional check with a `_log.warning()` when falling back to in-memory.
- `app/main.py` also instantiates a second `limiter` at line 152 with no Redis check — this is the limiter actually attached to `app.state.limiter`. The limiter in `core/limiter.py` is imported by routers via `from ..core.limiter import limiter`.
- The `main.py` limiter is only used for `app.state.limiter` (for the exception handler). Router rate limits use the `core/limiter.py` instance.
- **TODO comment confirmed** at `main.py:149–151`: "NOTE: slowapi uses in-memory storage by default. Set REDIS_URL in .env before multi-worker production deployment."

### 73% inferred edges in graph

Acknowledged. Graph edges are inferred from code patterns; this audit takes precedence over graph inference.

### Patient model inferred edges

**File**: `app/models/db_models.py:226–231`

Patient has these explicit ORM relationships:
- `doctor` → `Doctor` (FK: `Patient.doctor_id`)
- `recommendations` → `Recommendation`
- `meal_logs` → `MealLog`
- `progress_logs` → `ProgressLog`
- `patient_requests` → `PatientRequest`
- `patient_visits` → `PatientVisit`

No orphaned or unusual relationship fields. The "155 inferred edges" in the graph report reflects the large number of columns (30+) and all bidirectional relationship traversals, not structural problems.

### Cron jobs for subscription expiry

**File**: `app/main.py:40–147`

Both cron jobs are registered via `AsyncIOScheduler` in the `lifespan` context:
- `_flag_expiring_patients` → `CronTrigger(hour=1, minute=0)` (UTC)
- `_deactivate_expired_patients` → `CronTrigger(hour=1, minute=5)` (UTC)
- Scheduler starts at `scheduler.start()` (`main.py:143`) and shuts down at `scheduler.shutdown(wait=False)` (`main.py:146`).
- **They would fire in any environment that starts the server** — including staging or test environments if the server is running at 01:00–01:05 UTC. No environment flag disables them. Mitigation: test environments should ideally use a different `DATABASE_URL` pointing to a test database so cron mutations don't affect production data.

---

## Phase 3 — Live Test Results

**Test session**: 2026-05-01, server `http://localhost:8001`, PostgreSQL container `mityahar_postgres`.  
**Tokens obtained**:
- Patient (`audit.patient@mityahar.com`, `sub_status: inactive`, `patient_id: 1`) — registered via `POST /auth/register` then `POST /auth/token`
- Doctor (`dr.ashok.mehta@mitihar.test`, `doctor_id: 70`) — `POST /auth/doctor/login`
- Admin (`admin@mityahar.com`, `admin_id: 1`) — `POST /admin/login`

**Pre-test finding (new)**: Registration with `region: "North India"` returned HTTP 500 — `StringDataRightTruncationError` because `patients.region` is `VARCHAR(10)` (`db_models.py:158`) but the schema (`user.py:86`) applies no length validation. No user-facing error message, just `{"detail":"Internal server error"}`. See Risk R-13.

---

### Patient GET endpoints — inactive subscription (`sub_status: inactive`)

#### `/api/v1/users` — not in `_SUBSCRIPTION_PREFIXES`, accessible to inactive patients

| Endpoint | HTTP | Body (truncated) | Result |
|----------|------|-----------------|--------|
| GET /users/me | **200** | `{"id":1,"email":"audit.patient@mityahar.com",...}` | ✅ PASS |
| GET /users/bmi | **200** | `{"bmi":22.86}` | ✅ PASS |
| GET /users/me/notification-preferences | **200** | `{}` | ✅ PASS |

#### `/api/v1/calculations` — not in `_SUBSCRIPTION_PREFIXES` — **confirms R-2 live**

| Endpoint | HTTP | Body | Result |
|----------|------|------|--------|
| GET /calculations/bmr | **200** | `{"bmr":1623.75}` | ✅ R-2 CONFIRMED — inactive patient gets BMR |
| GET /calculations/tdee | **200** | `{"tdee":2232.66}` | ✅ R-2 CONFIRMED |
| GET /calculations/bmi | **200** | `{"bmi":22.86}` | ✅ R-2 CONFIRMED |

#### `/api/v1/diet-plans` — in `_SUBSCRIPTION_PREFIXES`, correctly blocked

| Endpoint | HTTP | Body | Result |
|----------|------|------|--------|
| GET /diet-plans/my-plan | **402** | `{"detail":"Subscription expired","code":"SUBSCRIPTION_EXPIRED"}` | ✅ PASS |
| GET /diet-plans/today | **402** | same | ✅ PASS |
| GET /diet-plans/ingredient-checklist | **402** | same | ✅ PASS |
| GET /diet-plans/weekly-ingredients | **402** | same | ✅ PASS |

#### `/api/v1/progress` — in `_SUBSCRIPTION_PREFIXES`, correctly blocked

| Endpoint | HTTP | Result |
|----------|------|--------|
| GET /progress/weight | **402** | ✅ PASS |
| GET /progress/today | **402** | ✅ PASS |
| GET /progress/weekly | **402** | ✅ PASS |
| GET /progress/meal/ratings | **402** | ✅ PASS |
| GET /progress/weight-history | **402** | ✅ PASS |
| GET /progress/weekly-report | **402** | ✅ PASS |
| GET /progress/streak | **402** | ✅ PASS |
| GET /progress/adherence/weekly | **402** | ✅ PASS |

#### `/api/v1/meal-plan` — in `_SUBSCRIPTION_PREFIXES`, correctly blocked

| Endpoint | HTTP | Result |
|----------|------|--------|
| GET /meal-plan/week | **402** | ✅ PASS |
| GET /meal-plan/history | **402** | ✅ PASS |
| GET /meal-plan/shopping-list | **402** | ✅ PASS |

#### `/api/v1/patients` — in `_SUBSCRIPTION_PREFIXES`

| Endpoint | HTTP | Result | Note |
|----------|------|--------|------|
| GET /patients/request-status | **402** | ✅ PASS | |
| GET /patients/doctors | **402** | ⚠️ UX GAP | Inactive patient cannot browse doctor directory — see Risk R-14 |
| GET /patients/my-visit | **402** | ✅ PASS | |

#### Cross-role enforcement — patient token on privileged routes

| Endpoint | HTTP | Body | Result |
|----------|------|------|--------|
| GET /admin/stats (patient token) | **403** | `{"detail":"Admin access required"}` | ✅ PASS |
| GET /doctor/patients (patient token) | **403** | `{"detail":"Doctor role required"}` | ✅ PASS |

---

### Doctor GET endpoints — `doctor_id: 70`

| Endpoint | HTTP | Body (truncated) | Result |
|----------|------|-----------------|--------|
| GET /doctor/patients | **200** | `{"patients":[],"total":0}` | ✅ PASS |
| GET /doctor/requests | **200** | `[]` | ✅ PASS |
| GET /doctor/subscription-codes | **200** | `[{"id":190,"code":"GEW8T25ANYGU",...}]` | ✅ PASS |
| GET /doctor/recipes | **200** | `[{"id":351,"recipe_name":"Akki roti",...}]` — food DB populated | ✅ PASS |
| GET /doctor/dashboard | **200** | `{"total_patients":0,...}` | ✅ PASS |
| GET /doctor/pending-renewals | **200** | `[]` | ✅ PASS |

---

### Admin GET endpoints — `admin_id: 1`

| Endpoint | HTTP | Body (truncated) | Result |
|----------|------|-----------------|--------|
| GET /admin/stats | **200** | `{"total_patients":1,"total_doctors":71,...}` | ✅ PASS |
| GET /admin/doctors | **200** | Array of 71 doctors | ✅ PASS |
| GET /admin/patients | **200** | `{"patients":[{"id":1,...}],"total":1}` | ✅ PASS |
| GET /admin/audit-logs | **200** | `{"logs":[],"total":0}` | ✅ PASS |
| GET /admin/codes | **200** | Array of subscription codes | ✅ PASS |
| GET /admin/food | **200** | Food item array — food DB is seeded | ✅ PASS |
| GET /admin/billing | **200** | `{"total_codes_issued":193,"total_codes_used":0,...}` | ✅ PASS |
| GET /admin/consultations | **200** | `{"month":"May 2026","total_consultations_this_month":0,...}` | ✅ PASS |
| GET /admin/consultations/annual | **200** | FY 2026–2027; **fields `royalty_pool_6pct` and `royalty_per_member_2pct` confirmed in live response** | ✅ R-7 CONFIRMED |
| GET /admin/renewals | **200** | `[]` | ✅ PASS |
| GET /admin/doctors/70 | **200** | Dr. Ashok Mehta profile | ✅ PASS |

---

### Open Question answers from live tests

- **Q-4 (Live HTTP verification)**: ✅ Answered — all Phase 3 endpoints tested above.
- **Q-5 (FoodItem table populated)**: ✅ Confirmed — `GET /doctor/recipes` and `GET /admin/food` both return seeded records.
- **Q-5 (MealTemplate table)**: Still unverified (no direct endpoint exposes templates). Requires DB query.
- **Q-6 (admin allowed_ips)**: Not verified here — requires direct DB query.

---

## Risk Register

| Severity | ID | Risk | Location | Evidence | Recommended Action |
|----------|----|------|----------|----------|--------------------|
| 🔴 Critical | R-1 | `AdminIPWhitelistMiddleware` silently allows admin requests if its DB lookup fails | `middleware.py:282–286` | `except Exception: logging.warning(...); # allow through` — DB outage disables IP filtering | Change to deny-on-error: return HTTP 503 or 403 if the whitelist query fails |
| 🟡 Warning | R-2 | Inactive patients can access `/users/*` and `/calculations/*` — **confirmed live** | `middleware.py:46–51` (`_SUBSCRIPTION_PREFIXES`) | Live test: `GET /calculations/bmr` returned 200 with `{"bmr":1623.75}` for `sub_status:inactive` patient | Add these prefixes to `_SUBSCRIPTION_PREFIXES` or annotate as intentional (profile access may be desirable) |
| 🟡 Warning | R-3 | Synchronous diet plan regeneration inside request handlers can cause timeouts | `progress.py:147` (`post_log_weight`), `progress.py:307` (`update_weight_log`), `users.py:126–130` (`update_user_profile`) | `await diet_service.generate_diet_plan(...)` called inline; `progress.py` uses `print()` for error logging instead of `logger.error()` | Move plan regen to a background task (as done in `patients.py:194`); replace `print()` with `logger.error()` |
| 🟡 Warning | R-4 | `POST /doctor/recipes/estimate` uses `gemini-2.0-flash` model (non-lite) | `doctor.py:1104–1106` | Hardcoded URL: `gemini-2.0-flash:generateContent`. `gemini-2.0-flash-lite` was retired per CLAUDE.md; `gemini-2.0-flash` status unknown | Verify model availability; update to `gemini-2.5-flash-lite` (consistent with `/recipes/lookup` at `doctor.py:1660`) |
| 🟡 Warning | R-5 | In-memory rate limiter unsafe for multi-worker deployment | `core/limiter.py:17–22`, `main.py:149–151` | No `REDIS_URL` in `.env` means all rate limits are per-process. Running `--workers 4` gives each worker 4× the nominal budget | Set `REDIS_URL` before any multi-worker deployment |
| 🔵 Info | R-6 | `audit_service.log_action` is labeled "fire-and-forget" but is awaited inline | `audit_service.py:3`, callers in all routers | Docstring: "fire-and-forget"; actual behavior: `await log_action(...)` in same request; errors swallowed after `_log.error()` | Update docstring to "never-raises" to avoid misleading future maintainers |
| 🔵 Info | R-7 | `GET /admin/consultations/annual` has misleadingly named legacy response fields — **confirmed live** | `admin.py:812–813` | Live response contains keys `royalty_pool_6pct` (holds 2% value) and `royalty_per_member_2pct` (holds 0.67% value) | Rename keys to `royalty_pool_2pct` and `royalty_per_member_0_67pct` and update frontend `Billing.tsx` simultaneously |
| 🔵 Info | R-8 | Muskmelon smoothie with all-zero nutritional values may be in `food_items` table | `app/graphify-out/converted/Morning_Snack (1)_d3d3d6ab.md:11` | Zero-cal item would enter meal plans with zero nutritional contribution (`meal_generator.py:410–412`) | Run `SELECT * FROM food_items WHERE cal_per_serving = 0;` and delete/fix any all-zero rows |
| 🔵 Info | R-9 | Cron jobs fire in any environment that starts the server | `main.py:141–143` | No `DISABLE_CRONS` env flag; APScheduler starts unconditionally in `lifespan` | Add `if not settings.DISABLE_CRONS: scheduler.start()` or document that test DBs must be isolated |
| 🔵 Info | R-10 | `POST /auth/logout` returns HTTP 200 for any unauthenticated caller | `auth.py:890–976` | No auth dependency; intentional for expired-token scenarios | Acceptable by design; document in API spec |
| 🔵 Info | R-11 | `POST /billing/{doctor_id}/mark-paid` stores payment records as audit log entries, not a billing table | `admin.py:630–671` | Comment: "No billing table yet (Phase 4 Razorpay will replace this)" | No action needed until Phase 4; ensure audit log retention policy covers billing records |
| 🟡 Warning | R-12 | CSP header uses `'unsafe-inline'` for `script-src` and `style-src`; `connect-src` is `*` | `middleware.py:154–210` (`SecurityHeadersMiddleware`) | Live response: `script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' ...; connect-src 'self' *` — `'unsafe-inline'` negates XSS protection; wildcard connect allows data exfiltration to any origin | Remove `'unsafe-inline'`; use nonces or hashes. Narrow `connect-src` to explicit API and font origins. |
| 🟡 Warning | R-13 | `POST /auth/register` returns HTTP 500 (not 422) when `region` exceeds 10 characters | `user.py:86`, `db_models.py:158` | `region` schema: `Optional[str]` with no `max_length`; DB column: `VARCHAR(10)`. Sending `"North India"` (11 chars) produces `StringDataRightTruncationError` with no user-visible message | Add `Field(default=None, max_length=10)` to `UserCreate.region`, or widen the DB column with an Alembic migration |
| 🔵 Info | R-14 | `GET /patients/doctors` (doctor directory) is subscription-gated, blocking new-patient onboarding flow | `middleware.py:46–51` | Live test: inactive patient gets 402 on `GET /patients/doctors`. Patient must find a doctor to get a code to activate, but can't browse the directory without already being active | Add `/api/v1/patients/doctors` to the subscription-check exclusion list alongside `/patients/activate` |

---

## Open Questions

Items that could not be determined from static analysis or live GET tests:

1. **Is Muskmelon smoothie in the live `food_items` table?** Needs `SELECT * FROM food_items WHERE recipe_name ILIKE '%muskmelon%';`
2. **Does `gemini-2.0-flash` (used by `/recipes/estimate`) still accept requests?** Needs a live API call.
3. **Does the `FIREBASE_SERVICE_ACCOUNT_PATH` file exist in the deployment environment?** Push notifications are silently disabled if absent.
4. ~~Live HTTP status verification~~ ✅ **Answered — Phase 3 complete.**
5. **Are the `MealTemplate` tables populated?** `FoodItem` table confirmed seeded (via `/doctor/recipes`). `MealTemplate` rows still unverified — requires `SELECT COUNT(*) FROM meal_templates;`
6. **`AdminIPWhitelistMiddleware`: what is the `allowed_ips` value for the current admin?** If `[]`, IP whitelisting is disabled. Needs `SELECT allowed_ips FROM admins WHERE id = 1;`
7. **`REQUIRE_EMAIL_VERIFICATION` in production**: currently `False` by default. Needs a policy decision before launch.
8. **`COOKIE_SECURE` in production**: startup logs `CRITICAL` if `False` on non-localhost but does not block. Verify it is `True` on any internet-facing deployment.
