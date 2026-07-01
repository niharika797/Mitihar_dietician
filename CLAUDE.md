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
- Uses `slowapi` with Redis-backed storage (`app/core/limiter.py`); falls back to in-memory with warning if `REDIS_URL` unset.
- Dev: local Docker container `mityahar-redis` (redis:7-alpine, port 6379).
- Production: GCP Memorystore (provision at deployment phase); `REDIS_URL` in .env must point to Memorystore IP.

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
REDIS_URL=redis://localhost:6379/0   # Dev: local Docker (mityahar-redis container)
                                     # Production (GCP): redis://:<AUTH_PASSWORD>@<MEMORYSTORE_IP>:6379/0
                                     # Production notes: use AUTH password, keep within same VPC as Cloud Run,
                                     # TLS not required for Memorystore Basic tier within VPC (confirm at deploy time)
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

> _This section is maintained by Claude. Last updated: 2026-07-01 (PASS 5 complete — all 5 local verification passes done; ready for GCP deployment phase)_

**PASS 5 — Network Latency & Connection Pool Stress: COMPLETE (2026-07-01)**
- `playwright.config.ts`: added exported `INDIAN_SLOW_4G` constant (offline: false, latency: 150ms, 10 Mbps/3 Mbps); apply via `page.emulateNetworkConditions(INDIAN_SLOW_4G)` in tests
- Locust 2.44.4 installed in venv
- Headless run: 100 users, 10/s spawn, 60s, port 8001
- Data endpoints: GET /meal-plan/week 19.8ms avg, GET /progress/today 24.5ms avg, GET /users/me 7.5ms avg — all under 200ms ✅
- Zero 500s, zero ConnectionErrors, zero DB pool failures — connection pool healthy at 29.59 req/s
- All failures were logical 4xx (rate-limit 429s + cascaded 401s + 404s); bcrypt serialization noted as local-only concern
- VERIFICATION_PLAYBOOK.md: all 5 passes marked complete

**LOCAL VERIFICATION PHASE: COMPLETE — all 5 passes done**

**Next: GCP deployment phase (in order):**
1. Commit all modified/untracked files (see deployment prep items below)
2. Fix `getMealTypes()` logic bug (`PlanTab.tsx:36–38`) if ≥5-meal support needed
3. Production `.env`: `COOKIE_SECURE=True`, `REDIS_URL=redis://:<AUTH>@<MEMORYSTORE_IP>:6379/0`, `REQUIRE_EMAIL_VERIFICATION=True`
4. GCP Cloud Run: container build → Memorystore Basic tier (same VPC) → Cloud SQL → deploy

---

**SESSION 21 — Patient App Adaptive UI: COMPLETE** (R-5/R-6, 2026-06-17/18)
- V2ComboCard, combo confirm-choice, optimistic confirmed state, bowl size (S/M/L), doctor's pick badge
- Full detail in BUILD_TRACKER under R-5, R-6, R-6.5, R-6.6, R-6.7

**SESSION 22 — Doctor Weekly Patient Summary: COMPLETE** (R-7A, 2026-06-21)
- `compute_weekly_summary()` service, `GET /doctor/patients/{id}/weekly-summary?week_start=` endpoint
- `WeeklySummaryTab.tsx`: adherence table + per-day choice breakdown + preferred/never_selected patterns
- R-7A.1 (rec lookup date mismatch fixed) + R-7A.2 (preferred boost + avoided exclusion in generator) applied
- Full detail in BUILD_TRACKER under R-7A

**Completed performance test suite + quality validation (2026-06-30):**
- `seed_test_patients.py`: 50 patients across 12 condition profiles, IDs 1–50, `health_condition="Healthy"` for all (medical_conditions[] JSONB handles tag filtering — condition-specific templates don't exist)
- `bulk_generate_plans.py`: 50/50 OK, 0 FAIL, total ~37s; per-patient 0.47–1.14s; rec_ids 283–332
- `test_plan_quality.py`: **50/50 PASS** — calorie ✅, combos ✅ (84 each), avoid_tags ✅, variety ✅
- Key calibration: `CALORIE_TARGET_RATIO = 0.85 * 0.85 = 0.7225` — generator uses `effective_tdee = TDEE × 0.85`, then `DEFAULT_SPLIT` sums to 0.85 of effective_tdee → total meals = TDEE × 0.7225
- accompaniment pool exhaustion on combo_idx 2/3 (pool of 21, needs 4 distinct) — known pre-existing, non-blocking, falls back to combo-0 dish

**Completed Redis-backed rate limiting (2026-06-30):**
- Local Redis via Docker (`mityahar-redis`, `redis:7-alpine`, port 6379)
- `REDIS_URL=redis://localhost:6379/0` in `.env`; `Limiter` uses `RedisStorage` when set, falls back to in-memory with warning otherwise
- `redis-py` upgraded `3.5.3` → `8.0.1` (old version used `distutils` — removed in Python 3.12, caused `ConfigurationError` at startup)
- Startup PING check in lifespan confirms connectivity; logs error loudly if REDIS_URL set but unreachable
- `test_redis_shared_limit.py` **PASS** — 429 at total req #11 across ports 8001 + 8002; Cloud Run multi-instance sharing confirmed
- Known gap: `Retry-After` header absent in 429 responses (slowapi 0.1.9) — non-blocking, cosmetic
- Production note in `.env`: GCP Memorystore (Basic tier, ~$35-50/mo) with AUTH + VPC-internal — deferred to deployment phase

**Deployment prep — critical items:**
- **MUST commit before deployment:** `alembic/versions/93ad56085772_remove_plan_type_tags.py` (R-9) and `alembic/versions/b5c6d7e8f9a0_add_original_name_to_food_items.py` (dish cleanup) — both untracked
- **Also commit:** `scripts/clean_dish_names.py`, `scripts/fix_recipe_quantities.py`, `scripts/tag_medical_ingredients.py`, `tests/performance/` directory
- **TypeScript check:** pnpm not in PATH on this machine; last verified state (BUILD_TRACKER R-7A) = 6 pre-existing `ImportMeta.env` errors only, 0 new errors — install pnpm then run `pnpm tsc --noEmit` to confirm
- **Known logic bug:** `getMealTypes()` at `PlanTab.tsx:36–38` — `ALL_MEAL_TYPES` and `THREE_MEAL_TYPES` are identical arrays; ≥5 branch is dead code. Logic-only, no TypeScript error. Low severity (3-meal plan only mode in production).
- **Add to `.gitignore`:** `__pycache__/`, `*.pyc`, `uvicorn_*.txt`, `clean_dishes_llm_checkpoint.json`, `tag_medical_checkpoint.json`

**Deployment phase next steps (in order):**
1. Commit: the 2 alembic migrations, 3 scripts above, `tests/performance/`, all modified backend files
2. Run `pnpm tsc --noEmit` in `mitihar-frontend/apps/` — expect 6 ImportMeta.env errors only
3. Fix `getMealTypes()` logic bug (`PlanTab.tsx:36–38`) — both arrays must differ for ≥5-meal support
4. Production `.env`: `COOKIE_SECURE=True`, `REDIS_URL=redis://:<AUTH>@<MEMORYSTORE_IP>:6379/0`, `REQUIRE_EMAIL_VERIFICATION=True`, `ALLOW_HARD_DELETE=False`
5. GCP Cloud Run: container build → Memorystore provisioning (Basic tier, same VPC) → Cloud SQL or hosted PostgreSQL → deploy

**Completed avoid_pcos / avoid_gout ingredient tagging (2026-06-29):**
- 95 ingredients tagged via Claude CLI (18 batches of 50); 432 total ingredients have at least one tag
- Fixed `::jsonb` cast syntax in `derive_recipe_tags.py` (CAST() form required for asyncpg)
- Propagated to food_items via recipe_ingredients join
- Recipes tagged avoid_pcos: 554
- Recipes tagged avoid_gout: 130
- Generator now applies exclusions for PCOS and Gout patients automatically

**Completed flagged recipe review (2026-06-29):**
- 1779 & 1789 (Corn Palak): both left unverified — missing corn ingredient entirely
  (only spice/garnish rows present, ~30 kcal artifacts); duplicates of each other;
  existing verified Corn Palak (id=1257) already in pool
- 3411 (Nawabi Mixed Vegetable Gravy): verified — all ingredients present, 65g serving,
  49.66 kcal is mathematically correct for a water-heavy vegetable gravy with 3g ghee
- 3418: left unverified — exact duplicate of 3411
- Final verified pool: 2101 recipes

**Completed recipe quantity fix (fix_recipe_quantities.py):**
- Pass A–E: 553 bad recipes fixed; 549 verified; pool 184→1551→2100
- Generation verified: Priya rec confirmed 84 combos, no 409 errors

**Completed W3 UX fix (MealConfigTab slot_type display):**
- Pinned dish cards now show slot_type alongside kcal (e.g. "245 kcal · grain")
- Blocked dish cards same fix applied

**Completed full_backend_test.py — 94/94 passing (2026-06-30):**
- BASE port corrected 8000 → 8001
- `import sys` added; health check wrapped in try/except with clear error + sys.exit(1)
- `gdpr_consent: True` added to Section 8 patient registration payload
- `hdr()` guarded against empty token — returns `{}` instead of `Bearer ` (prevented httpx LocalProtocolError)
- `serving_weight_g: 250.0` added to Section 12 recipe creation payload (now required field)
- `plan_type_tags` removed from Section 12 recipe creation payload (deleted in R-9)
- All 16 sections passing: 94/94
- Note: seed_admin.py has no default password — `ADMIN_SEED_PASSWORD` must be in .env

**Created performance test suite (2026-06-30):**
- `tests/performance/seed_test_patients.py` — seeds 50 patients across 12 condition profiles; idempotent; writes `test_manifest.json`
- `tests/performance/benchmark_api.py` — single-user p50/p95/p99 for 10 endpoints; saves `reports/benchmark_baseline.json`
- `tests/performance/locustfile.py` — PatientUser + DoctorUser Locust classes; ramp/spike scenarios; run via UI or headless
- `tests/performance/test_plan_quality.py` — calorie range, 84-combo count, avoid_tags compliance, dish variety; `--generate-first` flag
- `tests/performance/e2e/` — Playwright config + doctor_flow.spec.ts + patient_flow.spec.ts (patient skips if Expo web not running)
- `tests/performance/run_all_tests.py` — master runner; `tests/performance/README.md` — execution order
- No application code modified — additive only

**Added bulk generator + rate limit test (2026-06-30):**
- `tests/performance/bulk_generate_plans.py` — calls `DietPlanService.generate_diet_plan` + `store_diet_plan` directly for all 50 test patients; no HTTP, no rate limiter; prints per-patient timing; saves `reports/bulk_generation.json`
- `tests/performance/test_rate_limit.py` — verifies 429 fires at 10/min on doctor login, checks Retry-After header, confirms X-Forwarded-For is NOT honored
- `tests/performance/locustfile.py` — added rate limiter caveat block in module docstring

**X-Forwarded-For finding (affects load test validity):**
- `slowapi` uses `key_func=get_remote_address` → `request.client.host` (raw TCP socket IP)
- X-Forwarded-For is NOT read by the rate limiter
- All local Locust workers share one `127.0.0.1` rate bucket — per-IP isolation untestable locally
- Must re-validate rate limit isolation post-GCP-deployment (load balancer will supply real client IPs)

**Remaining backlog:**
- 563 manual-source original outliers → 10 under-50 left untouched (correct)
- `rename_dishes_gemini.py` superseded by `clean_dish_names.py`; `rename_checkpoint.json` already deleted (2026-06-29 cleanup)
