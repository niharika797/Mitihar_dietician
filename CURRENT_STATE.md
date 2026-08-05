# Current State

_Last updated: 2026-08-05. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Committed the quantity-aware pantry work (`0a2cfbe`): `patient_pantry.quantity_g` three-state (NULL=have/unknown, 0=out of stock, >0=grams) with new CHECK constraint and migration `e4f5a6b7c8d9`; `_PANTRY_IN_STOCK` predicate in `app/routers/meal_plan.py` centralizes "have" logic across week-plan coverage, pantry catalogue, and shopping list.
- `GET /shopping-list` computes live from confirmed choices (falling back to `combo_index=0`) minus pantry stock, staples excluded — replaces the old frozen `ingredient_checklist` JSONB read.
- `confirm-choice` nets pantry deltas (credits previous choice, debits new one) scaled by `BOWL_FACTORS`, stores `actual_calories`.
- Mobile: `PantrySection` debounced (300ms) grams input; `meals.tsx`/`combo-detail.tsx` invalidate pantry + shopping-list caches on confirm; `services/meals.ts`/`types/index.ts` carry `quantity_g` through.
- Promoted to staging: pre-flight confirmed `alembic_version=d3e4f5a6b7c8` (clean, matches migration's parent), backed up (`1785921324568`, SUCCESSFUL), deployed via `scripts.deploy_staging`, ran `mityahar-migrate`, re-verified `alembic_version=e4f5a6b7c8d9`, `/health` returns 200.

## Blockers / pending
- No endpoint/UI verification done against staging or a running app yet — schema is live, behavior isn't tested.
- Thin pools cap non-veg split (8 breakfast, 3 lunch-accompaniment non-veg mains) — 85/630 slots miss 2/4.
- Home-dashboard Kitchen sections still unverified in a running app.
- 61 flagged `ingredient_ifct_map.csv` rows need manual review; IFCT scrambled multi-line Food Names unfixed.
- Cloud Scheduler jobs for the 3 `/internal/cron/*` endpoints not created; `mityahar-audit-tmp` Cloud Run job left behind.
- Patient 1's 954 `patient_meal_choices` rows deleted during testing this session — local only, unrecoverable (`db-backups/` has no patient data).

## Next action
Verify pantry auto-deduct + shopping-list endpoints and the PantrySection quantity UI end-to-end in a running app (staging schema is ready, nothing exercised yet).
