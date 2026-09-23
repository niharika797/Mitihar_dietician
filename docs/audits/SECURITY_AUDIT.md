# Mityahar Security Audit — Tasks 1–4

> **Status:** Audit complete. Fixes pending.
> **Audited by:** Claude (Senior Security Engineer review session)
> **Date:** March 2026
> **Stack:** FastAPI backend · React Native (Expo) patient app · React/Vite admin frontend · PostgreSQL

---

## How to use this document

Each task section follows the same structure:

1. **What is already correct** — things that must not be changed
2. **Findings** — graded 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low
3. **Summary table** with file and field references

Fix order: all 🔴 Critical first, then 🟠 High, then 🟡 Medium.
Nothing in the "already correct" sections should be touched.

---

## Task 1 — Authentication Security Audit

**Files read:** `app/core/security.py`, `app/core/config.py`, `app/core/limiter.py`,
`app/core/middleware.py`, `app/routers/auth.py`, `app/services/user_service.py`,
`app/main.py`, both frontend axios files, both frontend `.env` files.


### ✅ Task 1 — Already Correct

- **Passwords:** bcrypt via passlib `CryptContext`. Hashed at creation, verified on login consistently across all three roles (patient, doctor, admin).
- **JWT structure:** Access tokens (15 min) and refresh tokens (7 days) are structurally separate via `token_type` claim. `_decode_jwt()` explicitly rejects refresh tokens used as access tokens.
- **Session expiry:** `ACCESS_TOKEN_EXPIRE_MINUTES=15` (short-lived). `REFRESH_TOKEN_EXPIRE_MINUTES=10080` (7 days, appropriate for mobile).
- **Password reset tokens:** `secrets.token_urlsafe(48)`, 30-minute expiry, consumed on use, one active per patient.
- **Email verification tokens:** Same secure generation, 24-hour expiry, one-time use.
- **Rate limiting:** `slowapi` applied per endpoint — register 10/min, patient login 20/min, admin/doctor login 10/min, forgot-password 5/min, resend-verification 3/min, logout 30/min.
- **Secrets not exposed to frontend:** `SECRET_KEY`, `GEMINI_API_KEY_*`, `DATABASE_URL`, `GOOGLE_CLIENT_SECRET` all live server-side only. Both frontend `.env` files contain only API URLs. Both are gitignored.
- **HttpOnly cookies:** Doctor and admin refresh tokens use `httponly=True` cookies, inaccessible to JavaScript.
- **Security headers middleware:** `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy` applied to every response.
- **MFA:** TOTP-based MFA for doctors and admins. Partial token (5-minute expiry) for MFA step-2 prevents replay.
- **Admin IP whitelisting:** `AdminIPWhitelistMiddleware` checks requesting IP against `allowed_ips` on all `/admin` routes.
- **`SECRET_KEY` startup guard:** `config.py` hard-fails at startup if `SECRET_KEY` is the default or under 32 characters.


### 🔴 Task 1 — Critical Issues

**Issue 1 — Rate limiter uses in-memory storage — bypassed in multi-worker deployments**
- **File:** `app/core/limiter.py`
- **Problem:** `Limiter(key_func=get_remote_address)` with no storage backend. Each uvicorn worker has its own in-process counter. With `--workers 4`, an attacker can send 4× the advertised limit by routing across workers. The existing TODO comment is not enough — this is a pre-production blocker.
- **Fix:** Add `REDIS_URL: Optional[str] = None` to `config.py`. In `limiter.py`, conditionally use `RedisStorage(settings.REDIS_URL)` if the URL is set, else keep the in-memory default with a startup warning. One-line change in `limiter.py`.

**Issue 2 — Patient refresh token sent in response body, not HttpOnly cookie**
- **File:** `app/routers/auth.py` — `POST /auth/token` and `POST /auth/refresh`
- **Problem:** Patient login returns `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`. The refresh token is in the JSON body — accessible to JavaScript in memory. Doctor and admin use HttpOnly cookies; patients do not. This is an asymmetric security posture.
- **Fix:** Set the patient refresh token as an HttpOnly cookie on login (matching doctor/admin). Update `POST /auth/refresh` to read it from the cookie for patients. Update the patient axios interceptor to stop reading `refresh_token` from the body.

**Issue 3 — `datetime.utcnow()` used — deprecated naive datetimes in JWT creation**
- **File:** `app/core/security.py` — `create_access_token`, `create_refresh_token`
- **Problem:** Both functions use `datetime.utcnow()` which returns a naive (timezone-unaware) datetime. Python 3.12 deprecated this. When compared against timezone-aware datetimes, silent bugs can occur. The rest of the codebase correctly uses `datetime.now(timezone.utc)`.
- **Fix:** Replace all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` in `security.py`.

**Issue 4 — `_decode_partial_token` does not explicitly enforce expiry/claim options**
- **File:** `app/routers/auth.py` — `_decode_partial_token`
- **Problem:** `jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])` is called without passing an explicit `options` dict. The `jose` library does check `exp` by default but `verify_iat` and `verify_nbf` are not explicitly enforced. This is a latent risk — if library defaults change across versions, there is no defence in depth.
- **Fix:** Add `options={"verify_exp": True, "verify_iat": True, "verify_nbf": True}` to match the pattern already used in `middleware.py`'s `_safe_decode`.


### 🟠 Task 1 — High Issues

**Issue 5 — Email verification generated but never enforced at login**
- **File:** `app/core/security.py` — `get_current_patient`
- **Problem:** `register` creates an `EmailVerificationToken` and logs the link. `is_email_verified` exists on the `Patient` model. But `get_current_patient` never checks it. A patient can register with any email and immediately log in without verifying. An attacker could register with someone else's email and lock them out.
- **Fix:** Add `REQUIRE_EMAIL_VERIFICATION: bool = False` to `config.py`. Add `if settings.REQUIRE_EMAIL_VERIFICATION and not patient.is_email_verified: raise HTTPException(403, "Email not verified. Check your inbox.")` to `get_current_patient`. Switch flag to `True` once real email sending is implemented (Phase 7).

**Issue 6 — No per-account lockout after repeated failed login attempts**
- **File:** `app/routers/auth.py` — all login endpoints
- **Problem:** IP-based rate limiting exists (20 req/min for patient, 10/min for admin/doctor). But there is no per-account lockout. An attacker with rotating IPs or a botnet can make unlimited password attempts against a single known email. bcrypt cost is good but not sufficient alone.
- **Fix:** Add `failed_login_attempts: int = 0` and `locked_until: Optional[datetime] = None` columns to the `Patient`, `Doctor`, and `Admin` models. On each failed login, increment the counter. After 10 consecutive failures, set `locked_until = now + 15 minutes`. Reset the counter on success. Check `locked_until` at the start of each login handler.

**Issue 7 — Password reset does not invalidate existing sessions**
- **File:** `app/routers/auth.py` — `POST /auth/reset-password`
- **Problem:** After a patient resets their password, existing access tokens (valid 15 min) and refresh tokens (valid 7 days) remain valid. A session thief who triggered the reset can continue using a stolen refresh token for up to 7 days.
- **Fix:** Add `password_changed_at: Optional[datetime]` column to the `Patient` model. Set it to `now()` on every password reset. In `_decode_jwt`, after decoding, check that `iat` (token issued-at) is after `password_changed_at`. If not, reject with 401. This is a stateless invalidation — no token blacklist needed.

**Issue 8 — No startup guard when `COOKIE_SECURE=False` in production**
- **File:** `app/core/config.py` / `app/main.py`
- **Problem:** `COOKIE_SECURE=False` is the default. If a developer forgets to set `True` before deploying, refresh tokens are sent over plain HTTP where they can be intercepted. There is no CI or startup check enforcing this.
- **Fix:** Add a startup check in `lifespan()` in `main.py`: if `settings.COOKIE_SECURE is False` and the server is not listening on localhost, log a `CRITICAL` warning. Not a hard fail (to allow flexible local tunnels) but loud enough to never be missed.


### 🟡 Task 1 — Medium Issues

**Issue 9 — `ResetPasswordRequest.validate_password` is dead code**
- **File:** `app/routers/auth.py`
- **Problem:** The method is `@staticmethod`, not `@field_validator("new_password")`. Pydantic never calls it automatically. Passwords set via reset have zero complexity enforcement beyond `min_length=8`. `"aaaaaaaa"` and `"12345678"` both pass.
- **Fix:** Change decorator to `@field_validator("new_password")` and add `@classmethod`. The body logic (letter + digit check) is already correct.

**Issue 10 — CORS `allow_methods=["*"]` and `allow_headers=["*"]` are too permissive**
- **File:** `app/main.py`
- **Problem:** Any HTTP method and any request header from any allowed origin is permitted. In practice only GET/POST/PUT/PATCH/DELETE/OPTIONS are needed, and only `Content-Type`, `Authorization`, and `Cookie` headers are used.
- **Fix:** Replace `allow_methods=["*"]` with `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` and `allow_headers=["*"]` with `["Content-Type","Authorization","Cookie"]`.

**Issue 11 — `resend-verification` calls `get_current_patient` as a raw function**
- **File:** `app/routers/auth.py` — `resend_verification_email`
- **Problem:** `patient = await get_current_patient(token=..., session=session)` calls a FastAPI dependency directly as a regular function, bypassing the DI system. If `get_current_patient`'s signature changes, this call silently fails or uses stale defaults.
- **Fix:** Add `current_patient: Patient = Depends(get_current_patient)` as a proper function parameter instead of the manual extraction.

**Issue 12 — `password_changed_at` column does not exist on Patient model**
- **File:** `app/models/db_models.py`
- **Note:** This is a schema prerequisite for Issue 7. The column must be added via Alembic migration before the session-invalidation fix can be applied.

### 🟢 Task 1 — Low / Informational

**Issue 13 — Redis TODO is production-critical but only a comment**
- The comment `# TODO: Switch to RedisStorage before multi-worker/production deployment` in `limiter.py` should be converted to a logged startup warning so it cannot be silently ignored.

**Issue 14 — Admin MFA is opt-in, not enforced**
- Admin accounts can have `mfa_enabled=False` and log in with just a password. For the highest-privilege role, MFA should be mandatory. Currently it is opt-in via `/admin/mfa-setup`.

**Issue 15 — Real Gemini API keys in `.env`**
- Backend-only, gitignored — low risk as long as `.env` was never committed. Periodic rotation recommended.

### Task 1 — Summary Table

| # | Severity | Issue | File |
|---|---|---|---|
| 1 | 🔴 Critical | Rate limiter in-memory — bypassed with multiple workers | `limiter.py` |
| 2 | 🔴 Critical | Patient refresh token in JSON body, not HttpOnly cookie | `auth.py` |
| 3 | 🔴 Critical | `datetime.utcnow()` deprecated naive datetimes in JWT creation | `security.py` |
| 4 | 🔴 Critical | Partial MFA token decoder has no explicit expiry/claim enforcement | `auth.py` |
| 5 | 🟠 High | Email verification never enforced at login | `security.py` |
| 6 | 🟠 High | No per-account lockout after failed logins | `auth.py` + DB |
| 7 | 🟠 High | Password reset doesn't invalidate existing sessions | `auth.py` |
| 8 | 🟠 High | No startup guard when `COOKIE_SECURE=False` | `config.py` / `main.py` |
| 9 | 🟡 Medium | Password complexity validator is dead code | `auth.py` |
| 10 | 🟡 Medium | CORS `allow_methods/allow_headers=["*"]` too permissive | `main.py` |
| 11 | 🟡 Medium | `resend-verification` calls FastAPI dep as raw function | `auth.py` |
| 12 | 🟡 Medium | `password_changed_at` column missing on Patient model | `db_models.py` |
| 13 | 🟢 Low | Redis TODO is production-critical but only a comment | `limiter.py` |
| 14 | 🟢 Low | Admin MFA optional rather than enforced | `auth.py` |
| 15 | 🟢 Low | Real Gemini API keys in `.env` (gitignored, backend-only) | `.env` |


---

## Task 2 — IDOR (Insecure Direct Object Reference) Audit

**Files read:** `app/routers/progress.py`, `app/routers/meal_plan.py`, `app/routers/diet_plans.py`,
`app/routers/doctor.py` (1,579 lines), `app/routers/admin.py`, `app/routers/users.py`,
`app/services/progress_service.py`.

### ✅ Task 2 — Already Correct

- **Patient routes** (`progress.py`, `diet_plans.py`, `meal_plan.py`, `users.py`): Every endpoint derives the target patient from `Depends(get_current_user)` (JWT). No URL `{patient_id}` parameters — patients can only ever touch their own data.
- **`progress_service.py` — `get_meal_log_by_id`, `update_meal_log`, `delete_meal_log`:** All filter with `WHERE MealLog.id = ? AND MealLog.patient_id = ?`. A patient cannot edit or delete another patient's log.
- **`progress.py` — `rate_meal`:** Explicit ownership check on `recommendation_id` before writing the rating: `Recommendation.patient_id == current_user.id`.
- **Doctor routes — patient-level ownership:** Every endpoint with a `patient_id` URL param runs `WHERE Patient.id = ? AND Patient.doctor_id = ?` before any sub-resource access. Doctor A cannot read Doctor B's patients.
- **Doctor routes — request/code isolation:** `accept_request`, `reject_request`, `list_codes`, `generate_codes` all filter by `doctor_id`. A doctor cannot act on another doctor's requests or codes.
- **PatientVisit fetch pattern:** All visit-related queries include `PatientVisit.doctor_id == did`. Safe as currently structured.

### 🔴 Task 2 — Critical Issues

**Issue 1 — `POST /doctor/recipes/{recipe_id}/assign`: any doctor can assign any other doctor's private recipe**
- **File:** `app/routers/doctor.py` — `assign_recipe`
- **Problem:** The recipe is fetched with `select(FoodItem).where(FoodItem.id == recipe_id)` — no ownership check. A doctor can pass any integer `recipe_id`, including a private recipe (`is_verified=False`, `source="doctor"`) owned by a completely different doctor. The recipe's full nutritional data is then embedded in the requesting doctor's patients' meal plans. An attacker can enumerate all private recipes in the database by guessing IDs.
- **Attack scenario:** Doctor A (competitor) calls `POST /doctor/recipes/999/assign`. Recipe 999 belongs to Doctor B. Doctor A extracts Doctor B's proprietary recipe data and assigns it to their own patients.
- **Fix:** After fetching the food item, add:
  ```python
  if not food.is_verified and food.doctor_id != did:
      raise HTTPException(status_code=403, detail="Recipe not accessible")
  ```
  This allows global verified recipes (accessible to all) and the doctor's own private recipes. Blocks other doctors' private/pending recipes.

**Issue 2 — Inner patient fetch in `override_patient_plan` missing ownership clause**
- **File:** `app/routers/doctor.py` — `override_patient_plan`
- **Problem:** The outer ownership check is correct. But inside the `if diffs:` block, a second patient fetch is made: `select(Patient).where(Patient.id == patient_id)` — the `Patient.doctor_id == did` clause is missing. Not an active exploit (patient_id was already verified above) but a latent IDOR. If the outer check is ever moved during refactoring, the second fetch becomes an open lookup.
- **Fix:** Change to `select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)` for defensive consistency.


### 🟠 Task 2 — High Issues

**Issue 3 — `log_meal` in `progress_service.py` does not verify `recommendation_id` belongs to the patient**
- **File:** `app/services/progress_service.py` — `log_meal`
- **Problem:** When a patient logs a meal with a `recommendation_id`, the service resolves the food_id by fetching:
  ```python
  select(Recommendation.meals).where(Recommendation.id == recommendation_id)
  ```
  There is no `AND Recommendation.patient_id = patient_id` clause. A patient can pass any `recommendation_id` — including one belonging to another patient — and the server silently uses that recommendation's meal data to resolve `food_id`. The meal log is still written to the correct patient (using `patient_id`) but the data extracted from the foreign recommendation corrupts the RL reward signal and calorie tracking. Note: `rate_meal` in `progress.py` correctly owns-checks the recommendation; `log_meal` does not.
- **Fix:** Change the query to:
  ```python
  select(Recommendation.meals).where(
      Recommendation.id == recommendation_id,
      Recommendation.patient_id == patient_id,
  )
  ```

**Issue 4 — Future clinical note deletion endpoint needs dual ownership check (pre-emptive)**
- **File:** `app/routers/doctor.py`
- **Problem:** There is a `POST` and `GET` for clinical notes but no `DELETE`. The `ClinicalNote` model has both `doctor_id` and `patient_id`. Any future delete endpoint must filter on both:
  ```python
  WHERE ClinicalNote.id = ? AND ClinicalNote.doctor_id = ? AND ClinicalNote.patient_id = ?
  ```
  If only `ClinicalNote.id` is used, Doctor A can delete Doctor B's clinical notes for any patient.
- **Fix:** Establish this as a code standard now so it is not missed when the delete endpoint is added.

### 🟡 Task 2 — Medium Issues

**Issue 5 — Hard-delete response leaks the deleted patient's email**
- **File:** `app/routers/admin.py` — `hard_delete_patient`
- **Problem:** Response includes `"email_freed": patient_email`. After deletion the email no longer exists in the DB — returning it in the response exposes a data point that is now deleted and should not be disclosed.
- **Fix:** Remove `email_freed` from the response. Return only `{"message": "Patient {id} permanently deleted."}`.

**Issue 6 — Adherence calculation does not check `is_active`**
- **File:** `app/services/progress_service.py` — `calculate_adherence`
- **Problem:** `select(Patient.meals_per_day, Patient.id).where(Patient.id == patient_id)` has no `is_active` check. An erased patient (is_active=False) can still have their adherence calculated. Low severity since the patient's token is invalid after erasure, but is an inconsistency.
- **Fix:** Add `.where(Patient.id == patient_id, Patient.is_active == True)`.

### Task 2 — Summary Table

| # | Severity | Vulnerability | File | Endpoint |
|---|---|---|---|---|
| 1 | 🔴 Critical | Any doctor can assign any other doctor's private recipe | `doctor.py` | `POST /doctor/recipes/{recipe_id}/assign` |
| 2 | 🔴 Critical | Inner patient fetch in plan override missing ownership clause | `doctor.py` | `PUT /doctor/patients/{id}/plan` |
| 3 | 🟠 High | `log_meal` does not verify `recommendation_id` belongs to patient | `progress_service.py` | `POST /progress/log/meal` |
| 4 | 🟠 High | Future note deletion endpoint needs dual ownership check | `doctor.py` | (endpoint not yet built) |
| 5 | 🟡 Medium | Hard-delete response leaks deleted email | `admin.py` | `DELETE /admin/patients/{id}/hard-delete` |
| 6 | 🟡 Medium | Adherence calculation doesn't check `is_active` | `progress_service.py` | `GET /progress/adherence/weekly` |


---

## Task 3 — Secrets & Credentials Scan

**Files read:** `.gitignore`, `.env`, `mitihar-patient-app/.env`, `mitihar-patient-app/.env.example`,
`mitihar-frontend/apps/.env`, `mitihar-frontend/apps/.env.example`,
`app/core/config.py`, `app/core/database.py`, `mitihar-patient-app/lib/axios.ts`,
`mitihar-frontend/apps/src/lib/axios.ts`, `mitihar-frontend/apps/src/stores/authStore.ts`,
`mitihar-frontend/apps/src/app/pages/Login.tsx`, `docker-compose.yml`,
`scripts/dump_creds.py`, `query_users.py`, `mitihar-patient-app/app.config.ts`.

### ✅ Task 3 — Already Correct

- **`.gitignore` is comprehensive:** Every `.env` file is gitignored at all three levels (backend root, `mitihar-patient-app/`, `mitihar-frontend/apps/`). Only `.env.example` files are committed.
- **Backend secrets are fully server-side:** `SECRET_KEY`, `GEMINI_API_KEY_*`, `DATABASE_URL`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CLIENT_ID` all live in the root `.env` and are read into `config.py` via `pydantic-settings`. None of them appear in any frontend file.
- **Frontend axios files contain zero secrets:** Both axios files reference only `EXPO_PUBLIC_API_URL` and `VITE_API_URL` — just API URLs, no keys.
- **Admin frontend auth store (`authStore.ts`) is clean:** Tokens live in memory only, never `localStorage` or `sessionStorage`. A comment explicitly documents this decision.
- **`docker-compose.yml` uses env substitution correctly:** `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}` causes Docker to fail loudly if the variable is missing — no hardcoded password.
- **`scripts/dump_creds.py` and `query_users.py`:** Use `os.getenv('DATABASE_URL')` and rely on the `.env` file. No hardcoded DB credentials.

### 🔴 Task 3 — Critical Issues

**Issue 1 — Real API keys present in `.env` — verify never committed to git**
- **File:** `.env` (root)
- **Problem:** The `.env` file contains four live Gemini API keys (`AIzaSy...`) and a live Google OAuth client secret (`GOCSPX-...`). While `.env` is gitignored, if it was ever committed accidentally even once, the keys are in git history permanently.
- **Action required (manual):**
  ```bash
  git log --all --full-history -- .env
  ```
  If any commits appear, rotate all keys immediately via Google Cloud Console and regenerate `SECRET_KEY`. Then use `git filter-repo` or BFG Repo Cleaner to purge the history.
- **Ongoing:** Rotate API keys every 90 days as a hygiene practice.

**Issue 2 — Admin and doctor passwords hardcoded in `Login.tsx` source code**
- **File:** `mitihar-frontend/apps/src/app/pages/Login.tsx`
- **Problem:** Quick-dev buttons contain hardcoded credential strings in committed source:
  ```ts
  setEmail('admin@mityahar.com');
  setPassword('Mityahar@2026');
  setEmail('dr.ashok.mehta@mitihar.test');
  setPassword('DoctorTest@2026');
  ```
  Anyone with repository read access sees the admin password. Since these match values in `.env`, the `.env` password is effectively public within the team git history.
- **Fix:** Replace hardcoded strings with `import.meta.env.VITE_DEV_ADMIN_EMAIL`, `VITE_DEV_ADMIN_PASSWORD`, `VITE_DEV_DOCTOR_EMAIL`, `VITE_DEV_DOCTOR_PASSWORD`. Add those vars to `mitihar-frontend/apps/.env` (gitignored) and to `.env.example` with placeholder values. Wrap the entire quick-dev block in `{import.meta.env.DEV && (...)}` so it is stripped from production builds.

**Issue 3 — `EXPO_PUBLIC_GOOGLE_CLIENT_ID` missing from patient app `.env`**
- **File:** `mitihar-patient-app/.env`
- **Problem:** The `.env.example` declares `EXPO_PUBLIC_GOOGLE_CLIENT_ID` and `app.config.ts` reads `process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID`. But the actual `.env` only has `EXPO_PUBLIC_API_URL`. Google Sign-In receives `undefined` as the client ID — silently broken.
- **Fix:** Add `EXPO_PUBLIC_GOOGLE_CLIENT_ID=753328753529-0j1bhpjbbk7l6g9b1rpfobq7rfqjistr.apps.googleusercontent.com` to `mitihar-patient-app/.env`. Note: the Google Client ID (not Client Secret) is safe to embed in mobile bundles — it is a public identifier by design. The `GOOGLE_CLIENT_SECRET` must remain server-side only.

**Issue 4 — `database.py` has a hardcoded fallback DB connection string**
- **File:** `app/core/database.py`
- **Problem:**
  ```python
  DATABASE_URL = os.getenv(
      "DATABASE_URL",
      "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"
  )
  ```
  The password `mityahar_dev` and username `admin` are committed in source code. If a developer forgets to set `DATABASE_URL` in their env, the app silently uses these credentials. These credentials are now permanently in git history.
- **Fix:** Remove the hardcoded fallback. Raise clearly if unset:
  ```python
  DATABASE_URL = os.environ.get("DATABASE_URL")
  if not DATABASE_URL:
      raise RuntimeError(
          "DATABASE_URL environment variable is not set. "
          "Copy .env.example to .env and fill in the database credentials."
      )
  ```


### 🟠 Task 3 — High Issues

**Issue 5 — `GEMINI_API_KEY_2`, `_3`, `_4` not declared in `config.py` Settings class**
- **File:** `app/core/config.py`
- **Problem:** `config.py` only declares `GEMINI_API_KEY_1: Optional[str] = None`. The other three keys exist in `.env` but have no corresponding field in `Settings`. They are accessible only via `os.getenv()` directly, bypassing the validated settings object. They are invisible to type checking and code review.
- **Fix:** Add to `Settings`:
  ```python
  GEMINI_API_KEY_2: Optional[str] = None
  GEMINI_API_KEY_3: Optional[str] = None
  GEMINI_API_KEY_4: Optional[str] = None
  ```
  Then replace any `os.getenv("GEMINI_API_KEY_2")` calls with `settings.GEMINI_API_KEY_2`.

**Issue 6 — `POSTGRES_PASSWORD` missing from root `.env`**
- **File:** `.env` (root)
- **Problem:** `docker-compose.yml` requires `POSTGRES_PASSWORD` (fails loudly if unset — correct). But the backend root `.env` does not define it, so `docker-compose up` using that `.env` fails on first run with no guidance. The `DATABASE_URL` has the password embedded but Docker reads `POSTGRES_PASSWORD` separately.
- **Fix:** Add `POSTGRES_PASSWORD=mityahar_dev` to the root `.env`. Add `POSTGRES_PASSWORD=your-secure-password-here` to `.env.example`.

### 🟡 Task 3 — Medium Issues

**Issue 7 — EAS `projectId` is a placeholder string committed in source**
- **File:** `mitihar-patient-app/app.config.ts`
- **Problem:** `eas: { projectId: "your-eas-project-id" }` is a placeholder. When EAS Build is configured, the real project ID goes here in committed source. EAS project IDs are public identifiers (not secret) but should come from an env var for consistency.
- **Fix:** `eas: { projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID ?? "your-eas-project-id" }`.

### Task 3 — Summary Table

| # | Severity | Finding | File | Action |
|---|---|---|---|---|
| 1 | 🔴 Critical | Real Gemini + OAuth keys in `.env` — verify never committed | `.env` | Check git log; rotate if ever committed |
| 2 | 🔴 Critical | Admin/doctor passwords hardcoded in `Login.tsx` source | `Login.tsx` | Move to `VITE_DEV_*` env vars; guard with `import.meta.env.DEV` |
| 3 | 🔴 Critical | `EXPO_PUBLIC_GOOGLE_CLIENT_ID` missing from patient app `.env` | `mitihar-patient-app/.env` | Add the Google Client ID |
| 4 | 🔴 Critical | Hardcoded DB credentials as fallback in `database.py` | `database.py` | Remove fallback; raise `RuntimeError` if unset |
| 5 | 🟠 High | `GEMINI_API_KEY_2/3/4` not declared in `config.py` | `config.py` | Add all four keys to `Settings` |
| 6 | 🟠 High | `POSTGRES_PASSWORD` missing from root `.env` | `.env` | Add it; add placeholder to `.env.example` |
| 7 | 🟡 Medium | EAS `projectId` is a placeholder in committed source | `app.config.ts` | Move to env var |


---

## Task 4 — Input Validation & Sanitization Audit

**Files read:** `app/schemas/user.py`, `app/schemas/patients.py`, `app/schemas/progress.py`,
`app/schemas/doctor.py`, `app/schemas/admin.py`, `app/routers/auth.py`,
`app/routers/admin.py`, `app/routers/doctor.py` (query params), `app/routers/progress.py`,
`app/services/progress_service.py`.

### ✅ Task 4 — Already Correct

- **`UserCreate`:** `email: EmailStr`, password `@field_validator` enforcing letter+digit mix, `activity_level: ActivityLevel` (enum), `diet: DietType` (enum), `health_condition: HealthCondition` (enum), `height/weight: float = Field(..., gt=0)`, `age: Optional[int] = Field(None, gt=0)`. These enums are defined in `user.py` and correctly used here.
- **`OnboardingRequest.date_of_birth`:** `@field_validator` ensures the date is in the past.
- **`MealRateRequest.rating`:** `@model_validator` enforces only `+1` or `-1`.
- **`GenerateCodesRequest`:** `count: int = Field(..., ge=1, le=50)`, `expires_in_days: int = Field(default=30, ge=1, le=365)`.
- **`BillingMarkPaidRequest.notes`:** Already has `max_length=500`.
- **Admin subscription override `status`:** Validated inline with `if status not in ("active", "inactive")`.
- **SQL injection:** All queries use SQLAlchemy ORM with parameterized statements. No raw SQL anywhere in the codebase. Zero SQL injection risk.
- **Command injection:** No `subprocess`, `os.system`, `os.popen`, or shell calls exist in any router or service. Zero command injection risk.
- **File uploads:** No file upload endpoints exist in the entire project. Zero upload surface.

### 🔴 Task 4 — Critical Issues

**Gap 1 — `ForgotPasswordRequest.email` is `str` not `EmailStr`**
- **File:** `app/routers/auth.py`
- **Problem:** `email: str = Field(..., min_length=3)`. Any string ≥3 characters passes. An attacker can send `"<script>alert(1)</script>"` or an arbitrarily long string. This is the password reset trigger — the email must be a valid RFC 5321 address.
- **Fix:** `email: EmailStr` — Pydantic validates format and normalizes the address automatically.

**Gap 2 — `ResetPasswordRequest.validate_password` is dead code — password complexity not enforced**
- **File:** `app/routers/auth.py`
- **Problem:** `@staticmethod` instead of `@field_validator("new_password")`. Pydantic never calls static methods automatically. New passwords set via reset have zero complexity enforcement beyond `min_length=8`. Passwords like `"aaaaaaaa"` or `"12345678"` pass.
- **Fix:**
  ```python
  @field_validator("new_password")
  @classmethod
  def validate_password(cls, v: str) -> str:
      if not any(c.isalpha() for c in v):
          raise ValueError("Password must contain at least one letter")
      if not any(c.isdigit() for c in v):
          raise ValueError("Password must contain at least one digit")
      return v
  ```

**Gap 3 — `MealLogCreate`: no enum on `meal_type`, no bounds on any numeric field**
- **File:** `app/schemas/progress.py`
- **Problem:**
  - `meal_type: str` — `"HACK"`, `"<script>alert(1)</script>"`, and `""` all pass. Stored in DB and embedded in JSONB recommendation structures rendered by the admin dashboard.
  - `calories: float` — no bounds. A patient can log 999,999 calories, corrupting TDEE-adjustment calculations. Or -1 calories to inflate "remaining" calories.
  - `protein`, `carbs`, `fat`, `fiber` — all `Optional[float]` with no bounds.
- **Fix:**
  ```python
  meal_type: Literal["Breakfast","MorningSnacks","Lunch","EveningSnacks","Dinner","Snack"]
  calories:  float = Field(..., ge=0, le=5000)
  protein:   Optional[float] = Field(default=0, ge=0, le=500)
  carbs:     Optional[float] = Field(default=0, ge=0, le=500)
  fat:       Optional[float] = Field(default=0, ge=0, le=500)
  fiber:     Optional[float] = Field(default=0, ge=0, le=200)
  ```

**Gap 4 — Water/steps/weight logs have no bounds whatsoever**
- **File:** `app/schemas/progress.py`
- **Problem:**
  - `WaterLogCreate.glasses: int` — no min, no max. `-999` and `999999` both pass.
  - `StepsLogCreate.steps: int` — no min, no max. The Guinness world record is ~70k steps/day.
  - `WeightLogCreate.weight: float` — no bounds. `0.001` kg and `9999` kg both pass.
  These feed directly into streak calculations, calorie adjustments, and the RL reward signal.
- **Fix:**
  ```python
  glasses: int   = Field(..., ge=0, le=50)
  steps:   int   = Field(..., ge=0, le=100_000)
  weight:  float = Field(..., gt=0, le=500)
  ```


### 🟠 Task 4 — High Issues

**Gap 5 — `OnboardingRequest`: six plain `str` fields should be enums**
- **File:** `app/schemas/patients.py`
- **Problem:** The enums `ActivityLevel`, `DietType`, `HealthCondition` are already defined in `user.py` but are not imported into `patients.py`. `gender`, `region`, and `pace_preference` need new `Literal` types. Without these, a patient can submit `"gender": "<script>alert(1)</script>"` which gets stored in the DB and later rendered in the admin patient list.
- **Fields affected:** `gender`, `activity_level`, `diet_type`, `region`, `health_condition`, `pace_preference`
- **Fix:**
  ```python
  from .user import ActivityLevel, DietType, HealthCondition
  from typing import Literal

  gender:           Literal["Male","Female","Other"]
  activity_level:   ActivityLevel = ActivityLevel.LIGHTLY_ACTIVE
  diet_type:        DietType = DietType.VEGETARIAN
  region:           Literal["North","South","East","West"] = "North"
  health_condition: HealthCondition = HealthCondition.HEALTHY
  pace_preference:  Literal["slow","moderate","fast"] = "moderate"
  ```

**Gap 6 — `OnboardingRequest` list fields have no per-item validation and no size limits**
- **File:** `app/schemas/patients.py`
- **Problem:** `health_goals`, `medical_conditions`, `food_allergies`, `dietary_preferences`, `fasting_days`, `eating_habits` are all `list[str]` with no item length cap and no list size cap. A patient can submit 10,000 items each 10,000 characters long — a memory/DoS attack. Items are also interpolated into Gemini AI prompts — an XSS/prompt-injection payload here goes directly into the meal generation model.
- **Fix:** Pydantic v2 approach using `Annotated`:
  ```python
  from typing import Annotated
  BoundedStrList = Annotated[list[Annotated[str, Field(max_length=100)]], Field(max_length=20)]

  health_goals:        BoundedStrList = Field(default_factory=list)
  medical_conditions:  BoundedStrList = Field(default_factory=list)
  food_allergies:      BoundedStrList = Field(default_factory=list)
  dietary_preferences: BoundedStrList = Field(default_factory=list)
  fasting_days:        BoundedStrList = Field(default_factory=list)
  eating_habits:       BoundedStrList = Field(default_factory=list)
  ```

**Gap 7 — `OnboardingRequest` numeric fields have no bounds**
- **File:** `app/schemas/patients.py`
- **Problem:** `meals_per_day`, `sleep_hours`, `water_glasses`, `nonveg_meals_per_week`, `target_weight_kg`, and `occupation` have no bounds or length caps.
- **Fix:**
  ```python
  meals_per_day:          int            = Field(default=3,   ge=1,  le=10)
  sleep_hours:            float          = Field(default=7.0, ge=0,  le=24)
  water_glasses:          int            = Field(default=8,   ge=0,  le=30)
  nonveg_meals_per_week:  int            = Field(default=0,   ge=0,  le=21)
  target_weight_kg:       Optional[float]= Field(default=None, gt=0, le=500)
  occupation:             Optional[str]  = Field(default=None, max_length=100)
  ```

**Gap 8 — `ClinicalNoteCreate.note_type` is plain `str`, `content` has no max_length**
- **File:** `app/schemas/doctor.py`
- **Problem:** `note_type` is stored in the DB and displayed in the admin audit dashboard — any string passes. `content` has `min_length=1` but no `max_length` — a doctor could submit a 10 MB note.
- **Fix:**
  ```python
  note_type: Literal["general","dietary","medical","progress"] = "general"
  content:   str = Field(..., min_length=1, max_length=5000)
  ```

**Gap 9 — `MealPlanNoteRequest.meal_date` and `meal_type` are unvalidated strings, `note` has no max**
- **File:** `app/schemas/doctor.py`
- **Problem:** `meal_date: str` — any string passes. `meal_type: str` — any string passes. `note: str` has `min_length=1` but no `max_length`. Notes are injected directly into meal JSONB which is rendered in the patient app — an XSS vector if the app renders HTML without escaping.
- **Fix:**
  ```python
  meal_date: date   # Pydantic parses and validates date format; serialize to str in the handler
  meal_type: Literal["Breakfast","MorningSnacks","Lunch","EveningSnacks","Dinner"]
  note:      str = Field(..., min_length=1, max_length=1000)
  ```
  In the handler, convert `body.meal_date` to `str(body.meal_date)` for the JSONB comparison.

**Gap 10 — `RecipeCreateRequest`: unvalidated `slot_type`, `diet_type`, tag lists, and `ingredients`**
- **File:** `app/schemas/doctor.py`
- **Problem:**
  - `slot_type: str` and `diet_type: str` — descriptive comments list valid values but no enforcement.
  - `meal_time_tags`, `plan_type_tags`, `region_tags`: `list[str]` with no item validation or size cap.
  - `ingredients: list[dict]` — completely unvalidated JSONB. A doctor can inject arbitrary nested JSON into the meal generator prompt and patient plan JSONB.
  - `recipe_name: str = Field(..., min_length=2)` — no max_length.
  - `cal_per_serving: float = Field(..., gt=0)` — no upper bound. `999999` kcal passes.
- **Fix:** Define an `IngredientItem` typed model, use `Literal` for enums, cap all lists and strings:
  ```python
  class IngredientItem(BaseModel):
      name:     str   = Field(..., min_length=1, max_length=100)
      quantity: str   = Field(..., min_length=1, max_length=50)
      unit:     str   = Field(..., min_length=1, max_length=20)

  slot_type:      Literal["grain","dal_protein","main_dish","sabzi","beverage","snack_item","fruit","egg_dish"]
  diet_type:      Literal["Vegetarian","Non-Vegetarian","Eggetarian"]
  recipe_name:    str = Field(..., min_length=2, max_length=200)
  cal_per_serving: float = Field(..., gt=0, le=5000)
  ingredients:    list[IngredientItem] = Field(default_factory=list, max_length=50)
  meal_time_tags: Annotated[list[Annotated[str, Field(max_length=50)]], Field(max_length=10)]
  plan_type_tags: Annotated[list[Annotated[str, Field(max_length=50)]], Field(max_length=10)]
  region_tags:    Annotated[list[Annotated[str, Field(max_length=50)]], Field(max_length=10)]
  ```

**Gap 11 — `RecipeAssignRequest.meal_date` and `meal_type` are unvalidated strings**
- **File:** `app/schemas/doctor.py`
- **Problem:** Same pattern as Gap 9 — plain strings with no format or allowlist enforcement. `note` has no `max_length`.
- **Fix:**
  ```python
  meal_date: date
  meal_type: Literal["Breakfast","MorningSnacks","Lunch","EveningSnacks","Dinner"]
  note:      Optional[str] = Field(default=None, max_length=500)
  ```

**Gap 12 — `PlanOverrideRequest.meals` is fully unvalidated, `doctor_notes` has no max_length**
- **File:** `app/schemas/doctor.py`
- **Problem:** `meals: Optional[list] = None` — a list of anything. Written directly to `rec.meals` (JSONB) and rendered in the patient app. A malicious doctor could inject `<script>` tags, oversized payloads, or corrupt meal structure. `doctor_notes: Optional[str] = None` — no max_length.
- **Fix:**
  ```python
  meals:        Optional[list[dict]] = None  # minimum; ideally a typed MealSlot model
  doctor_notes: Optional[str] = Field(default=None, max_length=2000)
  ```
  Long-term: define a `MealSlot` Pydantic model matching the exact meal JSONB structure and use `Optional[list[MealSlot]]`.


### 🟡 Task 4 — Medium Issues

**Gap 13 — Admin query parameters `search`, `actor_role`, `action`, `source` have no limits or allowlists**
- **File:** `app/routers/admin.py` — `list_patients`, `get_audit_logs`, `list_food_items`
- **Problem:**
  - `search: Optional[str] = Query(default=None)` — no max_length. Passed into `ilike(f"%{search.strip()}%")`. While ORM parameterization prevents SQL injection, a 100,000-character `search` string forces a full table scan with a massive LIKE pattern (ReDoS-adjacent behavior).
  - `actor_role` and `action` are passed directly into ORM equality/LIKE filters with no allowlist.
  - `source` is passed directly into `FoodItem.source == source` with no allowlist.
- **Fix:**
  ```python
  search:     Optional[str]     = Query(default=None, max_length=100)
  actor_role: Optional[Literal["patient","doctor","admin"]] = Query(default=None)
  action:     Optional[str]     = Query(default=None, max_length=50)
  source:     Optional[Literal["manual","doctor","doctor_global","rejected"]] = Query(default=None)
  ```

**Gap 14 — Doctor `search` query parameter has no length cap**
- **File:** `app/routers/doctor.py` — `list_patients`
- **Problem:** `search: Optional[str] = Query(default=None)` — same unbounded LIKE pattern issue as Gap 13.
- **Fix:** `search: Optional[str] = Query(default=None, max_length=100)`

**Gap 15 — `BillingMarkPaidRequest.period` has no format pattern**
- **File:** `app/routers/admin.py` — `BillingMarkPaidRequest`
- **Problem:** `period: Optional[str] = Field(default=None, description="e.g. '2026-03'")`. Any string passes. Stored in audit log `detail` JSONB and displayed on the billing dashboard.
- **Fix:** `period: Optional[str] = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")` — enforces `YYYY-MM` format exactly.

**Gap 16 — `CreateDoctorRequest` lacks field max_lengths, phone format, and password complexity**
- **File:** `app/schemas/admin.py`
- **Problem:**
  - `name`, `specialization`, `clinic_name`, `city`: no `max_length` — unlimited strings stored in the DB.
  - `phone: Optional[str] = None` — no format validation, no length cap.
  - `password: str = Field(..., min_length=8)` — only min_length. Doctor account passwords have no letter+digit complexity requirement, unlike patient accounts. `"12345678"` passes.
- **Fix:**
  ```python
  name:           str           = Field(..., min_length=1, max_length=100)
  phone:          Optional[str] = Field(default=None, max_length=20,
                                        pattern=r"^\+?[\d\s\-\(\)]{7,20}$")
  specialization: Optional[str] = Field(default=None, max_length=100)
  clinic_name:    Optional[str] = Field(default=None, max_length=200)
  city:           Optional[str] = Field(default=None, max_length=100)

  @field_validator("password")
  @classmethod
  def password_strength(cls, v: str) -> str:
      if not any(c.isalpha() for c in v):
          raise ValueError("Password must contain at least one letter")
      if not any(c.isdigit() for c in v):
          raise ValueError("Password must contain at least one digit")
      return v
  ```

### Task 4 — Summary Table

| # | Severity | Gap | File | Fields |
|---|---|---|---|---|
| 1 | 🔴 Critical | `ForgotPasswordRequest.email` is `str` not `EmailStr` | `auth.py` | `email` |
| 2 | 🔴 Critical | Reset password validator is dead `@staticmethod` | `auth.py` | `new_password` |
| 3 | 🔴 Critical | `MealLogCreate` — no enum on `meal_type`, no numeric bounds | `progress.py` | 6 fields |
| 4 | 🔴 Critical | Water / steps / weight log schemas have no bounds | `progress.py` | 3 schemas |
| 5 | 🟠 High | `OnboardingRequest` — 6 plain `str` fields should be enums | `patients.py` | gender, activity_level, diet_type, region, health_condition, pace_preference |
| 6 | 🟠 High | Onboarding list fields — no item length cap, no list size cap | `patients.py` | 6 list fields |
| 7 | 🟠 High | Onboarding numeric fields — no bounds | `patients.py` | meals_per_day, sleep_hours, water_glasses, nonveg_meals_per_week, target_weight_kg, occupation |
| 8 | 🟠 High | `ClinicalNoteCreate.note_type` plain `str`, `content` no max_length | `doctor.py` | 2 fields |
| 9 | 🟠 High | `MealPlanNoteRequest` — unvalidated date/type strings, note no max | `doctor.py` | 3 fields |
| 10 | 🟠 High | `RecipeCreateRequest` — unvalidated slot/diet types, tags, ingredients | `doctor.py` | 6+ fields |
| 11 | 🟠 High | `RecipeAssignRequest` — unvalidated date/type strings | `doctor.py` | 3 fields |
| 12 | 🟠 High | `PlanOverrideRequest.meals` fully unvalidated, notes no max | `doctor.py` | 2 fields |
| 13 | 🟡 Medium | Admin query params uncapped / unenumerated | `admin.py` | search, actor_role, action, source |
| 14 | 🟡 Medium | Doctor `search` query param uncapped | `doctor.py` | search |
| 15 | 🟡 Medium | `BillingMarkPaidRequest.period` no format pattern | `admin.py` | period |
| 16 | 🟡 Medium | `CreateDoctorRequest` no max_lengths, no phone format, weak password | `admin.py` | 6 fields |


---

## Master Fix Checklist

Use this as the implementation order. Fix all 🔴 Critical items before moving to 🟠 High.

### 🔴 Critical — Fix First (13 items)

**Auth (Task 1)**
- [x] **T1-1** `limiter.py` — connect slowapi to Redis storage; add startup warning if in-memory fallback used
- [x] **T1-2** `auth.py` — move patient refresh token to HttpOnly cookie; updated `/refresh` to cookie-only for all roles
- [x] **T1-3** `security.py` — replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)`
- [x] **T1-4** `auth.py` — added explicit `options={"verify_exp": True, "verify_iat": True, "verify_nbf": True}` to `_decode_partial_token`

**Secrets (Task 3)**
- [ ] **T3-1** ⚠️ MANUAL ACTION REQUIRED — run `git log --all --full-history -- .env`; if any commits appear, rotate all Gemini keys + Google OAuth secret + `SECRET_KEY` immediately via their respective consoles, then use `git filter-repo` or BFG to purge history
- [x] **T3-2** `Login.tsx` — credentials moved to `VITE_DEV_*` env vars; block wrapped in `{import.meta.env.DEV && (...)}`
- [x] **T3-3** `mitihar-patient-app/.env` — added `EXPO_PUBLIC_GOOGLE_CLIENT_ID`
- [x] **T3-4** `database.py` — hardcoded DB fallback removed; raises `RuntimeError` if `DATABASE_URL` unset

**Input Validation (Task 4)**
- [x] **T4-1** `auth.py` — `ForgotPasswordRequest.email` changed from `str` to `EmailStr`
- [x] **T4-2** `auth.py` — `ResetPasswordRequest.validate_password` fixed from `@staticmethod` to `@field_validator("new_password")`
- [x] **T4-3** `progress.py` (schema) — `MealLogCreate.meal_type` → `Literal`; all numeric fields bounded
- [x] **T4-4** `progress.py` (schema) — `WaterLogCreate.glasses`, `StepsLogCreate.steps`, `WeightLogCreate.weight` all bounded

**IDOR (Task 2)**
- [x] **T2-1** `doctor.py` — recipe ownership check added to `assign_recipe`
- [x] **T2-2** `doctor.py` — inner patient fetch in `override_patient_plan` now includes `Patient.doctor_id == did`

### 🟠 High — Fix Second (14 items)

**Auth (Task 1)**
- [x] **T1-5** `security.py` + `config.py` — `REQUIRE_EMAIL_VERIFICATION` flag added; enforced in `get_current_patient`
- [x] **T1-6** `db_models.py` + `auth.py` — `failed_login_attempts` + `locked_until` added to all three models; lockout enforced in all login handlers ⚠️ Run Alembic migration
- [x] **T1-7** `db_models.py` + `auth.py` + `security.py` — `password_changed_at` column added; set on reset; token `iat` checked in `get_current_patient` ⚠️ Run Alembic migration
- [x] **T1-8** `main.py` — `COOKIE_SECURE=False` logs CRITICAL warning on non-localhost hosts at startup

**IDOR (Task 2)**
- [x] **T2-3** `progress_service.py` — `log_meal` recommendation query now scoped to `patient_id`
- [x] **T2-4** Documented: future note-delete endpoint must filter `ClinicalNote.id AND doctor_id AND patient_id`

**Secrets (Task 3)**
- [x] **T3-5** `config.py` — `GEMINI_API_KEY_2/3/4` added to `Settings`; also added `REDIS_URL`
- [x] **T3-6** `.env` — `POSTGRES_PASSWORD` added; `REDIS_URL` + all Gemini keys added to `.env.example`

**Input Validation (Task 4)**
- [x] **T4-5** `patients.py` — 6 plain `str` fields replaced with `ActivityLevel`/`DietType`/`HealthCondition` enums + Literals
- [x] **T4-6** `patients.py` — `BoundedStrList` (max 20 items × 100 chars) applied to all 6 list fields
- [x] **T4-7** `patients.py` — all numeric fields bounded (`meals_per_day`, `sleep_hours`, `water_glasses`, `nonveg_meals_per_week`, `target_weight_kg`, `occupation`)
- [x] **T4-8** `doctor.py` (schema) — `ClinicalNoteCreate.note_type` → `Literal`; `content` → `max_length=5000`
- [x] **T4-9** `doctor.py` (schema) — `MealPlanNoteRequest.meal_date` → `date`; `meal_type` → `Literal`; `note` → `max_length=1000`; router updated to `str(body.meal_date)`
- [x] **T4-10** `doctor.py` (schema) — `RecipeCreateRequest`: `slot_type`/`diet_type` → `Literal`; tags → `BoundedTagList`; `IngredientItem` typed model; `cal_per_serving` capped; router serialises via `.model_dump()`
- [x] **T4-11** `doctor.py` (schema) — `RecipeAssignRequest.meal_date` → `date`; `meal_type` → `Literal`; `note` → `max_length=500`; router uses `str(body.meal_date)`
- [x] **T4-12** `doctor.py` (schema) — `PlanOverrideRequest.meals` → `Optional[list[dict]]`; `doctor_notes` → `max_length=2000`

### 🟡 Medium — Fix Third (8 items)

**Auth (Task 1)**
- [x] **T1-9** `auth.py` — `ResetPasswordRequest.validate_password` now `@field_validator` (same fix as T4-2; covered)
- [x] **T1-10** `main.py` — CORS `allow_methods` and `allow_headers` tightened to explicit lists
- [x] **T1-11** `auth.py` — `resend_verification_email` refactored to use `Depends(get_current_patient)` properly

**Secrets (Task 3)**
- [x] **T3-7** `app.config.ts` — EAS `projectId` reads from `EXPO_PUBLIC_EAS_PROJECT_ID` env var

**Input Validation (Task 4)**
- [x] **T4-13** `admin.py` (router) — `search` capped at 100; `actor_role` → `Literal`; `action` capped at 50; `source` → `Literal`
- [x] **T4-14** `doctor.py` (router) — `search` capped at 100
- [x] **T4-15** `admin.py` (schema) — `BillingMarkPaidRequest.period` enforces `YYYY-MM` pattern
- [x] **T4-16** `admin.py` (schema) — `CreateDoctorRequest`: all text fields capped; phone format pattern; password complexity validator added

---

---

## Ultrareview Fixes (2026-04-20)

Five additional bugs found and fixed in a follow-up ultrareview pass:

| ID | Severity | Fix | File |
|---|---|---|---|
| bug_019 | 🟡 Medium | CSP `connect-src` now built dynamically from `settings.CORS_ORIGINS` instead of a hardcoded stale URL | `middleware.py` |
| merged_bug_017 | 🟡 Medium | `_AUTH_PREFIXES` collapsed to one entry (dead `/doctors/auth` removed from `SubscriptionCheckMiddleware`); dead login skip in `AdminIPWhitelistMiddleware` removed | `middleware.py` |
| bug_012 | 🟠 High | Google OAuth new-user branch now enforces `gdpr_consent=True` — previously any new patient could register via Google without accepting the data policy | `auth.py` |
| bug_011 | 🟡 Medium | `PatientVisit` creation in `/patients/onboarding` now idempotency-guarded — duplicate onboarding calls no longer create duplicate visit rows | `patients.py` |
| merged_bug_009 | 🔴 Critical | TOCTOU race condition on `POST /patients/activate` — SubscriptionCode SELECT now uses `.with_for_update()` row-level lock, preventing double-spend under concurrent calls | `patients.py` |

All five fixes are committed on `feature/api-remediation-v0.2`.

---

## Notes for Implementation

- **No SQL injection risk** — all queries use SQLAlchemy ORM parameterized statements. No raw SQL anywhere.
- **No command injection risk** — no `subprocess`, `os.system`, or shell calls in any router or service.
- **No file upload risk** — no file upload endpoints exist in the entire project.
- **DB migrations needed for Task 1 Issues 6, 7, 12:** Adding `failed_login_attempts`, `locked_until`, and `password_changed_at` columns requires Alembic migrations. Run `alembic revision --autogenerate -m "auth_security_columns"` after adding the ORM fields.
- **Enum changes in Task 4** may reject previously stored data if enum values don't match existing DB rows. Verify all existing DB values match the new Literal/Enum constraints before deploying schema changes to a database with real data.
- **`meal_date: date` in Task 4 Gaps 9, 11** — Pydantic will parse `"2026-03-15"` strings automatically. In the handler, convert back to string for JSONB comparison: `str(body.meal_date)`.
