# Mityahar Performance Test Suite

Five-module test suite covering API baseline, load, plan quality, and E2E flows.

## Prerequisites

```powershell
# Activate venv
venv\Scripts\activate

# Install test deps (backend venv)
pip install locust httpx playwright

# Install Playwright browsers
playwright install chromium

# Backend + DB must be running
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
```

---

## Execution Order

### Step 1 — Seed 50 test patients

```powershell
python -m tests.performance.seed_test_patients
```

- Idempotent — safe to re-run
- Outputs: `tests/performance/test_manifest.json`
- Creates 6 test doctors + 50 patients across all medical condition profiles

### Step 2 — API baseline benchmark (single user)

```powershell
python -m tests.performance.benchmark_api
```

- Runs 10 requests per endpoint, records p50/p95/p99
- Output: `tests/performance/reports/benchmark_baseline.json`
- Run BEFORE and AFTER Locust to detect latency degradation under load

### Step 2.5 — Bulk plan generation (direct service call, no HTTP)

Use this instead of `--generate-first` when you need plans for all 50 patients quickly
without HTTP overhead or rate limiter interference. Calls `DietPlanService` directly —
the same internal path that doctor accept-request uses.

```powershell
python -m tests.performance.bulk_generate_plans
```

- Regenerates plans for all 50 patients sequentially
- Prints per-patient timing and pass/fail
- Output: `tests/performance/reports/bulk_generation.json`
- Run this before `test_plan_quality` when plans haven't been seeded yet

### Step 2.6 — Rate limit verification

```powershell
python -m tests.performance.test_rate_limit
```

Confirms:
1. `POST /auth/doctor/login` fires 429 after 10 requests (per limit in auth.py)
2. 429 response includes `Retry-After` header
3. X-Forwarded-For spoofing is **NOT** honored — see finding below

**X-Forwarded-For finding (affects all load test interpretation):**
`slowapi` is configured with `key_func=get_remote_address` (`app/core/limiter.py`),
which reads `request.client.host` (raw TCP socket IP), **not** `X-Forwarded-For`.
All 50 Locust workers from a local machine share the same `127.0.0.1` rate limit
bucket. Consequences:
- Local Locust runs can trigger rate limits for the entire simulated user pool at once
- Spoofing `X-Forwarded-For` in Locust has no effect on rate limiting
- Real per-IP rate limit isolation can only be verified **after GCP deployment**,
  where the load balancer exposes actual distinct client IPs via `request.client.host`

### Step 3 — Locust load test (50 concurrent users)

**Option A: UI mode (recommended for first run)**
```powershell
locust -f tests/performance/locustfile.py --host http://localhost:8001
# Open http://localhost:8089 → set 50 users, spawn rate 5
```

**Option B: Ramp test (headless)**
```powershell
locust -f tests/performance/locustfile.py --host http://localhost:8001 `
  --users 50 --spawn-rate 5 --run-time 5m --headless `
  --html tests/performance/reports/ramp_test.html
```

**Option C: Spike test (headless)**
```powershell
locust -f tests/performance/locustfile.py --host http://localhost:8001 `
  --users 50 --spawn-rate 50 --run-time 2m --headless `
  --html tests/performance/reports/spike_test.html
```

**Time-of-day scenario (Scenario C):** Run at 08:00, 12:00, 20:00 IST. Use a unique
`--html` output name each time so reports don't overwrite.

### Step 4 — Plan quality checks

```powershell
# If plans already exist for test patients:
python -m tests.performance.test_plan_quality

# If you want to generate plans first:
python -m tests.performance.test_plan_quality --generate-first
```

- Verifies calorie range, 84-combo count, avoid_tags compliance, dish variety
- Output: `tests/performance/reports/quality_report.json`

### Step 5 — Playwright E2E

```powershell
# Frontend (Doctor Dashboard) must be running at http://localhost:5173
cd tests/performance/e2e
npx playwright test
# Report: tests/performance/reports/playwright-report/index.html
```

Patient app Playwright tests use Expo web at `http://localhost:8081`.
If Expo web is not running, skip and test patient flows via Expo Go on device.

---

## Master Runner (all modules in sequence)

```powershell
# Full suite
python -m tests.performance.run_all_tests

# Skip seeding (already seeded) + skip Locust (run manually)
python -m tests.performance.run_all_tests --skip-seed --skip-locust

# Re-generate plans before quality check
python -m tests.performance.run_all_tests --skip-seed --skip-locust --generate-plans
```

---

## Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Primary doctor | dr.ashok.mehta@mitihar.test | DoctorTest@2026 |
| Test patient (any) | testpatient001–050@mityahar.test | TestPat@2026 |

Seeded doctors: `dr.ashok.mehta`, `dr.priya.sharma`, `dr.rahul.verma`,
`dr.sunita.nair`, `dr.amit.joshi`, `dr.kavita.reddy` — all `@mitihar.test`.

---

## Reports Directory

All outputs land in `tests/performance/reports/`:

| File | Module | Content |
|------|--------|---------|
| `benchmark_baseline.json` | 2 | p50/p95/p99 per endpoint |
| `bulk_generation.json` | 2.5 | Per-patient bulk gen pass/fail + timing |
| `ramp_test.html` | 3 | Locust ramp run HTML report |
| `spike_test.html` | 3 | Locust spike run HTML report |
| `quality_report.json` | 4 | Per-patient pass/fail with detail |
| `playwright-report/` | 5 | Playwright HTML report |
| `master_report.json` | All | Module-level pass/fail summary |

---

## Patient Profiles Seeded

| Condition | Count | Tags Checked |
|-----------|-------|-------------|
| Healthy | 5 | none |
| Diabetic | 5 | avoid_diabetes |
| PCOS | 5 | avoid_pcos |
| Hypothyroid | 5 | avoid_hypothyroid |
| High Cholesterol | 5 | avoid_highchol |
| Gout | 5 | avoid_gout |
| IBS | 4 | avoid_ibs |
| Hypertension | 4 | avoid_hypertension |
| Anemia | 4 | none (prefer_tags) |
| Kidney Disease | 3 | avoid_kidney |
| Healthy + Gym | 3 | none |
| Diabetic + Hypertension | 2 | avoid_diabetes + avoid_hypertension |
| **Total** | **50** | |
