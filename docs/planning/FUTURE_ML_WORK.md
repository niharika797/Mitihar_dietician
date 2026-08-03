# Mitihar — Future ML & Recommendation Work
> Written: 2026-03-20
> Status: Planned — do NOT implement until conditions noted per section are met
> Related files: `RL_Roadmap.md` (bandit algorithm detail), `Task_List.md` (overall progress)

---

## Overview

The meal generator is currently **rule-based** — macro calculations + food item filtering
by diet type, region, health condition, and allergy lists. This document describes two
independent tracks of future improvement:

1. **Track A — Rule-Based Improvements** (Phase 6): Better generator logic. No data required.
   Can be done any time before or after launch.

2. **Track B — RL / Preference Learning** (Phase 8): The system learns from real doctor and
   patient behaviour over time. Data-gated — do not build until conditions are met.

These tracks are **independent**. Track A makes the baseline better. Track B learns on top
of whatever baseline exists. Both can be implemented in any order relative to each other.

---

## Track A — Rule-Based Generator Improvements (4 tasks)
> **Prerequisite:** None. Can be done anytime.
> **Files to touch:** `app/services/meal_generator/meal_generator.py`, `app/services/diet_plan_service.py`

### A1 — Remove Region Filter at Level 1

**Problem:** The generator currently filters food items by region at the first candidate
selection stage. With only ~2,000 food items in the database, this shrinks the candidate
pool dramatically — a patient in "South" or "East" gets far fewer options than one in "North",
and variety suffers week-over-week.

**Fix:** Remove region as a hard filter at Level 1 selection. Keep it as a soft preference /
bonus scoring signal instead. Region-specific items are preferred but not required. Only apply
hard region filter if the patient explicitly has "regional_only" in their preferences.

**Impact:** Immediate improvement in meal variety for all non-North patients.

---

### A2 — Expand Health Conditions from 3 to 15+

**Problem:** Currently only 3 conditions are handled: `Healthy`, `Diabetic-Friendly`,
`Gym-Friendly`. The Indian market needs significantly more:

| Condition to Add | Macro / Food Rule |
|---|---|
| PCOS / PCOD | Low GI, high fibre, anti-inflammatory, reduce dairy |
| Thyroid (Hypothyroid) | Low goitrogen, high selenium, iodine-rich |
| Kidney Disease | Low potassium, low phosphorus, low sodium, low protein |
| Gluten-Free | Exclude wheat, barley, rye — use millets, rice |
| Vegan | No dairy or meat, ensure B12/iron sources |
| Keto | High fat (>60%), very low carbs (<20g/day), moderate protein |
| Jain (strict) | No root vegetables (onion, potato, carrot, garlic, beetroot) |
| High Cholesterol | Low saturated fat, high soluble fibre, no trans fat |
| High Blood Pressure | Low sodium (<1500mg/day), DASH-diet pattern |
| Fatty Liver (NAFLD) | Low sugar, low saturated fat, high fibre |
| IBS (irritable bowel) | Low FODMAP foods |
| Pregnancy | Higher iron, folate, calcium — avoid raw/undercooked |
| Post-Bariatric | Very small portions, high protein, avoid sugar |
| Eating Disorder (recovery) | Gentle variety, no calorie display |

**Implementation approach:**
- Add condition definitions to a new `app/services/meal_generator/health_profiles.py`
- Each profile declares: allowed food tags, blocked food tags, macro override percentages, max cal per serving
- `meal_generator.py` reads the active profile at generation time
- No DB migration needed — all logic in code

**Impact:** Massively expands the patient base that can be meaningfully served.

---

### A3 — Cross-Week Meal History (No Repeats Across Weeks)

**Problem:** `weekly_used_ids` is a local variable that resets on every plan generation call.
This means the generator has no memory of what was served last week — patients get the
same meals repeating week after week once the filtered pool is small.

**Fix:**
- After generating a plan, store the list of `food_item_id`s used in that plan on the
  `Recommendation` row (the `used_food_ids` JSONB column already exists — it's just not
  being populated or read correctly across generations)
- At generation time, load the last 3 weeks of `used_food_ids` from the DB for that patient
- Pass them into the generator as `cross_week_exclude_ids` in `user_data`
- The generator excludes these IDs from the candidate pool (same way `weekly_used_ids` works today)
- After 3 weeks, IDs age out naturally — meals can repeat after a month gap

**Files:** `app/services/diet_plan_service.py`, `app/services/meal_generator/meal_generator.py`

**Impact:** Eliminates the single most common patient complaint — seeing the same dal every Monday.

---

### A4 — Data Validation Script

**Problem:** The food database has ~2,000+ items seeded from CSV + manual entry. No validation
has been run to check for data quality issues.

**Task:** Write `scripts/data_validation.py` that checks:
- Calories = 0 or null (can't be used in planning)
- Protein/carbs/fat all = 0 (likely missing data, not truly zero-macro)
- Calories implausibly high (>1500 kcal per serving)
- Calories inconsistent with macros (protein×4 + carbs×4 + fat×9 differs from `cal_per_serving` by >20%)
- `slot_type` null or not in allowed values
- `diet_type` null or not in allowed values
- `region_tags` empty array (makes region filtering impossible for this item)
- `meal_time_tags` empty array (item can never be selected)
- Duplicate `recipe_name` entries

Output: a CSV report at `data/validation_report.csv` with one row per issue found.
Run after any ETL import or bulk seed operation.

---

## Track B — RL / Preference Learning

> **Data collection is already running** via `doctor_meal_overrides` and `meal_ratings` tables.
> These are populated from day one — Phase 8 Tier 0 is complete.
> The sections below describe when and how to *activate* learning on top of that data.

---

## Track B1 — Preference Scoring (Phase 8 Tier 1)
> **Prerequisite: ≥5 active doctors onboarded for ≥1 month**
> **Estimated work:** 7 tasks, ~3–4 days
> **Files:** `scripts/update_preference_scores.py` (new), `app/main.py`, `app/services/meal_generator/meal_generator.py`, `app/services/diet_plan_service.py`

### What it does

A weekly batch job reads the accumulated `doctor_meal_overrides` data and computes a
preference score per food item per patient context. The score is written back into a
`preference_context` JSONB column on `food_items` and used as a soft sort signal in
the generator.

### Task list

- [ ] Add `preference_score` Float column (default 0.0) to `food_items` + Alembic migration
- [ ] Add `preference_context` JSONB column to `food_items` + Alembic migration
      Format: `{"Healthy_North_Vegetarian": 2.3, "PCOS_South_Vegetarian": -1.0}`
      Key = `"{health_condition}_{region}_{diet_type}"`
- [ ] Write `scripts/update_preference_scores.py`:
      Reads `doctor_meal_overrides`, computes per-bucket score per food_item:
      `score = (chosen_count - rejected_count) / (chosen_count + rejected_count + 1)`
      Writes result into `preference_context` JSONB on each food_item row
- [ ] Register as APScheduler weekly job in `main.py` — Sunday 02:00 UTC
- [ ] Update `_find_food_item_single_diet()` in meal generator:
      Add `preference_score` as tertiary sort key after region_sort and cal_sort
      Read from `preference_context[patient_context_key]` for the current patient

- [ ] Write `_load_patient_preferences(patient_id, session)` service:
      Returns `(soft_prefer_ids: set[int], soft_avoid_ids: set[int])`
      prefer = items with net patient rating ≥ +2 (liked more than once)
      avoid  = items with net patient rating ≤ -2 (disliked more than once)
- [ ] Pass these sets into `user_data` dict in `diet_plans.py`
      Generator: preferred items get a boosted candidate pool (LIMIT 15)
      Generator: avoided items excluded alongside `weekly_used_ids`

### Reward signal used

From `RL_Roadmap.md`:
```
score += 1    food_item was chosen by doctor (doctor explicitly picked this)
score -= 1    food_item was rejected by doctor (doctor replaced this)
score += 0.5  patient gave 👍 (patient liked it)
score -= 0.5  patient gave 👎 (patient disliked it)
```

---

## Track B2 — Thompson Sampling Bandit (Phase 8 Tier 2)
> **Prerequisite: ≥50 active patients × ≥8 weeks of data (3–6 months post-launch)**
> **Estimated work:** 12 tasks, ~1 week
> **Files:** `app/models/db_models.py`, new migration, `app/services/bandit_service.py` (new),
>           `scripts/initialize_bandit_priors.py` (new), `scripts/run_bandit_update.py` (new),
>           `app/main.py`, `app/core/config.py`, `app/services/meal_generator/meal_generator.py`

### What it does

Replaces the pure sort-based food item selection with a **Contextual Bandit** using
Thompson Sampling. Each food item × patient context pair has a Beta distribution tracking
its success rate. The generator samples from these distributions and naturally explores
less-tried items while exploiting proven winners.

The algorithm activates via a feature flag — rule-based selection remains the fallback
until enough data exists per context bucket.

### Context vector

```
health_condition × medical_conditions_bucket × activity_level
× diet_type × age_bucket × gender × bmi_bucket × region
```
Hashed to a 32-char MD5 string. ~46,000 theoretical buckets. Most never populated —
cold-start handled by uniform Beta(1,1) prior (equal probability exploration).

### Task list

- [ ] Create `food_item_bandit_stats` DB model:
      `id`, `food_item_id`, `context_bucket_hash` (MD5 String 32),
      `context_label` (human-readable e.g. "Healthy_North_Veg_26-35_F_Normal_MA"),
      `alpha` (Float, default 1.0), `beta` (Float, default 1.0), `last_updated`
- [ ] Add unique constraint `(food_item_id, context_bucket_hash)`
- [ ] Write Alembic migration for the new table
- [ ] Write `scripts/initialize_bandit_priors.py`:
      Seeds all observed (food_item_id × context) pairs with alpha=1, beta=1
      (Uniform prior — no assumptions before real data)
- [ ] Write `app/services/bandit_service.py`:
      - `compute_context_hash(patient_profile) → str` — deterministic MD5
      - `thompson_sample(candidates, context_hash, session) → FoodItem`
        Fetches or creates bandit row per candidate, samples Beta(alpha, beta),
        returns highest-sampled candidate
      - `update_bandit(food_item_id, context_hash, reward, session)`
        alpha += reward; beta += (1 - reward)
- [ ] Write `scripts/run_bandit_update.py`:
      Reads new `doctor_meal_overrides` and `meal_ratings` since last run,
      computes reward per event (see formula below), calls `update_bandit()`
- [ ] Register nightly APScheduler job in `main.py` — 03:00 UTC
- [ ] Integrate `thompson_sample()` into `_find_food_item_single_diet()`:
      Only activates when `BANDIT_ENABLED=True` AND bandit data exists for the context
      AND alpha+beta ≥ `BANDIT_MIN_SAMPLES` for that pair
- [ ] Add `BANDIT_ENABLED: bool = False` to `app/core/config.py`
      Switch to True manually when data conditions are confirmed met
- [ ] Add `BANDIT_MIN_SAMPLES: int = 20` to `app/core/config.py`

### Reward formula

```
reward = 1.0    doctor kept the meal AND patient logged it AND weight on track
reward = 0.75   doctor kept the meal AND patient logged it
reward = 0.5    doctor kept the meal, patient didn't log (no data)
reward = 0.25   patient gave 👍 but doctor had replaced it (conflicting signal)
reward = 0.0    doctor replaced this meal (clearest negative signal)
reward = -0.5   patient gave 👎 (strong personal dislike — note: negative → clamp beta)
```

---

## Implementation Timeline

```
Now (pre-launch)       → Track A rule-based improvements (no data needed)
Month 1 (5+ doctors)  → Track B1 preference scoring activates
Month 3-6 (50+ pats)  → Track B2 Thompson Sampling bandit activates
```

---

## Hard Rules (Do Not Violate)

- **Do NOT** activate the bandit on fewer than 50 patients × 8 weeks of data
- **Do NOT** correlate weight loss with individual food items — causal attribution is wrong
- **Do NOT** use `ClinicalNote` free text as a training signal (unstructured, needs NLP pipeline)
- **Do NOT** use PPO / policy gradient / full RLHF — requires GPU + dense interaction data
  that a 30-day meal cycle app will never generate per patient
- **Do NOT** purge `doctor_meal_overrides` or `meal_ratings` — ever. These are the permanent
  training corpus. Archive to cold storage after 2 years but never delete.

---

## Task Summary

| Track | Task | Prerequisite | Estimated Work |
|---|---|---|---|
| A1 | Remove region hard filter | None | 2–3 hours |
| A2 | Expand health conditions to 15+ | None | 2–3 days |
| A3 | Cross-week meal history | None | 4–6 hours |
| A4 | Data validation script | None | 2–3 hours |
| B1 | Preference scoring (7 tasks) | 5 doctors + 1 month | 3–4 days |
| B2 | Thompson Sampling bandit (12 tasks) | 50 patients + 3-6 months | ~1 week |

**Total remaining ML work: 26 tasks**
