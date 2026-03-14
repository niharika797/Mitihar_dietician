# MITIHAR — SPRINT 5 HANDOFF
> Generated: 2026-03-13 | Sprint 4 complete | Next: Phase 4 Billing (Razorpay) + Phase 5 FCM

---

## HOW TO USE THIS FILE
Paste this entire file as your first message in the Sprint 5 chat.

**Session startup procedure (non-negotiable):**
1. Read this file top to bottom.
2. Confirm understanding across: (a) what is done, (b) two pending backend actions, (c) sprint 5 scope.
3. Wait for instruction. Do NOT begin writing any code until told to.

---

## Project Overview

**Name:** Mitihar — AI-powered Indian diet planning app
**Backend root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`
**Backend start:** `venv\Scripts\uvicorn app.main:app --reload --port 8000`
**Test suite:** `venv\Scripts\python scripts\test_all_endpoints.py` → **97/97 passing**
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`

**Web dashboard root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\mitihar-frontend\apps`
**Web dashboard start:** `pnpm dev` (port 5173)

**Patient app root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\mitihar-patient-app`
**Patient app start:** `pnpm start` → Expo Go on device/emulator

**Test credentials:**
- Doctor: `testdoctor@mityahar.com` / `doctor1234`
- Admin: `admin@mityahar.com` / `admin1234`

---

## Non-Negotiable Rules

1. **Never trust memory** — always read actual files from disk before writing any code.
2. **Middleware is zero-DB** — `DoctorIsolationMiddleware` and `SubscriptionCheckMiddleware` read JWT claims only, never touch the DB.
3. **Doctor isolation is absolute** — every `/doctor/*` query must filter by `request.state.doctor_id`.
4. **`db_models.py` is the single source of truth** for all ORM models.
5. **Alembic chain must stay clean** — always verify `down_revision` matches the previous head before writing a migration.
6. **97/97 tests must still pass** after every backend change.
7. **Surgical edits only** — never rewrite a whole file when a targeted edit will do.

---

## Current State (Verified 2026-03-13)

### Backend — 97/97 Tests Passing ✅

**Alembic chain (current):**
```
92084b0bc541  food_items_and_templates
4e5124b3e103  add_all_user_tables
cf7a21f007f0  fix_nullable_streak_requestedat
370efc812ae5  add_pace_preference_eating_habits_image
3fb0a727fee2  add_clinical_notes_table
861b9d58abdf  add_calorie_adjustment_to_progress_logs
eb8dbef8dd19  add_audit_logs_table
a1b2c3d4e5f6  add_google_id_to_patients      ← last APPLIED head
b2c3d4e5f6a7  add_doctor_id_to_food_items    ← WRITTEN, pending `alembic upgrade head`
```

**B2 + B3 code — DONE (verified from disk):**
- `app/schemas/doctor.py`: `RecipeCreateRequest` has `save_to_library: bool = Field(default=True)`. `FoodItemSummary` has `doctor_id: Optional[int] = None`.
- `app/routers/doctor.py`: `add_recipe` endpoint guards `save_to_library=False` with HTTP 501, sets `doctor_id=doctor.id` on `FoodItem`.
- `app/models/db_models.py`: `FoodItem` has `doctor_id` column + `doctor` relationship.
- Migration file `b2c3d4e5f6a7_add_doctor_id_to_food_items.py` — written, not yet applied.

### ⚠️ FIRST ACTION WHEN DB IS ONLINE

```cmd
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
venv\Scripts\python -m alembic upgrade head
venv\Scripts\python -m alembic current
# Expected: b2c3d4e5f6a7 (head)
venv\Scripts\python scripts\test_all_endpoints.py
# Expected: 97/97
```

### Web Dashboard — Sprint 3 Complete ✅
18 Doctor + 6 Admin pages live, all wired to real API, zero mock data.

### Patient App — Sprint 4 Complete ✅ (36/36 screens, tsc exit code 0)

---

## Patient App — Complete Screen Inventory

### Auth (`app/(auth)/`)
- `login.tsx` ✅ — email/password login, Google OAuth button, `POST /auth/token` + `POST /auth/google/verify`
- `register.tsx` ✅ — email/password + optional doctor_code, `POST /auth/register`

### Onboarding (`app/(onboarding)/`) — 9 screens ✅
`personal-info` → `activity-level` → `goals` → `medical-conditions` → `allergies` → `dietary-preferences` → `lifestyle` → `disclaimer` → `complete`

### Tabs (`app/(tabs)/`) — 4 screens ✅
- `index.tsx` — Home: today summary (calories/water/steps), ProgressRing, streak, meal log sheets, quick-log buttons
- `meals.tsx` — Today's plan, MacroRow, doctor note banners, empty state
- `progress.tsx` — Water/Steps/Weight metrics, gifted-charts bar chart, weight log sheet
- `profile.tsx` — Stats grid, subscription card, settings menu, logout

### Doctor flow (`app/doctor/`) — 3 screens ✅
`find-doctor` → `activate` → `connection-status`

### Meals (`app/meals/`) — 5 screens ✅
`meal-detail` · `week-view` · `shopping-list` · `plan-history` · `plan-empty`

### Log (`app/log/`) — 3 screens ✅
- `log-meal.tsx` — manual meal type dropdown, calories, collapsible macros, notes, `logMeal` mutation
- `log-from-plan.tsx` — pre-filled from `date`/`type` params, fetches from weekly plan
- `edit-log.tsx` — takes `id`, `meal_type`, `calories`, `editable` params; `editMealLog`/`deleteMealLog`; 24h lock banner

### Progress (`app/progress/`) — 4 screens ✅
- `weight-log.tsx` — 90-day history, diff per entry, modal bottom sheet
- `water-log.tsx` — glass grid tap-to-log, +/- stepper, profile-driven goal
- `steps-log.tsx` — hero stats, quick-set preset chips 500→10k, manual modal
- `charts.tsx` — 30d/90d toggle, weight LineChart, 7-day calorie BarChart, stats table

### Profile (`app/profile/`) — 4 screens ✅
`edit-profile` · `notifications` · `account` · `about`

### Home (`app/home/`) ✅
`notifications.tsx` — notification list with `AppNotification` type

---

## Navigation Architecture (Fixed Sprint 4)

Root `_layout.tsx` now explicitly registers all 22 push screens with typed animations:
- **`(auth)`, `(tabs)`** — `animation: "fade"` (no slide on tab/auth transitions)
- **`(onboarding)`** — `animation: "slide_from_right"`
- **`log/log-meal`, `log/log-from-plan`, `log/edit-log`** — `presentation: "modal"` + `animation: "slide_from_bottom"` (sheet UX)
- **All other screens** — `animation: "slide_from_right"` + `gestureEnabled: true` (back swipe)

---

## Key APIs & Types

### Store
- `useProgressStore`: `today`, `localWater/Steps/Weight`, `weightHistory`, `hydrateSummary()`, `setLocalWater/Steps/Weight()`, `appendWeightEntry()`, `hydrateWeightHistory()`
- Selectors: `selectWater`, `selectSteps`
- `useAuthStore`: `isAuthenticated`, `profile`, `isLoading`, `setTokens()`, `setProfile()`, `logout()`, `bootstrap()`

### QUERY_KEYS (from `lib/queryKeys.ts`)
`ME`, `BMI`, `REQUEST_STATUS`, `WEEK_PLAN`, `PLAN_HISTORY`, `SHOPPING_LIST`, `TODAY`, `WEEKLY_REPORT`, `WEIGHT_HISTORY(days)`, `STREAK`

### Services
- `services/progress.ts`: `getTodaySummary`, `logMeal`, `editMealLog`, `deleteMealLog`, `logWater`, `logSteps`, `logWeight`, `getWeightHistory`, `getWeeklyReport`, `getStreak`
- `services/meals.ts`: `getWeeklyPlan`, `getPlanHistory`, `getShoppingList`, `toggleShoppingItem(ingredient_name: string)`
- `services/profile.ts`: `getMyProfile`, `updateProfile`, `getBMI`, `submitOnboarding`, `acceptDisclaimer`, `activateSubscription`, `requestDoctor`, `getRequestStatus`
- `services/auth.ts`: `registerPatient`, `loginPatient`, `verifyGoogleToken`, `logoutPatient`

### Key Type Notes
- `MacroRow` props: `{ protein, carbs, fat, fiber }` — NO `calories`
- `toggleShoppingItem(ingredient_name: string)` — string, not number
- `ShoppingListResponse = { [category: string]: ShoppingItem[] }`
- `activateSubscription` returns `ActivateResponse` — must chain `getMyProfile()` to get `PatientProfile`
- TanStack Query v5: `onSuccess` callback REMOVED — use `useEffect(() => { if (data) fn(data) }, [data])` pattern

### Design Tokens
- brand-600: `#1E7C45`, brand-400: `#34B164`, brand-50: `#F0FDF4`
- Input height: 52, border-radius: 12, border: `#E5E7EB`
- Primary button: height 52, border-radius 26, bg `#1E7C45`
- Disabled: bg `#E5E7EB`, text `#9CA3AF`

---

## Sprint 5 Scope

### Priority 1 — Pending Backend Action
```
alembic upgrade head   (B3 migration for doctor_id on food_items)
```

### Priority 2 — Phase 4: Razorpay Billing
Backend:
- [ ] `POST /api/v1/billing/pay` — Razorpay order creation
- [ ] Razorpay webhook handler — verify signature, mark subscription paid
- [ ] `subscription_end_date` extension on payment
- [ ] Subscription auto-expiry daily cron (APScheduler)
- [ ] `billing_transactions` table (new Alembic migration)

Patient app:
- [ ] Subscription screen — Razorpay checkout sheet (React Native WebView or SDK)
- [ ] Payment success / failure screens
- [ ] Subscription status polling after payment

### Priority 3 — Phase 5: FCM Push Notifications
Backend:
- [ ] `POST /auth/token` + `POST /auth/google/verify` — accept `fcm_token` field, store on Patient
- [ ] `fcm_token` column on `patients` table (new Alembic migration)
- [ ] `notification_service.py` — `send_push()` via Firebase Admin SDK
- [ ] Trigger notifications on: new plan ready, doctor accepted, meal reminder (cron), sub expiry (3-day warning)

Patient app:
- [ ] `expo-notifications` setup — request permissions on login
- [ ] Send FCM token to backend after login
- [ ] Handle foreground + background notification tap → navigate to correct screen
- [ ] Notification preferences screen (currently placeholder)

### Priority 4 — Real Device Testing
```cmd
# Backend
venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Patient app — update API base URL to local network IP in lib/axios.ts
pnpm start
# Scan QR with Expo Go
```
Change `lib/axios.ts` `baseURL` from `http://localhost:8000` to `http://<LAN-IP>:8000` for device testing.

---

## Known Tech Debt (Do Not Fix in Sprint 5)

- `Set-Cookie secure=False` in `auth.py` — change to `True` before HTTPS deploy (Phase 7)
- slowapi in-memory — resets on restart (Phase 7: Redis)
- `ProgressLog.total_calories_consumed` column never written
- `MealLog.food_id` / `custom_food_name` rarely populated (slot linking deferred Phase 6)
- All Gemini free-tier keys quota-exhausted — `/doctor/recipes/estimate` falls back to local DB only
- Loading skeletons absent — all screens show spinner or blank until data arrives (Phase 5 polish)
- Offline state not handled in patient app (Phase 5)
- No monetary billing table (this sprint builds it)

---

## Sprint Status

| Sprint | Scope | Status |
|---|---|---|
| Sprint 0 | DB schema, migrations, models | ✅ Done |
| Sprint 1 | Patient + Doctor + Admin backend, ETL, allergy filtering | ✅ Done |
| Sprint 2 | Rate limits, MFA TOTP, IP whitelist — 97/97 | ✅ Done |
| Sprint 3 | Doctor Dashboard + Admin Dashboard (React+Vite, 18+6 pages) | ✅ Done |
| Sprint 4 | Backend B2+B3 + Patient App (Expo, 36 screens, tsc exit 0) | ✅ Done |
| **Sprint 5** | **Phase 4 Billing (Razorpay) + Phase 5 FCM + real device test** | 🔲 **Start here** |
| Sprint 6 | Phase 6 ML improvements | 🔲 Queued |
| Sprint 7 | Phase 7 Production Deploy (GCP + Cloud Run + CI/CD) | 🔲 Queued |
