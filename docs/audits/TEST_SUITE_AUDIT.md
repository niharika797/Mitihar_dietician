# Test Suite Audit — Mityahar Staging Readiness

**Audit date:** 2026-07-14
**Method:** Static/code inspection only. No tests executed, no staging calls made, no files modified outside this document.
**Branch audited:** `feature/api-remediation-v0.2`, HEAD `060840e` (2026-07-14).

---

## 0. Module identification — naming ambiguity

The task's 5-name list (API benchmarking / Locust / meal-plan quality / personalization simulation / Playwright E2E) does **not** match the project's own naming. `.claude/rules/backend-notes.md` records: *"Test suite (2026-06-30): 5 modules created (seed, benchmark, locust, quality, playwright)"* — i.e. **seed** is the 5th module, not "personalization simulation." `tests/performance/README.md` also only names 4 execution-order modules plus a seeding prerequisite.

No file or directory anywhere in the repo is literally named "personalization" as a module. Two real candidates were evaluated:

- `tests/performance/test_plan_quality.py` contains one **check** labelled "Personalization" in its own docstring (dish-variety check) — but it's a sub-check inside the quality module, not a standalone module.
- `scripts/simulate_weekly_time_machine.py` (`VERIFICATION_PLAYBOOK.md` Pass 3, built the same week, 2026-07-01) is a genuine simulation of personalization — it seeds a full 14-day cycle and asserts Week-2 plans boost the patient's Week-1 preferred dishes. This is a materially better match for "personalization simulation" than anything in `tests/performance/`.

This audit treats **Module 4 = `scripts/simulate_weekly_time_machine.py`** and flags the naming mismatch explicitly rather than reporting NOT FOUND. If the real intent was the variety sub-check inside `test_plan_quality.py`, see §2 finding — it is currently broken.

---

## 1. API Benchmarking

**1. File + last modified:** `tests/performance/benchmark_api.py` — 2026-07-01 (commit `09d1d95`).

**2. Target:** Hardcoded `BASE_URL = "http://127.0.0.1:8001"` (localhost only). No staging-URL variant, no env-var override.

**3. Data source:** Real API-created interaction (login as pre-seeded doctor/patient, then hits live endpoints), but the *patients/doctors it logs in as* come from `test_manifest.json`, which is produced by `seed_test_patients.py` — a **direct-DB seed script**, not the register API. So the benchmark itself calls real endpoints, but its test identities are fixture/DB-seeded, not register→activate→generate.

**4. Middleware/business logic:** Real HTTP calls through the full stack (auth, rate limiter, `SubscriptionCheckMiddleware`, generation service) — no bypass. One caveat: the "Generate plan" benchmark deletes and regenerates the *real* active plan for `testpatient001@mityahar.test` — destructive against whatever patient owns that fixture email, documented in the file's own docstring.

**5. Last run evidence:** `tests/performance/reports/benchmark_baseline.json`, timestamped 2026-06-30 02:27, contains real p50/p95/p99 numbers (e.g. Doctor login p50=213.5ms, 9/10 success) — this is genuine run output, not a stub.

**6. Runs clean against current code?** Spot-checked: `POST /api/v1/auth/doctor/login` and `POST /api/v1/diet-plans/generate` both still exist in `app/routers/auth.py` / `app/routers/diet_plans.py`. No APScheduler or removed-cron references. Should still run as-is.

**7. Verdict: REUSABLE** (against localhost only — would need a `--base-url`/env-var change to point at staging).

---

## 2. Locust Load Test

**1. File + last modified:** `tests/performance/locustfile.py` (2026-07-03, `5abe488`), `tests/performance/locustfile_1000users.py` (2026-07-03, same commit).

**2. Target:** Passed via CLI `--host` flag (not hardcoded) — defaults documented as `http://localhost:8001` in every example command in the file's docstring and `README.md`. No staging example exists anywhere in the repo.

**3. Data source:** Same as above — real HTTP calls, but identities sourced from `test_manifest.json` (DB-seeded fixtures), with an in-file fallback to a single hardcoded fixture patient if the manifest is missing.

**4. Middleware/business logic:** Full real stack — auth, rate limiter, meal-plan endpoints, doctor endpoints. No DB/service bypass. The file's own docstring documents a real limitation it discovered: `slowapi`'s `key_func` was `get_remote_address` (raw socket IP) at the time it was written, so all local Locust workers shared one rate-limit bucket — this is now **stale**, see finding below.

**5. Last run evidence:** Extensive — `tests/performance/reports/` has `load_200users.html` (929KB, 2026-07-01 20:59), `load_1000users_stats.csv`, `full_1000u_stats.csv`, `chaos_baseline_stats.csv`, etc. `VERIFICATION_PLAYBOOK.md` Pass 5 records a full headless 100-user run with a real endpoint-latency table (2026-07-01). Real, substantial run history.

**6. Runs clean against current code? — STALE COMMENT, not stale behavior.** `app/core/limiter.py` was rewritten to `gcp_aware_key()` (a CIDR-aware XFF reader) plus `FailOpenLimiter` (Redis-down fail-open) — both **after** this file's docstring was written, but the docstring in `locustfile.py`/`test_rate_limit.py` still describes the old `get_remote_address` behavior as current fact. The rate-limiter documentation risk (§ALSO CHECK) applies to the whole suite, not just this file. Endpoints hit (`/meal-plan/week`, `/progress/today`, `/users/me`, `/meal-plan/confirm-choice`, `/doctor/patients`, `/doctor/patients/{id}/weekly-plan`, `/doctor/patients/{id}/weekly-summary`, `/doctor/dashboard`, `/doctor/patients/{id}/weekly-plan/approve`, `/doctor/recipes`) — all spot-checked and still exist in current routers.

**7. Verdict: REUSABLE**, but the rate-limiter behavior claimed in comments should be re-verified/updated — the underlying `gcp_aware_key`/`TRUSTED_PROXY_CIDR` mechanism it describes as a workaround is now the actual production mechanism, and the comment reads as if it's still an open problem.

---

## 3. Meal-Plan Quality Verification

**1. File + last modified:** `tests/performance/test_plan_quality.py` — 2026-07-01 (`09d1d95`). Prerequisite: `bulk_generate_plans.py`, same commit.

**2. Target:** Hardcoded `BASE_URL = "http://127.0.0.1:8001"` for the optional `--generate-first` login/generate step; the actual quality checks read straight from the local Postgres DB via `AsyncSessionLocal` (uses `DATABASE_URL` from `.env`, so effectively "whichever DB `.env` points at" — localhost in dev, would silently point at staging DB only if `.env` were swapped, which is not how it's normally run).

**3. Data source:** **Mixed, and this is the critical distinction the task asked to flag.** Patient records are direct-DB fixtures from `seed_test_patients.py` (bypasses `/auth/register`, no Pydantic validation — the file's sibling `test_doctor_api_create.py` even notes `.test` emails are only possible *because* of this bypass, since `EmailStr` rejects the RFC-2606-reserved `.test` TLD). The diet **plans** being graded are generated either via the real `/api/v1/diet-plans/generate` endpoint (`--generate-first`) or via `bulk_generate_plans.py`, which calls `DietPlanService` directly, **bypassing HTTP, auth, and the rate limiter** (its own docstring: "no HTTP, no rate limiter"). Default/documented run order (`README.md` Step 2.5) is the **bypass** path.

**4. Middleware/business logic:** Depends on which prerequisite path was used (see above) — the quality checks themselves are read-only raw SQL against `weekly_combos`/`recommendations`/`food_items`, so they exercise no middleware regardless.

**5. Last run evidence:** `tests/performance/reports/quality_report.json`, 2026-06-30 22:09, reports **50/50 patients PASS** — looks like clean evidence, but see next finding.

**6. Runs clean against current code? — NO, two of four checks are silently broken by a field-name mismatch that predates this file.** `_check_avoid_tags()` reads `dish->>'food_item_id'` (line ~162) and `_check_variety_db()` reads `dish->>'name'` (line ~123). The actual dish JSONB shape produced by `MealGenerator._assemble_dish()` (`app/services/meal_generator/meal_generator.py:466`) has always used the keys `food_id` and `recipe_name` — confirmed via git history back to commit `1aeccaa`, i.e. this key mismatch existed *before* `test_plan_quality.py` was written on 2026-07-01, not a later rename. Effect: both `dish->>'food_item_id'` and `dish->>'name'` always evaluate to SQL `NULL`, so the `JOIN food_items fi ON fi.id = (dish->>'food_item_id')::integer` matches zero rows and the `WHERE dish->>'name' IS NOT NULL` filter excludes every row. **`avoid_tags_ok` and `variety_ok` are structurally incapable of ever failing** — the medical-safety tag check and the dish-repetition check both silently no-op and report `True` unconditionally. The 50/50 PASS in `quality_report.json` is real for calorie-range and combo-count, but meaningless for the two most safety-relevant checks (avoid-tag violations for diabetic/PCOS/kidney/etc. patients would never be caught).
   - `avg_kcal`/`combo_count` checks (direct column reads, not JSONB-key-dependent) are unaffected and still valid.
   - `Patient`, `WeeklyCombo`, `Recommendation`, `FoodItem` models all still exist with matching column names (`is_active`, `avoid_tags`, `combo_index`, `total_calories`) — no import/schema breakage, the bug is purely in the JSONB key names used inside raw SQL strings.

**7. Verdict: NEEDS REWORK** — not a staleness issue, a pre-existing correctness bug. Two one-line fixes (`food_item_id`→`food_id`, `name`→`recipe_name`) would make the safety checks actually check something; until then this module should not be relied on as evidence that generated plans respect medical avoid-tags.

---

## 4. Personalization Simulation

**1. File + last modified:** `scripts/simulate_weekly_time_machine.py` — 2026-07-01 (`09d1d95`, same commit as the `tests/performance/` suite). See §0 for why this file, not something under `tests/performance/`, is treated as Module 4.

**2. Target:** No HTTP target — talks directly to the DB via `AsyncSessionLocal` and calls `DietPlanService.generate_diet_plan()` / `compute_weekly_summary()` in-process. Whichever DB `.env`'s `DATABASE_URL` points at.

**3. Data source:** Direct DB. Requires a specific pre-seeded patient (`priya.test@mityahar.com`, id referenced as 53 in `VERIFICATION_PLAYBOOK.md`) created by `seed_test_patients.py` — fixture data, not register→activate→generate. The script itself also does direct-DB writes: it manually inserts `PatientMealChoice`/`PatientMealChoiceDish`/`MealLog` rows to simulate a week of patient app usage, rather than driving the real `/meal-plan/confirm-choice` / `/progress/log/meal` endpoints.

**4. Middleware/business logic:** Bypasses all HTTP middleware (auth, rate limiter, subscription check) — calls `DietPlanService` and `compute_weekly_summary()` service functions directly. It does exercise real business logic (the actual generator and actual summary/preference-boost computation), just not through the API layer.

**5. Last run evidence:** `VERIFICATION_PLAYBOOK.md` Pass 3, 2026-07-01, records a full successful run with concrete output: adherence=100% (21/21 slots), 4 preferred dishes, 4 never-selected dishes, and a confirmed 4/4 preferred-dish boost into Week 2. Genuine, detailed evidence — the most narratively complete of the five modules.

**6. Runs clean against current code?** `DietPlanService`, `compute_weekly_summary`, and every model it imports (`Patient`, `Recommendation`, `WeeklyCombo`, `PatientMealChoice`, `PatientMealChoiceDish`, `MealLog`) all still exist with matching signatures. Unlike `test_plan_quality.py`, this script reads `dish["food_id"]` (line ~152) — the **correct** key — so it does not share the Module 3 bug. No APScheduler or removed-cron references. Would need `priya.test@mityahar.com` to exist in whatever DB it's pointed at, or it fails fast with a clear error (`fail(...)`, not a silent no-op).

**7. Verdict: REUSABLE.**

---

## 5. Playwright E2E

**1. File + last modified:** `tests/performance/e2e/tests/doctor_flow.spec.ts` (2026-07-03, `5abe488`), `tests/performance/e2e/tests/patient_flow.spec.ts` (2026-07-01, `09d1d95`), config `tests/performance/e2e/playwright.config.ts` (2026-07-01).

**2. Target:** Hardcoded in `playwright.config.ts`: doctor project `baseURL: 'http://localhost:5173'` (Vite dev server), patient project `baseURL: 'http://localhost:8081'` (Expo web dev server). No staging-URL config anywhere; both are local dev-server ports, not even the backend's own port.

**3. Data source:** Browser-driven login against fixture credentials (`dr.ashok.mehta@mitihar.test` / `testpatient001@mityahar.test`) — same DB-seeded fixtures from `seed_test_patients.py`. Real UI interaction end-to-end from the browser's perspective (real login form, real network calls the frontend makes), so this is the one module that exercises the full stack including frontend code, even though the underlying identity is a fixture.

**4. Middleware/business logic:** Full stack, unbypassed — this is genuine E2E through both frontends and the real backend API.

**5. Last run evidence:** `tests/performance/reports/playwright-compiled-report/index.html` (2026-07-03 10:24) contains **real results: 6 passed, 5 failed** — this is an actual executed run with actual failures, not a stub or an unrun scaffold. `VERIFICATION_PLAYBOOK.md` Pass 5 separately notes E2E execution was "deferred" at verification time (network-throttle profile wired but not run) — that note is now superseded by the later `playwright-compiled-report` evidence, which is more recent and shows it *was* eventually run, with failures.

**6. Runs clean against current code? — Selectors need re-verification given the 5 failures.** `doctor_flow.spec.ts` targets `#login-email`/`#login-password` — confirmed those ids exist in `mitihar-frontend/apps/src/app/pages/Login.tsx`. It also depends on `getByText('Active Patients')`, sidebar link text `'Patients'`, `'Weekly Summary'`, `'Meal Config'`, and text `'Calorie Distribution'` — none of these were verified against current component render output in this audit (would require running the frontend, out of scope for a static audit), and given `CLAUDE.md`'s own note that `PlanTab.tsx` has "unverified changes from Sprint 5," some of the 5 recorded failures may already stem from exactly this kind of drift. `patient_flow.spec.ts` self-skips cleanly if Expo web isn't running (no crash risk), and targets generic `input[name="email"]`/`role=button` selectors, which are more resilient to markup changes than the doctor spec's mix of text/role selectors.

**7. Verdict: NEEDS REWORK** — infrastructure and target config are fine, but there is a *known, evidenced* 5-failure result that has not been triaged; re-running against current `main` before trusting it is required, not optional.

---

## Also Checked (cross-cutting)

**Rate-limiter test coverage:** Present and reasonably adversarial, not merely functional. `tests/performance/test_rate_limit.py` (2026-07-01) fires 15 rapid requests at `POST /auth/doctor/login`, asserts the 429 fires at the documented `10/minute` threshold, checks for a `Retry-After` header, and specifically probes X-Forwarded-For spoofing resistance. `tests/performance/test_redis_shared_limit.py` goes further — it runs two uvicorn instances against the same Redis and proves the rate-limit counter is shared across processes (catches the class of bug where each worker has its own in-memory counter). `scripts/simulate_multi_ip_rate_limiting.py` (`VERIFICATION_PLAYBOOK.md` Pass 2, 2026-07-01) is the most adversarial of the three: it spoofs a single IP for a lockout check and 50 distinct spoofed IPs for a scale check, with recorded PASS results (first block at request #11 exactly; zero cross-tenant throttling). One caveat carried over from §2: `test_rate_limit.py`'s docstring still asserts XFF spoofing is "NOT honored," which was true under the old `get_remote_address` key func but is now conditionally *true only outside* `TRUSTED_PROXY_CIDR` — the test's own behavior is probably still correct (it doesn't set `TRUSTED_PROXY_CIDR`, so it exercises the untrusted-IP path), but its prose claim of an absolute fact is now stale relative to `gcp_aware_key()`.

**Redis-down / failure-injection coverage:** Strong, and it's real chaos testing, not a mock. `tests/performance/chaos_test.py` and `chaos_test_scale.py` both literally run `docker stop mityahar-redis` mid-load (and `docker_start_redis` to restore it), sustaining concurrent traffic through the outage window, and assert the `FailOpenLimiter` behavior in `app/core/limiter.py` holds (fail-open, not fail-closed) with no fail-rate spike. Recorded evidence in `tests/performance/reports/chaos_report.json` (2026-07-02) shows `redis_fail_open: true`, `db_pool_recovery: true`, `combined_no_additive_failure: true` across 1840–3600 requests per phase, 0 failures throughout — genuine, favorable results. This is real infrastructure fault injection against a real Docker container, not a stub.

**Real-registration-API patient creation (vs. seed script):** Exists, but incomplete relative to the "register → activate → generate" flow the task is checking for. `tests/performance/seed_via_api.py` (2026-07-03) fires 50 concurrent `POST /api/v1/auth/register` calls through the real HTTP stack with distinct spoofed source IPs (to dodge the register endpoint's `3/hour` per-IP limit) — this is genuine register-via-API coverage, with real evidence at `tests/performance/reports/api_load_test.json` (2026-07-01). `tests/performance/test_doctor_api_create.py` similarly creates doctors via the real `POST /api/v1/admin/doctors` endpoint (sequential + concurrent-duplicate-409 checks) rather than direct ORM. **However, neither script goes on to activate a subscription/token or call `/diet-plans/generate` for the registered identities** — every plan-generation and plan-quality test in this suite (Modules 1, 3, 4) instead reads identities from `test_manifest.json`, which is produced entirely by the direct-DB `seed_test_patients.py`. No single script in the repo currently exercises the full register→activate→generate chain end-to-end through real APIs; that combined flow would need to be assembled from pieces of `seed_via_api.py` + `bulk_generate_plans.py`'s HTTP variant + a token-activation step that doesn't appear to exist as a test at all.

---

## Summary

- **Reusable as-is:** API benchmarking (`benchmark_api.py`), Locust load test (`locustfile.py`), personalization simulation (`simulate_weekly_time_machine.py`) — all target real endpoints/services against current code, with genuine prior-run evidence.
- **Needs rework:** Meal-plan quality verification has a real, pre-existing bug (`food_item_id`/`name` vs. actual `food_id`/`recipe_name` JSONB keys) that silently disables its two medical-safety checks — fix before trusting its "50/50 PASS"; Playwright E2E has an evidenced 5-failure run that needs triage against current frontend markup before reuse.
- **Must be built from scratch:** An end-to-end register→activate→generate test through real APIs (no such script currently exists — every generation-adjacent test relies on direct-DB-seeded fixtures instead).
