# Current State

_Last updated: 2026-07-15 (Stage 2 session). Overwritten each session — no history here. Full narrative in BUILD_TRACKER_ARCHIVE.md._

## Done this session
- `56eee5b`: docs/ un-ignored and committed (audit-trail migration docs now in git; CREDENTIALS.local.md stays ignored). Includes `docs/STAGE1_PLAN_IMPACT.md`.
- `4f93d82`: Stage 2 — JSONB backfill applied (net 21 rows; 1 whitespace-dup removed), all 3 readers repointed to `recipe_ingredients` (incl. allergy filter `_is_allergenic`), doctor add-recipe dual-writes, `FoodItem.ingredients` marked DEPRECATED, nutrition re-stamped (2122 calculated / 15 manual, real-dish macros unchanged in 10-dish spot-check).
- STAGE1_PLAN_IMPACT.md: 52 patients, old vs corrected B/L/D/buffer targets + indicative dish diff — decision pending (doctor notification / re-approval). No plans regenerated.
- Verified: ruff clean, split-math tests pass, 52 in-memory regenerations exercised new readers, backend boots clean, doctor dashboard Recipe tab loads with 0 console errors, `tsc --noEmit` 0 errors (PlanTab `patientMealsPerDay` flag was stale — resolved).

## Blockers / pending
- 61 flagged artifact rows: untouched, Stage 3 scope (documented in NUTRITION_SOURCE_MIGRATION.md).
- 52 underfed plans: report delivered, regeneration/notification decision with product owner.
- 6 commits ahead of origin (dda93d6..4f93d82 + session-end commit) — none pushed.
- `recipe_ingredients_audit.csv` left untracked (regenerable via scripts/export_recipes_to_csv.py).
- Recipe tab shows 2 dishes with non-ASCII names rendering as "?????" — check encoding during UI review.

## Next action
UI review of Recipe tab (backend :8001 + Vite :5173 left running); then Stage 3 artifact-row cleanup and 52-plan decision.
