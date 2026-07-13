# Current State

_Last updated: 2026-07-13. Overwritten each session — no history here. Full narrative in BUILD_TRACKER_ARCHIVE.md._

## Done this session
- db_models.py: 24/26 classes migrated to `Mapped[]`/`mapped_column()`; `FoodItem`/`MealTemplate` excluded (DO NOT MODIFY). Verified vs live schema (local + staging), zero mismatches.
- Migration 651cd3d46fa9: drops dead `beverages` table + `food_items.instructions` (0 rows, confirmed on both local & staging via temp Cloud Run job). Downgrade round-trip tested.
- Added 3 model-missing indexes (idx_patients_doctor_id, idx_patient_requests_doctor_id, idx_sc_reserved_by) — alembic check now clean except deliberate `original_name` (kept, still a live rollback column — see backend-notes.md)
- CI finalized: ruff now blocking (0 errors — 30 auto-fixed, 24 deferred + documented in pyproject.toml comments), mypy non-blocking (154 findings, `continue-on-error`), pytest blocking. `.python-version` relaxed to `3.13` (was exact patch `3.13.14` — GitHub Actions manifest-lag risk)
- Fixed stale CLAUDE.md claim about `rename_checkpoint.json` (file was deleted 2026-06-29, doc still said "safe to re-run")
- doctor.py dup-check fix, full_backend_test.py Section 12 idempotency, Dockerfile/.gitignore fixes, .claude/rules/*-notes.md, Firebase hosting config (all carried from earlier this session)

## Blockers / pending
- Staging DB is 1 migration behind local dev (651cd3d46fa9 applied locally only; staging still has dead `beverages`/`instructions`) — apply via `mityahar-migrate` Cloud Run job before/with next staging deploy
- `food_items.original_name` empty on both DBs — dish-rename pipeline resume-safety unclear, needs a product decision (not a code fix)
- Ruff's 24 deferred findings (19 raise-without-from, 3 strip-multi-char, 1 unused-loop-var, 1 unused-var) + mypy's 154 need a dedicated cleanup pass eventually
- Nothing committed since dd39dde (2026-07-03) — 30 commits ahead of origin/feature branch, all above uncommitted
- Cloud Scheduler jobs for the 3 cron endpoints not yet created; FCM project ownership (`mitihar-prod`) still undecided

## Next action
Commit everything (incl. CI + schema cleanup), then create the 3 Cloud Scheduler jobs.
