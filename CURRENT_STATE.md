# Current State

_Last updated: 2026-07-15. Overwritten each session — no history here. Full narrative in BUILD_TRACKER_ARCHIVE.md._

## Done this session
- `cf1b6ab`: fixed double-applied 15% TDEE buffer in meal generator (meals were landing at 72.25% of TDEE, not 85%); added unit tests. 52 existing patient plans were generated under the old math — regeneration deliberately not done.
- `02d8d4a`: JSONB vs `recipe_ingredients` diff report (1555/2137 dishes agree; remaining gram conflicts are stale 10x values, `recipe_ingredients` is authoritative) + gated, dry-run-by-default `backfill_recipe_ingredients.py` (22-row scope). Flagged `meal_generator._is_allergenic` as still reading the legacy JSONB.
- Uncommitted: `scripts/export_recipes_to_csv.py` + its output `recipe_ingredients_audit.csv` (18,213 rows); `scripts/deploy_staging.py`; doc refreshes to BUILD_TRACKER.md/CLAUDE.md.

## Blockers / pending
- 4 commits ahead of `origin/feature/api-remediation-v0.2` (dda93d6, fa5e05b, cf1b6ab, 02d8d4a), none pushed; new scripts/CSV + doc edits also uncommitted
- 52 active plans generated under the pre-fix TDEE math — no regeneration decision made yet
- `meal_generator._is_allergenic` still reads the legacy JSONB — migration must repoint it before cutover
- Staging DB 1 migration behind local dev; `food_items.original_name` empty (needs product decision); Ruff/mypy cleanup pending; Cloud Scheduler jobs + FCM project ownership undecided

## Next action
Review `recipe_ingredients_audit.csv`, commit pending doc/script changes, push all local commits to origin, then decide on plan regeneration and the JSONB backfill.
