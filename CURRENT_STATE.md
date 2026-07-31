# Current State

_Last updated: 2026-08-01. Overwritten each session — no history here. Full narrative in BUILD_TRACKER_ARCHIVE.md._

## Done this session — Stage 6 multi-doctor duplicate-dish system (commit `80d0a17`, branch feature/api-remediation-v0.2)
- **Data cleanup applied + audited** (reversible via `deleted_at`): 139 Tier-1 exact dupes merged, 14 Tier-2 converged, 315 rows recomputed from ingredients, 168 genuine conflicts parked (unverified) + pending `DataChangeRequest`. Pool 2101→1780 verified+live, **0 canonical collisions**.
- **Prevention**: `name_normalized` + `uq_fi_canonical` partial-unique index (one canonical dish per name/slot/diet in served pool). All 4 insert paths set it; add_recipe dedup canonical+deleted_at-aware; admin approve blocks 2nd canonical (409, tested).
- **Security/governance**: `patch_recipe_tags` ownership (own-unverified only, no force-verify); generator now filters `deleted_at IS NULL`; DataChangeRequest queue + append-only DataChangeAuditLog; admin delete→soft-delete.
- **UI**: admin "Data Review" queue + doctor "Data Review" flag-only tab — both browser-verified E2E (doctor flag → admin approve → status flip; 0 console errors).
- Migrations `d1e2f3a4b5c6`→`d2e3f4a5b6c7`→`d3e4f5a6b7c8` applied, `alembic check` clean. Content dump refreshed `2026-07-31` (dedup+FK-clean); RESTORE.md updated.

## Blockers / pending
- 168 parked same-name conflicts await admin decisions in the Data Review queue (expected — genuine conflicts, never auto-picked).
- Deferred (named in plan): AI web-research sourcing, monthly Tier-1 re-verify cron, DB-grant audit enforcement, ingredient synonym canonicalisation, fuzzy spelling-variant auto-merge.
- Local test creds reset this session: testdoctor@mityahar.com / admin@mityahar.com → `DoctorTest@2026` / `Admin@2026`.

## Next action
Work the parked Tier-2 conflicts via the admin Data Review queue, or start the deferred ingredient-canonicalisation pass. Backend (:8001) + web (:3000) left running.
