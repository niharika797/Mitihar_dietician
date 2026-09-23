---
name: generator-notes
description: Technical gotchas for Mityahar meal generator, diet plan service, and tag system — loaded when touching generator code
paths: "app/services/meal_generator/**"
---

## Data Shape

- **food_id now stored in dishes[]** — each meal slot in `recommendations.meals` has `dishes` array containing `food_id` (FoodItem.id PK), `recipe_name`, `slot_type`, per-dish macros. Plans without `dishes` key are legacy (pre-Session 11), shown read-only.
- **Generator produces 21 meal slots** — 3 meals × 7 days. `EXPECTED_MEAL_COUNT = 7 * 3` in `diet_plans.py`. Update constant there if structure changes again.
- **DEFAULT_SPLIT** constant at module level in `meal_generator.py`: `{"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.25}`. Used when no PatientMealConfig override exists for patient.

## Tag System

- **Condition tag filtering (Session 19)** — `app/services/meal_generator/tag_utils.py` is the canonical mapping of patient condition strings → avoid/prefer tag lists. `CONDITION_AVOID_TAGS` and `CONDITION_PREFER_TAGS` dicts use exact UI strings as keys (e.g. `"Type 2 Diabetes"`, `"PCOS/PCOD"`). `get_avoid_tags(conditions)` and `get_prefer_tags(conditions)` return deduplicated lists. Called in `generate_meal_plan()` from `user_data["medical_conditions"]`. Results passed as `patient_avoid_tags: frozenset` and `patient_prefer_tags: frozenset` through `_find_food_item()` → `_find_food_item_single_diet()` → `base_stmt()`. Empty frozenset → filter/sort skipped entirely.
- **JSONB overlap for avoid filter** — `FoodItem.avoid_tags.contains([tag])` → `avoid_tags @> '["tag"]'::jsonb`. Uses GIN index. `.overlap()` does NOT exist on JSONB (only on ARRAY). Avoid filter: `NOT (tag1_contains OR tag2_contains ...)`. Prefer boost: `OR(tag1_contains, ...).desc()` as first ORDER BY clause.
- **avoid_pcos / avoid_gout** — included in CONDITION_AVOID_TAGS but produce 0-match queries (no food_items have these tags). Silent no-ops until Layer 2 ingredient tagging adds them.

## Pool & Preference Logic

- **Generator blocked dishes** — `blocked_food_ids` threaded as `frozenset` through `_find_food_item` → `_find_food_item_single_diet` → `base_stmt()` WHERE NOT IN clause. Empty frozenset = no change to query.
- **Generator pinned dishes** — since R-2: pin = preference signal only (boosts via `prefer_sort`, does NOT force-inject). Old force-inject block removed in R-2; `prefer_sort` boosts `FoodItem.id.in_(pinned_food_ids)` alongside `prefer_tags`.
- **patient_id must be int in generator** — `user_data["id"]` is a string from the API route. `int(patient_id)` cast is required before PatientMealConfig query. asyncpg does not implicit-cast varchar to integer column (raises UndefinedFunctionError).
