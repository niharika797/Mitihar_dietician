# Current State

_Last updated: 2026-08-04. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Data fixes applied locally AND promoted to staging (verified equal: food_items 2115 / ingredients 907 / recipe_ingredients 18172, alembic `d3e4f5a6b7c8`). Cloud SQL backup `1785820521122` is the rollback point. Took 8 attempts — every failure was a local/staging parity assumption; captured in the local-only `staging-deploy` skill (`.claude/` is gitignored, so it is NOT version-controlled).
- `backfill_gap_dish_ingredients.py` + `reclassify_low_kcal_dishes.py` both run with `--write` (5 dishes recalculated, 10 retagged; 44 dishes remain <50 kcal, all legitimately condiments/beverages).
- Meal-gen tested against all 121 real patients: 121/121 generate, 0 avoid-tag violations, 0 calorie failures.
- Variety was 0/121 because the check counted accompaniments (11 distinct dishes over 10,108 placements — repetition guaranteed by construction). Now slot-type-exempt, and two real generator bugs fixed behind it. **121/121 verified.**
- Generator `_pick_for_slot` fallback reordered: an unseen fallback-diet dish now beats a repeat from the patient's own pool (was re-serving one dish 7 days running while 220 sat unused).
- Generator non-veg mix is now **2 of every slot's 4 combos**, breakfast included, replacing the weekly-budget pre-allocation that left Non-Veg patients whole days with no meat option. 545/630 slots hit 2/4 exactly. `nonveg_meals_per_week` no longer gates generation (kept on the model/API).
- Patient app: Pantry + Shopping List moved off the Meals tab into collapsible Home-dashboard sections (`components/PantrySection.tsx`, `ShoppingListSection.tsx`); old pushed screens and routes deleted. Plan History stays on Meals.

## Blockers / pending
- Thin pools cap the non-veg split: breakfast has 8 servable non-veg/egg `main_dish` vs the 14 a full week needs; non-veg lunch `accompaniment` is 3. That alone explains the 85/630 slots that miss 2/4.
- New Home-dashboard Kitchen sections typecheck clean but have NOT been verified in a running app.
- 61 flagged `ingredient_ifct_map.csv` rows still need manual review (`audit_ifct_variety_matches.py`).
- IFCT extraction: scrambled multi-line Food Names are detected but NOT fixed — reading order isn't recoverable from x/y for some wrapped rows.
- Approved but unbuilt: `patient_pantry.quantity_g` migration, pantry auto-deduct on confirm-choice, live-derived shopping list replacing the static `ingredient_checklist` blob.
- Cloud Scheduler jobs for the three `/internal/cron/*` endpoints still not created; `mityahar-audit-tmp` Cloud Run job left behind.

## Next action
Build the approved pantry quantity + auto-deduct + live shopping-list backend work, or add non-veg recipes to the thin breakfast/accompaniment pools.
