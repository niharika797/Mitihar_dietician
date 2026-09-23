# Mitihar Deployment & Production Status Audit

**Date:** 2026-09-18
**Scope:** Verify actual deployed/tested state of Mitihar across backend, frontend, patient app, database, Redis, and testing — evidence-based, not documentation-based. No infrastructure was touched during this audit; all findings are read-only observations of the repository, its scripts, its logs, and its committed reports as of this date.

**Method:** Three parallel research passes over the repo — (1) deployment/infra config (Dockerfile, deploy scripts, Cloud Scheduler, env vars, DB/Redis config), (2) testing evidence (test scripts, `tests/performance/reports/`, `logs/`, audit docs, `BUILD_TRACKER.md`), (3) architecture and frontend/patient-app deployment state. Every claim below traces to a specific file; where CLAUDE.md's prose claims could not be corroborated by a config file in the repo, that gap is flagged explicitly.

---

## 1. Executive Summary

Mitihar's **FastAPI backend has a real, working staging deployment on Google Cloud Run** (`mityahar-api`, project `mityahar-staging`, `asia-south1`), backed by a private-IP Cloud SQL Postgres instance and GCP Memorystore Redis, both reached via Direct VPC Egress. This backend has been load-tested against real GCP infrastructure — not just locally — and passed a 4-iteration tuning exercise on 2026-08-07 after two rounds of failure.

**Neither client application is deployed.** The web dashboard (React) has a Firebase Hosting project configured but zero evidence it was ever pushed — no CI step, no deploy log, `dist/` gitignored. The patient mobile app (Expo) has EAS build profiles containing literal, unfilled placeholder URLs (`STAGING-URL-NOT-DEPLOYED-YET`) — it has never been built for distribution and runs only via local dev client against `localhost`.

**The most recent full load-test evidence is over 5 weeks stale** (2026-08-07) relative to this audit date, and the team's own session log (`CURRENT_STATE.md`, 2026-09-11) states CI was not reconfirmed green after the last fix, and a known DB performance hotspot from that load test remains unaddressed. True horizontal autoscaling (multiple concurrent Cloud Run instances under load) has never been tested — it's an open, unchecked item in the team's own deploy checklist.

**Bottom line on "does Mitihar have a live application?"**: A backend API is live, public, and reachable at a stable HTTPS URL. No user-facing application (web or mobile) is deployed against it. A teammate could hit API endpoints directly (curl/Postman) but could not currently open "Mitihar" as a product and use it.

---

## 2. Current Architecture

```
                    ┌─────────────────────────┐
                    │   Web Dashboard (React)   │  NOT DEPLOYED
                    │   Firebase Hosting config  │  (configured, never pushed)
                    │   project: mitihar-46a17   │
                    └─────────────────────────┘
                                   │ (never wired live)
                    ┌─────────────────────────┐
                    │  Patient App (Expo/RN)    │  NOT DEPLOYED
                    │  EAS placeholders only     │  (dev-client / localhost only)
                    └─────────────────────────┘
                                   │
                                   ▼  HTTPS (public ingress)
                 ┌───────────────────────────────────┐
                 │  Cloud Run: mityahar-api            │  ● LIVE (staging)
                 │  asia-south1 · mityahar-staging      │
                 │  FastAPI + uvicorn                   │
                 │  Middleware: RequestID → Security-   │
                 │  Headers → CORS → SubscriptionCheck  │
                 │  → DoctorIsolation → AdminIPWhitelist│
                 └───────────────────────────────────┘
                     │ Direct VPC Egress (mityahar-vpc)
           ┌─────────┴──────────┐
           ▼                    ▼
┌───────────────────┐  ┌──────────────────────┐
│ Cloud SQL Postgres  │  │ Memorystore Redis      │
│ mityahar-pg          │  │ mityahar-redis (Basic) │
│ private IP only      │  │ AUTH on, transit        │
│ db-custom-4-15360    │  │ encryption DISABLED     │
│ (bumped from -2-7680 │  │ used for: rate limiting │
│ after load-test fail)│  └──────────────────────┘
└───────────────────┘
           ▲
           │ HTTP, X-Cron-Secret header (only real auth —
           │ Cloud Run ingress is public/allUsers)
┌───────────────────────────────────┐
│  Cloud Scheduler — 3 jobs           │  ● LIVE
│  flag-expiring-patients (daily)      │
│  deactivate-expired-patients (daily) │
│  complete-expired-plans (Mondays)    │
└───────────────────────────────────┘

External: Gemini API (gemini-2.0-flash, gemini-2.5-flash-lite) called
directly from app/routers/doctor.py for nutrition-lookup fallback,
4-key rotation via itertools.cycle. Firebase Admin SDK for FCM push.
Google OAuth (ID-token verify) for patient login.
```

No background worker or task queue exists (no Celery/RQ). All "background work" is the 3 HTTP cron endpoints above, invoked externally by Cloud Scheduler — confirmed via grep across `app/`.

---

## 3. Google Cloud Deployment

| Item | Status |
|---|---|
| Cloud Run service `mityahar-api` | **Deployed, Running** — `https://mityahar-api-759811872653.asia-south1.run.app` |
| Region | `asia-south1` — **Configured** (CLAUDE.md, deploy script) |
| CPU/RAM/instance count/concurrency/timeout | **NOT FOUND in repo.** No Cloud Run YAML, no `gcloud run deploy` resource flags anywhere in `scripts/deploy_staging.py` (it passes only `--source .`). The only concrete numbers on record are from the 2026-08-07 load-test narrative in `BUILD_TRACKER.md` — Run 4's passing config was "2 workers/2 vCPU" — but this describes what was tested, not a config file asserting what's live today. **Configured via ad hoc gcloud/Console action never captured in version control.** |
| Networking | Direct VPC Egress on `mityahar-vpc`/`mityahar-subnet` (no serverless VPC connector) — **Configured**, stated in CLAUDE.md, consistent with Cloud SQL/Redis being private-IP only |
| Ingress | `allUsers` / public — confirmed by `infra/cloud_scheduler_jobs.sh`'s own comments |
| Cloud SQL | `mityahar-pg`, private IP only, tier `db-custom-2-7680` initially → bumped to `db-custom-4-15360` on 2026-08-07 after load-test failures — **Deployed, Running, Verified under load** |
| Redis | GCP Memorystore `mityahar-redis`, Basic tier, AUTH enabled, **transit encryption disabled** (`transitEncryptionMode=DISABLED`, the default) — CLAUDE.md itself flags this as "pending formal review before production" |
| Secrets | Secret Manager refs for `SECRET_KEY`, `CRON_SECRET`, `GEMINI_API_KEY_1`, `DATABASE_URL`, `REDIS_URL` — **Configured** per CLAUDE.md; plain env vars for the rest (`ENVIRONMENT=staging`, `COOKIE_SECURE=True`, `CORS_ORIGINS`, `ADMIN_IP_WHITELIST`, `TRUSTED_PROXY_CIDR`, `GOOGLE_CLIENT_ID`, `REQUIRE_EMAIL_VERIFICATION=False`, `ALLOW_HARD_DELETE=False`) |
| Cloud Scheduler | 3 jobs, confirmed live and correctly scheduled (see §2 diagram) — **Deployed, Running, Verified** (one historical bug, fixed — see §9) |
| CI/CD deploy automation | **NOT IMPLEMENTED.** No `cloudbuild.yaml` anywhere in the repo. GitHub Actions (`ci.yml`) runs lint + non-blocking mypy + 3 unit test files only — zero deploy step. All deploys are manual: `python -m scripts.deploy_staging`, which the script itself documents as necessary because two Cloud Run jobs (`mityahar-migrate`, `mityahar-seed-runner`) are pinned to an image digest that a bare `gcloud run deploy` never updates. |

**A documentation discrepancy worth flagging**: `deploy-env-reference.txt` (root, gitignored) is labeled a **production** values reference sheet, but its values don't match CLAUDE.md's description of the actually-live **staging** environment (e.g. `REQUIRE_EMAIL_VERIFICATION=True` in the reference file vs. `False` on staging per CLAUDE.md). If this file is ever used as a literal template for a real production deploy, that mismatch should be resolved first — it's not clear which values are current-intent.

**Configured → Deployed → Running → Verified, by component:**

| Component | Configured | Deployed | Running | Verified (load-tested) |
|---|:---:|:---:|:---:|:---:|
| Cloud Run (`mityahar-api`) | ✅ | ✅ | ✅ | ✅ (2026-08-07, stale) |
| Cloud SQL (`mityahar-pg`) | ✅ | ✅ | ✅ | ✅ (same run) |
| Memorystore Redis | ✅ | ✅ | ✅ | ⚠ partial (chaos-tested locally via Docker, not the live Memorystore instance) |
| Cloud Scheduler (3 jobs) | ✅ | ✅ | ✅ | ✅ (one historical bug, fixed) |
| Horizontal autoscaling (multi-instance) | ❌ not found | — | — | ❌ explicitly unchecked in DEPLOY_CHECKLIST.md |
| Firebase Hosting (web) | ✅ (project wired) | ❌ | ❌ | ❌ |
| EAS (patient app) | ⚠ placeholders only | ❌ | ❌ | ❌ |

---

## 4. Frontend Deployment

**Web dashboard (`mitihar-frontend/apps/`) — configured, not deployed.**
- `firebase.json` and `.firebaserc` (project `mitihar-46a17`) exist and are correctly formed.
- `dist/` exists locally but is gitignored — never committed, and CI has no build/deploy step referencing Firebase at all (grep for "firebase|deploy|vercel" across `.github/workflows/ci.yml` returns nothing).
- No deploy script for the frontend exists anywhere in `scripts/` (only `deploy_staging.py`, which deploys the backend).
- The CORS origins the backend is configured to allow (`https://mitihar-46a17.web.app`, `https://mitihar-46a17.firebaseapp.com`, per `deploy-env-reference.txt`) describe an *intended* target, not confirmation the site is live there.
- `src/lib/axios.ts` defaults its API base URL to `http://localhost:8001/api/v1` — confirms the dashboard is built and run against localhost in practice; `.env`/`.env.example` values could not be read in this pass (permission-restricted) so it's unconfirmed whether a real deploy would even point at the staging URL without manual edits.

**What remains to be done**: add a Firebase deploy step (CI or manual `firebase deploy`), confirm `.env.production` actually targets the staging Cloud Run URL, and do one real deploy + smoke test before this can be called "hosted."

**Patient app (`mitihar-patient-app/`) — dev-only.**
- `eas.json` `preview` and `production` profiles contain literal placeholder strings: `"https://STAGING-URL-NOT-DEPLOYED-YET.example.com/api/v1"` and `"https://PLACEHOLDER-CLOUD-RUN-URL-NOT-DEPLOYED-YET.example.com/api/v1"`.
- `app.config.ts` Sentry org is `"mitihar-placeholder-org"` with a comment flagging it must be replaced before a real EAS build. `eas.projectId` falls back to the literal string `"your-eas-project-id"` — suggesting the EAS project itself may never have been properly linked.
- No build artifacts, no store-listing references, nothing indicating `eas build`/`eas submit` was ever run.
- The `development` profile correctly points at `http://10.0.2.2:8001/api/v1` (Android emulator loopback) — this is the only environment the app has actually run in.

**What remains to be done**: fill in the real staging/production API URLs, link a real EAS project, then run an actual `eas build` for at least an internal-distribution preview build before any teammate could install and use it on a device.

---

## 5. Backend Deployment

- **Framework**: FastAPI + uvicorn, `app/main.py`. Confirmed 6-layer middleware stack (outermost→innermost): `RequestIDMiddleware` → `SecurityHeadersMiddleware` → `CORSMiddleware` → `SubscriptionCheckMiddleware` → `DoctorIsolationMiddleware` → `AdminIPWhitelistMiddleware`.
- **Startup guard, verified in code**: `COOKIE_SECURE=False` outside `ENVIRONMENT=development` raises `RuntimeError` at boot — a real fail-closed safety check, not just documentation.
- **All 9 routers registered** (`auth`, `users`, `diet_plans`, `calculations`, `progress`, `meal_plan`, `patients`, `doctor`, `admin`, `internal`) — 1:1 match with files in `app/routers/`, nothing orphaned.
- **Auth is genuinely implemented, not stubbed**: JWT (15-min access, 7-day refresh in HttpOnly cookie), Google OAuth (ID-token verification against `GOOGLE_CLIENT_ID`), and TOTP MFA (real `pyotp` backend, wired into both doctor and admin login). One item worth noting: `CURRENT_STATE.md` (2026-09-11) records an uncommitted fix for a prior privacy issue where the MFA QR code was rendered via a third-party API (`api.qrserver.com`), sending the TOTP secret off-server — fixed client-side but **unclear from this audit whether that fix has since been committed and deployed.** Flag as UNKNOWN, verify before relying on it.
- **AI/ML**: Gemini calls live in `app/routers/doctor.py` only (not in `meal_generator.py` despite proximity in naming) — two endpoints, nutrition-lookup fallback and dish-lookup fallback, rotating across 4 API keys.
- **Deploy path**: manual only, via `python -m scripts.deploy_staging`, which deploys the service then repoints the two pinned Cloud Run jobs to the new image digest. No automated trigger exists.

---

## 6. Database

| Item | Detail |
|---|---|
| Technology | PostgreSQL 15 (local Docker), Cloud SQL Postgres in staging |
| Cloud service | Cloud SQL, instance `mityahar-pg`, project `mityahar-staging` |
| Tier | `db-custom-2-7680` initially, bumped to `db-custom-4-15360` on 2026-08-07 after the original tier pegged CPU at 0.88–1.00 under 1000-user load |
| Connectivity | Private IP only — no public IP. `cloud-sql-proxy` from a local machine **cannot** reach it (confirmed in CLAUDE.md as a known non-viable path) |
| Connection pooling | `app/core/database.py`: `pool_size=20, max_overflow=20, pool_timeout=30, pool_recycle=1800, pool_pre_ping=True`, 30s statement timeout. Env-overridable but unset in both dev and prod, so these are the values actually in effect everywhere. |
| Migrations | Alembic, run as a Cloud Run job (`mityahar-migrate`) with VPC egress — this is the only way to reach the private-IP instance for schema changes |
| Backups | **NEEDS WORK.** No automated backup evidence in-repo for Cloud SQL. `scripts/pre_migrate_backup.py`'s docstring describes a manual GCP Console procedure ("Console → Backups → Create backup before migration") — prose guidance, not a tested/automated restore path. `db-backups/RESTORE.md` documents restoring the **local dev** DB from a committed dump only — no staging/Cloud SQL restore has been exercised or documented as tested. |
| Load testing / performance | **Real, executed against live Cloud SQL** — the 2026-08-07 4-run tuning exercise (see §8) used `pg_stat_statements` to identify `/meal-plan/week`'s `selectinload` query pattern as ~77% of top-5 query time. **This hotspot is confirmed still unaddressed** as of the 2026-09-11 session note. |
| Problems | QueuePool exhaustion at 1000 local concurrent users (expected — motivated the move to Cloud Run); Postgres CPU pegged at 0.88–1.00 on the original tier under staging load, resolved by the tier bump |

---

## 7. Redis

| Item | Detail |
|---|---|
| Provider | GCP Memorystore, instance `mityahar-redis` |
| Tier | Basic (per CLAUDE.md — no HA/replica tier) |
| Auth | AUTH enabled |
| Transit encryption | **Disabled** (`transitEncryptionMode=DISABLED`, the default — never explicitly reviewed). CLAUDE.md's own words: "connection is AUTH-authenticated but unencrypted in transit ... acceptable within single-VPC-only access, pending formal review before production." This is a standing, self-identified gap — not resolved as of this audit. |
| Used for | Rate limiting only (`slowapi`-backed `FailOpenLimiter` in `app/core/limiter.py`) — no session storage, no caching layer, no queues observed |
| Fail-open behavior | Deliberate and verified: on Redis error the limiter logs and lets requests through rather than 500ing; confirmed by real chaos tests (`docker stop mityahar-redis` mid-load, see §8) — `redis_fail_open: true` in `chaos_report.json` |
| Performance testing | Chaos-tested locally via Docker container kill, not against the live Memorystore instance directly. No dedicated Memorystore-specific load test found. |
| Problems | None found beyond the standing transit-encryption gap noted above |

---

## 8. Testing Results

Do not treat script existence as proof of execution — the table below is built from actual timestamped result files, not script inventories.

| Test | Status | Key Result | Evidence |
|---|---|---|---|
| Unit tests (3 files) | **COMPLETED** (CI-verified, every push) | Pass/fail per push | `.github/workflows/ci.yml` |
| Unit tests (remaining ~11 files) | **SCRIPT-ONLY** | No per-file execution log found | `tests/*.py` |
| Full integration suite | **COMPLETED** (manual, off-CI) | 94/94 steps + 10/10 error cases pass | `BUILD_TRACKER.md` (2026-07-28), `DEPLOY_CHECKLIST.md` |
| API benchmark (single-user) | **COMPLETED** | Doctor login p50=213.5ms, 9/10 success | `reports/benchmark_baseline.json` (2026-06-30) |
| Load test, 100 users, local | **COMPLETED** | 29.59 req/s sustained, 0 errors; but `POST /auth/token` p95=5200ms, p99=5800ms | `reports/pass5_stress_stats.csv` |
| Load test, 1000 users, local single-process | **COMPLETED** (deliberately breaking) | 83% failure rate — used to justify Cloud Run migration | `reports/load_1000users_stats.csv` |
| **Staging Cloud Run + Cloud SQL load test** | **COMPLETED, but stale** | 4 iterative runs; Runs 1–3 **failed** (CPU pinned / DB CPU pinned / worst p95); Run 4 **passed** after 2 workers/2 vCPU + DB tier bump — error rate 0.0088%, p95>3s streak ~4s (vs 30s threshold), mean latency 176.6ms | `BUILD_TRACKER.md`, 2026-08-07 |
| Horizontal autoscaling at 1000 users | **NOT COMPLETED** | Explicitly unchecked open item | `docs/guides/DEPLOY_CHECKLIST.md` §B |
| Chaos/failure recovery (Redis kill, DB terminate) | **COMPLETED** | ~0% failure across baseline/redis-kill/db-terminate/combined scenarios | `reports/chaos_report.json`, `chaos_scale_report.json` |
| Rate limiting / throttling (multi-IP spoof) | **COMPLETED** (local only) | 50 spoofed XFF IPs, all 401 not 429, zero cross-tenant throttling | `VERIFICATION_PLAYBOOK.md` |
| Rate limiting behind real GCP load balancer | **NOT COMPLETED** | Real per-IP isolation with actual GCLB headers never tested | `DEPLOY_CHECKLIST.md` §B |
| Network latency emulation (Indian 4G) | **PARTIAL** | Config wired (`playwright.config.ts`), unclear if active in the one completed E2E run | — |
| E2E (Playwright, doctor + patient flows) | **COMPLETED, with known failures** | 6 passed / 5 failed, unresolved as of 2026-07-03 | `reports/playwright-compiled-report/index.html` |
| Meal-plan medical-safety quality checks | **PARTIAL — silently broken** | Reports "50/50 PASS" but the SQL checks read JSONB keys (`food_item_id`/`name`) that don't match what the generator actually writes (`food_id`/`recipe_name`) — checks always no-op | `docs/audits/TEST_SUITE_AUDIT.md` §3 |
| Personalization simulation (14-day cycle) | **COMPLETED** | 100% adherence, 4/4 preferred dishes boosted correctly | `VERIFICATION_PLAYBOOK.md` Pass 3 |
| CI coverage of integration/load/e2e | **NOT COMPLETED** | CI runs unit tests only; explicit comment in `ci.yml` says integration suite "is not wired into CI yet" | `.github/workflows/ci.yml` |

**Staleness flag**: all load/chaos/autoscaling test evidence dates to 2026-06-30 through 2026-08-07. As of 2026-09-18 (today), over 6 weeks have passed with unrelated feature work landing (pantry planning, dish-tag locking, a new `DataChangeRequest` model, per `BUILD_TRACKER.md`) that was never re-load-tested. `CURRENT_STATE.md` (2026-09-11) additionally notes CI was **not reconfirmed green** after the last fix (`27a8577`, 2026-08-07) and the `/meal-plan/week` query hotspot identified by the load test remains open.

---

## 9. Deployment Problems (verified, with resolution status)

1. **Cloud Scheduler `complete-expired-plans` fired on the wrong day.** Cause: cron expression `0 1 * * 0` (Sundays) instead of `0 1 * * 1` (Mondays), against `internal.py`'s week-boundary math which assumes Monday. Fix: `gcloud scheduler jobs update` applied directly on 2026-08-06 (not via the checked-in `infra/cloud_scheduler_jobs.sh`, which the script's own header now documents as a reference/idempotent-recreate tool rather than the live source of schedule truth). **Verified fixed** — CLAUDE.md and the script both now show the corrected Monday schedule.
2. **APScheduler removed in favor of Cloud Scheduler HTTP cron.** Historical risk: in-process APScheduler would run jobs once per worker under multi-worker/autoscaled deployment, causing duplicate execution. Fix: fully removed, replaced with the 3 HTTP cron endpoints. **Verified fixed** — zero references to APScheduler remain in `app/`.
3. **Meal-plan medical-safety quality checks are silently broken.** JSONB key mismatch (checks look for `food_item_id`/`name`, generator writes `food_id`/`recipe_name`) means every check evaluates against SQL NULL and trivially "passes." **Not fixed** — reported "50/50 PASS" cannot currently be trusted as evidence the medical-safety logic is sound.
4. **MFA QR code sent TOTP secret to a third-party API** (`api.qrserver.com`) for image rendering — a privacy leak for a security-sensitive secret. A client-side fix (local rendering via `qrcode.react`) is recorded in `CURRENT_STATE.md` as of the last session note, but **whether it's committed and deployed is UNKNOWN** to this audit — verify before treating it as resolved.
5. **`deploy-env-reference.txt` vs. actual staging env mismatch** (e.g. `REQUIRE_EMAIL_VERIFICATION`). Not a runtime bug (the reference file is never read by the app), but a documentation-hygiene risk if it's used as a template for a future production deploy without reconciling against the values CLAUDE.md records as actually live on staging. **Not resolved**, low urgency.
6. **`docs/guides/DEPLOY_CHECKLIST.md` is itself stale.** Dated 2026-07-03, it states "GCP deployment not yet started" and lists "no staging environment" as a high-severity open item — both since overtaken by events (staging has existed and been load-tested since). This is a documentation-currency issue, not an infrastructure one, but it means anyone using that checklist today would be working from outdated assumptions.

---

## 10. Live Server Assessment

**What "live" currently means for Mitihar, precisely:**

- **Backend**: publicly accessible ✅, stable URL ✅ (`https://mityahar-api-759811872653.asia-south1.run.app`), HTTPS ✅ (Cloud Run default domain — **no custom domain found anywhere in the repo**), continuously running ✅ (Cloud Run serverless — scales to zero/up automatically, no evidence of min-instances configuration either way).
- **Frontend (web dashboard)**: **not publicly accessible** — no evidence of a live Firebase Hosting deploy.
- **Patient app**: **not publicly accessible** — never built for distribution, dev-client only.
- **Can another person currently open and use Mitihar?** No, not as a product. A teammate could authenticate against and call the backend API directly with a tool like curl or Postman, but there is no deployed UI — web or mobile — for them to actually use.

**Does a live backend mean the application is "live"?** No — for a three-tier product (web dashboard, patient app, API), a live API with no deployed client is infrastructure readiness, not product readiness. The distinction matters here specifically because both client apps have concrete, unambiguous evidence of non-deployment (gitignored `dist/`, literal placeholder EAS URLs) rather than mere documentation silence.

**Stage classification:**

| Stage | Backend | Web dashboard | Patient app |
|---|:---:|:---:|:---:|
| Local | passed | current state | current state |
| Cloud Testing | passed (load-tested 2026-08-07) | — | — |
| **Staging** | **← currently here** | not started | not started |
| Production/Live | not started | not started | not started |

**What's still required for a proper live application**: deploy the web dashboard to the already-configured Firebase Hosting project and confirm it talks to the staging API; replace the EAS placeholder URLs and run a real internal-distribution build of the patient app; re-run the load test suite against current code (the last one predates several feature merges); resolve the open `/meal-plan/week` query hotspot; reconfirm CI is green; and only then have a real conversation about a production (as opposed to staging) cutover, custom domain, and Redis transit-encryption review.

---

## 11. Production Readiness

| Area | Status | Basis |
|---|---|---|
| Frontend (web) | **NOT IMPLEMENTED** | Configured, never deployed — no CI step, no deploy log |
| Frontend (patient app) | **NOT IMPLEMENTED** | Literal placeholder URLs in `eas.json`, never built |
| Backend | **NEEDS VERIFICATION** | Deployed and load-tested once (2026-08-07), evidence now stale, CI not reconfirmed green since |
| Database | **NEEDS VERIFICATION** | Provisioned and load-verified, but backup/restore for Cloud SQL is manual-prose only, never exercised in-repo |
| Redis | **NEEDS WORK** | Functioning, AUTH-protected, but transit encryption is off — self-flagged as pending review |
| Authentication | **READY** | JWT+cookie, Google OAuth, TOTP MFA all genuinely implemented and exercised |
| Security (general) | **NEEDS VERIFICATION** | `security_verification_test.py` reportedly passed once (bundled in the 94/94 figure), not in CI, not recently rerun |
| Networking | **NEEDS VERIFICATION** | Direct VPC Egress + private IPs configured per docs; no in-repo config artifact confirms current Cloud Run resource settings |
| Monitoring | **NOT IMPLEMENTED** | No standing monitoring/alerting config found; Cloud Run/SQL metrics were read manually during the one-off Aug 7 test |
| Logging | **NEEDS VERIFICATION** | Ad hoc local logs exist; no structured logging/alerting pipeline evidenced for staging |
| Error handling | **NEEDS VERIFICATION** | Rate limiter fails open by design (verified); no broader error-handling audit found |
| Autoscaling | **NEEDS VERIFICATION** | Vertical tuning validated once; true horizontal multi-instance autoscaling explicitly untested |
| Rate limiting | **NEEDS VERIFICATION** | Mechanism implemented and locally verified; real behavior behind GCP's load balancer untested |
| Backups | **NEEDS WORK** | No automated, tested Cloud SQL backup/restore procedure found |
| CI/CD | **NEEDS WORK** | CI covers lint + 3 unit test files only; zero deploy automation, zero integration/load/e2e in CI |
| Domain/HTTPS | **NEEDS VERIFICATION** | HTTPS via Cloud Run default domain confirmed; no custom domain; frontend domain status unconfirmed |
| Performance | **NEEDS VERIFICATION** | One successful tuned config found, over 6 weeks stale, known unaddressed query hotspot |
| Cost management | **NOT IMPLEMENTED** | No budget alerts or cost-tracking config found in repo |
| Failure recovery | **NEEDS VERIFICATION** | Chaos tests for Redis/DB outage passed once; not repeated since, and not run against the live Memorystore instance |

---

## 12. Completed Work

- FastAPI backend deployed and running on Cloud Run staging, with a documented, working manual deploy script that correctly handles pinned Cloud Run jobs.
- Cloud SQL Postgres (private IP) and Memorystore Redis (AUTH-enabled) provisioned and reachable via Direct VPC Egress.
- Cloud Scheduler cron replacing in-process APScheduler — architecturally correct for an autoscaled/multi-worker deployment, with one real scheduling bug found and fixed.
- JWT + cookie auth, Google OAuth, and TOTP MFA all genuinely implemented (not stubs).
- A real 4-run load-tuning exercise against live Cloud Run + Cloud SQL that found and fixed two genuine bottlenecks (Cloud Run CPU saturation, Cloud SQL CPU saturation).
- Chaos testing (Redis kill, DB terminate) confirming the rate limiter's fail-open design and DB pool recovery behavior work as intended.
- Local load testing up to 1000 concurrent users that correctly identified the local single-process ceiling and motivated the Cloud Run migration.
- CI pipeline running lint + 3 unit test files on every push.
- Firebase Hosting project and EAS build profiles scaffolded (not deployed, but the scaffolding itself is real and correctly formed).

## 13. Partially Completed Work

- Web dashboard: hosting target configured, never deployed.
- Patient app: build profiles scaffolded with explicit placeholder markers, never built.
- Meal-plan medical-safety quality checks: run and reported passing, but the checks themselves are broken (JSONB key mismatch) and prove nothing currently.
- E2E (Playwright) suite: executed with a real, evidenced 5-failure result that was never triaged to resolution.
- Rate limiting: mechanism verified locally; real GCP load-balancer-level per-IP behavior unverified.
- MFA QR privacy fix: client-side fix exists per session notes; commit/deploy status unconfirmed.

## 14. Pending Work

- Deploy the web dashboard to Firebase Hosting and confirm it reaches the staging API.
- Fill in real EAS URLs and build a distributable version of the patient app.
- Fix the broken JSONB key check in the meal-plan quality-verification script.
- Re-run the full load/chaos/E2E test suite against current `main` (last run predates several feature merges).
- Test true horizontal autoscaling at target concurrency.
- Test rate limiting behind the real GCP load balancer with real client IPs.
- Address the `/meal-plan/week` `selectinload` query hotspot identified in the Aug 7 load test.
- Establish an automated, tested Cloud SQL backup/restore procedure.
- Wire the full integration suite and E2E tests into CI.
- Reconcile `deploy-env-reference.txt` against the actual staging env values before it's used as a production template.
- Review Redis transit encryption before any production cutover (CLAUDE.md's own stated gap).
- Reconfirm CI is green post the Aug 7 `SECRET_KEY`-quoting fix.

## 15. Unknown / Unverified Items

- Whether the MFA QR-code client-side rendering fix has actually been committed and deployed.
- Actual current Cloud Run CPU/RAM/instance-count/concurrency/timeout configuration (no config-as-code exists; only inferred from a one-off load-test narrative).
- Whether the `.env`/`.env.production` files in either client app actually point at the staging API URL (could not be read in this audit pass — permission-restricted).
- Whether a custom domain exists or is planned (none found in repo).
- Whether any monitoring/alerting is configured directly in the GCP console outside of what's captured in this repo.

## 16. Recommended Next Steps (sequenced)

1. **Re-verify the backend is actually still in the state the Aug 7 test left it** — confirm CI is green, confirm the Cloud Run config matches what passed Run 4, before trusting any of the existing load-test evidence as current.
2. **Fix the broken meal-plan quality check** (JSONB key mismatch) — this is a one-line-class bug currently masking whether medical-safety logic works at all.
3. **Deploy the web dashboard** to the already-configured Firebase Hosting project; smoke-test it against the staging API; this is the fastest path to an actual "live application" a teammate can open.
4. **Re-run the full load/chaos/E2E suite** against current `main` given 6+ weeks of unreviewed feature drift.
5. **Address the `/meal-plan/week` query hotspot** flagged by the load test and still open.
6. **Build and distribute an internal patient-app preview** via EAS once real URLs are filled in.
7. Only after 1–6: begin a formal staging→production readiness review covering monitoring, backups, cost management, and the Redis transit-encryption gap — none of which are close to ready today.
