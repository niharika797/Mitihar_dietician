# Mityahar — Deployment Checklist
**Last updated:** 2026-07-02  
**Branch:** feature/api-remediation-v0.2  
**Status:** Local verification complete. GCP deployment not yet started.

---

## Section A — Verifiable locally (Docker only, zero cost)

- [x] 94/94 backend tests pass — `python tests/full_backend_test.py`
- [x] Redis fail-open graceful degradation — `app/core/limiter.py` FailOpenLimiter; live injection test passed (Jul 1)
- [x] Duplicate email race (10 concurrent) → 1 created, 9×409 — `tests/performance/test_duplicate_email.py`
- [x] DB statement_timeout=30s kills runaway queries — `app/core/database.py` connect_args; pg_sleep(40) killed at 30.0s
- [x] BMR/TDEE calculation accuracy (5/5 patients) — multiplier 1.375→1.2 fixed in `seed_test_patients.py:139`
- [x] Per-IP XFF rate bucket isolation — 10-req lockout + 50 distinct IPs 0×429 — `scripts/simulate_multi_ip_rate_limiting.py`
- [x] Auth bcrypt/DB connection decoupled (three-phase sessions) — p50 400ms at 200 users — `app/routers/auth.py`
- [x] confirm-choice 0% failure at 200 concurrent users — `tests/performance/locustfile.py`
- [x] 200-user sustained 120s — 0% failure all patient endpoints
- [x] patients.doctor_id index: Seq Scan → Index Scan (0.106ms) — migration `a1b2c3d4e5f6`; EXPLAIN ANALYZE verified
- [x] 14-day weekly cycle: preference extraction + week-2 boost (4/4 food_ids) — `scripts/simulate_weekly_time_machine.py`
- [x] Plan quality 50/50 patients: calorie range, 84 combos, avoid_tags, dish variety — `tests/performance/test_plan_quality.py`
- [x] TypeScript zero errors — `npx tsc --noEmit` in `mitihar-frontend/apps/` (PASS 4, Jul 1)
- [x] Indian 4G E2E tab transitions all <300ms — `tests/performance/e2e/tests/doctor_flow.spec.ts`
- [x] bcrypt cost factor audit — cost=12 (default); avg 196ms/hash; OWASP ≥100ms satisfied — `tests/performance/reports/bcrypt_benchmark.txt`
- [ ] `.gitignore` cleanup — add `__pycache__/`, `*.pyc`, `frontend_dev.txt`, `frontend_err.txt`, `rename_checkpoint.json`, `tag_medical_checkpoint.json`, `*.txt` uvicorn logs
- [ ] Commit all untracked files — `alembic/versions/a1b2c3d4e5f6_*`, modified `app/core/database.py`, `app/core/limiter.py`, `app/routers/auth.py`, full `tests/performance/` suite, `DEPLOY_CHECKLIST.md`
- [ ] `requirements.txt` verified — no dev-only packages (pytest, locust) included in production image
- [ ] Dockerfile created — not yet written; Cloud Run deploy is blocked without it

---

## Section B — Requires external services (free-tier)

- [ ] **Horizontal autoscaling at 1000 users** — Cloud Run free tier / $300 GCP trial credit  
  Proves: 5 instances × 200-user safe threshold handles 1000 concurrent; local single-process hits `QueuePool limit` at 1000 users; Cloud Run per-instance isolation makes this a non-issue

- [ ] **XFF rate bucket with real GCP LB headers** — Cloud Run + Cloud Load Balancer  
  Proves: `TRUSTED_PROXY_CIDR=130.211.0.0/22,35.191.0.0/16` correctly buckets by real client IP; locally all traffic = `127.0.0.1` so per-user isolation is unverifiable without real LB

- [ ] **Auth latency at scale with real multi-IP traffic** — Cloud Run deployed  
  Proves: bcrypt p50 stays bounded per-IP under real concurrent multi-IP load (not bcrypt queue from single 127.0.0.1 bucket)

- [ ] **Login Indian 4G timing with production bundle** — Cloud Run + Playwright  
  Proves: 5.9s dev-server login improves with compiled bundle; dev Vite bundle load is the dominant factor (estimate 5.1s post-compile, unconfirmed)

- [ ] **Memorystore Redis cross-instance rate limit sharing** — GCP Memorystore Basic ($35–50/mo, or $300 trial)  
  Proves: rate counters shared across Cloud Run instances; local Redis verified but on single instance only

- [ ] **Email verification flow** — SendGrid / Resend free tier (100 emails/day)  
  Required before: `REQUIRE_EMAIL_VERIFICATION=True` in production `.env`

- [ ] **Google OAuth end-to-end** — Production GCP OAuth credentials  
  Requires: OAuth redirect URI matching deployed domain; locally configured redirect won't work in Cloud Run

- [ ] **FCM push notifications in production** — Firebase project + real device  
  Locally untestable; `notification_service.py` sends to FCM but real delivery unverified

---

## Section C — Blocked / not started

- [ ] **[HIGH] Dockerfile missing** — Cloud Run requires a container image; no Dockerfile exists in the repo. Deploy is hard-blocked.

- [ ] **[HIGH] No rollback plan** — no `alembic downgrade` procedure documented, no DB snapshot strategy, no blue/green or canary deployment plan. A failed migration has no documented recovery path.

- [ ] **[HIGH] APScheduler in Cloud Run** — APScheduler runs in-process with FastAPI. If `min-instances=0` (Cloud Run default), the process is killed on idle → cron jobs (01:00 UTC subscription expiry flag, 01:05 UTC deactivation) never fire on idle nights. Fix: set `min-instances=1` in Cloud Run config, OR migrate cron to Cloud Scheduler HTTP triggers against dedicated `/internal/cron/expire-tokens` and `/internal/cron/flag-expiring` endpoints.

- [ ] **[HIGH] No staging environment** — all testing has been local Docker; deploying directly to production with no staging rehearsal. Any configuration error (wrong DB URL, bad CORS, missing env var) surfaces live.

- [ ] CORS_ORIGINS production value — currently `localhost:3000`; must be set to actual deployed frontend domain before deploy or all browser requests will be rejected

- [ ] Admin IP whitelist production CIDRs — `AdminIPWhitelistMiddleware` reads allowed IPs from config; production admin IPs not specified or documented

- [ ] SECRET_KEY rotation procedure — no documented plan for rotating the JWT signing key; rotation immediately invalidates all active sessions for all users

- [ ] Chaos + load combined test — Redis failure under concurrent 200-user load never tested together; Redis isolated test (PASS 1) and load test (PASS 5) run separately

- [ ] APScheduler cron smoke test in container — jobs untested in containerized environment; `startup` event registration may behave differently under gunicorn/uvicorn workers

- [ ] `ALLOW_HARD_DELETE=False` confirmed in production `.env` — easy to miss; hard deletes would permanently destroy patient records

- [ ] Dish rename 78% incomplete (≈1697/2137 dishes pending) — `scripts/clean_dish_names.py`, checkpoint `rename_checkpoint.json`; non-blocking for launch but ongoing UX debt
