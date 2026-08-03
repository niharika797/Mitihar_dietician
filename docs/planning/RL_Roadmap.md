# Mityahar — RL Data Infrastructure Roadmap
> Created: 2026-03-17
> Status: Planned — Tier 0 to be implemented before first real doctor onboards

---

## Why This Exists

The meal generator is currently rule-based (macro calculations + food item filtering).
This roadmap describes how the system evolves to learn from doctor edits and patient
feedback over time using a Contextual Bandit (Thompson Sampling) approach.

**Core principle:** Data collected before the algorithm exists is still useful.
The most valuable data (doctor override events) can never be recovered retroactively.
Start collecting from day one, activate the algorithm when the data is sufficient.

---

## The 3 Signal Types

| Signal | Source | Quality | Table |
|---|---|---|---|
| Doctor replaces a meal | PUT /doctor/patients/{id}/plan | ⭐⭐⭐ Highest | `doctor_meal_overrides` |
| Patient rates a meal 👍/👎 | Patient app meal card | ⭐⭐ High | `meal_ratings` |
| Patient logs the meal back | POST /progress/log/meal | ⭐ Medium | existing `meal_logs` |

---

## Reward Formula (for future algorithm)

```
reward = 1.0   doctor kept the meal AND patient logged it AND weight on track
reward = 0.75  doctor kept the meal AND patient logged it
reward = 0.5   doctor kept the meal, patient didn't log (no data)
reward = 0.25  patient gave 👍 but doctor had replaced it (conflict)
reward = 0.0   doctor replaced this meal (clearest negative signal)
reward = -0.5  patient gave 👎 (strong personal dislike)
```

---

## Tier 0 — Pre-Launch (Must Complete Before First Doctor)

**Goal: Silent data collection. No algorithm yet. Just clean storage.**

### Backend — `doctor_meal_overrides` table

- [ ] Create DB model with columns:
  - `id`, `doctor_id`, `patient_id`, `override_date`
  - `slot_type`, `meal_type`
  - `rejected_food_id` (nullable — None if original was a custom meal)
  - `chosen_food_id` (nullable — None if doctor added a custom meal)
  - `patient_health_condition` (e.g. "Healthy")
  - `patient_medical_conditions` (JSONB, e.g. ["PCOS/PCOD"])
  - `patient_region` (e.g. "South")
  - `patient_diet_type` (e.g. "Vegetarian")
  - `patient_age_bucket` (e.g. "26-35")
  - `patient_bmi_bucket` (e.g. "normal")
  - `created_at`
- [ ] Write Alembic migration
- [ ] Helper `_bucket_age(dob) → str` — returns "18-25" / "26-35" / "36-50" / "50+"
- [ ] Helper `_bucket_bmi(bmi) → str` — returns "underweight" / "normal" / "overweight" / "obese"
- [ ] Helper `_extract_food_id(meal_dict) → int | None` — reads `food_id` key from meal JSONB
- [ ] Update `PUT /doctor/patients/{id}/plan`:
  - Diff old meals array vs new meals array by (Date + Meal Type)
  - For each changed slot, write one `doctor_meal_overrides` row
  - Capture full patient context snapshot at time of override
- [ ] `GET /doctor/patients/{id}/plan/overrides` — override history for audit trail

### Backend — `meal_ratings` table

- [ ] Create DB model with columns:
  - `id`, `patient_id`, `food_item_id`, `recommendation_id`
  - `rating` (SmallInt: +1 or -1)
  - `rated_at`
- [ ] Add unique constraint `(patient_id, food_item_id, recommendation_id)`
- [ ] Write Alembic migration
- [ ] `POST /api/v1/progress/meal/rate` — `{ food_item_id, recommendation_id, rating: 1|-1 }`
- [ ] `GET /api/v1/progress/meal/ratings` — patient's own ratings for UI state restore

### Patient App

- [ ] Add 👍/👎 buttons to each meal card (visible after meal time has passed)
- [ ] Wire to `POST /api/v1/progress/meal/rate`
- [ ] On screen load: fetch existing ratings, restore button states

### Fix Tech Debt Blocking Signal Quality

- [ ] `ProgressLog.total_calories_consumed` — write in `progress_service.log_meal()`
       by summing today's meal logs after each new log entry
- [ ] `MealLog.food_id` — populate when logging a meal from a recommendation
       (match by recommendation_id + meal_type + logged_date to find food_item_id)

**Tier 0 total: 14 tasks**

---

## Tier 1 — ~1 Month Post-Launch (5+ Active Doctors)

**Goal: Generator starts consulting preference data from doctor overrides.**

### Preference Scoring Batch Job

- [ ] Add `preference_score` Float column (default 0.0) to `food_items` + migration
- [ ] Add `preference_context` JSONB column to `food_items` + migration
       Format: `{"Healthy_North_Vegetarian": 2.3, "PCOS_South_Vegetarian": -1.0}`
       Key = `"{health_condition}_{region}_{diet_type}"`
- [ ] Write `scripts/update_preference_scores.py`:
       Reads `doctor_meal_overrides`, computes per-bucket score per food_item:
       `score = (chosen_count - rejected_count) / (chosen_count + rejected_count + 1)`
       Writes into `preference_context` JSONB
- [ ] Register batch job in APScheduler in `main.py` — weekly, Sunday 02:00 UTC
- [ ] Update `_find_food_item_single_diet()` in meal generator:
       Add `preference_score` as tertiary sort key after region_sort and cal_sort
       Read from `preference_context[patient_context_key]` for the current patient

### Patient Rating Integration

- [ ] Write `_load_patient_preferences(patient_id, session)` service:
       Returns `(soft_prefer_ids: set[int], soft_avoid_ids: set[int])`
       prefer = net rating ≥ +2, avoid = net rating ≤ -2
- [ ] Pass these sets into `user_data` dict in `diet_plans.py`
- [ ] Update generator: preferred items get LIMIT 15 candidate pool;
       avoided items excluded alongside `weekly_used_ids`

**Tier 1 total: 7 tasks**

---

## Tier 2 — ~3–6 Months Post-Launch (50+ Active Patients)

**Goal: Thompson Sampling bandit activates. System explores and exploits autonomously.**

### Context Bucket

The context vector hashed per patient:
```
health_condition    × medical_conditions_bucket × activity_level
× diet_type × age_bucket × gender × bmi_bucket × region
```
Gives ~46,000 theoretical buckets. Most will never be populated — algorithm handles
cold-start gracefully via uniform Beta(1,1) prior.

### Bandit Infrastructure

- [ ] Create `food_item_bandit_stats` DB model:
       `id`, `food_item_id`, `context_bucket_hash` (MD5 String 32),
       `context_label` (human-readable e.g. "Healthy_North_Veg_26-35_F_Normal"),
       `alpha` (Float, default 1.0), `beta` (Float, default 1.0), `last_updated`
- [ ] Add unique constraint `(food_item_id, context_bucket_hash)`
- [ ] Write Alembic migration
- [ ] Write `scripts/initialize_bandit_priors.py`:
       Seeds all observed (food_item_id × context) pairs with alpha=1, beta=1
- [ ] Write `app/services/bandit_service.py`:
       - `compute_context_hash(patient_profile) → str` — deterministic MD5
       - `thompson_sample(candidates, context_hash, session) → FoodItem`
         Fetches or creates bandit row per candidate, samples Beta(alpha, beta),
         returns highest-sampled candidate
       - `update_bandit(food_item_id, context_hash, reward, session)`
         alpha += reward; beta += (1 - reward)
- [ ] Write `scripts/run_bandit_update.py`:
       Reads new `doctor_meal_overrides` and `meal_ratings` since last run,
       computes rewards per event, calls `update_bandit()` for each
- [ ] Register bandit update job in APScheduler — nightly, 03:00 UTC
- [ ] Integrate `thompson_sample()` into `_find_food_item_single_diet()`:
       Replaces pure sort-based selection when bandit data exists for the context
- [ ] Add `BANDIT_ENABLED = False` feature flag to `app/core/config.py`
       Switch to True manually when data is sufficient (≥50 patients × 8 weeks)
- [ ] Add `BANDIT_MIN_SAMPLES = 20` config — minimum alpha+beta before bandit
       overrides rule-based selection for a given (food_item × context) pair

**Tier 2 total: 12 tasks**

---

## Implementation Timeline

```
Pre-launch        → Tier 0 (14 tasks): tables created, events start collecting
Month 1 (5+ drs)  → Tier 1 (7 tasks):  preference scores activate in generator
Month 3-6 (50+ p) → Tier 2 (12 tasks): Thompson Sampling bandit goes live
```

## Total: 33 tasks across 3 tiers

---

## What NOT to Do

- Do NOT correlate weight loss with individual food items — causal attribution is wrong
- Do NOT use ClinicalNote free text as a training signal (unstructured, needs NLP)
- Do NOT activate the bandit on fewer than 50 patients × 8 weeks of data
- Do NOT use full RLHF / PPO / policy gradient — requires GPU and dense interaction data
  that a 30-day meal cycle app will never generate per patient

---

## Data Retention Policy

`doctor_meal_overrides` and `meal_ratings` are permanent records.
Never purge them — they are the training corpus. Archive after 2 years to cold storage.

---

## Files to Modify When Implementing

| Tier | Files |
|---|---|
| 0 | `app/models/db_models.py`, new alembic migration, `app/routers/doctor.py`, `app/routers/progress.py`, `app/services/progress_service.py`, patient app meal card component |
| 1 | `scripts/update_preference_scores.py` (new), `app/main.py` (APScheduler), `app/services/meal_generator/meal_generator.py`, `app/services/diet_plan_service.py` |
| 2 | `app/models/db_models.py`, new alembic migration, `app/services/bandit_service.py` (new), `scripts/initialize_bandit_priors.py` (new), `scripts/run_bandit_update.py` (new), `app/main.py`, `app/core/config.py`, `app/services/meal_generator/meal_generator.py` |
