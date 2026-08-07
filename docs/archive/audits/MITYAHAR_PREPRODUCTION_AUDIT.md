# Mityahar — Pre-Production Audit Report
**Date:** 2026-03-31  
**Stack:** FastAPI (Python) · React (Vite/TS) · React Native (Expo)  
**Auditor:** Full-stack static analysis (no live server required)

---

## 1. Issues Found

### 🔴 CRITICAL

---

**C-1 · API Port Mismatch — All Frontend → Backend Traffic Is Dead by Default**

| File | Line | Value |
|---|---|---|
| `mitihar-frontend/apps/.env` | 4 | `VITE_API_URL=http://localhost:8000/api/v1` |
| `mitihar-frontend/apps/src/lib/axios.ts` | 21 | fallback `http://localhost:8000/api/v1` |
| `mitihar-patient-app/.env` | 1 | `EXPO_PUBLIC_API_URL=http://192.168.0.100:8000/api/v1` |
| `mitihar-patient-app/lib/axios.ts` | 15 | fallback `http://10.0.2.2:8000/api/v1` |

The backend runs on **port 8001** (per `MITYAHAR_TESTING_GUIDE.md` and project startup docs). Both the doctor web dashboard and the patient mobile app point to port **8000**. Every API call from both frontends will receive a connection refused error until this is corrected in all four locations above.

---

**C-2 · Mobile App Hardcoded to Developer's Personal LAN IP**

`mitihar-patient-app/.env` line 1:
```
EXPO_PUBLIC_API_URL=http://192.168.0.100:8000/api/v1
```
`192.168.0.100` is a local machine IP. This value is baked into every Expo build. The app will fail to connect on any device not on the same router. On a physical device over cellular, or on any other developer's machine, the app is non-functional.

---

**C-3 · Mobile Meal Logging Calls the Wrong Endpoint (404 on Every Log)**

`mitihar-patient-app/services/progress.ts` line 22:
```ts
const { data } = await api.post("/progress/meal", payload);
```
Backend defines: `POST /api/v1/progress/log/meal` (`app/routers/progress.py` line 27).  
The mobile app sends to `/progress/meal` — a path that does not exist. Every meal log attempt from the patient app silently fails with a 404.

---

**C-4 · Mobile Shopping-List Toggle — Double Mismatch (Wrong Format + Missing Param)**

`mitihar-patient-app/services/meals.ts` line 42:
```ts
await api.post("/meal-plan/shopping-list/toggle", { ingredient_name });
```
The backend route (`app/routers/meal_plan.py` lines 253–258) declares:
```python
ingredient_name: str = Query(...),
at_home: bool = Query(...),       # ← required, not optional
```
Two problems: (1) the mobile app sends a JSON body, but the backend reads **query parameters**; (2) the required `at_home` boolean is never sent at all. Every toggle call returns HTTP 422 Unprocessable Entity. The shopping-list check-off feature is completely broken on mobile.

---

**C-5 · Patient Mobile App Calls a Doctor-Gated Route for Subscription Renewal**

`mitihar-patient-app/services/profile.ts` line 72:
```ts
await api.post(`/doctor/patients/${patientId}/request-renewal`);
```
`/api/v1/doctor/*` is protected by `DoctorIsolationMiddleware` (`app/main.py` line 134). Any request arriving with a patient JWT is rejected with HTTP 403 before it reaches the handler. Patients using the renewal flow in the app will get a 403 on every attempt. There is no patient-facing renewal endpoint in `app/routers/patients.py`.

---

**C-6 · `TodaySummary` Type Completely Mismatched with Backend Response**

`mitihar-patient-app/types/index.ts` lines 162–168 declares:
```ts
interface TodaySummary {
  tdee: number;
  calories_consumed: number;
  water: number;
  steps: number;
  streak: number;
}
```
The backend `GET /progress/today` (`app/routers/progress.py` lines 148–162) returns:
```python
{
  "calories": { "consumed": ..., "target": ..., "remaining": ... },
  "water_intake": { "glasses": ..., "target": 8 },
  "activity": { "steps": ..., "target_steps": 10000 },
}
```
Fields are nested, not flat. No `tdee`, `streak`, or top-level `calories_consumed` exist. The home screen (`app/(tabs)/index.tsx` lines 202–205) reads:
```ts
const cals   = today?.calories_consumed ?? 0;   // always 0
const streak = today?.streak ?? 0;               // always 0
```
**The calorie ring, streak pill, and all progress indicators on the home screen always display zero.** Users who have logged data will never see it reflected in the UI.

---

**C-7 · `ALLOW_HARD_DELETE=True` Set in Root `.env`**

`/.env` line 16:
```
ALLOW_HARD_DELETE=True
```
This enables `DELETE /api/v1/admin/patients/{id}/hard-delete` which physically removes the patient row and all associated data. The flag is gated in `app/core/config.py` with a comment "*MUST be False in production*". It is currently `True` and anyone with admin access (or whose credentials are leaked) can permanently and irreversibly wipe patient records. This must be `False` everywhere except a developer's local machine.

---

**C-8 · Nutrition Lookup Endpoint Name Mismatch**

`mitihar-frontend/apps/src/lib/doctorApi.ts` line 318:
```ts
apiClient.post('/doctor/recipes/lookup', { food_name: dishName })
```
Backend defines: `POST /api/v1/doctor/recipes/estimate` with body field `dish_name` (not `food_name`) — `app/routers/doctor.py` ~line 1055.  
Two issues: the URL path (`lookup` vs `estimate`) does not exist, and the field name is wrong (`food_name` vs `dish_name`). The Gemini nutrition estimation feature on the Recipes page is completely broken.

---

### 🟡 WARNING

---

**W-1 · CORS Origins Do Not Include Backend's Actual Port**

`/.env` line 41:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:5173,http://localhost:8000
```
If the backend runs on port 8001, the CORS list includes port 8000 (legacy) but not 8001. Browsers making cross-origin requests from `localhost:5173` (Vite) will be blocked for preflight OPTIONS requests that include an origin not in this list. Vite (5173) is present, so the web app works, but any tooling hitting the 8001 base URL directly will fail CORS.

---

**W-2 · `PlatformStats` TypeScript Interface Missing New Backend Fields**

`mitihar-frontend/apps/src/lib/adminApi.ts` lines 26–31:
```ts
export interface PlatformStats {
  total_patients: number;
  active_subscriptions: number;
  total_doctors: number;
  total_plans_generated: number;
}
```
The backend `GET /admin/stats` now also returns `expiring_soon_count`, `pending_renewals_count`, and `total_consultations_this_month` (`app/routers/admin.py` lines 68–84). `AdminOverview.tsx` reads these correctly with optional chaining (`stats?.expiring_soon_count ?? 0`), so there is no runtime crash. But TypeScript will emit type errors, and if strict mode is enforced in CI, builds will fail.

---

**W-3 · `registerPatient` Response Typed with Non-Existent `user_id` Field**

`mitihar-patient-app/services/auth.ts` line 23:
```ts
return data as { message: string; user_id: number; doctor_connected: boolean };
```
`POST /api/v1/auth/register` (`app/routers/auth.py` ~line 165) returns `{ message, doctor_connected }` — no `user_id`. Any screen consuming `user_id` from this response receives `undefined`, which silently becomes `NaN` when used in arithmetic or API calls.

---

**W-4 · `ActivateResponse` Type Mismatched with Backend Schema**

`mitihar-patient-app/types/index.ts` lines 208–213:
```ts
interface ActivateResponse {
  message: string;
  doctor_name?: string;
  access_token?: string;
  token_type?: string;
}
```
`POST /api/v1/patients/activate` returns `ActivationResponse` from `app/schemas/patients.py`, which contains `{ patient: PatientProfile, access_token, refresh_token }`. The frontend type is missing `refresh_token` and `patient`, and includes `doctor_name` which doesn't exist. Screens reading `doctor_name` from the activate response will always get `undefined`.

---

**W-5 · `ShoppingItem` Field Name Mismatch (`have_at_home` vs `at_home`)**

`mitihar-patient-app/types/index.ts` line 152: `have_at_home: boolean`  
Backend (`app/routers/meal_plan.py` line 228): item dict uses `"at_home"` key.  
The mobile shopping list will never show any item as checked regardless of its stored state.

---

**W-6 · Dead Code / Unreachable Exception in `meal_plan.py`**

`app/routers/meal_plan.py` lines 181–182:
```python
return {}
raise HTTPException(status_code=404, detail="No active meal plan found")  # ← never reached
```
The `HTTPException` is unreachable. The endpoint silently returns `{}` on a missing plan. The frontend handles this (`services/meals.ts` lines 9–12), so no crash — but this was clearly meant to be a 404 and the logic was broken during a refactor.

---

**W-7 · `LoginResponse` Type Includes `refresh_token` for Doctor/Admin Login**

`mitihar-frontend/apps/src/lib/types.ts` line 14:
```ts
export interface LoginResponse {
  access_token: string;
  refresh_token: string;   // ← not returned for doctor/admin
  token_type: 'bearer';
}
```
Doctor and admin logins (`/auth/doctor/login`, `/auth/admin/login`) return `{ access_token, token_type }` only — the refresh token is placed in an HttpOnly cookie. The frontend never reads `refresh_token` from the response body for these roles, so there's no functional crash, but the type contract is violated and will cause TypeScript noise.

---

**W-8 · Rate Limiter Uses In-Memory Storage (Not Production-Safe)**

`app/main.py` line 111:
```python
# TODO: Switch to RedisStorage before multi-worker/production deployment
limiter = Limiter(key_func=get_remote_address)
```
`REDIS_URL` is `None` in `app/core/config.py` (line 30) and not set in `.env`. The in-memory rate limiter state is per-process. Under `uvicorn --workers N`, every worker has an independent counter — so a client can exceed the rate limit N× before being blocked. In production this must be backed by Redis.

---

**W-9 · `print()` Used for Error Logging in Production Code**

`app/routers/progress.py` lines 120–121:
```python
print("Auto-regenerated diet plan upon weight update")
print(f"Failed to auto-generate diet plan: {e}")
```
`print()` writes to stdout and is invisible in any log aggregation system (Sentry, Loki, CloudWatch). These should use `logging.getLogger(__name__).info/error(...)` like the rest of the codebase.

---

**W-10 · Email Verification Not Enforced**

`app/core/config.py` line 54:
```python
REQUIRE_EMAIL_VERIFICATION: bool = False
```
Email verification tokens are generated on registration and logged to console (`app/routers/auth.py` ~line 143), but logins are never gated on `is_email_verified`. Sending real verification emails (Phase 7) and enabling this flag must happen together before production, otherwise unverified accounts accumulate silently.

---

**W-11 · `PublicDoctorResponse` Includes Fields Not on the Doctor Model**

`mitihar-patient-app/services/profile.ts` lines 56–68 declares `PublicDoctor` with fields `experience_years`, `fee_per_month`, `rating`, `review_count`, `is_accepting`. These need to be verified against `app/schemas/patients.py` `PublicDoctorResponse` and the `Doctor` DB model. If these columns don't exist on the table, the API will return 500 on `GET /patients/doctors`.

---

**W-12 · Doctor Patient-Progress Endpoint Not Wired in `doctorApi.ts`**

Backend: `GET /api/v1/doctor/patients/{id}/progress` exists (`app/routers/doctor.py` ~line 450).  
Frontend: `doctorApi.ts` has no `getPatientProgress()` function.  
The patient progress chart tab in `PatientDetail.tsx` likely falls back to empty or mock data.

---

**W-13 · Sensitive Credentials in Cleartext `.env` (Gitignored, but Live)**

`/.env` contains:
- 4 live Gemini API keys (`GEMINI_API_KEY_1` through `_4`)
- Google OAuth client secret (`GOOGLE_CLIENT_SECRET`)
- PostgreSQL password (`POSTGRES_PASSWORD=mityahar_dev`)
- JWT `SECRET_KEY` (256-bit hex)

`.gitignore` correctly excludes `.env`, so these are not in git history. However, they are live production-capable keys sitting in a plaintext file on a developer workstation. Any accidental copy, screen share, or backup will expose them. Move secrets to a secrets manager (Doppler, AWS Secrets Manager, or at minimum a password-protected vault) before production.

---

### 🔵 MINOR

---

**M-1 · Admin Endpoints Not Surfaced in `adminApi.ts`**

Backend has `GET /admin/consultations`, `GET /admin/consultations/annual`, `GET /admin/renewals`, and `POST /admin/renewals/{id}/override-approve`. None are in `adminApi.ts`. The corresponding admin pages (`Billing.tsx`) likely show incomplete data.

---

**M-2 · Doctor Plan Overrides History Not Wired**

Backend: `GET /api/v1/doctor/patients/{id}/plan/overrides` (doctor.py ~line 290).  
No matching function in `doctorApi.ts`. The RL override audit trail is never visible in the UI.

---

**M-3 · `MacroRow` on Home Screen Always Renders 0**

`app/(tabs)/index.tsx` ~line 255:
```tsx
<MacroRow protein={0} carbs={0} fat={0} />
```
Hardcoded zeros — macros are never computed from the meal plan data. Even when a plan is loaded, macros stay at 0.

---

**M-4 · `hasUnread` Notification Badge is Hardcoded `true`**

`app/(tabs)/index.tsx` line 209:
```ts
const hasUnread = true; // static badge — Phase 5 FCM will drive this
```
The bell icon always shows a red dot, regardless of whether the user has unread notifications. This degrades trust — users will stop reacting to the badge.

---

**M-5 · `ActivateResponse` Missing `refresh_token` on Mobile**

`app/routers/patients.py` line 264 returns `{ patient, access_token, refresh_token }`. The mobile `profile.ts` does not store the new `refresh_token` after activation. The patient's old refresh token will be used until it expires (7 days), at which point the silent refresh fails and the user is logged out.

---

---

## 2. API Endpoint Status

| Endpoint | Method | Web (Doctor/Admin) | Mobile (Patient) | Notes |
|---|---|---|---|---|
| `/auth/register` | POST | — | ⚠️ At Risk | Response type includes `user_id` which backend doesn't return (W-3) |
| `/auth/token` | POST | — | ✅ OK | Patient login; form-encoded correctly |
| `/auth/doctor/login` | POST | ✅ OK | — | Correct form-encoding |
| `/auth/admin/login` | POST | ✅ OK | — | Correct form-encoding |
| `/auth/doctor/mfa-login` | POST | ✅ OK | — | — |
| `/auth/admin/mfa-login` | POST | ✅ OK | — | — |
| `/auth/doctor/mfa-setup` | POST | ✅ OK | — | — |
| `/auth/doctor/mfa-confirm` | POST | ✅ OK | — | — |
| `/auth/doctor/mfa-disable` | POST | ✅ OK | — | — |
| `/auth/admin/mfa-setup` | POST | ✅ OK | — | — |
| `/auth/admin/mfa-confirm` | POST | ✅ OK | — | — |
| `/auth/admin/mfa-disable` | POST | ✅ OK | — | — |
| `/auth/refresh` | POST | ✅ OK | ✅ OK | Web uses cookie; mobile sends body |
| `/auth/google/verify` | POST | — | ✅ OK | — |
| `/auth/logout` | POST | ✅ OK | ✅ OK | — |
| `/auth/verify-email` | GET | — | — | Not wired to any frontend yet |
| `/auth/resend-verification` | POST | — | — | Not wired to any frontend yet |
| `/users/me` | GET | — | ✅ OK | — |
| `/users/me` | PUT | — | ✅ OK | — |
| `/users/me` | DELETE | — | ✅ OK | — |
| `/users/bmi` | GET | — | ✅ OK | — |
| `/diet-plans/generate` | POST | — | ✅ OK | — |
| `/patients/onboarding` | POST | — | ✅ OK | — |
| `/patients/activate` | POST | — | ⚠️ At Risk | Response type mismatch; `refresh_token` not stored (W-4, M-5) |
| `/patients/request-doctor` | POST | — | ✅ OK | — |
| `/patients/request-status` | GET | — | ✅ OK | — |
| `/patients/doctors` | GET | — | ⚠️ At Risk | Extra fields on `PublicDoctor` may not exist in DB (W-11) |
| `/patients/my-visit` | GET | — | ✅ OK | — |
| `/patients/disclaimer` | POST | — | ✅ OK | — |
| `/progress/today` | GET | — | ❌ Broken | Response shape nested; mobile type flat — home screen always shows 0 (C-6) |
| `/progress/log/meal` | POST | — | ❌ Broken | Mobile calls `/progress/meal` — 404 (C-3) |
| `/progress/log/meal/{id}` | PUT | — | ✅ OK | — |
| `/progress/log/meal/{id}` | DELETE | — | ✅ OK | — |
| `/progress/log/water` | PUT | — | ✅ OK | — |
| `/progress/log/steps` | PUT | — | ✅ OK | — |
| `/progress/log/weight` | PUT | — | ✅ OK | — |
| `/progress/meal/rate` | POST | — | ✅ OK | — |
| `/progress/meal/ratings` | GET | — | ✅ OK | — |
| `/progress/weight-history` | GET | — | ✅ OK | — |
| `/progress/weekly-report` | GET | — | ✅ OK | — |
| `/progress/streak` | GET | — | ✅ OK | — |
| `/progress/adherence/weekly` | GET | — | — | Not wired in mobile |
| `/meal-plan/week` | GET | — | ✅ OK | — |
| `/meal-plan/history` | GET | — | ✅ OK | — |
| `/meal-plan/shopping-list` | GET | — | ✅ OK | — |
| `/meal-plan/shopping-list/toggle` | POST | — | ❌ Broken | Body vs query-param mismatch; `at_home` missing (C-4) |
| `/meal-plan/adjust` | POST | — | — | Not wired in mobile |
| `/doctor/dashboard` | GET | ✅ OK | — | — |
| `/doctor/patients` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}` | DELETE | — | — | Exists in backend; not in `doctorApi.ts` |
| `/doctor/patients/{id}/plan` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}/plan` | PUT | ✅ OK | — | — |
| `/doctor/patients/{id}/plan/notes` | POST | ✅ OK | — | — |
| `/doctor/patients/{id}/plan/overrides` | GET | — | — | Backend exists; not in `doctorApi.ts` (M-2) |
| `/doctor/patients/{id}/logs` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}/progress` | GET | — | — | Backend exists; not in `doctorApi.ts` (W-12) |
| `/doctor/patients/{id}/notes` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}/notes` | POST | ✅ OK | — | — |
| `/doctor/patients/{id}/record-visit` | POST | ✅ OK | — | — |
| `/doctor/patients/{id}/visits` | GET | ✅ OK | — | — |
| `/doctor/patients/{id}/request-renewal` | POST | ✅ OK (doctor) | ❌ Broken (patient) | Patient JWT blocked by `DoctorIsolationMiddleware` (C-5) |
| `/doctor/patients/{id}/approve-renewal` | POST | ✅ OK | — | — |
| `/doctor/patients/approve-all-renewals` | POST | ✅ OK | — | — |
| `/doctor/patients/pending-renewals` | GET | ✅ OK | — | — |
| `/doctor/requests` | GET | ✅ OK | — | — |
| `/doctor/requests/{id}/accept` | POST | ✅ OK | — | — |
| `/doctor/requests/{id}/reject` | POST | ✅ OK | — | — |
| `/doctor/subscription-codes` | GET | ✅ OK | — | — |
| `/doctor/subscription-codes` | POST | ✅ OK | — | — |
| `/doctor/recipes` | GET | ✅ OK | — | — |
| `/doctor/recipes` | POST | ✅ OK | — | — |
| `/doctor/recipes/{id}/assign` | POST | ✅ OK | — | — |
| `/doctor/recipes/estimate` | POST | ❌ Broken | — | Frontend calls `/recipes/lookup` with wrong field name (C-8) |
| `/admin/stats` | GET | ⚠️ At Risk | — | TypeScript type missing 3 new fields (W-2) |
| `/admin/doctors` | GET | ✅ OK | — | — |
| `/admin/doctors` | POST | ✅ OK | — | — |
| `/admin/doctors/{id}` | GET | — | — | Backend exists; not in `adminApi.ts` |
| `/admin/doctors/{id}/deactivate` | PATCH | ✅ OK | — | — |
| `/admin/doctors/{id}` | DELETE | ✅ OK | — | — |
| `/admin/patients` | GET | ✅ OK | — | — |
| `/admin/patients/{id}/subscription/override` | PATCH | ✅ OK | — | — |
| `/admin/patients/{id}` | DELETE | ✅ OK | — | — |
| `/admin/patients/{id}/hard-delete` | DELETE | ✅ OK | — | **ALLOW_HARD_DELETE=True in .env** (C-7) |
| `/admin/food` | GET | ✅ OK | — | — |
| `/admin/food/{id}/approve` | PATCH | ✅ OK | — | — |
| `/admin/food/{id}/reject` | PATCH | ✅ OK | — | — |
| `/admin/food/{id}` | DELETE | ✅ OK | — | — |
| `/admin/billing` | GET | ✅ OK | — | — |
| `/admin/billing/{id}/mark-paid` | POST | ✅ OK | — | — |
| `/admin/codes/generate` | POST | ✅ OK | — | — |
| `/admin/codes` | GET | ✅ OK | — | — |
| `/admin/audit-logs` | GET | ✅ OK | — | — |
| `/admin/consultations` | GET | — | — | Not wired in `adminApi.ts` (M-1) |
| `/admin/consultations/annual` | GET | — | — | Not wired in `adminApi.ts` (M-1) |
| `/admin/renewals` | GET | — | — | Not wired in `adminApi.ts` (M-1) |
| `/admin/renewals/{id}/override-approve` | POST | — | — | Not wired in `adminApi.ts` (M-1) |

---

## 3. What's Left — Pre-Production Checklist

### Must Fix Before Any Deployment

- [ ] **C-1** Fix all `VITE_API_URL` and `EXPO_PUBLIC_API_URL` values to match the actual backend port (update both `.env` files and verify `axios.ts` fallbacks match)
- [ ] **C-2** Remove hardcoded LAN IP `192.168.0.100` from `mitihar-patient-app/.env`; use `10.0.2.2` for Android Emulator and the machine's actual LAN IP only as a local override, never committed
- [ ] **C-3** Fix `mitihar-patient-app/services/progress.ts` line 22: change `"/progress/meal"` → `"/progress/log/meal"`
- [ ] **C-4** Fix `mitihar-patient-app/services/meals.ts` shopping-list toggle: switch from JSON body to query params and include the `at_home` boolean; or change the backend to accept a JSON body
- [ ] **C-5** Add a patient-facing renewal-request endpoint to `app/routers/patients.py` (e.g. `POST /patients/request-renewal`); remove the `/doctor/patients/{id}/request-renewal` call from `profile.ts`
- [ ] **C-6** Align `TodaySummary` in `mitihar-patient-app/types/index.ts` with the actual nested backend response, or change the backend to return a flat shape
- [ ] **C-7** Set `ALLOW_HARD_DELETE=False` in `/.env` immediately; document it as dev-only
- [ ] **C-8** Fix `doctorApi.ts` `fetchNutritionFromGemini`: change URL to `/doctor/recipes/estimate` and request body field from `food_name` to `dish_name`

### Fix Before Beta / User Testing

- [ ] **W-1** Add port 8001 to `CORS_ORIGINS` in `/.env` (or align backend port to match existing config)
- [ ] **W-2** Add `expiring_soon_count`, `pending_renewals_count`, `total_consultations_this_month` to `PlatformStats` in `adminApi.ts`
- [ ] **W-3** Remove `user_id` from `registerPatient` return type; check all callers
- [ ] **W-4** Fix `ActivateResponse` type to match actual backend `ActivationResponse` schema
- [ ] **W-5** Rename `have_at_home` → `at_home` in `ShoppingItem` (or vice-versa in backend)
- [ ] **W-6** Remove the unreachable `raise HTTPException` in `meal_plan.py` after `return {}`; decide whether an empty plan should be a 200 `{}` or a 404
- [ ] **W-7** Fix `LoginResponse` type — remove `refresh_token` or annotate it as optional for doctor/admin
- [ ] **W-8** Configure Redis (`REDIS_URL`) before deploying with `--workers > 1`; see `main.py` TODO comment
- [ ] **W-9** Replace `print()` in `app/routers/progress.py` lines 120–121 with `logging.getLogger(__name__)`
- [ ] **W-10** Wire real email sending in Phase 7; flip `REQUIRE_EMAIL_VERIFICATION=True` at the same time
- [ ] **W-11** Verify `Doctor` DB model has `experience_years`, `fee_per_month`, `rating`, `review_count`, `is_accepting` columns before enabling `GET /patients/doctors` in production
- [ ] **W-12** Add `getPatientProgress(id)` to `doctorApi.ts` pointing to `/doctor/patients/{id}/progress`
- [ ] **W-13** Rotate all secrets currently in `/.env` to a secrets manager; especially the 4 Gemini API keys and Google OAuth client secret

### Incomplete Integrations / Future Wiring

- [ ] **M-1** Wire `GET /admin/consultations`, `/admin/consultations/annual`, `/admin/renewals`, `POST /admin/renewals/{id}/override-approve` into `adminApi.ts` and relevant admin pages (`Billing.tsx`, etc.)
- [ ] **M-2** Wire `GET /doctor/patients/{id}/plan/overrides` into `doctorApi.ts` and the PatientDetail override history tab
- [ ] **M-3** Compute and pass real macro values to `<MacroRow>` on the home screen instead of hardcoded `0`
- [ ] **M-4** Replace `hasUnread = true` with real unread-notification state (Phase 5 FCM work)
- [ ] **M-5** Store `refresh_token` returned by `/patients/activate` in SecureStore after activation
- [ ] Wire `GET /auth/verify-email` and `POST /auth/resend-verification` to UI email verification screens (Phase 7)
- [ ] Wire `GET /progress/adherence/weekly` and `GET /meal-plan/adjust` to mobile screens
- [ ] Wire `DELETE /doctor/patients/{id}` into `doctorApi.ts` with a confirmation dialog in PatientDetail
- [ ] Verify `Doctor` model schema for public-facing fields before enabling the find-doctor screen
- [ ] Remove or replace `Phone screens/` directory from the repo (large static assets, no `.gitignore` exclusion)
- [ ] Confirm `alembic/versions/` is complete and all migrations are idempotent before first production deploy

---

*This report covers static code analysis only. No live network calls were made. All line numbers are approximate (±5) due to the tool's line-windowed reading.*
