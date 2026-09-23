# Two-Week Summary — Mityahar Dietician

_Range: 2026-06-28 → 2026-07-12. Generated from git log + CURRENT_STATE.md + session memory._

---

## 1. Pre-deployment hardening sprint (Jul 1–3, commits `09d1d95` → `dd39dde`)

This was the main body of work: getting the backend and patient app ready for a staging deploy.

**Security**
- Constant-time secret comparison on internal cron endpoints (`a221707`)
- Atomic UPDATE closes an FCM double-fire race in `flag-expiring-patients` (`9d516db`)
- COOKIE_SECURE fail-closed guard at startup (`0e50a87`)
- Replaced hostname-heuristic environment detection with an explicit `ENVIRONMENT` flag (`412f810`)
- CVE bumps + pinned `pip-tools` lockfile (`2fac4e0`)
- Retired `.env.production` (misleading reference file) (`e2d4b07`)

**Infra**
- Migrated from in-process APScheduler to Cloud Scheduler → HTTP cron endpoints (`b2bc7c0`)
- Chaos test suite + migration audit + pre-migration backup script (`c5a37a6`)
- Dockerfile hardening, dev-only pytest requirements split (`5abe488`, `a05e5a5`)
- Removed dead `apscheduler` dep, added missing `redis` pin (`8826962`)

**Performance**
- Static `axios` import in `PlanTab.tsx` — Plan tab load on 4G: 314ms → 224ms (`66e9b76`)
- New index on `patient_requests.doctor_id`, migration `2b3c4d5e6f7a` (`3c7f724`)

**Patient app**
- EAS build profiles + Sentry crash reporting (`f5f8c9e`)
- Persist rotated refresh token, route dead sessions to login (`4ea1377`)
- `npx expo install --fix` — 17 SDK 55 packages realigned (`0e7029a`)

**Housekeeping**
- Untracked local `.claude/` config, removed tracked `__pycache__` artifacts, gitignore triage

Deploy checklist tracked throughout in docs commits; local verification (5 passes) completed and committed `09d1d95`.

## 2. Staging deploy + read-only audits (Jul 4–6, uncommitted / infra-only — no git commits)

Per session memory, not reflected in git history since this was GCP console/CLI work:

- Ran all 34 Alembic migrations against staging Cloud SQL via a Cloud Run job (proxy path doesn't work — instance is private-IP-only)
- Fixed Firebase service-account credential loading on staging Cloud Run (deploy revision `00006-nqb` now serving 100%)
- Validated FCM notification flow end-to-end via a temporary Cloud Run job (insert test patient → trigger cron → dispatch push → cleanup)
- Flagged Memorystore Redis transit encryption as disabled — pending formal review before production
- Migrated a backup file off the D: drive into the project dir with integrity verification
- **Read-only audit of subscription-expiry logic** — found:
  - `token_1_expiry` (operational, cron-driven) and `subscription_end_date` (billing metadata, admin-only) are two decoupled expiry concepts
  - Doctor dashboard "expiring soon" widget reads the stale `subscription_end_date` field — likely shows empty in normal flow
  - `admin.override_subscription` sets `subscription_status` without syncing `token_1_expiry`/`token_1_active` — cron can silently undo the override within 24h
  - 3 DEBUG-level logs hide notification failures/successes from production observability
  - No code changes made — findings only, reported to user

## 3. Current uncommitted state (as of Jul 12)

Nothing has been committed since `dd39dde` (Jul 3). Working tree currently has:

- `app/routers/doctor.py` — duplicate recipe-name lookup now orders by `id desc` before `.limit(1)` (deterministic)
- `tests/full_backend_test.py` — Section 12 now pre/post-cleans the "Test Dal Tadka" recipe so reruns are idempotent
- `Dockerfile` — now copies `scripts/`
- `.gitignore` — ignores `docs/CREDENTIALS.local.md`, narrowed to let `.claude/rules/**` through
- New: `.claude/rules/{backend,frontend,generator}-notes.md`
- `BUILD_TRACKER.md`/`CLAUDE.md` trimmed; full prior narrative moved to new `BUILD_TRACKER_ARCHIVE.md`
- New untracked: `mitihar-frontend/apps/.firebaserc`, `.gitignore`, `firebase.json` (Firebase hosting config for the web dashboard)
- New untracked: `tests/_clean_test_recipes.py`, `tests/performance/e2e/playwright.compiled.config.ts`
- New untracked: `vibecoding-legal-guide.md`
- Just added today: `harness-engineering` skill under `.claude/skills/`

## 4. Open blockers

- **Nothing committed since `dd39dde`** — all of section 2 and 3's work is sitting locally uncommitted
- Cloud Scheduler jobs for the 3 cron endpoints (flag-expiring, deactivate-expired, complete-expired-plans) still not created
- FCM project ownership unresolved — patient app targets `mitihar-prod`, which the active `gcloud` account cannot access (out-of-policy)
- Doctor dashboard "expiring soon" widget likely broken (reads stale field, see §2)
- Admin subscription override / cron desync race (see §2) — not yet fixed
- Notification DEBUG logging hides prod observability — not yet fixed
- `axios.ts` bundle-splitting warning still open (pre-launch debt, flagged for Layer 2 4G retest)
- Memorystore Redis transit encryption disabled — pending formal review

## Next action (per CURRENT_STATE.md)

Commit the accumulated local changes, then create the 3 Cloud Scheduler jobs.
