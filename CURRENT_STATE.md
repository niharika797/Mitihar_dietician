# Current State

_Last updated: 2026-08-05. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Patient-side flagged-visit approval: `GET /patients/pending-visits` + `POST /patients/pending-visits/{id}/respond` (atomic claim, prices by visit_date not approval time), `RespondVisitRequest` schema, `PendingVisitSection.tsx` card on patient home, `profile.ts`/`queryKeys.ts` wiring, `visit_flagged` push routing.
- Centralized billing constants in `token_service.py` (`VISIT_CHARGE_INR=1500`, `CYCLE_DAYS=30`, `VISIT_GRACE_DAYS=15`; fixed a stale ₹1,200 docstring vs the real ₹1,500); `is_chargeable_visit` now takes an explicit `now`; replaced scattered literals in `admin.py`/`doctor.py`/`patients.py`.
- Doctor dashboard: `recordVisit` now sends required `token_2`; added `flagVisit`; `VisitsTab.tsx` gained a Token 2 input + "Flag Visit" button; corrected a wrong comment claiming `/recipes/lookup` was dead (found via new `scripts/audit_endpoint_usage.py`).
- Made `notify_visit_flagged` best-effort in `doctor.py`'s `flag_visit` so a push failure can't roll back the approval row.
- Marked 3 `/internal/cron/*` endpoints external-trigger; added `infra/cloud_scheduler_jobs.sh` (written, not run).
- Added `tests/test_flag_visit.py` (10 DB-free tests), wired into `ci.yml`.
- Closed the doctor's side of the loop: `GET /doctor/flagged-visits` (filters `patient_id` / `answered_only`), a Flagged Visits status table in `VisitsTab.tsx`, and the header bell in `DoctorShell.tsx` — previously hardcoded `[]` — now fed with patient answers. Doctors have no `fcm_token`, so in-app is the only channel.
- Verified end-to-end against live HTTP + DB: record-visit 400s on wrong token / 200s on right one; flag → approve charges once (counter 0→1); **replayed approval 404s and does not double-bill**; reject never charges. Constant extraction proven inert (86 boundary cases, 0 diffs).

## Blockers / pending
- `PendingVisitSection.tsx` (patient app) never run — typechecks only, no emulator driven.
- `infra/cloud_scheduler_jobs.sh` not yet executed — the 3 cron endpoints remain unscheduled in GCP.
- Pantry endpoints/UI (prior session) still unverified against a running app.
- **Pre-existing, untouched:** `approve-renewal` 500s for any patient with NULL `token_1` (`RenewalApproveResponse` requires a str).

## Next action
Exercise `PendingVisitSection` in the patient app, then run `infra/cloud_scheduler_jobs.sh` against staging (needs `CRON_SECRET` from Secret Manager).
