# Ingredient-habit learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native, one session). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Plans learn which ingredients a patient keeps choosing or keeps in the pantry, lean toward them softly, flag matching options in the app, and old meal-option rows can be pruned.

**Architecture:** The weekly summary gains per-ingredient intake (grams, nutrients). Plan generation reads the last 6 summaries plus in-stock pantry, derives a small set of "habit ingredients", and the generator boosts dishes containing them for combo 1 of each slot. `/meal-plan/week` flags options that contain habit ingredients. A Monday cron prunes `weekly_combos` older than 8 weeks.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 15, pytest (pure functions) plus a DB simulation script, Expo (React Native) for the badge.

**Spec:** `docs/superpowers/specs/2026-10-28-ingredient-habit-learning-design.md`

## Global Constraints

- Allergies, condition avoid-tags and doctor blocks stay hard filters; habit boost only orders candidates that already passed them.
- Combo 0 of every slot is unchanged (shopping list and planned calories read it).
- Habit data needs at least 2 weeks of summaries; pantry counts from week 1. `is_usual` needs at least 3 weeks of summaries.
- Memory window 6 weeks, decay `0.8 ** weeks_back`, top 8 habit ingredients. Combos kept 8 weeks. Summaries never pruned.
- Staples excluded (`is_staple`). Match ingredients by normalized name (`_norm_name`), as the pantry code does.
- No DB migration. Generation CPU and SQL-statement count must not rise more than about 10%.

## Review Focus

- Patient with no summaries and an empty pantry: plan identical to today (no habit data, no error).
- Summary where an ingredient has NULL nutrient data: counted in meals and grams, skipped in nutrient totals, skip count reported.
- Habit ingredient that conflicts with an allergy or condition avoid-tag: never appears.
- Thin pool where every dish is "avoided": all 21 slots x 4 combos still produced.
- Re-running the weekly job twice: identical `ingredient_intake`.

## File Structure

- Create `app/services/ingredient_habits.py`: pure aggregation (`aggregate_habits`) and DB helpers (`build_ingredient_intake`, `load_habits`).
- Modify `app/services/weekly_summary_service.py`: call `build_ingredient_intake`, add to `summary_data`; stored-summary guard for pruned weeks.
- Modify `app/services/diet_plan_service.py:28-56`: use `load_habits`.
- Modify `app/services/meal_generator/meal_generator.py`: boost on combo 1, demote avoided.
- Modify `app/routers/meal_plan.py` (`/week`): `is_usual`.
- Modify `app/routers/internal.py` and `infra/cloud_scheduler_jobs.sh`: prune cron.
- Modify patient app meal-choice screen: badge.
- Create `tests/test_ingredient_habits.py`, `docs/audits/capacity_2026-10/rig/habit_simulation.py`.

### Task 1: Pure aggregation

**Files:** Create `app/services/ingredient_habits.py`, `tests/test_ingredient_habits.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Habits: names: frozenset[str]; summary_names: frozenset[str]` (names from summaries only, no pantry; used by `is_usual`)`; preferred_food_ids: frozenset[int]; avoided_food_ids: frozenset[int]; weeks: int`
- Produces: `aggregate_habits(summaries: list[dict], pantry_names: set[str], *, top_n: int = 8, decay: float = 0.8) -> Habits`. `summaries` newest first, each a `summary_data` dict; `weeks = len(summaries)`.

- [ ] **Step 1: Failing tests** in `tests/test_ingredient_habits.py`: (a) three summaries with `ingredient_intake` `{"egg": {"meals": 5}}`, `{"egg": {"meals": 4}}`, `{"rice": {"meals": 9}}` and no pantry give `"egg" in names`; (b) one summary only gives `names == frozenset()` but pantry `{"egg"}` gives `{"egg"}`; (c) newest-week ingredient outranks an older one with the same count; (d) `top_n=2` caps `names`; (e) `preferred_food_ids` = dishes with summed `times_selected >= 2`, `avoided_food_ids` = summed `times_offered >= 3` and `times_selected == 0`, over all windows; (f) empty list and empty pantry gives all-empty `Habits`.
- [ ] **Step 2:** Run `venv/Scripts/python.exe -m pytest tests/test_ingredient_habits.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `aggregate_habits` and `Habits`. Score = sum over weeks of `meals * decay**i`; ignore ingredients with 0 meals; habit names need `len(summaries) >= 2`, pantry names always added (counted toward `top_n` after score-ranked names).
- [ ] **Step 4:** Run tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat: pure ingredient-habit aggregation`.

### Task 2: Ingredient intake in the weekly summary

**Files:** Modify `app/services/ingredient_habits.py`, `app/services/weekly_summary_service.py`

**Interfaces:**
- Produces: `async build_ingredient_intake(db: AsyncSession, choices: list[PatientMealChoice]) -> dict` returning `{"ingredient_intake": {name_norm: {"ingredient_id": int, "meals": int, "grams": float, "protein_g": float, "fibre_g": float, "iron_mg": float, "calcium_mg": float, "calories": float}}, "nutrient_totals": {"protein_g": {"total": float, "top": [{"name": str, "amount": float}]}, ...}, "nutrient_data_missing": int}`. Empty dict values when `choices` is empty.

- [ ] **Step 1: Failing test** (in the simulation DB script's assertions; see Task 8) that a patient with 3 confirmed meals each containing a known dish produces `meals` equal to the count of meals containing that ingredient, `grams = quantity_g x BOWL_FACTORS[bowl]` summed, and `protein_g = grams / 100 x protein_per_100g`.
- [ ] **Step 2:** Implement with one batched query joining `PatientMealChoiceDish -> RecipeIngredient -> Ingredient` for `choice_id IN (...)`. Bowl factor from `PatientMealChoice.bowl_size` (default medium). `BOWL_FACTORS` imported lazily inside the function from `..routers.meal_plan` to avoid an import cycle. Skip `is_staple` names. Ingredients with NULL nutrient column add 0 and increment `nutrient_data_missing` once per distinct ingredient.
- [ ] **Step 3:** In `_compute`, merge the returned dict into `summary_data` before the upsert. Expected: `summary_data` has the three new keys; existing keys unchanged.
- [ ] **Step 4:** Run `venv/Scripts/python.exe -m ruff check app/services`. Expected: pass. Commit.

### Task 3: Load habits and wire plan generation

**Files:** Modify `app/services/ingredient_habits.py`, `app/services/diet_plan_service.py:28-56`

**Interfaces:**
- Produces: `async load_habits(session: AsyncSession, patient_id: int) -> Habits`. One query for the last 6 `WeeklyPatientSummary` rows (newest first), one for in-stock pantry names (same predicate as `_PANTRY_IN_STOCK`, defined again as `or_(quantity_g.is_(None), quantity_g > 0)`), then `aggregate_habits`.
- Consumes (generator): `user_data["habit_names"]`, `["preferred_food_ids"]`, `["avoided_food_ids"]`, `["habit_ingredient_ids"]`.

- [ ] **Step 1:** In `generate_diet_plan`, replace the single-summary block with `habits = await load_habits(session, int(patient_id))`; set the four `user_data` keys. `habit_ingredient_ids` = ids of `Ingredient` rows whose `lower(trim(name))` is in `habits.names` (one query; empty set skips it).
- [ ] **Step 2:** Verify with a plan generation on the rig DB for a patient with no summaries: output unchanged from before (compare combo dish ids with a fixed `random.seed`). Commit.

### Task 4: Generator uses habits softly

**Files:** Modify `app/services/meal_generator/meal_generator.py` (`generate_meal_plan` ~231, `_fill_slot_dishes` ~609, `_find_food_item` ~495-552)

**Interfaces:**
- `_fill_slot_dishes` and `_find_food_item` gain `habit_ingredient_ids: frozenset = frozenset()`. Boost applies only when `combo_idx == 1`.

- [ ] **Step 1:** Add to `prefer_sort` an `EXISTS` over `RecipeIngredient` where `food_item_id == FoodItem.id` and `ingredient_id IN habit_ingredient_ids`, only when the set is non-empty and the caller passed `combo_idx == 1`.
- [ ] **Step 2:** Replace `.where(FoodItem.id.notin_(avoided_food_ids))` with a demotion: an extra sort key `FoodItem.id.in_(avoided_food_ids)` ascending placed after `prefer_sort`. Blocked ids stay a hard filter.
- [ ] **Step 3:** Test in the simulation (Task 8): thin-pool case still yields 84 combos; allergen dish never present.
- [ ] **Step 4:** Commit.

### Task 5: `is_usual` in `/meal-plan/week`

**Files:** Modify `app/routers/meal_plan.py` (`get_week_plan`, around lines 202-266)

- [ ] **Step 1:** After `pantry_names`, call `load_habits`; `usual_names = habits.names` only when `habits.weeks >= 3`, else empty (pantry names alone do not set `is_usual`: compute from summary-derived names; add a second field `summary_names` to `Habits` for this).
- [ ] **Step 2:** In each combo dict add `"is_usual": bool(required & usual_names)`. Expected: key present on every combo, False when no data.
- [ ] **Step 3:** Commit.

### Task 6: Prune cron and summary guard

**Files:** Modify `app/routers/internal.py`, `app/services/weekly_summary_service.py`, `infra/cloud_scheduler_jobs.sh`

**Interfaces:** `POST /internal/cron/prune-old-combos` returns `{"cutoff": "YYYY-MM-DD", "deleted": int}`.

- [ ] **Step 1:** Endpoint: `_check_secret`, `cutoff = today - 56 days`, delete `WeeklyCombo` where `recommendation_id IN (select id from recommendations where week_start_date < cutoff and is_active = false)`.
- [ ] **Step 2:** In `compute_weekly_summary`, if `week_start` is not None, older than 56 days, and a stored `WeeklyPatientSummary` exists, return its `summary_data` untouched.
- [ ] **Step 3:** Add the Scheduler job line (Mondays after the summary job, `Etc/UTC`), commented the same way as the others.
- [ ] **Step 4:** Commit.

### Task 7: Patient app badge

**Files:** Modify the meal-choice combo card in `mitihar-patient-app/app/meals/` (locate with `graft grep "coverage"` in that folder); the combo type in `mitihar-patient-app/types`.

- [ ] **Step 1:** Add `is_usual?: boolean` to the combo type. Render a small "Your usual" pill when true, styled like the existing doctor-pick marker.
- [ ] **Step 2:** `npx tsc --noEmit` in `mitihar-patient-app`. Expected: no new errors. Commit.

### Task 8: Simulation

**Files:** Create `docs/audits/capacity_2026-10/rig/habit_simulation.py`

- [ ] **Step 1:** Against the rig DB (`localhost:15432`, password from scratchpad `perf.env`), inside one transaction rolled back at the end: take a synthetic patient, insert 4 weeks of confirmed choices that always pick an egg-containing breakfast, run `compute_weekly_summary` for each week, then generate a plan before (no history) and after (4 weeks).
- [ ] **Step 2:** Print: egg-ingredient share of breakfast combo 1 before vs after; whether combo 0 changed; `is_usual` count; nutrient totals sample; plan generation time and SQL statement count before vs after; an allergy case (patient allergic to egg never sees egg); a thin-pool case (all candidates avoided still gives 84 combos); weekly job run twice gives identical `ingredient_intake`.
- [ ] **Step 3:** Fix any failures found, rerun, write results to `docs/audits/capacity_2026-10/HABIT_SIMULATION_2026-10-28.md`, commit.
