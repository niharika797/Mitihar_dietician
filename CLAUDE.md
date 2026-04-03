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
python -m uvicorn app.main:app --reload

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

