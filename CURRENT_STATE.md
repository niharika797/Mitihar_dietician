# Current State

_Last updated: 2026-08-03. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- **Repo reorg**: `docs/` bucketed (`architecture/`, `audits/`, `guides/`, `planning/`, `reference/`, `walkthroughs/`, `archive/`); dead one-offs to `scripts/archive/`; working CSVs/checkpoints to `data/review/`; `.gitignore` + `CLAUDE.md` layout updated.
- **Ingredient quantities rebuilt** (`scripts/rebuild_ingredient_quantities.py`): root cause was a flat 80 g/piece conversion for every *counted* ingredient. Rebuilt from the pre-damage backup — ERROR rows 1,158 → 0. Deprecated `fix_ingredient_quantities.py` (flat-value collapse, `clove`→garlic keyword collision, flat 180 g cap) stays archived.
- **Checker vocabulary** (`scripts/sanity_check_ingredients.py`): uncategorized rows 1,582 → 29; new `curry_leaf` / `condiment_sauce` / `beverage_liquid` categories; fixed `Mustard/Coconut/Sesame oil` + `Buttermilk` miscategorization; fixed the same `clove` collision inside `check_count_vs_grams`.
- **Non-food purge**: 25 rows deleted (`Coal`, `Charcoal`, `Toothpicks`, parser fragments) — 1,980 g of phantom weight.
- **Ingredient dedup** (`scripts/merge_duplicate_ingredients.py`): 43 duplicates merged, 2,816 recipe rows repointed. Wired in the previously **orphaned** IFCT 2017 data (0 → 4,720 rows on IFCT-sourced ingredients), then corrected two bad variety matches (coconut → fresh kernel 624→408.9; milk → cow 107.3→72.9).
- **Assignment gate**: `get_assignable_dish()` (`app/services/dish_service.py`) wired into `patch_dish`/`pin_dish` — blocks soft-deleted always, unverified unless it's the doctor's own dish.
- Nutrition recalculated: 2,101 calculated, median 272 kcal/serving, **0 dishes >1,500 kcal**. 71 tests pass.

## Blockers / pending
- `ingredient_ifct_map.csv` has more variety mismatches: 5 of the 15 audited were wrong. Remaining known-but-accepted: `mango`→green-raw, `cabbage`→Chinese, `tomato`→green (all ≤7 kcal). **~73 of 88 IFCT mappings never audited.**
- 49 dishes still <50 kcal/serving and 1 with zero ingredients (id 3724) — ingest dropped unmatched ingredients; a quantity fix cannot recover a missing main ingredient.
- `weekly_combos` holds 1,388 refs to soft-deleted dishes + 1 dangling id (3718). Display is safe (JSONB snapshots); the new gate stops new ones.

## Next action
Audit the remaining `ingredient_ifct_map.csv` entries for variety mismatches, then decide on the <50 kcal ingest-completeness gap.
