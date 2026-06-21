# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Mityahar** is an AI-powered dietetics platform with three sub-applications:

| App | Location | Stack |
|-----|----------|-------|
| Backend API | `app/` | FastAPI + SQLAlchemy (async) + PostgreSQL |
| Web Dashboard (Doctor + Admin) | `mitihar-frontend/apps/` | React + Vite + Tailwind + Radix UI |
| Patient Mobile App | `mitihar-patient-app/` | Expo (React Native) + NativeWind |

---

## Backend Commands

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate

# Run backend
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

# Run all tests (requires live DB at localhost:5432)
python tests/full_backend_test.py

# Run a specific pytest test file
pytest tests/test_calculations.py -v

# DB migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Start DB via Docker (requires POSTGRES_PASSWORD in env)
docker-compose up -d

# Seed scripts (run after alembic upgrade)
python -m scripts.seed_admin
python -m scripts.seed_food_items
python -m scripts.seed_6k_recipes

# Rename dishes with Gemini (checkpointed, idempotent)
python -m scripts.rename_dishes_gemini
python -m scripts.rename_dishes_gemini --dry-run
```

## Frontend Commands

```bash
# Web dashboard (Doctor + Admin)
cd mitihar-frontend/apps
pnpm dev        # dev server
pnpm build

# Patient mobile app
cd mitihar-patient-app
pnpm start      # Expo dev server
pnpm android
pnpm ios
```

---

## Backend Architecture

### Middleware stack (outermost → innermost, LIFO registration order)
`SecurityHeadersMiddleware` → `CORSMiddleware` → `SubscriptionCheckMiddleware` → `DoctorIsolationMiddleware` → `AdminIPWhitelistMiddleware`

- **SubscriptionCheckMiddleware** — zero-DB JWT claim check; blocks patients with inactive subscriptions from diet generation
- **DoctorIsolationMiddleware** — zero-DB; restricts `/doctor/*` routes to the doctor's own patients only
- **AdminIPWhitelistMiddleware** — single DB read; IP check for all `/admin/*` routes

### Router → prefix mapping
| Router file | URL prefix |
|-------------|------------|
| `auth.py` | `/api/v1/auth` |
| `users.py` | `/api/v1/users` |
| `diet_plans.py` | `/api/v1/diet-plans` |
| `calculations.py` | `/api/v1/calculations` |
| `progress.py` | `/api/v1/progress` |
| `meal_plan.py` | `/api/v1/meal-plan` |
| `patients.py` | `/api/v1/patients` |
| `doctor.py` | `/api/v1/doctor` |
| `admin.py` | `/api/v1/admin` |

### Key services
- `app/services/meal_generator/meal_generator.py` — core diet plan generation against 6000+ recipe DB; uses Gemini as fallback for unknown foods
- `app/services/diet_plan_service.py` — orchestrates plan creation/regeneration
- `app/services/token_service.py` — subscription token lifecycle (activate, expire, flag expiring)
- `app/services/mfa_service.py` — TOTP-based MFA via `pyotp`
- `app/services/notification_service.py` — Firebase push notifications (FCM)
- `app/services/audit_service.py` — admin audit log writes

### Auth model
- Short-lived JWTs (15 min access) + 7-day refresh token in HttpOnly cookie
- `COOKIE_SECURE=False` in dev; **must** be `True` in production
- Google OAuth supported for patients
- `REQUIRE_EMAIL_VERIFICATION=False` by default (flip for production)
- `ALLOW_HARD_DELETE=False` by default; `True` only for local dev testing

### Cron jobs (APScheduler, runs at startup)
- 01:00 UTC — flag patients expiring within 4 days (`expiring_soon=True`)
- 01:05 UTC — deactivate patients whose `token_1_expiry` has passed

### Rate limiting
- Uses `slowapi` with in-memory storage. Switch to `REDIS_URL` before multi-worker deployment.

---

## Web Frontend Architecture (`mitihar-frontend/apps/`)

- **React Router v7** — routes defined in `src/app/routes.tsx`
- Two role-based shells: `DoctorShell` (`/doctor/*`) and `AdminShell` (`/admin/*`)
- Protected by `RequireAuth` component checking JWT role claim
- API calls centralized in `src/app/data/` (doctorApi.ts, adminApi.ts, queryKeys.ts)
- React Query for server state; Zustand or context for local state

---

## Patient Mobile App Architecture (`mitihar-patient-app/`)

- **Expo Router** file-based routing: `app/(auth)/`, `app/(onboarding)/`, `app/(tabs)/`
- `lib/axios.ts` — shared Axios instance (timeout: 30s); `EXPO_PUBLIC_API_URL` in `.env`
- IP in `EXPO_PUBLIC_API_URL` must match the dev machine's LAN IP (check Metro output). Assign a static local IP in router settings to avoid frequent changes.
- Gemini model in use: `gemini-2.5-flash-lite` (previous model `gemini-2.0-flash-lite` was retired March 2026)

---

## Environment Variables (`.env`)

```env
DATABASE_URL=postgresql+asyncpg://mityahar_user:mityahar_password@localhost:5432/mityahar_db
SECRET_KEY=<min 32 chars — generate with: python -c "import secrets; print(secrets.token_hex(32))">
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GEMINI_API_KEY_1=      # Only KEY_1 is used; rotating keys doesn't help (quota is per project)
COOKIE_SECURE=False    # Set True in production
ALLOW_HARD_DELETE=False
REQUIRE_EMAIL_VERIFICATION=False
REDIS_URL=             # Required for multi-worker deployments
```

---

## Known Pending Issues (as of Sprint 5)

- `mitihar-frontend/apps/` has unverified changes from Sprint 5 (`PlanTab.tsx` rewrite). Run `pnpm dev` and check browser console for TypeScript errors around `patientMealsPerDay` prop before editing.
- Dish rename script (`scripts/rename_dishes_gemini.py`) is ~22% complete (~440/2137 dishes). Checkpoint at `rename_checkpoint.json`; safe to re-run.



---

## Working Agreement

At the end of every task or session, Claude must update the **Current State** section below with:
- What was completed this session
- Anything broken, blocked, or pending
- The single most important next action

Do NOT summarize the whole project — only what changed. Keep it tight.

---

## Current State

> _This section is maintained by Claude. Last updated: 2026-06-18 (R-6.7 complete)_

**Completed R-5 (Backend v2 patient surfacing):** `GET /meal-plan/week` returns `WeekResponseV2` for v2 plans; `POST /confirm-choice` extended with `weekly_combo_id`.

**Completed R-6 (Patient app v2 UI):** `V2ComboCard` component, `isV2` gate, v2 confirmation mutation, TS cast fixes across 4 files. 0 new TS errors.

**Completed R-6.5 (Seven targeted fixes):** Calorie ring merge, macro tracking, bottom sheet animation, steps/water removal, notifications empty state, plan history v2 label, beverage dedup.

**Completed R-6.6 (V2 Combo Detail Screen + Bowl Size + Confirmed State Fix):**
- `bowl_size` (small/medium/large) added to `POST /confirm-choice`; defaults to `medium`; validated against existing DB constraint
- `weekly_combo_id` exposed by `GET /choices/{date}` — confirmed state now restores on hard refresh
- New `GET /meal-plan/combo/{combo_id}/dishes` endpoint with ownership check + JSONB enrichment
- New screen `app/meals/combo-detail.tsx`: S/M/L bowl selector, live calorie scaling, expandable ingredients, 3-state confirm button
- `V2ComboCard` tappable — card body navigates to combo-detail; Select button still quick-confirms
- `getComboDetails` service + `ComboDetailDish`/`ComboDetailResponse` types added

**Completed R-6.7 (Four targeted fixes):**
- Approve Week button fixed: `approveWeeklyPlan` now sends `{}` body (was sending none → 422)
- Doctor weekly summary `confirmed_kcal` fallback: uses `actual_calories ?? calories` (NULL-safe)
- Weight goal null display: shows `"Not set"` instead of `"0 kg"` when `target_weight_kg` null
- Weight chart: `BarChart` → `LineChart` (curved, area fill, auto-scale Y-axis)
- Weight data seeded for Priya (5 entries, 66.2→65.0 kg)
- 0 new TS errors vs R-6.6 baseline

**Rebuild track:** R-0 → R-1 → R-2 → R-3 → R-4 → R-4.5 → R-5 → R-6 → R-6.5 → R-6.6 → **R-6.7 COMPLETE**.

**Pending / Backlog:**
- **W3 clinical guardrail decision:** Doctor pin of 2nd main_dish → amber fires but no hard block.
- **Pool expansion (accompaniment/one_pot):** Swap 409s on thin pools for Vegetarian/Healthy.
- **DB creds note:** `.env` shows `mityahar_user/mityahar_password` but Docker runs `POSTGRES_USER=admin`, `POSTGRES_PASSWORD=mityahar_dev`.
- **Pre-existing:** `full_backend_test.py` admin login crash, water-log.tsx orphaned, avoid_pcos/avoid_gout tags absent, dish rename ~22% done.
- **R-6.6/R-6.7 manual verification pending:** Combo detail screen, bowl size persistence, confirmed state across reload, LineChart rendering.

**Next action:** R-7 — Weekly Cycle Automation (product owner to confirm scope before starting).
