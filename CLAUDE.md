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

### Repo layout (cleaned up 2026-08-03)

- `scripts/` — flat, all live scripts run via `python -m scripts.<name>` (some cross-import
  each other, e.g. `export_recipe_ingredients_review.py` imports `sanity_check_ingredients.py`
  — do not nest into subpackages). Dead one-offs and debug scripts live in `scripts/archive/`
  (untracked, gitignored) and are not run.
- `data/review/` — working CSVs and checkpoint JSONs produced/consumed by the ingredient
  review pipeline (`export_recipe_ingredients_review.py` → edit → `import_recipe_ingredients_review.py`).
  Gitignored (covered by the top-level `data/` rule).
- `docs/` — bucketed into `architecture/`, `audits/`, `guides/`, `planning/`, `reference/`,
  `walkthroughs/`, `design/`, `archive/` (old/superseded material). `docs/CREDENTIALS.local.md`
  stays at `docs/` root (gitignored by exact path).
- `logs/` — all local dev log/process-output dumps (gitignored).

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

# Lint / typecheck (pyproject.toml — correctness rules only, see comments there)
ruff check app
mypy

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

### Models (`app/models/db_models.py`)
24 of 26 ORM classes use SQLAlchemy 2.0 typed `Mapped[...] = mapped_column(...)` style (migrated 2026-07-13). `FoodItem` and `MealTemplate` are excluded — marked `DO NOT MODIFY` in the file itself, still on legacy `Column(...)`. New model fields on any other class should follow the `Mapped[]` style; nullability must transcribe the actual DB constraint, not an assumption (verify against `alembic check` / live schema, not just app behavior).

### Auth model
- Short-lived JWTs (15 min access) + 7-day refresh token in HttpOnly cookie
- `COOKIE_SECURE=False` in dev; **must** be `True` in production
- **COOKIE_SECURE fail-closed guard only triggers when `ENVIRONMENT=production`.** Staging (`ENVIRONMENT=staging`) has no automatic enforcement — `COOKIE_SECURE=True` must be set explicitly in every non-production deploy or cookies silently ship insecure. This is a standing constraint for any future environment tier, not just staging.
- Google OAuth supported for patients
- `REQUIRE_EMAIL_VERIFICATION=False` by default (flip for production)
- `ALLOW_HARD_DELETE=False` by default; `True` only for local dev testing

### Cron endpoints (Cloud Scheduler → HTTP; APScheduler removed)
In-process APScheduler is **fully removed** (verified 2026-07-05, zero references in `app/`). Scheduled work is exposed as HTTP endpoints in `app/routers/internal.py` under `/internal/cron/*`, each guarded by the `X-Cron-Secret` header (constant-time compare against `CRON_SECRET`):
- `POST /internal/cron/flag-expiring-patients` — flag patients expiring within 4 days (`expiring_soon=True`) + FCM push
- `POST /internal/cron/deactivate-expired-patients` — deactivate patients whose `token_1_expiry` has passed
- `POST /internal/cron/complete-expired-plans` — snapshot weekly summaries for the week that just ended (Mon–Sun)

All three are idempotent and race-safe. **Cloud Scheduler jobs are live in staging** (3 ENABLED jobs, named `flag-expiring-patients`, `deactivate-expired-patients`, `complete-expired-plans`, timezone `Etc/UTC`) and `infra/cloud_scheduler_jobs.sh` was reconciled 2026-08-06 to match these live names/timezone/schedules exactly — re-running it now correctly hits `ALREADY_EXISTS` instead of creating duplicates. Auth: OIDC token via `mityahar-scheduler-sa` plus the `X-Cron-Secret` header (the header is the only auth that actually matters — Cloud Run ingress is `allUsers`/public, so OIDC/IAM never rejects an unauthenticated call). **`complete-expired-plans` previously fired Sundays (`0 1 * * 0`) instead of Mondays**, silently snapshotting one week too early against `internal.py:141`'s `last_monday = today - (today.weekday() + 7)` math — fixed 2026-08-06 via `gcloud scheduler jobs update` to `0 1 * * 1` (Mondays, `Etc/UTC`).

### Rate limiting
- Uses `slowapi` with Redis-backed storage (`app/core/limiter.py`); falls back to in-memory with warning if `REDIS_URL` unset.
- Dev: local Docker container `mityahar-redis` (redis:7-alpine, port 6379).
- Staging/Production: GCP Memorystore `mityahar-redis` (provisioned 2026-07-05, AUTH enabled); `REDIS_URL` is injected via Secret Manager on Cloud Run — not `.env`.

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
DATABASE_URL=postgresql+asyncpg://admin:<POSTGRES_PASSWORD>@localhost:5432/mityahar_db
# DB user is `admin`, db `mityahar_db` (docker-compose defaults: POSTGRES_USER=admin,
# POSTGRES_DB=mityahar_db, POSTGRES_PASSWORD must be set). To populate food/recipe data on a
# fresh clone, restore db-backups/mityahar_content_*.sql — see db-backups/RESTORE.md (do NOT
# run seed_food_items.py / seed_6k_recipes.py — broken / API-bound).
SECRET_KEY=<min 32 chars — generate with: python -c "import secrets; print(secrets.token_hex(32))">
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
GOOGLE_CLIENT_ID=
# GOOGLE_REDIRECT_URI removed 2026-08-06 (dead config, zero references anywhere).
# GOOGLE_CLIENT_SECRET: DEAD CONFIG — never read by any code path, but kept because
# scripts/audit_google_oauth.py checks for its presence via hasattr(). Not in Secret
# Manager, not on Cloud Run. Safe to delete from .env.
GEMINI_API_KEY_1=      # Only KEY_1 is used; rotating keys doesn't help (quota is per project)
COOKIE_SECURE=False    # Set True in production
ALLOW_HARD_DELETE=False
REQUIRE_EMAIL_VERIFICATION=False
REDIS_URL=redis://localhost:6379/0   # Dev: local Docker (mityahar-redis container)
                                     # Staging/Production (GCP): redis://:<AUTH_PASSWORD>@<MEMORYSTORE_IP>:6379/0
                                     # Injected via Secret Manager on Cloud Run — not .env. Cloud Run reaches
                                     # Memorystore over Direct VPC Egress on mityahar-vpc — NOT a serverless
                                     # VPC connector. AUTH enabled. TLS/transit encryption NOT enabled
                                     # (transitEncryptionMode=DISABLED, the default — never explicitly reviewed):
                                     # connection is AUTH-authenticated but unencrypted in transit; acceptable
                                     # within single-VPC-only access, pending formal review before production.
```

---

## Staging (GCP)

- Project `mityahar-staging`, region `asia-south1`. Service `mityahar-api`: https://mityahar-api-759811872653.asia-south1.run.app
- Runtime SA `mityahar-api-sa`; Cloud Scheduler invoker SA `mityahar-scheduler-sa`
- Secrets via Secret Manager (secret refs, key `latest`): SECRET_KEY, CRON_SECRET, GEMINI_API_KEY_1, DATABASE_URL, REDIS_URL. Plain env on the service: `ENVIRONMENT=staging`, `COOKIE_SECURE=True`, `CORS_ORIGINS` (Firebase hosting origins), `ADMIN_IP_WHITELIST`, `TRUSTED_PROXY_CIDR` (GCLB ranges), `GOOGLE_CLIENT_ID`, `REQUIRE_EMAIL_VERIFICATION=False`, `ALLOW_HARD_DELETE=False`
- Networking: **Direct VPC Egress** onto `mityahar-vpc`/`mityahar-subnet` — no serverless VPC connector. Cloud SQL `mityahar-pg` (db-custom-2-7680) is **private IP only**; Memorystore `mityahar-redis` (AUTH enabled) on the same VPC
- **Migrations/seeds MUST run as Cloud Run jobs** (pattern: job `mityahar-migrate` — DATABASE_URL secret + VPC egress + command override). Local `cloud-sql-proxy` CANNOT reach the instance (no public IP) — do not retry the proxy path. The job is pinned to an image digest; update `--image` before reuse.
- **Deploy via `python -m scripts.deploy_staging`, not a bare `gcloud run deploy`.** `mityahar-migrate` and `mityahar-seed-runner` are pinned to an image digest — any deploy that doesn't explicitly repoint them leaves the jobs on the stale pre-deploy image (confirmed 2026-07-13: jobs were still on a 2026-07-05 image, missing `scripts/`, after multiple later service redeploys). The script deploys the service, reads back the new image digest, and repoints both jobs in the same run.

---

## Known Pending Issues (updated 2026-07-05)

- `mitihar-frontend/apps/` has unverified changes from Sprint 5 (`PlanTab.tsx` rewrite). Run `pnpm dev` and check browser console for TypeScript errors around `patientMealsPerDay` prop before editing.
- **Dish-rename state is unclear — don't trust old checkpoint claims.** `scripts/rename_dishes_gemini.py` + its `rename_checkpoint.json` were deleted 2026-06-29, superseded by `scripts/clean_dish_names.py` (uses `food_items.original_name` as its rollback snapshot; session notes record a completed run — 117 changes). But as of 2026-07-13, `original_name` is **0/2137 rows populated on both local dev and staging** — the completed run's snapshot didn't survive to the current dataset (likely lost in a later pool-expansion reseed). Before re-running `clean_dish_names.py`, verify current data state first — it will not resume cleanly on the assumption anything is already snapshotted.
- **Admin IP whitelist is dynamic (residential ISP)**: `ADMIN_IP_WHITELIST` in `deploy-env-reference.txt` (formerly `.env.production`) is set to `49.36.111.236/32`. This is a Jio residential IP and **will change** on modem restart or ISP reassignment. If admin endpoints return 403, re-check public IP (`curl ifconfig.me`) and update the env var.
- **axios.ts bundle-splitting warning (pre-launch debt)**: `lib/axios.ts` in `mitihar-frontend/apps/` is dynamically imported by `PlanTab.tsx` but statically imported by 5 other modules. Vite warns that dynamic import will not move it into a separate chunk, contributing to a 675 KB monolithic JS bundle (above 500 KB recommended limit). Fix before Layer 2 4G retest: either make all imports static, or use `build.rollupOptions.output.manualChunks` to force code-splitting.
- ~~**`POST /progress/log/weight` is slow (Layer 3/4 watch item)**~~ — **RESOLVED 2026-07-04** (`dd39dde`): weight-log Gemini plan regeneration made non-blocking (fire-and-forget); endpoint no longer waits synchronously on `DietPlanService.generate_diet_plan()`.

---

## Working Agreement

End of session: overwrite `CURRENT_STATE.md` with the latest snapshot (max 20 lines, no history). Append full narrative detail to `BUILD_TRACKER_ARCHIVE.md`, not this file, not `BUILD_TRACKER.md`.
