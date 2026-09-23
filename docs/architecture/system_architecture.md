# Mityahar — System Architecture Reference

**Generated:** 2026-06-15 (Session 22F complete)  
**Scope:** Read-only audit of current code + BUILD_TRACKER. Intended for product-owner rebuild decision.  
**Codebase branch:** `feature/api-remediation-v0.2`

---

## Table of Contents

1. [Data Model Layer](#1-data-model-layer)
2. [Generation Layer](#2-generation-layer)
3. [Medical Tagging Layer](#3-medical-tagging-layer)
4. [API Layer](#4-api-layer)
5. [Doctor Dashboard Layer](#5-doctor-dashboard-layer)
6. [Patient App Layer](#6-patient-app-layer)
7. [Weekly Cycle Layer](#7-weekly-cycle-layer)
8. [Known Gaps & Technical Debt](#8-known-gaps--technical-debt)
9. [Rebuild Impact Summary](#9-rebuild-impact-summary)

---

## 1. Data Model Layer

### 1.1 Core Tables

#### `food_items` — Recipe/Dish Database
**Source:** `app/models/db_models.py:14`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `recipe_name` | String(255) | NOT NULL |
| `slot_type` | String(50) | NOT NULL. Valid values: `grain`, `dal_protein`, `main_dish`, `sabzi`, `one_pot`, `accompaniment`, `beverage` |
| `cal_per_serving` | Numeric(7,2) | NOT NULL. Unscaled per-serving value. 1519/2143 calculated from ingredient chain; 623 manual. See §3. |
| `protein_per_serving` | Numeric(6,2) | NOT NULL, default 0 |
| `carbs_per_serving` | Numeric(6,2) | NOT NULL, default 0 |
| `fat_per_serving` | Numeric(6,2) | NOT NULL, default 0 |
| `fiber_per_serving` | Numeric(6,2) | NOT NULL, default 0 |
| `sodium_per_serving` | Numeric(6,2) | default 0 (added Session 9) |
| `serving_weight_g` | Numeric(6,1) | Nullable (added Session 9) |
| `diet_type` | String(30) | NOT NULL. Values: `Vegetarian`, `Eggetarian`, `Non-Vegetarian` |
| `region_tags` | ARRAY(Text) | GIN indexed. e.g. `["South"]` |
| `meal_time_tags` | ARRAY(Text) | GIN indexed. e.g. `["Breakfast"]`, `["Lunch","Dinner"]` |
| `plan_type_tags` | ARRAY(Text) | GIN indexed. Default `["Healthy","Diabetic-Friendly","Gym-Friendly"]`. Currently all 2143 recipes share this default — effectively a no-op filter. |
| `ingredients` | JSONB | `[{"name": str, "amount_g": float}]`. Preserved as fallback alongside `recipe_ingredients` table. |
| `source` | String(20) | `manual` or `excel` |
| `nutrition_source` | Text | `calculated` (1519) or `manual` (623). `calculated` = IFCT2017 + LLM ingredient chain. |
| `is_verified` | Boolean | default False. 197 pre-verified at start. Doctor PATCH tags sets True. |
| `submitted_for_review` | Boolean | default False. Set True when doctor submits custom recipe to admin queue. (Added Session 16, migration e6f7a8b9c0d1) |
| `avoid_tags` | JSONB | GIN indexed. e.g. `["avoid_diabetes","avoid_hypertension"]`. (Added Session 18A, migration f7a8b9c0d1e2) |
| `prefer_tags` | JSONB | GIN indexed. e.g. `["diabetes_friendly"]`. (Added Session 18A) |
| `image_url` | String(500) | Nullable. Phase 6 ETL — not yet populated. |
| `doctor_id` | FK → doctors | Nullable. Tracks which doctor submitted this item. NULL for system/ETL items. |

**FK relationships:** `doctor_id → doctors.id`, `recipe_ingredients` (cascade delete), `doctor` (relationship).  
**Total rows:** ~2143 (includes 7 empty test artifacts at IDs 3698–3716).

---

#### `meal_templates` — Slot Composition DB
**Source:** `app/models/db_models.py:65`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `meal_time` | String(20) | `Breakfast`, `Lunch`, `Dinner` (snack types dead post-Session 11) |
| `region` | String(10) | `North`, `South`, `East`, `West` |
| `diet_type` | String(30) | `Vegetarian`, `Eggetarian`, `Non-Vegetarian` |
| `plan_type` | String(30) | `Healthy`, `Diabetic-Friendly`, `Gym-Friendly` |
| `slots` | JSONB | `[{"slot_type": "grain", "calorie_pct": 0.35, "required": true}, ...]` |

**UNIQUE constraint:** `(meal_time, region, diet_type, plan_type)` — prevents duplicate templates.  
**Current use:** Queried at generation time. However, `BREAKFAST_SLOTS` and `ONE_POT_SLOTS` in-code constants *shadow* the DB for Breakfast and 40% of Lunch/Dinner (see §2.3). The 36 Breakfast template rows still include a `beverage: 0.10` slot that is never reached.

---

#### `doctors`
**Source:** `app/models/db_models.py:89`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String | UNIQUE, NOT NULL |
| `hashed_password` | String | bcrypt |
| `name`, `phone`, `specialization`, `clinic_name`, `clinic_address`, `city`, `state` | String/Text | Profile fields |
| `experience_years` | Integer | default 0 |
| `fee_per_month` | Integer | ₹ default 0 |
| `rating` | Numeric(3,2) | default 0 |
| `review_count` | Integer | default 0 |
| `is_accepting` | Boolean | False = not taking new patients |
| `mfa_secret`, `mfa_enabled` | String/Boolean | TOTP-based MFA |
| `failed_login_attempts`, `locked_until` | Integer/DateTime | Login lockout (T1-6) |
| `is_active` | Boolean | |
| `role` | String(10) | `doctor` |

---

#### `admins`
**Source:** `app/models/db_models.py:128`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String | UNIQUE |
| `hashed_password` | String | |
| `mfa_secret`, `mfa_enabled` | | TOTP |
| `allowed_ips` | JSONB | IP whitelist for `AdminIPWhitelistMiddleware` |
| `failed_login_attempts`, `locked_until` | | Lockout |
| `role` | String(10) | `admin` |

---

#### `patients`
**Source:** `app/models/db_models.py:151`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String | UNIQUE |
| `hashed_password` | String | |
| `name`, `phone` | String | |
| `date_of_birth` | Date | Nullable |
| `gender` | String | NOT NULL |
| `height_cm`, `weight_kg` | Numeric | NOT NULL |
| `activity_level` | String(5) | `S`/`LA`/`MA`/`VA`/`SA` (Sedentary → Super Active) |
| `diet_type` | String(30) | NOT NULL. `Vegetarian`/`Eggetarian`/`Non-Vegetarian` |
| `region` | String(10) | NOT NULL. `North`/`South`/`East`/`West` |
| `health_condition` | String(30) | `Healthy` (default) / `Diabetic-Friendly` / `Gym-Friendly`. Used as `plan_type` for template lookup. |
| `bmi`, `bmr`, `tdee` | Numeric | Calculated + stored at onboarding. NOT re-read from fresh calculation at generation time — stored value is used. |
| `target_weight_kg` | Numeric | Nullable (optional field) |
| `health_goals` | JSONB | e.g. `["Weight Loss"]`. First goal drives macro split via `_calculate_targets()`. |
| `medical_conditions` | JSONB | Array of exact UI strings. e.g. `["Type 2 Diabetes", "Hypertension"]`. Drives avoid/prefer tag filters. |
| `food_allergies` | JSONB | Array of chip labels e.g. `["Peanuts", "Dairy / Lactose"]`. Matched as substring against ingredient names. |
| `dietary_preferences` | JSONB | Array of preference strings (stored but currently unused in generation). |
| `meals_per_day` | Integer | default 3. No longer settable from onboarding (removed Session 21.5). |
| `nonveg_meals_per_week` | Integer | default 3. Capped at 4 in generator. |
| `eating_habits` | JSONB | e.g. `["skips_breakfast"]`. Stored but unused in generation. |
| `user_type` | String(20) | `standalone` / `doctor_connected` |
| `doctor_id` | FK → doctors | Nullable |
| `subscription_status` | String(20) | `inactive` / `active` |
| `token_1` | String(20) | e.g. `TKN1-PAT-00142`. Generated once at subscription activation. |
| `token_1_active` | Boolean | True = subscription active |
| `token_1_expiry` | DateTime | 30-day rolling window |
| `renewal_requested`, `expiring_soon` | Boolean | Flags set by patient/cron |
| `fcm_token` | String(512) | Firebase push notification token. Updated every login. |
| `google_id` | String(128) | Unique, nullable. Partial unique index (where NOT NULL). |
| `is_email_verified` | Boolean | |
| `pace_preference` | String(20) | `slow`/`moderate`/`fast`. Stored but unused in generation. |
| `failed_login_attempts`, `locked_until`, `password_changed_at` | | Security fields (T1-6, T1-7) |
| Lifestyle columns (`sleep_hours`, `water_glasses`, `occupation`, `smoking`, `alcohol`, `fasting_days`) | Various | Collected in onboarding until Session 21.5 removed Lifestyle step. Defaults submit via store. |

---

#### `recommendations` — Generated Plan Container
**Source:** `app/models/db_models.py:254`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `patient_id` | FK → patients | |
| `week_start_date` | Date | Set at generation time |
| `week_number` | Integer | |
| `meals` | JSONB | The full 21-meal plan array. See §1.2. |
| `ingredient_checklist` | JSONB | Aggregated weekly ingredient list with amounts. |
| `used_food_ids` | JSONB | List of food_item IDs used THIS generation (not cumulative). Enables cross-week variety. Bug 1 fix: Session 22A removed the snowball accumulation. |
| `is_active` | Boolean | One active plan per patient at a time. |
| `generated_by` | String(20) | `system` / `doctor` |
| `doctor_notes` | Text | Nullable |
| `version` | Integer | Incremented on each regeneration |

---

#### `patient_meal_choices` — Plan-Time Confirmed Choice (Parent)
**Source:** `app/models/db_models.py:690`  
**Added:** Session 20, migration `c9d0e1f2a3b4`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `patient_id` | FK → patients (CASCADE) | |
| `food_item_id` | FK → food_items (CASCADE) | PRIMARY dish in a combo (first of food_item_ids). Budget-math source. |
| `date` | Date | |
| `meal_type` | String(20) | `Breakfast`/`Lunch`/`Dinner` |
| `calories` | Float | Sum of `cal_per_serving` for all confirmed dishes. Denormalized total. |
| `confirmed_at` | DateTime | |

**UNIQUE constraint:** `(patient_id, date, meal_type)` — one choice per slot per day.  
**Note:** `calories` in parent = unscaled per-serving sum. This differs from `meal_logs.calories_consumed` which may be scaled — two intentionally different calorie bases.

---

#### `patient_meal_choice_dishes` — Per-Dish Breakdown (Child)
**Source:** `app/models/db_models.py:710`  
**Added:** Session 22E (Part 3), migration `d0e1f2a3b4c5`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `choice_id` | FK → patient_meal_choices (CASCADE) | |
| `food_item_id` | FK → food_items (no CASCADE) | Keeps historical record even if dish deleted |
| `slot_type` | String(30) | Nullable |
| `calories` | Float | UNSCALED per-serving (`= food_items.cal_per_serving`) |

**Purpose:** Enables doctor weekly summary analytics. NOT read by budget-math path. Never replaces parent `calories`.

---

#### `patient_dish_preferences` — Doctor Pin/Block
**Source:** `app/models/db_models.py:663`  
**Added:** Session 10 (migration c2d3e4f5a6b7), ORM added Session 17

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `patient_id` | FK (CASCADE) | |
| `food_item_id` | FK (CASCADE) | |
| `preference_type` | Text | `pin` or `block`. CHECK constraint. |
| `added_by_doctor_id` | FK → doctors (RESTRICT) | NOT NULL |
| `note` | Text | Nullable |

**UNIQUE:** `(patient_id, food_item_id)` — one preference per patient-dish pair.

---

#### `meal_logs` — Patient Consumption Logging
**Source:** `app/models/db_models.py:285`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `patient_id` | FK | |
| `recommendation_id` | FK nullable | Backfilled gradually; may be NULL for older logs |
| `logged_date` | Date | |
| `meal_type` | String(20) | `Breakfast`/`Lunch`/`Dinner`/`Snack` |
| `food_id` | FK → food_items | Nullable (NULL for custom/free-text meals) |
| `custom_food_name` | String | Nullable |
| `calories_consumed` | Numeric(7,2) | |
| `protein_g`, `carbs_g`, `fat_g`, `fiber_g` | Numeric(6,2) | |
| `portion_servings` | Numeric(4,2) | default 1.0 |
| `notes` | Text | Nullable |

**Note:** This table tracks *consumption*, not *plan-time choices*. The two systems (`meal_logs` vs `patient_meal_choices`) run in parallel with different calorie bases — intentional design (see §7.1).

---

#### `meal_ratings` — Patient Thumbs Up/Down
**Source:** `app/models/db_models.py:518`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `patient_id` | FK | |
| `food_item_id` | FK | |
| `recommendation_id` | FK nullable | NULL = rating still recorded; UNIQUE may not deduplicate correctly when NULL (PostgreSQL NULL semantics) |
| `rating` | Integer | `+1` (liked) or `-1` (disliked) |

**UNIQUE:** `(patient_id, food_item_id, recommendation_id)` — one rating per combo.  
**Purpose:** Phase 8 Tier 0 RL training signal.

---

#### `subscription_codes` — Three-State Code Lifecycle
**Source:** `app/models/db_models.py:368`

| Column | Type | Notes |
|--------|------|-------|
| `code` | String(20) | UNIQUE |
| `doctor_id` | FK | Issuing doctor |
| `is_used` | Boolean | |
| `used_by_patient_id` | FK nullable | Set at CONSUMED |
| `reserved_by` | FK nullable | Set at RESERVED (patient registration) |
| `reserved_at`, `used_at`, `expires_at` | DateTime | |

**Lifecycle:** AVAILABLE → RESERVED (at patient registration) → CONSUMED (at `POST /patients/activate`).

---

#### `patient_meal_config` — Doctor TDEE Split Override
**Source:** `app/models/db_models.py:640`  
**Added:** Session 10 (migration c2d3e4f5a6b7)

| Column | Type | Notes |
|--------|------|-------|
| `patient_id` | FK (CASCADE), UNIQUE | One row per patient |
| `meal_split_override` | JSONB | `{"Breakfast": 25, "Lunch": 35, "Dinner": 25}`. NULL = use default. Application enforces sum = 85 (buffer 15% implicit). |

---

#### `doctor_meal_overrides` — RL Training Corpus
**Source:** `app/models/db_models.py:474`

Permanent record of every doctor dish swap. Patient context snapshot captured at override time (age bucket, BMI bucket, region, diet type, medical conditions). Never purge — this is Phase 8 Tier 0 training data.

---

#### Other Tables (summary)

| Table | Purpose | Source |
|-------|---------|--------|
| `progress_logs` | Daily weight/water/steps/calories (UNIQUE per patient+date) | `db_models.py:318` |
| `patient_requests` | Patient→Doctor connection requests (pending/accepted/rejected) | `db_models.py:348` |
| `clinical_notes` | Doctor notes per patient (general/dietary/medical/progress) | `db_models.py:393` |
| `audit_logs` | Doctor/admin action audit trail | `db_models.py:419` |
| `patient_visits` | Token 2 billing cycle (30-day, >15-day chargeable visit gap) | `db_models.py:442` |
| `pending_visit_approvals` | Fraud prevention: patient must confirm doctor-recorded visits | `db_models.py:602` |
| `email_verification_tokens` | Single-use, 24h expiry | `db_models.py:550` |
| `password_reset_tokens` | Single-use, 30min expiry, one per patient | `db_models.py:575` |
| `ingredients` | Master nutrition per 100g (INDB-compatible, 950 rows) | `db_models.py:744` |
| `recipe_ingredients` | food_item → ingredient with quantity_g (18,248 rows) | `db_models.py:785` |

---

### 1.2 JSONB Structures

#### `recommendations.meals` — Weekly Plan JSONB

Array of 21 objects (7 days × 3 meal types). Post-Session 22E shape:

```json
{
  "Date": "2026-06-15",
  "Meal Type": "Lunch",
  "Diet Type": "Vegetarian",
  "Region": "South",
  "Total Calories": 528.45,
  "Total Protein": 22.3,
  "Total Carbs": 68.1,
  "Total Fiber": 8.4,
  "Total Fat": 18.2,
  "Menu Names": "Dondakkai Puli + Chana Masala + Cabbage Foogath + Chaas",
  "Target Calories": 555.40,
  "Ingredients Scaling": {
    "Ivy Gourd": 145.2,
    "Chickpeas": 88.5
  },
  "dishes": [
    {
      "food_id": 276,
      "recipe_name": "Dondakkai Puli",
      "slot_type": "sabzi",
      "diet_type": "Vegetarian",
      "calories": 142.30,
      "scaled_calories": 156.20,
      "factor": 1.0978,
      "protein": 4.2,
      "carbs": 22.1,
      "fat": 3.8,
      "fiber": 2.1,
      "ingredients": [
        {"name": "Ivy Gourd", "amount_g": 145.2},
        {"name": "Tamarind", "amount_g": 11.0}
      ]
    }
  ]
}
```

**Field semantics:**
- `dishes[].calories` = unscaled `cal_per_serving` from `food_items`. Never changes.
- `dishes[].scaled_calories` = `calories × factor`. What the patient actually consumes.
- `dishes[].factor` = `target_cal / cal_per_serving`, clamped [0.5, 3.0]. Pinned dishes always 1.0.
- `Total Calories` = Σ(`scaled_calories`) across all dishes including pinned.
- `Target Calories` = generation-time slot budget (= `effective_tdee × meal_split_pct`). Never modified post-generation. Anchor for the >10% divergence warning.
- `Ingredients Scaling` = aggregate ingredient amounts across slot (SCALED). Used for shopping list.
- `dishes[].ingredients` = per-dish ingredient list (SCALED amounts).
- Macro fields (`Total Protein` etc.) = Σ(unscaled macro × factor) — see `meal_generator.py:434-437`.

**Pre-Session 11 plans** (legacy): `meals` array has no `dishes` key — old format with `Menu Names` only. Doctor dashboard shows read-only fallback for these.

---

#### `food_items.avoid_tags` / `prefer_tags`

JSONB arrays of tag strings. GIN indexed.

**Valid avoid tags** (from `tag_utils.py:CONDITION_AVOID_TAGS`):
`avoid_diabetes`, `avoid_hypertension`, `avoid_highchol`, `avoid_pcos`, `avoid_hypothyroid`, `avoid_hyperthyroid`, `avoid_heart`, `avoid_kidney`, `avoid_fattyliver`, `avoid_ibs`, `avoid_gluten`, `avoid_gout`

**Valid prefer tags** (from `tag_utils.py:CONDITION_PREFER_TAGS`):
`diabetes_friendly`, `heart_friendly`, `cholesterol_friendly`, `pcos_friendly`, `thyroid_support`, `liver_friendly`, `gut_friendly`, `gluten_free`, `calcium_rich`, `iron_rich`

**Note:** `avoid_pcos` and `avoid_gout` have 0 food_items currently — these filters are silent no-ops (`tag_utils.py:7-23` documents the intent, BUILD_TRACKER Session 19 confirms 0 matches).

---

#### `food_items.plan_type_tags` (ARRAY, not JSONB)

All 2143 recipes share the default `["Healthy", "Diabetic-Friendly", "Gym-Friendly"]`. This means the `plan_type_tags.any(plan_type)` filter in generation always matches everything — effectively a no-op filter. The `health_condition` field on the patient (`Healthy`/`Diabetic-Friendly`/`Gym-Friendly`) determines which template is selected but does NOT further narrow the dish pool.

---

#### `patients.medical_conditions` / `.food_allergies` / `.health_goals` / `.dietary_preferences`

All JSONB arrays. Exact stored values:

- `medical_conditions`: UI chip labels: `"Type 2 Diabetes"`, `"Pre-diabetes"`, `"Hypertension"`, `"High Cholesterol"`, `"PCOS/PCOD"`, `"Hypothyroidism"`, `"Hyperthyroidism"`, `"Heart Disease"`, `"Kidney Disease"`, `"Fatty Liver"`, `"IBS/IBD"`, `"Celiac Disease"`, `"Gout"`, `"Osteoporosis"`, `"Anemia"`.
- `food_allergies`: chip labels e.g. `["Peanuts", "Dairy / Lactose", "Gluten / Wheat"]`. 7 options (Nightshades removed Session 21.5). Matched as `allergen in ingredient_name.lower()` substring check — compound labels ("Dairy / Lactose") never match ingredient names exactly.
- `health_goals`: e.g. `["Weight Loss", "Muscle Gain"]`. First element drives macro split in `_calculate_targets()`.
- `dietary_preferences`: stored but not currently used in generation.

---

### 1.3 Key Relationships Diagram

```
food_items (id)
  ├── recipe_ingredients (food_item_id → food_items.id, CASCADE)
  │     └── ingredients (ingredient_id → ingredients.id, RESTRICT)
  ├── patient_dish_preferences (food_item_id)
  ├── patient_meal_choices (food_item_id)
  │     └── patient_meal_choice_dishes (food_item_id, choice_id)
  ├── meal_logs (food_id)
  ├── meal_ratings (food_item_id)
  └── doctor_meal_overrides (rejected_food_id, chosen_food_id)

meal_templates (id)
  [no FK relations — standalone slot definitions]

doctors (id)
  ├── patients (doctor_id)
  ├── subscription_codes (doctor_id)
  ├── clinical_notes (doctor_id)
  ├── patient_dish_preferences (added_by_doctor_id, RESTRICT)
  ├── patient_visits (doctor_id)
  └── food_items (doctor_id) [custom recipes]

patients (id)
  ├── recommendations (patient_id)
  │     ├── [JSONB: meals[] → dishes[] → food_id]
  │     ├── [JSONB: ingredient_checklist[]]
  │     └── [JSONB: used_food_ids[]]
  ├── patient_meal_choices (patient_id, UNIQUE per date+meal_type)
  │     └── patient_meal_choice_dishes (choice_id, CASCADE)
  ├── patient_dish_preferences (patient_id)
  ├── patient_meal_config (patient_id, UNIQUE)
  ├── meal_logs (patient_id)
  ├── progress_logs (patient_id, UNIQUE per log_date)
  ├── meal_ratings (patient_id)
  ├── patient_requests (patient_id)
  ├── patient_visits (patient_id)
  ├── clinical_notes (patient_id)
  └── doctor_meal_overrides (patient_id)

subscription_codes (id)
  ├── doctor_id → doctors
  ├── reserved_by → patients (nullable)
  └── used_by_patient_id → patients (nullable)
```

---

## 2. Generation Layer

### 2.1 Entry Point & Call Chain

**Primary trigger — manual:** `POST /api/v1/diet-plans/generate` (`app/routers/diet_plans.py:117`). Rate limited 10/hour.

**Secondary triggers (automatic):**
- Onboarding completion: `POST /api/v1/patients/onboarding` → `_launch_plan_background()` → `_generate_plan_background()` in asyncio task (`app/routers/patients.py:34-64`)
- Weight change: `POST /progress/log/weight` → `_handle_weight_change()` → regeneration (`app/routers/progress.py:80`)
- Profile update: `PUT /users/me` on diet_type changes triggers regeneration (`app/routers/users.py`)
- Doctor PATCH: `PATCH /doctor/patients/{id}/meal-config` with regenerate=True flag

**Full call chain:**

```
API endpoint
  → DietPlanService.generate_diet_plan(user_data, session)  [diet_plan_service.py:48]
      → MealGenerator.generate_meal_plan(user_data, session) [meal_generator.py:121]
          → PatientMealConfig query (if patient_id present)   [meal_generator.py:132]
          → PatientDishPreferences query                       [meal_generator.py:145]
          → FoodItem queries per slot (×21 slots)             [meal_generator.py:320]
          → returns {"meals": [...], "ingredient_checklist": [...], "used_food_ids": [...]}
  → DietPlanService.store_diet_plan(plan, session)          [diet_plan_service.py:67]
      → soft-delete previous active recommendation (is_active=False)
      → INSERT new Recommendation row
      → session.commit()
```

---

### 2.2 Patient Profile Assembly

Fields assembled in `generate_meal_plan()` from `user_data` dict. The dict is populated at the call site (e.g. `diet_plans.py`) from the `Patient` ORM row:

| Field | Source | Used for |
|-------|--------|---------|
| `tdee` | `Patient.tdee` (stored, computed at onboarding) | `effective_tdee = tdee × 0.85` |
| `diet` | `Patient.diet_type` → `_normalize_diet_label()` | Breakfast fallback chain, non-veg budget |
| `region` | `Patient.region` | Template lookup + sort priority |
| `health_condition` | `Patient.health_condition` | `plan_type` for template lookup |
| `medical_conditions` | `Patient.medical_conditions` (JSONB) | `get_avoid_tags()` + `get_prefer_tags()` |
| `food_allergies` | `Patient.food_allergies` (JSONB) | Ingredient substring filter |
| `nonveg_meals_per_week` | `Patient.nonveg_meals_per_week` | `min(n, 4)` weekly non-veg budget |
| `health_goals` | `Patient.health_goals` | First goal → macro sub-goal in `_calculate_targets()` |
| `PatientMealConfig` | DB query by `patient_id` | TDEE split override |
| `PatientDishPreferences` | DB query by `patient_id` | `pinned_food_ids`, `blocked_food_ids` |
| `prior_used_food_ids` | Passed in from caller (NOT used by DietPlanService post-22A fix) | `weekly_used_ids` seed |

**Source:** `meal_generator.py:121-229`

---

### 2.3 Slot Template System

A "slot" is a single dish position in a meal, defined by `slot_type` and `calorie_pct`.

**Where defined:**
- DB: `meal_templates.slots` JSONB column — still queried, but shadowed for Breakfast and ~40% of Lunch/Dinner.
- In-code constants (shadow DB):
  - `BREAKFAST_SLOTS` (`meal_generator.py:40-43`): `[main_dish: 78%, accompaniment: 22%]`
  - `ONE_POT_SLOTS` (`meal_generator.py:30-33`): `[one_pot: 70%, accompaniment: 30%]`

**Template selection logic** (`meal_generator.py:252-292`):
1. Query `meal_templates` WHERE `(meal_time, region, diet_type, plan_type)`.
2. If not found: fallback without `region` constraint.
3. If still not found (non-veg query): fallback to Vegetarian template.

**Slot list selection** (`meal_generator.py:287-292`):
- **Breakfast**: always uses `BREAKFAST_SLOTS` (ignores DB template slots).
- **Lunch/Dinner**: `random.random() < 0.40` → try `ONE_POT_SLOTS` first; if required slot fails, fall back to `template.slots` (standard 4-slot). Long-run average: ~40% of Lunch+Dinner slots are one-pot.

**Standard 4-slot template structure** (from DB, Lunch/Dinner):
```json
[
  {"slot_type": "grain",       "calorie_pct": 0.35, "required": true},
  {"slot_type": "dal_protein", "calorie_pct": 0.28, "required": true},
  {"slot_type": "sabzi",       "calorie_pct": 0.22, "required": true},
  {"slot_type": "accompaniment","calorie_pct": 0.15, "required": false}
]
```

---

### 2.4 Dish Selection Per Slot

**Source:** `meal_generator.py:567-660`

For each slot, `_find_food_item()` runs a diet-type fallback chain, then `_find_food_item_single_diet()` runs a 2-level lookup:

**Base query** (inner closure `base_stmt()` at `meal_generator.py:606`):
```python
SELECT food_items WHERE
    slot_type == slot_type
    AND diet_type == diet_type
    AND meal_time_tags @> ARRAY[meal_time]       -- GIN index
    AND plan_type_tags @> ARRAY[plan_type]       -- GIN index (always matches — see §1.2)
    AND cal_per_serving BETWEEN target/3.0 AND target/0.5   -- calorie window
    AND id NOT IN (daily_used_ids)               -- hard block: no same dish twice/day
    AND id NOT IN (blocked_food_ids)             -- doctor-blocked
    AND NOT (avoid_tags @> '["tag"]'::jsonb OR ...)  -- medical condition tags (GIN index)
ORDER BY prefer_sort DESC, region_sort ASC, cal_sort ASC
LIMIT 10
```

- `prefer_sort`: `OR(prefer_tags @> ["tag"] for tag in patient_prefer_tags).desc()` — preferred dishes bubble up.
- `region_sort`: `CASE WHEN region_tags @> [region] THEN 0 ELSE 1` — regional dishes first, not a hard filter.
- `cal_sort`: `ABS(cal_per_serving - target_cal)` — closest calorie match among regional.

**Level 1** (`meal_generator.py:649-652`): base_stmt + `id NOT IN (weekly_used_ids)` — excludes already-used-this-week.  
**Level 2** (`meal_generator.py:655-658`): base_stmt without weekly exclusion — pool exhausted, any candidate accepted.  
**`daily_used_ids`** is NEVER dropped. Same dish cannot appear twice in the same day across any meal.

**Post-query filter** `_pick()` (`meal_generator.py:633-643`):
- For `PROTECTED_SLOTS` (grain/dal_protein/main_dish/sabzi/one_pot): skip if name contains any `BLOCKLIST_PATTERNS` (chutney/powder/pickle/papad etc.).
- Allergy filter: skip if any ingredient name contains any allergen substring.
- Returns first candidate passing all filters.

**Diet-type fallback chain** (`meal_generator.py:507-519`):
- Breakfast (uses `user_diet`): Non-Veg → `[Eggetarian, Vegetarian]`; Eggetarian → `[Eggetarian, Vegetarian]`; Vegetarian → `[Vegetarian]`
- Lunch/Dinner (uses per-slot `query_diet`): Non-Veg → `[Non-Veg, Egg, Veg]`; Egg → `[Egg, Veg]`; Veg → `[Veg]`

**Non-veg weekly budget** (`meal_generator.py:202-218`): Pre-allocated at generation start. `min(nonveg_meals_per_week, 4)` slots randomly chosen from 14 Lunch/Dinner slots (max one non-veg per day). Only those slots use `query_diet = "Non-Vegetarian"`.

---

### 2.5 Scaling / Factor Calculation

**Source:** `meal_generator.py:340-363`

```python
target_cal = meal_targets[meal_type] * slot["calorie_pct"]

if cal_per_serving > 0:
    factor = target_cal / cal_per_serving
else:
    factor = 1.0

factor = max(0.5, min(3.0, factor))   # clamp: never scale below 50% or above 300%
```

**What `factor` affects:**
- `ingredient.amount_g` in `dishes[].ingredients` and `Ingredients Scaling` (SCALED)
- `scaled_calories = calories × factor` (SCALED)
- Macro totals: `Total Protein/Carbs/Fat/Fiber = Σ(unscaled_macro × factor)` — see `meal_generator.py:434-437`
- Individual dish macros (`dishes[].protein/carbs/fat/fiber`): **NOT scaled** — stored unscaled

**What `factor` does NOT affect:**
- `dishes[].calories`: stored unscaled per-serving. Never changes.
- Custom/PATCH-swapped dishes: factor = 1.0 explicitly set by doctor PATCH.
- Pinned dishes: factor = 1.0 (`meal_generator.py:396`).

**Post-22E fields written per dish:**

| Field | Basis | Notes |
|-------|-------|-------|
| `calories` | `cal_per_serving` | Unscaled. Never changes. |
| `scaled_calories` | `calories × factor` | What the patient eats. |
| `factor` | `target_cal / cal_per_serving`, clamped [0.5, 3.0] | 1.0 for pinned/custom |
| `protein`, `carbs`, `fat`, `fiber` | Unscaled per-serving | Not scaled in the dish object |
| Slot `Total Calories` | `Σ(scaled_calories)` | Post-pin-injection sum |
| Slot `Target Calories` | Generation-time budget | Anchors >10% divergence warning |

---

### 2.6 Pinned Dish Injection

**Source:** `meal_generator.py:377-415`

After all slots are filled for a meal, doctor-pinned dishes are injected:

1. Check if pinned dish is already in `daily_used_ids` (skip if so).
2. Check if pinned dish's `meal_time_tags` includes the current `db_meal_time` (skip if incompatible).
3. **Beverage exception** (`meal_generator.py:404-408`): if `slot_type='beverage'` and `meal_time='Breakfast'`, the pinned dish **appends** (no displacement) — beverage is no longer a standard Breakfast slot post-22E.
4. **Standard case**: if dishes array is at capacity (`len(dishes) >= slot_capacity`), `dishes.pop()` removes the last auto-selected dish, then `dishes.insert(0, pinned_dish)` prepends the pin.
5. Only one pinned dish per meal slot per generation.
6. Pinned dish added to `daily_used_ids` and `weekly_used_ids`.

**Factor:** Always 1.0 for pinned dishes. Slot `Total Calories` includes the pin's `scaled_calories` (= `cal_per_serving`). This can cause large divergence from `Target Calories` (verified: 54% for Doi chira pin in Session 22E.5 — correct behavior, not a bug). No guardrail prevents calorie-doubled slots (W3 open question).

---

### 2.7 Output Structure

`generate_meal_plan()` returns:
```python
{
    "meals": [...],               # 21 meal dicts (7 days × 3 types)
    "ingredient_checklist": [...], # [{Ingredient, Total Amount (g)}, ...]
    "used_food_ids": [...]         # IDs picked THIS generation only (not cumulative)
}
```

Each meal dict structure documented in §1.2. Per generation: 21 slots, Breakfast 2 dishes (main+acc), Lunch/Dinner 2 dishes (one_pot path) or 4 dishes (standard path). Total dishes per week: 21×2=42 (all one-pot) to 21×4=84 (all standard). Actual: ~42-63 depending on random one-pot rolls.

---

## 3. Medical Tagging Layer

### 3.1 Layer 1 — Ingredient-Level Tags

**Storage:** `ingredients.avoid_tags`, `ingredients.prefer_tags` (JSONB, added Session 18B).  
**Process:** Gemma 4 E4B Q4_K_M (llama.cpp, local) + Claude API review for 0.50–0.89 confidence range.  
**Coverage:** 950 ingredients in DB; Layer 1 tags written to most via `scripts/tag_recipes_pilot.py` / full batch.  
**Propagation to `food_items`:** Via Layer 3 derivation (union of recipe_ingredients' ingredient tags).

### 3.2 Layer 2 — Condiment/Accompaniment Reclassification

Session 22B reclassified 859 food_items from `slot_type='grain'` to correct slot_types. Session 22B.5 reclassified 3 accompaniment items. See §8 for current pool sizes.

**Before (Session 22B):** `grain` = 925 rows (most were curries, sabzis, mains — completely wrong).  
**After:** `grain` = 66 (true carb bases: chapati/roti/rice/ragi-mudde/porridges only).

### 3.3 Layer 3 — Deterministic Recipe Tag Derivation

**Script:** `scripts/derive_recipe_tags.py`  
**Logic:** For each food_item, reads its `recipe_ingredients` rows → looks up `ingredients.avoid_tags` and `prefer_tags` → takes union → writes to `food_items.avoid_tags`/`prefer_tags`.  
**Coverage:** 2116/2143 food_items tagged. 27 have no `recipe_ingredients` rows (no ingredients linked).  
**Known gap (Backlog A):** ~27 biryani/pulao dishes missing `avoid_diabetes`. Root cause: their grain/rice ingredients don't carry `avoid_diabetes` tags in Layer 1 (rice is not universally `avoid_diabetes`), but as composite high-GI dishes they should have the tag. Requires a targeted tag-correction pass.

### 3.4 Layer 4 — LLM Enrichment / Doctor Correction

- **Doctor correction endpoint:** `PATCH /doctor/recipes/{id}/tags` — validates against `VALID_TAGS` frozenset (`tag_utils.py:45`), 422 on unknown tag, sets `is_verified=True`.
- **Doctor UI:** `TagEditPanel` in `Recipes.tsx` — 12 avoid + 10 prefer pill toggles.
- **Corrections are immediate** — next plan generation reflects corrected tags.

### 3.5 Tag Filtering in Generation

**Source:** `meal_generator.py:606-621` (avoid) and `meal_generator.py:601-604` (prefer sort)

**Avoid (hard filter):**
```python
# For each avoid_tag in patient_avoid_tags:
s = s.where(not_(or_(*[FoodItem.avoid_tags.contains([tag]) for tag in patient_avoid_tags])))
# Produces: NOT (avoid_tags @> '["tag1"]' OR avoid_tags @> '["tag2"]' ...)
# Uses GIN index on avoid_tags.
```

**Prefer (soft boost, not filter):**
```python
prefer_sort = or_(*[FoodItem.prefer_tags.contains([tag]) for tag in patient_prefer_tags]).desc()
# Prepended as first ORDER BY clause — preferred dishes surface first, not hard-required.
```

**diet_type filter in suggestions endpoint** (post-Session 22F Backlog B fix):  
`FoodItem.diet_type.in_(allowed_diet_types)` — `meal_plan.py:310-314`:
```python
DIET_TYPE_HIERARCHY = {
    "Vegetarian":     ["Vegetarian"],
    "Eggetarian":     ["Vegetarian", "Eggetarian"],
    "Non-Vegetarian": ["Vegetarian", "Eggetarian", "Non-Vegetarian"],
}
```
Applied to suggestions endpoint only. Generator itself uses per-slot `query_diet` equality match.

---

## 4. API Layer

### 4.1 Middleware Stack

Registration order in `app/main.py:157-179` (outermost → innermost, LIFO):

| Middleware | Check | Notes |
|-----------|-------|-------|
| `SecurityHeadersMiddleware` | Sets HSTS, X-Frame-Options etc. | |
| `CORSMiddleware` | Origin whitelist from `CORS_ORIGINS` env | |
| `SubscriptionCheckMiddleware` | JWT claim check (zero DB reads) | Blocks inactive patients from diet generation endpoints |
| `DoctorIsolationMiddleware` | Restricts `/doctor/*` routes to doctor's own patients | Sets `request.state.doctor_id` |
| `AdminIPWhitelistMiddleware` | IP check for `/admin/*` (1 DB read) | |

### 4.2 Authentication

- **Patients:** `POST /api/v1/auth/token` with `application/x-www-form-urlencoded` (form data, not JSON). Returns JWT access (15min) + refresh (7 days in HttpOnly cookie).
- **Doctors:** `POST /api/v1/auth/doctor/login` (JSON body).
- **Admin:** `POST /api/v1/admin/login`.
- **Google OAuth:** Patients only. Sets `is_email_verified=True` automatically.
- **MFA (TOTP):** Doctors and admins. First login returns partial token (5min), second call with TOTP code upgrades to full access token.
- **Session invalidation:** `password_changed_at` timestamp on Patient row — tokens issued before this timestamp are rejected.

### 4.3 Endpoint Reference

#### `/api/v1/auth` — `app/routers/auth.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | Public | 3/hour rate limit. GDPR consent, age check, optional `doctor_code`. |
| POST | `/token` | Public | Patient login (form-data). 5/15min rate limit. |
| POST | `/doctor/login` | Public | Doctor login (JSON). Returns partial token if MFA enabled. |
| POST | `/doctor/mfa/verify` | Partial token | TOTP verification step 2. |
| POST | `/refresh` | Patient JWT | Refresh access token via HttpOnly cookie. |
| POST | `/logout` | Patient JWT | Clears refresh cookie. |
| POST | `/google` | Public | Google OAuth token exchange for patients. |
| POST | `/forgot-password` | Public | Sends reset email. |
| POST | `/reset-password` | Reset token | Validates token, updates password, invalidates sessions. |
| POST | `/verify-email` | Email token | One-time email verification. |

#### `/api/v1/users` — `app/routers/users.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/me` | Patient JWT | Full patient profile. |
| GET | `/bmi` | Patient JWT | Computed BMI. |
| PUT | `/me` | Patient JWT | Update profile. Recalculates BMI/BMR/TDEE. Auto-regenerates plan on diet_type changes. |
| GET | `/me/notification-preferences` | Patient JWT | FCM notification prefs. |
| POST | `/me/notification-preferences` | Patient JWT | Update FCM prefs. |
| DELETE | `/me` | Patient JWT | Self-delete with password confirm. Anonymises PII. |

#### `/api/v1/diet-plans` — `app/routers/diet_plans.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/my-plan` | Patient JWT | Active recommendation with checklist. Regenerates checklist if missing. |
| GET | `/today` | Patient JWT | Today's 3 meal entries only. |
| POST | `/generate` | Patient JWT | Generate new plan. 10/hour. Retry loop (max 3 attempts). |

**Validator** `_validate_generated_plan()` (`diet_plans.py:25`): checks `EXPECTED_MEAL_COUNT = 21`, Date fields, checklist, diet constraints. Returns `(valid, errors)`.

#### `/api/v1/meal-plan` — `app/routers/meal_plan.py` *(most important)*

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/adjust` | Patient JWT | Adjust plan calories (applies yesterday's surplus/deficit, floor at 800 kcal). 10/hour. |
| GET | `/week` | Patient JWT | Full weekly plan as `{"2026-06-15": [meals...]}`. 404 if no active plan. |
| GET | `/history` | Patient JWT | Plan metadata list, newest first (no meals). |
| GET | `/shopping-list` | Patient JWT | Ingredient checklist grouped by category heuristic. |
| POST | `/shopping-list/toggle` | Patient JWT | Mark ingredient as at-home/need-to-buy. |
| GET | `/suggestions/{plan_date}/{meal_type}` | Patient JWT | Up to 4 whole-meal combos. Slot composition from active plan JSONB. Diet-type filtered. See §2 for combo logic. |
| POST | `/confirm-choice` | Patient JWT | Record patient's combo choice (`food_item_ids: list[int]`). Upserts parent + child rows atomically. |
| GET | `/choices/{plan_date}` | Patient JWT | All confirmed choices for a date with per-dish breakdown. |
| GET | `/beverages` | Patient JWT | Beverage catalog (slot_type='beverage', cal < 300). Currently 22 items (591+2447 excluded). |

**Known issue (P2):** `confirm-choice` does not validate that `food_item_ids` match the `meal_type`'s `meal_time_tags`. A Breakfast dish can be confirmed into a Lunch slot via direct API call. Low risk because suggestions endpoint only surfaces slot-appropriate dishes.

#### `/api/v1/doctor` — `app/routers/doctor.py` (2439 lines)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/patients` | Doctor JWT | Paginated patient list with name/email search. 100/min. |
| GET | `/patients/{id}` | Doctor JWT | Single patient detail. |
| GET | `/patients/{id}/plan` | Doctor JWT | Patient's active recommendation. |
| PATCH | `/patients/{id}/plan/meals/{date}/{meal_type}/dishes/{dish_index}` | Doctor JWT | Swap/remove/add a dish. Recalculates slot totals. Records `DoctorMealOverride`. Backfills `recommendation_id`. |
| POST | `/patients/{id}/plan/meals/{date}/{meal_type}/add` | Doctor JWT | Add custom dish to JSONB only (no food_items row by default). `add_to_library=True` creates food_items with `submitted_for_review=True`. |
| GET | `/patients/{id}/meal-config` | Doctor JWT | Get TDEE split override + pinned/blocked dishes. |
| PATCH | `/patients/{id}/meal-config` | Doctor JWT | Set TDEE split (must sum to 85%). Optionally regenerates plan. |
| POST | `/patients/{id}/dishes/pin` | Doctor JWT | Pin a dish for a patient. |
| DELETE | `/patients/{id}/dishes/pin/{food_item_id}` | Doctor JWT | Remove pin. |
| POST | `/patients/{id}/dishes/block` | Doctor JWT | Block a dish for a patient. |
| DELETE | `/patients/{id}/dishes/block/{food_item_id}` | Doctor JWT | Remove block. |
| GET | `/recipes` | Doctor JWT | Browse food_items. `?is_verified=true/false` filter optional. |
| POST | `/recipes` | Doctor JWT | Add recipe. Dedup check on name. |
| GET | `/recipes/{id}/tags` | Doctor JWT | Get avoid/prefer tags for a recipe. |
| PATCH | `/recipes/{id}/tags` | Doctor JWT | Update tags. Validates against VALID_TAGS. Sets `is_verified=True`. |
| POST | `/patients/{id}/visits/record` | Doctor JWT | Record a chargeable visit (>15 day gap rule). |
| GET | `/patients/{id}/visits` | Doctor JWT | Visit history. |
| GET | `/renewals/pending` | Doctor JWT | Patients expiring within 4 days. |
| POST | `/renewals/{patient_id}/approve` | Doctor JWT | Approve renewal (resets token_1_expiry +30 days). |
| POST | `/patients/request/{id}/accept` | Doctor JWT | Accept patient connection request. |
| POST | `/patients/request/{id}/reject` | Doctor JWT | Reject request. |
| POST | `/patients/{id}/notes` | Doctor JWT | Add clinical note. |
| GET | `/patients/{id}/notes` | Doctor JWT | Get clinical notes. |
| GET | `/patients/{id}/logs` | Doctor JWT | Patient meal logs + activity. |
| GET | `/dashboard/stats` | Doctor JWT | Aggregate stats (patient count, active subscriptions etc.). |

#### `/api/v1/patients` — `app/routers/patients.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/onboarding` | Patient JWT | Submit full onboarding data. Stores bmi/bmr/tdee. Triggers background plan generation. Creates PatientVisit if doctor assigned. 100/min. |
| POST | `/activate` | Patient JWT | Activate subscription code. Generates token_1. |
| POST | `/doctor/request` | Patient JWT | Request connection to a doctor. |
| GET | `/doctor/request/status` | Patient JWT | Check connection request status. |
| GET | `/doctors` | Patient JWT | Browse public doctor list (for "Find a Doctor"). |
| GET | `/doctors/{id}` | Patient JWT | Single doctor public profile. |
| POST | `/visits/confirm` | Patient JWT | Confirm pending visit approval. |

#### `/api/v1/progress` — `app/routers/progress.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/log/meal` | Patient JWT | Log consumed meal. Triggers calorie adjustment when ≥80% TDEE consumed. 60/min. |
| POST | `/log/water` | Patient JWT | Log water intake (glasses). 30/min. |
| POST | `/log/steps` | Patient JWT | Log daily steps. 30/min. |
| POST | `/log/weight` | Patient JWT | Log weight. Triggers TDEE recalculation + plan regeneration. |
| POST | `/log/activity` | Patient JWT | Log exercise activity. |
| GET | `/today` | Patient JWT | Today's summary (calories consumed vs TDEE, water, steps, streak). |
| GET | `/weekly` | Patient JWT | Weekly nutrition report. |
| GET | `/weight` | Patient JWT | Weight history. |
| POST | `/rate/meal` | Patient JWT | Submit thumbs up/down on a food_item_id + recommendation_id. |
| GET | `/rate/meal` | Patient JWT | Get all ratings for current patient. |
| PUT | `/log/meal/{id}` | Patient JWT | Edit meal log entry. |
| DELETE | `/log/meal/{id}` | Patient JWT | Delete meal log entry. |

**Dual budget system (important):** `/progress/log/meal` writes to `meal_logs.calories_consumed` (consumption tracking). `/meal-plan/confirm-choice` writes to `patient_meal_choices.calories` (plan-time budget). These are separate systems with different calorie bases. `/progress/today` reads `meal_logs`. Suggestions endpoint reads `patient_meal_choices`. They can diverge.

#### `/api/v1/calculations` — `app/routers/calculations.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/bmr` | Patient JWT | Compute BMR (not stored). |
| GET | `/tdee` | Patient JWT | Compute TDEE (not stored). |
| GET | `/bmi` | Patient JWT | Compute BMI (not stored). |

#### `/api/v1/admin` — `app/routers/admin.py` (1008 lines)

Doctor management (activate/deactivate), subscription code generation, patient management, audit log review, IP whitelist management. All endpoints require admin JWT + IP whitelist check.

---

## 5. Doctor Dashboard Layer

**Stack:** React + Vite + Tailwind + Radix UI (`mitihar-frontend/apps/`)  
**State:** React Query for server state; React local state for UI.  
**API client:** `src/lib/doctorApi.ts`

### 5.1 Patient Management

**PatientDetail.tsx** — 6-tab interface:

| Tab | What doctor sees |
|-----|-----------------|
| Profile | Demographics, BMI, TDEE, diet type, region, health condition, subscription status (token_1 expiry, active/inactive badge) |
| Plan | Active meal plan (7 days × 3 meals). Per-dish cards with swap/remove controls. |
| Activity | Meal logs, weight history, calorie trends. |
| Notes | Clinical notes (add/view). Private vs visible-to-patient toggle. |
| Visits | Token 2 billing history. Record visit button. |
| Meal Config | TDEE split sliders + pin/block dish management. |

**Patient list** (`/doctor/patients`): paginated, name/email search, token_1 status + expiry, 30-day countdown.

### 5.2 Plan Controls (PlanTab.tsx)

**View:** Displays `recommendations.meals` JSONB grouped by date. Each slot shows:
- Slot label (Breakfast/Lunch/Dinner)
- Menu Names string (legacy display compat)
- Per-dish DishCard with recipe_name, slot_type, calories, macros
- Amber warning if `|Total Calories - Target Calories| / Target Calories > 10%`
- Doctor note field per slot

**Swap/edit dishes:** `DishCard` component opens `RecipeSearchModal` → PATCH endpoint with action: `swap`/`remove`/`add`. Recalculates slot `Total Calories = Σ(scaled_calories)` post-swap. `factor=1.0` for PATCH-created dishes.

**Pin a dish:** `MealConfigTab.tsx` → dish search dropdown → `POST /doctor/patients/{id}/dishes/pin`. Pin injected at NEXT plan generation (not into existing plan).

**Block a dish:** Same flow via `POST /doctor/patients/{id}/dishes/block`. Blocked dishes excluded from current AND future generations.

**Add custom dish to plan:** Inline without food_items record by default. `add_to_library=True` creates food_items with `submitted_for_review=True`.

**TDEE split:** `MealConfigTab.tsx` → three sliders (Breakfast/Lunch/Dinner summing to 85%) + Save & Regenerate. Validation: sum must equal 85 exactly. Doctor can also set per-patient nonveg_meals_per_week here.

### 5.3 Doctor Dashboard Current Gaps

| Gap | Details |
|-----|---------|
| No weekly patient summary | `SESSION 22 — Doctor Weekly Patient Summary` is NOT STARTED. Doctor cannot see what patient actually chose, calorie trends, or adherence. The child table (`patient_meal_choice_dishes`) has the data but no API endpoint reads it for doctor view. |
| No meal rating visibility | Doctor cannot see patient thumbs-up/down ratings from dashboard. Data exists in `meal_ratings` table. |
| `assign_recipe` endpoint creates dishes-less slots | `doctor.py:1264` (per BUILD_TRACKER 22D). These slots render as legacy read-only. |
| Pin operates on next regen only | Pinning a dish does NOT update the current plan. Doctor must click Regenerate or wait for next generation. |
| No guard for calorie-doubled pin | If doctor pins a 2nd main_dish to a slot, amber warning fires (correct) but plan still reaches patient with 54%+ calorie divergence (W3 open question, no guard). |

---

## 6. Patient App Layer

**Stack:** Expo (React Native) + NativeWind (`mitihar-patient-app/`)  
**API:** Axios instance at `lib/axios.ts`, `EXPO_PUBLIC_API_URL` → LAN IP of dev machine.  
**State:** React Query + Zustand (onboarding store persisted to AsyncStorage).

### 6.1 Onboarding Flow

Post-Session 21.5: **7 steps** (was 8). Lifestyle step removed.

| Step | Screen | Data Collected |
|------|--------|---------------|
| 1 | `personal-info.tsx` | Date of birth (day/month/year pickers), gender, height_cm, weight_kg, target_weight_kg (optional) |
| 2 | `goals.tsx` | health_goals (multi-select chips) |
| 3 | `medical-conditions.tsx` | medical_conditions (multi-select chips, 15 conditions) |
| 4 | `allergies.tsx` | food_allergies (multi-select, 7 chips: Dairy/Lactose, Peanuts, Tree Nuts, Shellfish/Fish, Gluten/Wheat, Soy, Eggs) |
| 5 | `dietary-preferences.tsx` | diet_type, region, dietary_preferences, nonveg_meals_per_week |
| 6 | `activity-level.tsx` | activity_level (S/LA/MA/VA/SA), pace_preference |
| 7 | `disclaimer.tsx` | disclaimer_accepted_at |

**Submit:** `POST /api/v1/patients/onboarding` — calculates BMI/BMR/TDEE, stores atomically. Background task generates plan. Firebase push notification sent when plan ready.

**Onboarding store:** Zustand + AsyncStorage. Survives app kill mid-flow. Doctor code entry during registration (`POST /auth/register`) enters code as optional field.

### 6.2 Main App Screens

#### Home Tab (`index.tsx`)
- Calorie ring: TDEE target vs consumed (from `GET /progress/today`)
- Streak count
- Snack quick-log: bottom sheet with calorie presets (50/100/200/300 kcal) + free entry. Logs as `meal_type="Snack"` to `meal_logs`.
- Doctor status banner: connection request status, doctor info
- Next visit card: derived from `PatientVisit.cycle_start`

#### Meals Tab (`meals.tsx`)
- **WeekStrip:** Mon-Sun horizontal date selector.
- **Past days:** `PastDayView` — shows confirmed choices (from `GET /meal-plan/choices/{date}`) as read-only. Shows "Not logged" if no choice.
- **Today (and future):** `SuggestionSlot` per meal type (Breakfast/Lunch/Dinner):
  - If no choice confirmed: shows `ComboCard` components (up to 4 combos from `GET /suggestions/{date}/{meal_type}`)
  - If choice confirmed: shows combo names joined with " + " and total calories
- **ComboCard:** Dish names + ` + ` separator, `~X kcal`, slot-type tags per dish. Select button triggers `POST /meal-plan/confirm-choice` with `food_item_ids[]`.

**Suggestions shape (post-22F):**
```json
{
  "slot_calorie_target": 555.4,
  "slot_composition": ["grain", "dal_protein", "sabzi", "accompaniment"],
  "calories_remaining_today": 1234.5,
  "suggestions": [
    {
      "combo_id": 0,
      "total_calories": 528.3,
      "dishes": [
        {"food_item_id": 276, "recipe_name": "...", "slot_type": "grain", "calories": ...}
      ]
    }
  ]
}
```

#### Meal Detail Screen (`meal-detail.tsx`)
- Per-dish `DishCard` with staggered entry animation
- Each card: dish name, slot_type badge, `scaled_calories` (displayed), macros
- Expandable ingredients list (SCALED amounts)
- Thumbs up/down rating wired to `food_item_id`
- "I Had This" → logs to `meal_logs` + 1.4s success state → back navigation

#### Progress / Beverage Logging
- Beverage picker: `GET /meal-plan/beverages` → list of 22 items. Patient selects and logs via `POST /progress/log/meal` with `food_id`.
- Water logging: quick-log bottom sheet (removed native HealthKit integration deferred)
- Steps logging: deferred (native HealthKit integration pending)
- Weight logging: `POST /progress/log/weight`

### 6.3 Patient App Current Gaps

| Gap | Details |
|-----|---------|
| No gram quantities displayed | Planned (Session 23 not started). Currently ingredients show scaled `amount_g` in meal detail. |
| Proportional labels not implemented | Session 23. Intended: "large portion/small bowl/1 tsp/pinch" mapping. |
| Allergy substring match is weak | Compound labels ("Dairy / Lactose", "Tree Nuts") never match ingredient names as substrings. Silent no-ops. |
| Water/steps native sync not built | HealthKit (iOS) / Health Connect (Android) deferred. Manual entry removed but no auto-sync. |
| Shopping list gram quantities | Labels show but amounts are often unrealistic (batch data errors in `quantity_g` for 582 recipes). |
| Week view no calorie ring per day | Past days show confirmed dish names but no calorie total comparison. |
| No teaser for free users on Meals tab | Teaser is in `TEASER_MEALS` constant but free user suggestions flow is undefined post-22F redesign. |

---

## 7. Weekly Cycle Layer

### 7.1 Current Weekly Cycle (What Actually Happens)

1. **Doctor generates plan** (manual): `POST /diet-plans/generate` or via Doctor Dashboard "Regenerate". Produces 21 meal slots for a 7-day window starting from `user_data["start_date"]` (defaults to today).

2. **Doctor optionally edits plan** (manual): Swaps individual dishes via PATCH. Each swap creates a `DoctorMealOverride` row. Total Calories recalculated post-swap.

3. **Doctor optionally configures**: Sets TDEE split or pins/blocks dishes via MealConfigTab. Pin takes effect on NEXT regeneration only.

4. **Patient sees plan**: Via `GET /meal-plan/week` on Meals tab. No notification to patient when plan is ready (Firebase push sent on background generation, not on doctor edits).

5. **Patient sees suggestions**: `GET /meal-plan/suggestions/{date}/{meal_type}` on demand. Returns up to 4 combos based on plan JSONB slot composition.

6. **Patient confirms choice**: `POST /meal-plan/confirm-choice` → `patient_meal_choices` row + `patient_meal_choice_dishes` children. Reduces `calories_remaining_today`.

7. **Patient logs consumption**: `POST /progress/log/meal` → `meal_logs`. Separate from confirm-choice. Both can be used simultaneously.

8. **Patient logs beverages**: `POST /progress/log/meal` with `food_id` from beverage picker.

9. **End of week**: Nothing automated. No weekly summary generated. No next-week plan generated. No feedback loop from patient choices to next plan.

**What is automated:**
- Plan generation triggered on onboarding, weight change, and profile diet_type change.
- Daily cron: flag patients expiring within 4 days (`expiring_soon=True`).
- Daily cron: deactivate expired patients (`token_1_active=False`).

**What requires manual action:**
- Plan generation for a new week.
- Doctor review of patient choices (no UI exists).
- Doctor renewal approval.

### 7.2 Intended Weekly Cycle (Not Yet Built)

| Intended Feature | Current State |
|-----------------|--------------|
| Doctor Weekly Patient Summary | NOT STARTED (Session 22 spec exists in BUILD_TRACKER). `patient_meal_choices` + `patient_meal_choice_dishes` have the data. No API endpoint. |
| Auto-generation of next week's plan | NOT STARTED. No trigger exists. Doctor must manually regenerate. |
| Patient choice → next week personalization | PARTIAL. Data infrastructure in place (`patient_meal_choice_dishes`). No code reads this data for personalization. `used_food_ids` provides cross-week variety avoidance but that's independent of patient choices. |
| Adaptive budget (suggestions sized to remaining budget) | PARTIAL. `calories_remaining_today` is returned by suggestions endpoint. But suggestions do not actually resize combos to remaining budget — they return fixed combos ranked by `slot_calorie_target`, not by `calories_remaining`. |
| Rating-driven personalization | NOT STARTED. `meal_ratings` table populated by patient. Not read by generator. Phase 8 Tier 0 collection only. |

---

## 8. Known Gaps & Technical Debt Inventory

### Clinical (Patient Safety Risk)

| Issue | Severity | Details |
|-------|----------|---------|
| Backlog A: ~27 biryani/pulao missing `avoid_diabetes` | **P0** | Diabetic patients may receive high-GI rice dishes. Root cause: rice/biryani ingredient doesn't carry `avoid_diabetes` at ingredient level. Dedicated tagging pass required. |
| `avoid_pcos` / `avoid_gout` — 0 food_items | P1 | PCOS and Gout filters are silent no-ops. `tag_utils.py:11,18`. No patient protection for these conditions. |
| W3 pin guardrail missing | P1 | Doctor pinning 2nd main_dish to a slot causes 54%+ calorie divergence with amber warning only — no guard prevents calorie-doubled slot reaching patient. W3 open question. |
| Allergy filter is substring only | P1 | Compound allergen labels ("Dairy / Lactose") don't match ingredient names. Peanut allergy would miss "groundnut", "moongphali". |

### Functional (Feature Broken or Missing)

| Issue | Details |
|-------|---------|
| Doctor Weekly Summary — NOT BUILT | Session 22 not started. Doctor has zero visibility into what patient chose. |
| Patient choice → plan feedback loop — NOT BUILT | Child table has data; nothing reads it for personalization. |
| `confirm-choice` lacks meal_time_tags validation | P2. Breakfast dish can be confirmed into Dinner slot via API. |
| Auto-plan generation not weekly | No weekly trigger. Doctor regenerates manually. |
| Water/steps native health sync missing | HealthKit / Health Connect not built. Manual entry removed (Session 21.5). |
| `assign_recipe` creates dishes-less slots | Legacy code path in doctor.py creates slots without `dishes[]`, shown read-only. |
| Budget ring not adaptive | `calories_remaining_today` returned by suggestions but combos are not resized to match. |

### Data Quality

| Issue | Details |
|-------|---------|
| 582 recipes with bad `quantity_g` | Batch entry errors (8000g makhana etc.). `nutrition_source='manual'`. Inflated shopping list quantities. Identified Session 15. |
| Beverage data errors | id 591 (Buttermilk Soup: 2857.7 kcal), id 2447 (Spiced Beetroot Buttermilk: 403.56 kcal). Hidden by `cal_per_serving < 300` guard in beverages endpoint. Underlying data not fixed. |
| Dish rename script 22% complete | `scripts/rename_dishes_gemini.py` — ~440/2137 dishes renamed. Checkpoint at `rename_checkpoint.json`. |
| 3 food_items with "Gm " prefix ingredient names | IDs with "Gm arhar dal", "Gm makhana" — corrupted names only, amounts correct. |
| id 2674 (Drumstick Buttermilk Curry) slot_type='grain' | Should be 'sabzi'. Identified Session 9, not fixed in 22B sweep. |
| 104 NULL ingredient nutrition rows | Measurement-phrase names ("1/2 tablespoons mustard seeds"). Artifact of source dataset. |
| ~7 test artifact food_items | IDs 3698–3716 "Doctor2 Private Dal" / "Global Test Recipe" — empty meal_time_tags, unreachable. Manual DB cleanup needed. |

### Technical Debt

| Issue | Details |
|-------|---------|
| 2 pre-existing TypeScript errors | `PlanTab.tsx:888` — `meal.id` doesn't exist in `MealEntry` interface. `Recipes.tsx` — `submit_to_global` missing from `addRecipe` call. Both pre-Session 16, not fixed. |
| `full_backend_test.py` admin login crash | Admin login uses wrong path prefix. Pre-existing. Blocks regression test suite. |
| `progress/water-log.tsx` orphaned | Orphaned route in patient app. Water logging removed from quick-log, this screen unreachable. |
| `plan_type_tags` effectively useless | All 2143 recipes share default `["Healthy", "Diabetic-Friendly", "Gym-Friendly"]`. Filter never narrows results. |
| `dietary_preferences` field collected but unused | Stored in `patients.dietary_preferences` via onboarding. Not read in generation. |
| `eating_habits` field collected but unused | `["skips_breakfast", "late_night_eating"]` etc. Not used in generation. |
| `recommendation_id` NULL on older meal_logs | Backfilled only on doctor PATCH, not retroactively. Old ratings may not deduplicate correctly. |
| Ingredient deduplication not done | Many ingredients appear 2–3× with different capitalization. All duplicates were tagged identically so Layer 3 is correct, but dedup pass needed. |
| `Urad dal papad` in ingredients table | Processed product behaves differently from base dal. Needs condiment reclassification. |
| `test_results_archive/` in docs | Build artifact directory, not code. |
| Rate limiter uses in-memory storage | `slowapi` in-memory. Must switch to `REDIS_URL` before multi-worker deployment. |

---

## 9. Rebuild Impact Summary

**Solid / reusable layers:**

- **Data model** (tables, FKs, JSONB schemas) — well-designed with one exception: the dual calorie-basis problem (`calories` unscaled vs `scaled_calories`) is a permanent complication that the rebuild will need to resolve cleanly.
- **Medical tagging infrastructure** (`tag_utils.py`, `food_items.avoid_tags/prefer_tags`, GIN indexes, `ingredients` table) — solid. The 4-layer architecture is sound; the coverage gaps (Backlog A, avoid_pcos, avoid_gout) are data problems, not architecture problems.
- **Authentication & subscription lifecycle** (JWT, MFA, token_1/token_2, three-state codes, daily crons) — battle-tested across 22 sessions.
- **Food item database** (2143 recipes, slot_type taxonomy corrected, 1519 nutrition-chain-calculated) — usable as-is, though 582 bad-quantity recipes and the rename-22%-done debt remain.

**Layers that need significant redesign for weekly-cycle architecture:**

- **Generation layer** — currently produces one static plan for the whole week. The intended architecture (adaptive combos, patient choice drives next week, calorie remaining drives suggestion sizing) requires: (1) on-demand combo generation replacing precomputed plan, or (2) a plan-update webhook when patient choices are made. The current `meal_generator.py` is a good foundation but the 7-day-at-once approach cannot directly support real-time adaptive suggestions.
- **Weekly cycle orchestration** — entirely absent. No scheduled generation, no weekly summary, no feedback pipeline. The data infrastructure (`patient_meal_choice_dishes`, `used_food_ids`) exists but is not wired into any loop. Building the weekly cycle from scratch is the single largest new development need.
- **Doctor weekly summary** — no API endpoint, no UI. Requires Session 22 (spec exists). The child table is ready; the aggregation query + dashboard tab are the work.
- **Suggestions endpoint** — the current combo-building (Session 22F) is a correct foundation but does not yet resize combos to remaining daily budget, and the legacy fallback path is still active for ~50% of patients (pre-22E plans). Replacing with a fully budget-aware, always-combo endpoint is a clean rebuild project.
- **Patient app** — `meals.tsx` correctly implements the combo card + confirm-choice flow, but the week view, past-day restoration, and calorie ring are all disconnected from the intended adaptive budget loop. The TypeScript types are up-to-date post-22F, making this the most rebuild-ready frontend layer.
