# Ingredient-habit learning for meal plans (design)

Status: draft for approval. Nothing is built yet.

## Why

Patients shop and cook from a fairly stable set of ingredients week to week. The 3-4 options per meal exist so the patient can cook from what is already at home, within their health conditions and goals. Today the system barely learns this:

- `generate_diet_plan` reads only the **latest** `weekly_patient_summary` (`app/services/diet_plan_service.py:28-56`). Week 4 knows nothing about weeks 1-3.
- Learning is per **dish**, not per **ingredient**. A patient who eats eggs every morning gets no egg-based option unless the exact same dish happens to be picked.
- Dishes offered 3+ times and never picked are **hard-excluded** the next week (`avoided_food_ids`, `meal_generator.py:548`), which shrinks an already small dish pool.
- The pantry only re-ranks the 4 options when the week is displayed (`routers/meal_plan.py:202-275`). The generator never sees it.
- `weekly_combos` (84 rows per patient per week) is never pruned: ~110 MB per 1,000 patients per week.

## Goals

1. From week 2 on, plans lean toward ingredients the patient keeps choosing or keeps in the pantry.
2. Every day offers at least one option built around a favourite ingredient (the "eggs every breakfast" case), once there is data.
3. A small pool is never made smaller by learning. Learning only re-orders, never removes.
4. The app marks the options that match the patient's habits ("Your usual").
5. Old `weekly_combos` can be deleted safely, because the learned signal no longer depends on them.

## Non-goals

- 3-day plans / twice-weekly doctor review. Separate decision.
- Changing 4 options to 3 (would change both apps).
- Any model training. Counting with decay only.
- The patient and doctor **nutrient report** (ingredient and nutrient intake against goals, for discussion in a visit). v1 only stores the data it needs; the report screens are a follow-up design.
- Showing the learned profile to the doctor in v1.

## Anti-goals (failure even if it works)

- Learning overriding a health rule. Allergies, condition avoid-tags and doctor blocks stay hard filters. Affinity only orders candidates that already passed them.
- The plan collapsing into the same 3 dishes every week. Novelty stays.
- Generation getting noticeably slower. Plan generation is already ~1.0-1.6 CPU-s and ~700 SQL statements.

## Design

### 1. Capture: ingredient counts in the weekly summary (no new table)

`compute_weekly_summary` already walks the week's confirmed choices and their dishes. Add `summary_data["ingredient_intake"]`: for each non-staple ingredient, the **meals** containing it, the **grams** eaten (`recipe_ingredients.quantity_g` x the confirmed bowl factor, `BOWL_FACTORS` in `routers/meal_plan.py`), and the nutrients that gram amount supplied (grams / 100 x the per-100g values already on `ingredients`: protein, fibre, iron, calcium, calories). Also a `nutrient_totals` block for the week (protein, fibre, iron, calcium) with the top contributing ingredients for each. Join `patient_meal_choice_dishes` to `recipe_ingredients` and `ingredients`; skip `is_staple`. One extra batched query, in the same style as the batching done on 2026-10-28.

The doctor cares about what reached the patient's goal, not which dish carried it. If a patient needs more protein, the summary should say "protein 62 g/day against a target of 80 g; mostly from dal and curd; eggs fell from 5 days to 1", not "dish X was served".

Because it lives in the per-week summary row, recompute is idempotent (the cron overwrites the same week) and old weeks age out naturally. Ingredients with no nutrient data (about 104 of 950 have NULL) are counted for meals and grams but add nothing to nutrient totals; the summary lists how many were skipped so nothing looks complete when it isn't.

### 2. Memory: last 6 weeks, decayed

When generating, read the last 6 `weekly_patient_summary` rows (one query, replacing the current `limit(1)`). Weight week n back by `0.8^n` (my choice). From the weighted sums derive:

- `affinity_ingredient_ids`: top 8 ingredients by weighted count, only when at least 2 weeks of summaries exist (my choice; the user said 3-4 weeks before highlighting, which is a UI matter, see 5).
- `preferred_food_ids` / `avoided_food_ids`: same rules as today but computed over the 6 weeks.

Pantry is a stronger signal: ingredients in `patient_pantry` that are in stock (quantity NULL or > 0, the `_PANTRY_IN_STOCK` rule in `routers/meal_plan.py`) are added to `affinity_ingredient_ids` regardless of week count, so a patient who fills in the pantry benefits in week 1.

### 3. Use in the generator (soft only)

In `_find_food_item` (`meal_generator.py:523-552`):

- Add one more term to `prefer_sort`: the dish contains any `affinity_ingredient_ids` (a subquery on `recipe_ingredients.ingredient_id`).
- Change `avoided_food_ids` from `notin_` (hard exclude) to a **demotion**: sorted after everything else, still selectable at Levels 1-4 when nothing better exists.
- Combo rule (my call, adjust if wrong): combo 0 stays the health-optimal baseline exactly as today, because shopping list and planned calories read combo 0. Combo 1 of every slot uses the affinity boost; combos 2-3 are unchanged, so novelty and the non-veg mix stay. This gives the "at least one egg option" guarantee per slot when a matching dish exists.

### 4. App: "Your usual"

`GET /meal-plan/week` adds `is_usual: bool` per combo: true when the combo contains at least one of the patient's top affinity ingredients (needs data from at least 3 weeks, matching the user's "3 or 4 weeks"). The Expo meal-choice screen shows a small badge on those options. Wording and look are open (see below).

### 5. Retention

Two different windows (disk: combos ~5.8 GB per 1,000 patients per year, summaries ~200 MB):

- **Meal options (`weekly_combos`): 8 weeks.** New cron endpoint `POST /internal/cron/prune-old-combos`, same `X-Cron-Secret` guard as the others, run after the Monday summary job. Deletes `weekly_combos` whose recommendation `week_start_date` is older than 8 weeks and which is not the active plan.
- **Weekly summaries (`weekly_patient_summary`): 6 months or longer, never pruned in v1.** Patient and doctor reports read from these, so they must outlive the options. Guard: `compute_weekly_summary` for a week older than the cutoff returns the stored summary instead of recomputing from pruned rows. Needs a new Cloud Scheduler job in `infra/cloud_scheduler_jobs.sh`.

## Constraints

- Backend only changes: `weekly_summary_service.py`, `diet_plan_service.py`, `meal_generator.py`, `routers/meal_plan.py`, `routers/internal.py`; plus the patient app badge. No migration.
- Doctor review flow and doctor dashboard unchanged.
- Generation cost must not rise more than about 10% in CPU and SQL statements (measure with the rig's `regen_cpu.py`).

## Acceptance checks

1. Synthetic patient picks egg dishes for 3 weeks, then a new plan has at least one egg-ingredient combo in every breakfast slot.
2. A dish on the patient's allergy list or a condition avoid-tag never appears, whatever the affinity.
3. A patient with a thin pool still gets all 21 slots x 4 combos (demotion, not exclusion).
4. Re-running the weekly job gives identical `ingredient_frequency`.
5. After pruning, the active plan, its shopping list and `/meal-plan/week` are unchanged.
6. Generation CPU and statement count measured before and after.

## Left to the builder

Exact decay weights, top-N sizes, subquery shape, badge styling, and the Scheduler job definition.

## Open for the user

- Retention window: 8 weeks assumed.
- "Your usual" badge wording and placement in the app.
- Whether the doctor should see the learned ingredients later.
