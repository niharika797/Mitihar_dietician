# Schema Review — Session 10

**Status:** AWAITING PRODUCT OWNER APPROVAL  
**Migration file:** `alembic/versions/c2d3e4f5a6b7_add_ingredients_recipe_ingredients_beverages_patient_config.py`  
**Do not run** `alembic upgrade head` until product owner confirms below.

---

## SUMMARY

This migration adds five schema additions that form the foundation for Sessions 11–22. It does not touch any existing table or data. The additions are: (1) an `ingredients` master table to hold ICMR/INDB-verified nutritional data per 100g; (2) a `recipe_ingredients` join table to link food_items to verified ingredients; (3) a standalone `beverages` catalog separate from meal slots; (4) a `patient_meal_config` table for doctor-set TDEE split overrides per patient; and (5) a `patient_dish_preferences` table for doctor pin/block control per patient per dish. All new tables are empty at creation — no data is migrated in this step.

---

## NEW TABLES

### `ingredients`

Master nutritional source of truth. All values are per 100g, matching the INDB dataset format.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | integer PK | — | autoincrement |
| name | text | NOT NULL | English name e.g. "Spinach" |
| name_hindi | text | NULL | Regional name e.g. "Palak" |
| calories_per_100g | float | NOT NULL | |
| protein_per_100g | float | NOT NULL | |
| carbs_per_100g | float | NOT NULL | |
| fat_per_100g | float | NOT NULL | |
| fiber_per_100g | float | NULL | |
| sodium_per_100g | float | NULL | |
| iron_per_100g | float | NULL | Required for Anemia condition tag |
| calcium_per_100g | float | NULL | Required for Osteoporosis condition tag |
| glycemic_index | integer | NULL | Required for diabetes filtering |
| source | text | NOT NULL | "INDB_ICMR" \| "doctor_added" \| "manual" |
| is_verified | boolean | NOT NULL | default false |
| added_by_doctor_id | integer FK→doctors | NULL | NULL = system/import |
| created_at | timestamptz | — | server default now() |
| updated_at | timestamptz | — | server default now() |

**Constraints:**
- `UNIQUE (name, source)` — same ingredient name can exist from multiple sources during transition, not duplicated within a source
- FK `added_by_doctor_id` → `doctors.id` ON DELETE SET NULL — deleting a doctor does not delete their ingredient contributions

**Indexes:** `idx_ing_name`, `idx_ing_source`, `idx_ing_verified`

---

### `recipe_ingredients`

Links food_items to ingredients with per-serving quantities. This is the replacement for the existing `food_items.ingredients` JSONB column, but the JSONB column is NOT dropped — both coexist during the soft transition period.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | integer PK | — | autoincrement |
| food_item_id | integer FK→food_items | NOT NULL | ON DELETE CASCADE |
| ingredient_id | integer FK→ingredients | NOT NULL | ON DELETE RESTRICT |
| quantity_g | float | NOT NULL | grams per serving (must be > 0, enforced at app layer) |
| notes | text | NULL | e.g. "to taste", "adjust to preference" |

**Constraints:**
- `UNIQUE (food_item_id, ingredient_id)` — one ingredient appears once per recipe. Two different oils = two separate ingredient rows.
- ON DELETE CASCADE on food_item_id: deleting a recipe removes its ingredient links.
- ON DELETE RESTRICT on ingredient_id: cannot delete an ingredient that is linked to a recipe.

**Indexes:** `idx_ri_food_item`, `idx_ri_ingredient`

---

### `beverages`

Standalone beverage catalog, not linked to meal slots. The 18 food_items with `slot_type='beverage'` (fixed in Session 9) remain in `food_items` during transition — this table is additive.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | integer PK | — | autoincrement |
| name | text | NOT NULL | e.g. "Masala Chai" |
| category | text | NOT NULL | "daily_staple" \| "occasional" \| "therapeutic" |
| calories_per_serving | float | NOT NULL | |
| protein_per_serving | float | NULL | |
| carbs_per_serving | float | NULL | |
| fat_per_serving | float | NULL | |
| serving_size_ml | integer | NULL | standard serving in ml |
| is_caffeinated | boolean | NOT NULL | default false |
| suitable_for_conditions | JSONB | NULL | array of condition tags e.g. `["diabetes_friendly", "avoid_kidney"]` |
| is_active | boolean | NOT NULL | default true — soft delete |
| created_at | timestamptz | — | server default now() |

**Category definitions:**
- `daily_staple` — chai, coffee, milk, buttermilk (consumed every day)
- `occasional` — juices, lassi, sharbat (2-3x per week)
- `therapeutic` — kadha, herbal drinks, medicinal preparations (prescribed)

**Indexes:** `idx_bev_name`, `idx_bev_category`, `idx_bev_active`

---

### `patient_meal_config`

One row per patient. Created when a doctor first sets a TDEE split override. No row = use system defaults.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | integer PK | — | autoincrement |
| patient_id | integer FK→patients | NOT NULL UNIQUE | ON DELETE CASCADE |
| meal_split_override | JSONB | NULL | see structure below |
| created_at | timestamptz | — | server default now() |
| updated_at | timestamptz | — | server default now() |

**`meal_split_override` structure when set:**
```json
{
  "breakfast_pct": 10,
  "lunch_pct": 45,
  "dinner_pct": 30
}
```

- NULL = use system defaults: breakfast 25 / lunch 35 / dinner 25
- Application layer enforces: `breakfast_pct + lunch_pct + dinner_pct == 85`
- The remaining 15% is always the passive buffer — not configurable
- Values are integers (whole percentages only)

**Indexes:** `idx_pmc_patient`

---

### `patient_dish_preferences`

Doctor-set pin/block preferences per patient per dish. One preference row per (patient, food_item) pair — a dish cannot be both pinned and blocked for the same patient.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | integer PK | — | autoincrement |
| patient_id | integer FK→patients | NOT NULL | ON DELETE CASCADE |
| food_item_id | integer FK→food_items | NOT NULL | ON DELETE CASCADE |
| preference_type | text | NOT NULL | "pin" \| "block" |
| added_by_doctor_id | integer FK→doctors | NOT NULL | ON DELETE RESTRICT |
| note | text | NULL | doctor's reason e.g. "patient dislikes bitter gourd" |
| created_at | timestamptz | — | server default now() |

**Constraints:**
- `UNIQUE (patient_id, food_item_id)` — one preference per patient-dish pair
- ON DELETE CASCADE on patient_id — patient deleted → preferences deleted
- ON DELETE CASCADE on food_item_id — recipe deleted → preferences deleted
- ON DELETE RESTRICT on added_by_doctor_id — doctor cannot be deleted while they have active preferences

**Indexes:** `idx_pdp_patient`, `idx_pdp_food_item`, `idx_pdp_doctor`

---

## PATIENTS TABLE CHANGE

**No change to the patients table itself.**

The TDEE split override is stored in the new `patient_meal_config` table (see above) rather than as a column on patients. See DECISIONS MADE below for rationale.

---

## JSONB STRUCTURE CHANGE (NO MIGRATION REQUIRED)

This is a spec for Session 11 (generator rewrite). No DB change is needed — it is a change to the output format of `meal_generator.py`.

**Current structure (confirmed from live DB, rec_id=128):**
```json
{
  "Date": "2026-05-24",
  "Region": "West",
  "Diet Type": "Vegetarian",
  "Meal Type": "Breakfast",
  "Total Fat": 31.93,
  "Menu Names": "Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk",
  "Total Carbs": 40.99,
  "Total Fiber": 0.52,
  "Total Protein": 6.63,
  "Total Calories": 443.95,
  "Ingredients Scaling": {
    "Milk": 207.45,
    "curd": 121.63,
    "Sooji": 98.29
  }
}
```

**New structure (generator output after Session 11 rewrite):**

All existing fields are preserved unchanged. A new `dishes` array is added alongside `Menu Names`.

```json
{
  "Date": "2026-05-24",
  "Region": "West",
  "Diet Type": "Vegetarian",
  "Meal Type": "Breakfast",
  "Total Fat": 31.93,
  "Menu Names": "Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk",
  "Total Carbs": 40.99,
  "Total Fiber": 0.52,
  "Total Protein": 6.63,
  "Total Calories": 443.95,
  "Ingredients Scaling": {
    "Milk": 207.45,
    "curd": 121.63,
    "Sooji": 98.29
  },
  "dishes": [
    {
      "food_id": 412,
      "recipe_name": "Sooji Halwa Breakfast Bowl",
      "slot_type": "main_dish",
      "calories": 300.0,
      "protein": 5.0,
      "carbs": 28.0,
      "fat": 20.0,
      "fiber": 0.3
    },
    {
      "food_id": 89,
      "recipe_name": "Curd chutney",
      "slot_type": "accompaniment",
      "calories": 98.0,
      "protein": 1.3,
      "carbs": 10.0,
      "fat": 9.9,
      "fiber": 0.1
    },
    {
      "food_id": 229,
      "recipe_name": "Chai/Coffee/Milk",
      "slot_type": "beverage",
      "calories": 45.95,
      "protein": 0.33,
      "carbs": 2.99,
      "fat": 2.03,
      "fiber": 0.12
    }
  ]
}
```

**Backward compatibility:** Old meal plans without `dishes` key continue to work unchanged. The frontend reads `Menu Names` for display and checks for `dishes` array presence for dish-level features. Absence of `dishes` = legacy plan, show read-only.

**Where food_id is lost today (generator audit):**

In `meal_generator.py`, `food_item` (with `food_item.id` accessible) is returned by `_find_food_item` at line 393. At line 407, `food_item.id` is added to `daily_used_ids` and `weekly_used_ids` sets — but is NOT stored in `meal_option`. At line 417, only `food_item.recipe_name` is appended. At line 437, the list is joined with `" + "` and `food_id` is permanently lost.

**Session 11 fix point:** In the loop body (lines 386–435), alongside `meal_option["Menu Names"].append(food_item.recipe_name)` at line 417, build a parallel `dishes` list that accumulates per-dish dicts. After the loop, both are written to `meal_option`.

---

## DECISIONS MADE

### 1. `patient_meal_config` as separate table (not JSONB column on patients)

The `patients` table already has 40+ columns covering core patient identity, health profile, subscription lifecycle, FCM tokens, login lockout, and password management. It is the most-read table in the system.

Adding `meal_split_override` directly to patients would be a single nullable JSONB column — low risk technically. However, most patients will never have a doctor-set TDEE override (it defaults to 25/35/25). Storing a NULL column on every patient row for a feature used by a minority is wasteful. More importantly, the patients table is already at a complexity level where additional columns should be added only when there's no clean alternative.

**Decision:** Separate `patient_meal_config` table. One row per patient, created lazily only when a doctor first sets a config. The generator does a `LEFT JOIN patient_meal_config USING (patient_id)` and uses the JSONB when present, system defaults when NULL. This keeps the patients table focused on core profile data and makes the config's purpose self-documenting by table name.

### 2. `added_by_doctor_id` FK in `patient_dish_preferences` uses ON DELETE RESTRICT (not CASCADE or SET NULL)

If a doctor is deleted, their patient-dish preferences remain meaningful clinical data (they tell us what a patient cannot tolerate). Cascading-delete them would silently remove dietary restrictions, which could be harmful.

SET NULL was considered but the column is NOT NULL by design — the preference should always have a traceable source. RESTRICT prevents deleting a doctor while their preferences exist, which is the correct behavior: deactivate the doctor (`is_active=False`) rather than delete them.

### 3. `ingredients.added_by_doctor_id` uses ON DELETE SET NULL (not RESTRICT)

Ingredient contributions are scientific data (calories per 100g, etc.) that retain value independent of who added them. Blocking doctor deletion because they added an ingredient would be too restrictive. SET NULL means the ingredient persists but loses its attribution — acceptable.

### 4. `recipe_ingredients` ON DELETE RESTRICT on `ingredient_id`

Cannot delete an ingredient that is linked to recipes, because deleting it would silently break the nutrition chain for those recipes. The correct operation is: (1) unlink the ingredient from all recipes, (2) then delete it. RESTRICT enforces this two-step process explicitly.

### 5. `beverages` table has no FK to `food_items`

The 18 food_items with `slot_type='beverage'` are the initial population source for this table, but they stay in `food_items` too. The beverages table is an independent catalog — when the doctor adds a beverage via the new UI (Session 22), it goes into this table, not food_items. No cross-reference FK is needed because the two tables serve different purposes (beverages = patient-facing catalog, food_items = generator pool).

---

## WHAT THIS MIGRATION DOES NOT TOUCH

- **`food_items.ingredients` JSONB column** — preserved as-is. `recipe_ingredients` table is additive.
- **`recommendations.meals` JSONB structure** — existing stored plans are unchanged. The new `dishes[]` field is only added by the generator rewrite in Session 11.
- **All existing table rows** — migration creates empty tables only, no data moves.
- **`food_items` rows with `slot_type='beverage'`** — remain in food_items. The `beverages` table is additive and independent.
- **All existing indexes, constraints, and relationships** — no modifications.
- **Alembic revision chain** — new revision `c2d3e4f5a6b7` chains from `a9b8c7d6e5f4` cleanly.

---

## MIGRATION FILE LOCATION

```
alembic/versions/c2d3e4f5a6b7_add_ingredients_recipe_ingredients_beverages_patient_config.py
```

---

## OPEN QUESTIONS FOR PRODUCT OWNER

**Q1 — `beverages` table vs `food_items` long-term:**
The 18 beverage items fixed in Session 9 exist in `food_items` with `slot_type='beverage'`. They are used by the generator for Breakfast beverage slots via templates. Should these items eventually be migrated to the `beverages` table and removed from `food_items`, or should they stay in `food_items` indefinitely (dual-stored)? This affects Session 22 (beverage UI) scope.

**Q2 — `patient_meal_config` vs column on patients:**
Confirmed decision is separate table. Product owner should confirm this aligns with how the doctor dashboard's Meal Config tab will work (Session 17) — specifically whether config is created proactively for all patients or lazily only when a doctor changes a default.

**Q3 — `glycemic_index` on `ingredients`:**
Glycemic index is a property of a food/dish, not strictly an ingredient. For example, white rice has a GI of ~72 but brown rice has ~50 — the difference is processing, not the ingredient itself. Is storing GI on the ingredient table the right model, or should it be on `food_items` instead? This affects Session 18 (diabetes filtering).

**Q4 — `patient_dish_preferences` `preference_type` as free text vs CHECK constraint:**
Currently `preference_type` is `TEXT` with the two valid values "pin" and "block" enforced at application layer. Should we add a DB-level CHECK constraint (`CHECK (preference_type IN ('pin', 'block'))`) for data integrity? This is low risk to add now vs later.

**Q5 — `recipe_ingredients.quantity_g` must be > 0:**
The brief specifies `gt 0` (greater than zero) enforced at app layer. Should this be a DB CHECK constraint (`CHECK (quantity_g > 0)`)? Same question as Q4 — add now or later.
