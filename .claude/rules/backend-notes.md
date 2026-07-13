---
name: backend-notes
description: Technical gotchas for Mityahar backend — API endpoints, DB schema quirks, scripts, and infra notes — loaded when touching app/ or scripts/
paths: "app/**"
---

## Dev Environment

- **PowerShell only** for running Python on Windows — bash fails on Windows venv
- **Rate limiter:** login endpoint limited to 5 per 15 min — restart backend to clear during testing
- **Docker Desktop** must be running before starting backend (PostgreSQL in container)

## API Endpoint Gotchas

- **Doctor login** uses `POST /api/v1/auth/doctor/login` NOT `/api/v1/auth/token`
- **Patient auth endpoint** — `/api/v1/auth/token` with `application/x-www-form-urlencoded` body (not JSON). Username/password as form fields.
- **Diet plan endpoint** — `/api/v1/diet-plans/my-plan` returns current patient plan. Not `/diet-plans/current`.
- **Meal log endpoint** — correct path is `POST /api/v1/progress/log/meal` (not /meal-log). Note for future regression scripts.
- **/diet-plans/my-plan response shape** — returns `{ user_id, created_at, meals: [...], ingredient_checklist, version, used_food_ids }`. Access `plan["meals"]` not the top-level object. Note for regression scripts.

## DB Schema — Recipes & Food Items

- **add_recipe dedup** — `POST /doctor/recipes` now checks LOWER(TRIM(recipe_name)) match before creating. Returns existing record if found (status 201, same body — idempotent from caller perspective).
- **browse_recipes change** — previously hardcoded `is_verified=True` filter (only returned verified items). Now returns all items by default; use `?is_verified=true/false` to filter.
- **Custom dish JSONB path** — `POST /doctor/patients/{id}/plan/meals/{date}/{meal_type}/add` writes directly to `recommendations.meals` JSONB. Default: `food_id=null`, `is_custom_override=True`, no food_items row created. `add_to_library=True`: creates food_items with `submitted_for_review=True`.
- **Dish-level PATCH** — `PATCH /doctor/patients/{id}/plan/meals/{date}/{meal_type}/dishes/{dish_index}` — actions: swap/remove/add. Recalculates slot totals, rebuilds Menu Names, records DoctorMealOverride with patient_id + override_date + meal_type, backfills recommendation_id onto slot.
- **submitted_for_review column** — added to food_items (migration `e6f7a8b9c0d1`, default=False). Set True when doctor explicitly submits a custom recipe to the admin approval queue.

## DB Schema — Doctor Preferences

- **PatientDishPreferences ORM** — added to `db_models.py` in Session 17. `CheckConstraint` also added to the sqlalchemy import line.
- **meal-config endpoints (Session 17)** — `GET/PATCH /doctor/patients/{id}/meal-config` + `POST/DELETE` pin/block. PATCH validates sum=85%, stores `{"Breakfast": x, "Lunch": y, "Dinner": z}`. `meal_split=null` deletes the row (resets to default). No row = default 25/35/25.
- **meal_split_override format** — `{"Breakfast": 25, "Lunch": 35, "Dinner": 25}` (integer percentages summing to 85). NOT the old breakfast_pct/lunch_pct/dinner_pct format.
- **patient_dish_preferences** — one row per (patient_id, food_item_id), `preference_type = 'pin' or 'block'`. ON CONFLICT DO UPDATE atomically switches pin↔block. Generator reads this at plan generation time via `blocked_food_ids` and `pinned_food_ids` sets.

## DB Schema — Ingredient Chain

- **Ingredient ORM models** — `Ingredient` and `RecipeIngredient` ORM classes added to `db_models.py` in Session 15.
- **ingredients table** — 950 rows (846 with LLM-estimated nutrition, 104 NULL = measurement-phrase names). Unique constraint on (name, source). `name_normalized` = lowercase+stripped for matching. `source='estimated_llm'` for Gemma-estimated values.
- **recipe_ingredients table** — 18,248 rows linking all food_items to ingredients. `quantity_g` has CHECK > 0 (`ck_ri_quantity_positive`). `food_items.ingredients` JSONB preserved as fallback.
- **nutrition_source column** on food_items — `'calculated'` for 1519 recipes (recalculated from ingredient chain via IFCT2017 + LLM values), `'manual'` for 623 (26 have no recipe_ingredients, 582 have bad quantity_g batch data errors, 15 low coverage). Calculated set: 0 outliers, range 50–1499 kcal.
- **IFCT2017 import** — 88 ingredients upgraded (`scripts/import_ifct.py`). `ARTIFACT_RE` filter added to skip measurement-phrase ingredient names (e.g. "1/2 tablespoons mustard seeds"). Blocklist in place for 4 known wrong matches. Re-run with `python -m scripts.import_ifct --write` after any ingredient additions.
- **582 manual recipes with bad quantity_g** — these recipes have pre-existing batch data entry errors (e.g. `quantity_g=8000` for makhana, 1600 for cashews). They are correctly labelled `'manual'` with their original hand-entered `cal_per_serving` values. Future session: audit quantity_g outliers and correct them to recover these recipes for calculation.

## Local Tooling

- **llama.cpp** at `C:\llama` — `llama-server.exe -m C:\llama\gemma-4-E4B-it-Q4_K_M.gguf --port 11434 --gpu-layers 99 --reasoning off`. OpenAI-compatible API at `/v1/chat/completions`. Model: Gemma 4 E4B Q4_K_M (4.97GB, fits RTX 4050 6GB).

## Rebuild History Notes (R-series, 2026-06-28)

- **R-8 gate cleared (2026-06-28):** v1 recs 169/171 deactivated; v2 plans generated for patients 3+4 (rec IDs 184/185, 84 weekly_combos each); gate count=0. R-8 unblocked.
- **R-8 complete (2026-06-28):** v1 branch + SuggestionSlot + suggestions endpoint removed. v2 is now the only path.
- **R-9 (2026-06-28):** `plan_type_tags` removed (migration + code); dead code deleted; orphaned screens removed; TS errors resolved. Rebuild complete R-0→R-9.
- **Dish cleanup (2026-06-28):** 4-pass hybrid pipeline — migration `b5c6d7e8f9a0` adds `original_name` rollback col; Pass A soft-flags test artifacts (`is_verified=False`); Pass B initcap() casing fix (0 API calls); Pass C LLM rename (claude-sonnet-4-6) for short/single-word names with slot/diet context; Pass D full change report. Script: `scripts/clean_dish_names.py`. Checkpoint: `clean_dishes_llm_checkpoint.json`.
- **Pool expansion (2026-06-28):** 6k_dataset recipes bulk-verified — calculated 1354 (IFCT-backed, all safe) + manual 13 (50–1500 kcal). Pool: `is_verified=True` 1551 (was 184). 563 manual outliers remain unverified (bad quantity_g, e.g. 30491 kcal — pending quantity_g audit). Priya rec 186: 84 combos, `validation_error=None`. Accompaniment pool exhaustion (Level-4 fallback) pre-existing thin-pool issue.
- **Dish cleanup (2026-06-28, full run):** Dish cleanup complete: 117 changes (13 flagged, 60 casing, 53 LLM); pool=1551; 0 casing issues remain.
- **Recipe quantity fix (2026-06-28):** 553 bad recipes fixed (÷10 + artifact deletion); 549 verified; pool 184→1551→2100 (11.4× total expansion); 4 flagged.
- **Flagged recipe review (2026-06-29):** 1779+1789 (Corn Palak) left unverified — missing corn ingredient, duplicates of each other, existing verified Corn Palak (id=1257) covers slot; 3411 verified (Nawabi Mixed Veg Gravy, 49.66 kcal, legit low-cal); 3418 left unverified (exact duplicate of 3411). Pool: 2101.
- **Cleanup (2026-06-29):** Old Gemini rename artifacts deleted — `scripts/rename_checkpoint.json`, `scripts/rename_dishes_backup.json`, `docs/archive/scripts/rename_dishes_backup.json`. Superseded by `clean_dish_names.py` + `clean_dishes_llm_checkpoint.json`.
- **Test suite (2026-06-30):** 5 modules created (seed, benchmark, locust, quality, playwright). Run order documented in `tests/performance/README.md`.
