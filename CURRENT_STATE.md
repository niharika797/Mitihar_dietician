# Current State

_Last updated: 2026-08-05. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Finished wiring quantity-aware pantry end to end (still uncommitted). `patient_pantry.quantity_g` is three-state (NULL=have/unknown, 0=out of stock, >0=grams), enforced by a new CHECK constraint; `_PANTRY_IN_STOCK` predicate in `app/routers/meal_plan.py` centralizes "have" logic across week-plan coverage, the pantry catalogue, and the shopping list.
- `GET /shopping-list` rewritten to compute live from confirmed choices (falling back to `combo_index=0`) minus pantry stock, staples excluded — replaces the old frozen `ingredient_checklist` JSONB read.
- `toggle_ingredient_at_home` now writes to `patient_pantry` instead of the legacy JSONB blob, sharing `_pantry_set` with `/pantry/toggle`.
- `confirm-choice` nets pantry deltas (credits back the previous choice for that slot, debits the new one) scaled by `BOWL_FACTORS`, and stores `actual_calories`.
- Mobile: `PantrySection` has a debounced (300ms) grams input per item; `meals.tsx`/`combo-detail.tsx` invalidate pantry + shopping-list caches on confirm; `services/meals.ts`/`types/index.ts` carry `quantity_g` through.

## Blockers / pending
- Migration `e4f5a6b7c8d9` still not run; no endpoint/UI verification done.
- Thin pools cap non-veg split (8 breakfast, 3 lunch-accompaniment non-veg mains) — 85/630 slots miss 2/4.
- Home-dashboard Kitchen sections still unverified in a running app.
- 61 flagged `ingredient_ifct_map.csv` rows need manual review; IFCT scrambled multi-line Food Names unfixed.
- Cloud Scheduler jobs for the 3 `/internal/cron/*` endpoints not created; `mityahar-audit-tmp` Cloud Run job left behind.
- Patient 1's 954 `patient_meal_choices` rows deleted during testing this session — local only, unrecoverable (`db-backups/` has no patient data).

## Next action
Run `alembic upgrade head` for `e4f5a6b7c8d9`, then verify pantry auto-deduct + shopping-list endpoints and the PantrySection quantity UI end-to-end before committing.
