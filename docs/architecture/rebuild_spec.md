# Mityahar — Migration-Aware Rebuild Spec

**Version:** 1.1  
**Generated:** 2026-06-15 (post-Session 22F, pre-rebuild)  
**Source documents:** `docs/system_architecture.md` (all §), `BUILD_TRACKER.md`, `CLAUDE.md`  
**This document:** Authoritative spec for all future implementation sessions. Every session reads this before touching code. Do not alter product decisions (PD-1 through PD-10) — those are locked.

**Changelog:**
- **v1.1 (2026-06-15):** OQ-1 through OQ-5 resolved by product owner. Pin mechanism reframed from forced injection to preference signal + patient-app highlight. `doctor_meal_overrides` enriched with 3 new columns for clinical edit trail. Patient visibility model confirmed: patient always sees last approved plan, never a "pending" state. W3 pin guardrail removed (scenario cannot arise under new pin model). All open questions closed; no blocking decisions remain before R-0. **Post-R-0 additions (2026-06-16):** Eggetarian merged into Non-Vegetarian pool for `DIET_TYPE_HIERARCHY` (§3.3); pool exhaustion fallback now routes through Vegetarian pool before duplicating (§3.1); new §3.8 Bowl Size (PD-9) — S/M/L multipliers, `actual_calories` schema addition for R-1; `is_verified=True` filter added to generation pool query scope for R-2 (§3.2).
- **v1.0 (2026-06-15):** Initial draft.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Data Model Delta](#2-data-model-delta)
3. [Generation Layer Delta](#3-generation-layer-delta)
4. [Doctor Dashboard Delta](#4-doctor-dashboard-delta)
5. [Patient App Delta](#5-patient-app-delta)
6. [Weekly Cycle Orchestration (New Layer)](#6-weekly-cycle-orchestration-new-layer)
7. [Known Gaps: Rebuild vs Defer](#7-known-gaps-rebuild-vs-defer)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Open Questions for Product Owner](#9-open-questions-for-product-owner)

---

## 1. Executive Summary

### What the rebuild achieves

The current system generates one meal option per slot and serves it as a fixed weekly plan. The rebuild expands this to four pre-generated, calorie-equivalent combo options per slot per day (84 combos per patient per week), adds a doctor-approval gate before patient visibility, closes the patient-choice → next-week-personalization feedback loop, and builds the weekly cycle orchestration layer that is entirely absent today (`system_architecture.md §7.2`).

### What is NOT changing (reused layers)

| Layer | Why reused |
|-------|------------|
| Food item database (2143 recipes, slot_type taxonomy, nutrition chain) | Solid, tested across 22 sessions |
| Medical tagging infrastructure (4-layer architecture, GIN indexes, `tag_utils.py`) | Architecture sound; coverage gaps are data problems, not code problems |
| Pool queries + DIET_TYPE_HIERARCHY filter (22F Backlog B) | Correct and tested |
| Factor/scaled_calories math (`meal_generator.py:340-363`) | Correct; keep as-is per PD-8 |
| Slot template system (BREAKFAST_SLOTS, ONE_POT_SLOTS, `meal_templates` DB) | Reused per PD-6 |
| Medical tag filtering (avoid/prefer GIN queries, `meal_generator.py:601-621`) | Correct |
| Authentication & subscription lifecycle (JWT, MFA, token_1, daily crons) | Battle-tested |
| `patient_dish_preferences` pin/block mechanism | Reused; pin is injected at generation time across all 4 combos |
| `patient_meal_choices` + `patient_meal_choice_dishes` (22E Option B) | Schema reused; add one FK column |
| `doctor_meal_overrides` RL corpus | Append-only, untouched |

### What IS changing (rebuilt/new layers)

| Layer | Change |
|-------|--------|
| `recommendations` table | +2 columns: `generation_version`, `approval_status` |
| `weekly_combos` table | New — 84 rows/patient/week, replaces JSONB multi-combo storage |
| `weekly_patient_summary` table | New — doctor-visible week-end summary + personalization seed |
| `patient_meal_choices` | +1 nullable FK column: `weekly_combo_id` |
| Generation loop (`meal_generator.py`) | Runs slot selection 4× per slot; writes to `weekly_combos` |
| APScheduler | New weekly generation job (Saturday night) |
| Doctor API (`doctor.py`) | New endpoints: weekly plan view, combo edit, approve, summary |
| Doctor Dashboard UI | New: multi-combo plan view, approval button, weekly summary tab |
| Patient API (`meal_plan.py`) | `GET /meal-plan/week` returns `weekly_combos` for v2 patients |
| Patient App (`meals.tsx`) | New: 4-combo card view reading stored combos |
| Weekly cycle orchestration | Built from scratch (absent today, `system_architecture.md §7.2`) |

### Estimated session count

10 implementation sessions (R-0 through R-9). R-0 is a pre-rebuild data pass; R-1 through R-7 are the core rebuild; R-8 and R-9 are contract/cleanup phases. Sessions are scoped to 1–3 hours each based on prior session velocity.

### Biggest risk

**Doctor review bottleneck at scale.** If a doctor has 30 patients and auto-generation fires Saturday night, all 30 plans require approval before Monday morning meals are visible. There is currently no push notification mechanism for doctors (only patients have `fcm_token`). If the doctor doesn't open the dashboard over the weekend, patients see nothing. This is the single highest operational risk in the rebuild — it requires either (a) an email notification to doctors on plan generation, or (b) a patient-facing "plan pending doctor approval" state with a clear ETA. This is not an architectural problem but a workflow gap that must be addressed in R-3 (Doctor API) at minimum with a `GET /doctor/pending-approvals` endpoint.

---

## 2. Data Model Delta

### generation_version marker — design decision

**Options considered:**
1. `patients.generation_version` column — fails because one patient may have both v1 active plan and v2 plan being generated during migration
2. Check for existence of `weekly_combos` rows for a given `recommendation_id` — no explicit field, requires a JOIN to determine model version
3. `recommendations.generation_version` Integer column — one value per plan, lives on the table that holds the plan

**Chosen: Option 3.** `recommendations.generation_version` Integer NOT NULL DEFAULT 1. Value 1 = old single-combo JSONB model. Value 2 = new multi-combo `weekly_combos` model. Existing rows auto-default to 1 with no data migration needed. New-model generations write 2. Backward-compatible: v1 patients unaffected.

---

#### `recommendations`
**Status:** Modified  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:254`. Stores 21-entry JSONB in `meals` column. No approval state. One active plan per patient (`is_active=True`).  
**Target state:** Same structure, plus `generation_version` and `approval_status` columns. Existing `meals` JSONB untouched for v1 plans.  
**Delta:**
```
ADD COLUMN generation_version  INTEGER NOT NULL DEFAULT 1
ADD COLUMN approval_status     VARCHAR(20) NOT NULL DEFAULT 'approved'
  -- v1 plans default to 'approved' (they were always patient-visible)
  -- v2 plans start at 'draft'; doctor transitions to 'approved'
  -- CHECK constraint: approval_status IN ('draft', 'approved')
```
**Migration:** Phase 1. New columns with defaults — zero downtime. All existing `recommendations` rows auto-receive `generation_version=1, approval_status='approved'`. No backfill query needed; the defaults handle it.  
**Blocking dependency:** None. This is the first migration to run (R-1).

---

#### `weekly_combos` (new table)
**Status:** New  
**Current state:** Does not exist. Combo generation is on-demand via `GET /meal-plan/suggestions/{date}/{meal_type}` (`system_architecture.md §4.3`).  
**Target state:** Pre-generated combos, one row per combo, 84 rows per patient per week.

**Schema:**
```sql
CREATE TABLE weekly_combos (
    id                  SERIAL PRIMARY KEY,
    recommendation_id   INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    slot_date           DATE NOT NULL,
    meal_type           VARCHAR(20) NOT NULL,         -- 'Breakfast'|'Lunch'|'Dinner'
    combo_index         SMALLINT NOT NULL,             -- 0|1|2|3 (hard cap: 4 per slot)
    slot_composition    TEXT[] NOT NULL,              -- e.g. ['grain','dal_protein','sabzi','accompaniment']
    total_calories      NUMERIC(7,2) NOT NULL,        -- SUM(cal_per_serving) across dishes, unscaled (PD-8)
    dishes              JSONB NOT NULL DEFAULT '[]',  -- same shape as recommendations.meals[].dishes[]
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_weekly_combo UNIQUE (recommendation_id, slot_date, meal_type, combo_index),
    CONSTRAINT ck_combo_index CHECK (combo_index BETWEEN 0 AND 3),
    CONSTRAINT ck_meal_type CHECK (meal_type IN ('Breakfast', 'Lunch', 'Dinner'))
);

CREATE INDEX idx_wc_rec_date_meal
    ON weekly_combos (recommendation_id, slot_date, meal_type);

CREATE INDEX idx_wc_rec_id
    ON weekly_combos (recommendation_id);
```

**`dishes` JSONB shape (identical to existing `recommendations.meals[].dishes[]`, `system_architecture.md §1.2`):**
```json
[
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
    "ingredients": [{"name": "Ivy Gourd", "amount_g": 145.2}]
  }
]
```

**`slot_composition` field:** Derived from the slot template selected for this combo. Stored here so the patient app and doctor dashboard can render slot-type tags per dish without re-reading the template. Matches `BREAKFAST_SLOTS`, `ONE_POT_SLOTS`, or DB template `slots` field per `system_architecture.md §2.3`.

**Migration:** Phase 1 (additive, no existing rows affected). Phase 2: generation engine writes to this table for v2 plans. Phase 3: reads switch from `recommendations.meals` JSONB to this table. Phase 4: no cleanup needed for this table.  
**Blocking dependency:** `recommendations.generation_version` column must exist first (same R-1 session).

---

#### `weekly_patient_summary` (new table)
**Status:** New  
**Current state:** Does not exist. `system_architecture.md §7.2` confirms doctor weekly summary is NOT STARTED.  
**Target state:** One row per patient per week. Computed on-demand when doctor opens summary tab. Cached in JSONB to avoid recomputation.

**Schema:**
```sql
CREATE TABLE weekly_patient_summary (
    id                  SERIAL PRIMARY KEY,
    patient_id          INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recommendation_id   INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    week_start_date     DATE NOT NULL,
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary_data        JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT uq_wps_patient_week UNIQUE (patient_id, week_start_date)
);

CREATE INDEX idx_wps_patient_id ON weekly_patient_summary (patient_id);
```

**`summary_data` JSONB shape:**
```json
{
  "days_with_all_confirmed": 5,
  "total_slots": 21,
  "confirmed_slots": 17,
  "adherence_pct": 81.0,
  "per_day": [
    {
      "date": "2026-06-15",
      "breakfast_confirmed": true,
      "lunch_confirmed": true,
      "dinner_confirmed": false,
      "planned_calories": 1850,
      "confirmed_calories": 1230
    }
  ],
  "dish_frequency": [
    {
      "food_item_id": 276,
      "recipe_name": "Dondakkai Puli",
      "times_offered": 4,
      "times_selected": 3
    }
  ],
  "most_selected_dish": {"food_item_id": 276, "recipe_name": "...", "times_selected": 3},
  "least_selected_dish": {"food_item_id": 512, "recipe_name": "...", "times_selected": 0}
}
```

**Computation source query:**
```sql
-- Per-day confirmation status
SELECT 
    pmc.date,
    pmc.meal_type,
    pmc.calories AS confirmed_calories,
    wc.total_calories AS planned_calories,
    wc.combo_index AS selected_combo
FROM patient_meal_choices pmc
LEFT JOIN weekly_combos wc ON pmc.weekly_combo_id = wc.id
WHERE pmc.patient_id = :patient_id
  AND pmc.date BETWEEN :week_start AND :week_end;

-- Dish frequency
SELECT 
    pmcd.food_item_id,
    fi.recipe_name,
    COUNT(*) AS times_selected,
    (SELECT COUNT(*) FROM weekly_combos wc2
     JOIN weekly_combos wc3 ON wc3.recommendation_id = wc2.recommendation_id
     WHERE wc2.recommendation_id = :recommendation_id
       AND pmcd.food_item_id = ANY(
         SELECT (dish->>'food_id')::int FROM jsonb_array_elements(wc2.dishes) AS dish
       )
    ) AS times_offered
FROM patient_meal_choice_dishes pmcd
JOIN food_items fi ON fi.id = pmcd.food_item_id
JOIN patient_meal_choices pmc ON pmc.id = pmcd.choice_id
WHERE pmc.patient_id = :patient_id
  AND pmc.date BETWEEN :week_start AND :week_end
GROUP BY pmcd.food_item_id, fi.recipe_name;
```

**When computed:** On-demand when doctor calls `GET /doctor/patients/{id}/weekly-summary/{week_start}`. Result written to `weekly_patient_summary.summary_data` and cached. TTL: re-computed if week is not yet `completed` (current week's summary may change as patient confirms more meals).  
**Migration:** Phase 1 (additive).  
**Blocking dependency:** `weekly_combos` must exist. `patient_meal_choices.weekly_combo_id` FK must exist.

---

#### `patient_meal_choices`
**Status:** Modified (one column added)  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:690`. UNIQUE `(patient_id, date, meal_type)`. Parent row for confirmed combo; child table `patient_meal_choice_dishes` stores per-dish breakdown.  
**Target state:** Same structure plus `weekly_combo_id` FK to identify which of the 4 stored combos the patient selected.  
**Delta:**
```
ADD COLUMN weekly_combo_id  INTEGER REFERENCES weekly_combos(id) ON DELETE SET NULL
  -- Nullable: NULL for v1 legacy choices, populated for v2 choices
  -- SET NULL on delete: preserve choice record if combo is later edited
```
**Migration:** Phase 1 (additive). Existing rows remain with `weekly_combo_id = NULL`. When doctor queries weekly summary, NULL `weekly_combo_id` means v1 legacy patient — handled by legacy path.  
**Blocking dependency:** `weekly_combos` table must exist first.

---

#### `patient_meal_choice_dishes`
**Status:** Reused unchanged  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:710`. Stores per-dish breakdown for each confirmed combo. Added Session 22E (migration `d0e1f2a3b4c5`).  
**Target state:** No change. Schema already supports N dishes per choice (variable-length combo). `choice_id → patient_meal_choices`, `food_item_id → food_items (no CASCADE)`.  
**Why no change:** The 22E Option B child-table design already satisfies the v2 requirement. A v2 choice is still one `patient_meal_choices` row with N `patient_meal_choice_dishes` children.

---

#### `patient_dish_preferences`
**Status:** Reused unchanged  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:663`. Pin/block per `(patient_id, food_item_id)` pair. `preference_type IN ('pin', 'block')`.  
**Target state:** No schema change. Pin is now a **preference signal** at generation time — not a forced slot injection. Pinned dish IDs are moved to the front of the pool `ORDER BY` for that `slot_type` so they surface naturally in 1-2 of the 4 combos. If a pinned dish is unavailable (wrong `meal_time_tags`, conflicts with `avoid_tags`), it is silently skipped. No `combo_index_mask` column needed.  
**Response enrichment (read-time only):** When assembling the weekly-plan response, the API JOINs `patient_dish_preferences` to annotate each combo with `contains_doctor_pick: bool` and `pinned_dish_ids: list[int]`. These fields are computed, not stored in `weekly_combos`.

---

#### `meal_templates`
**Status:** Reused unchanged (shadowing behavior documented)  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:65`. 36 Breakfast templates still include `beverage: 0.10` slot (never reached). DB shadowed by in-code constants `BREAKFAST_SLOTS` and `ONE_POT_SLOTS` (`meal_generator.py:30-43`).  
**Target state:** No change per PD-6 ("Combo composition is determined by the slot template system, existing, reused as-is"). Shadow override behavior stays as-is.  
**Future:** Rationalize in a post-rebuild cleanup session. The in-code constants should eventually become the canonical source and the DB rows removed to eliminate the shadow confusion.

---

#### `doctor_meal_overrides`
**Status:** Modified  
**Current state:** `system_architecture.md §1.1`, `app/models/db_models.py:474`. Append-only RL training corpus. Logs what was changed but not why.  
**Target state:** Same append-only corpus; 3 columns added to capture clinical context so the recommendation engine can learn from doctor edits and progressively require less supervision.  
**Delta:**
```sql
ALTER TABLE doctor_meal_overrides
  ADD COLUMN patient_condition_snapshot  JSONB,
    -- {"conditions": ["Type 2 Diabetes"], "avoid_tags": ["avoid_diabetes"]}
    -- patient's medical_conditions + derived avoid_tags at edit time
  ADD COLUMN edit_reason                 VARCHAR(20) NOT NULL DEFAULT 'swap',
    -- CHECK: edit_reason IN ('swap', 'add', 'remove', 'custom_add')
  ADD COLUMN doctor_note                 TEXT;
    -- optional free-text clinical reasoning
```
**Migration:** Phase 1. Additive. `edit_reason` defaults to `'swap'` for existing rows. `patient_condition_snapshot` and `doctor_note` default to NULL.  
**Blocking dependency:** R-1 migration session.

---

## 3. Generation Layer Delta

**Status:** Modified (not replaced — pool queries, tagging, factor math reused)  
**Current entry point:** `POST /api/v1/diet-plans/generate` → `DietPlanService.generate_diet_plan()` (`diet_plan_service.py:48`) → `MealGenerator.generate_meal_plan()` (`meal_generator.py:121`). Full call chain at `system_architecture.md §2.1`.  
**Target entry point:** Same endpoint for doctor-triggered first-week generation. New APScheduler job calls `DietPlanService` directly for auto-generation.

---

### 3.1 Input change — 4 combos per slot

**Current loop** (`meal_generator.py:252-440`): 21 slots (7 days × 3 meal types). For each slot, one run of `_find_food_item()` per slot position.

**New loop:** Same outer structure. For each slot, run the slot-filling logic **4 times** (combo indices 0–3). On each run, exclude dishes already committed to prior combos for the same slot.

**Concrete mechanism:**
```python
# Per slot (per day × meal_type):
combo_slot_used_ids = set()        # resets at each new slot; grows across 4 combo runs
all_combos_for_slot = []

for combo_idx in range(4):          # PD-1: exactly 4 combos
    dishes = _fill_slot_dishes(
        slot_template=selected_slots,
        daily_used_ids=daily_used_ids,          # same as current — hard block across meal types
        weekly_used_ids=weekly_used_ids,        # same as current — cross-week variety
        extra_exclusion=combo_slot_used_ids,    # NEW — prevents repeat within the 4 combos
        ...
    )
    combo_slot_used_ids.update(d["food_id"] for d in dishes)
    all_combos_for_slot.append(dishes)

# After generating all 4 combos for this slot:
# Update weekly_used_ids with ONLY combo-0 dishes.
# Rationale: updating with all 4 combos would 4× expand the exclusion pool
# and exhaust variety faster. Combo-0 is the "primary" option.
weekly_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])
# daily_used_ids updated with combo-0 dishes to prevent same dish in Breakfast/Lunch/Dinner.
daily_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])
```

**Pool exhaustion fallback:** If Level 1 + Level 2 queries (`meal_generator.py:649-658`) both return empty (pool too small for 4 distinct combos), fall back to Vegetarian pool for remaining combos before duplicating. Duplication only if Vegetarian pool also exhausted. Log a warning. Do NOT fail generation.

---

### 3.2 Output change — write to `weekly_combos`, not JSONB

**Recommended approach:** Write 84 rows to `weekly_combos` table. Keep `recommendations.meals` JSONB as-is for v1 backward compatibility; do NOT write the 4-combo structure into it.

**Why not JSONB:** The JSONB approach would require `recommendations.meals` to become a 3-level nested array (`meals[21] → combos[4] → dishes[2-4]`). This makes per-combo edits (doctor PATCH), per-combo FK references (`patient_meal_choices.weekly_combo_id`), and per-combo queries (weekly summary aggregation) all significantly harder. A relational row-per-combo is queryable, FK-backed, and atomically editable.

**Write path:**
1. `generate_meal_plan()` returns `{"combos": [...84 combo dicts...], "ingredient_checklist": [...], "used_food_ids": [...]}` for v2 generation.
2. `DietPlanService.store_diet_plan()` (`diet_plan_service.py:67`) inserts the `Recommendation` row (with `generation_version=2`, `approval_status='draft'`) then bulk-inserts `weekly_combos` rows in a single transaction.
3. `recommendations.meals` is written as `[]` for v2 plans (empty, not null — backward compat).

**`is_verified` filter (R-2 scope):** Add `is_verified=True` to `base_stmt` pool query in `meal_generator.py`. Rationale: unverified dishes have unreviewed nutrition data. Once any doctor verifies a dish it is globally trusted across all patients. Suggestions endpoint already filters `is_verified=True` — generation must match.

---

### 3.3 Reused unchanged — explicit confirmation

| Component | Location | Reused unchanged |
|-----------|----------|-----------------|
| Base pool query with GIN tag filters | `meal_generator.py:606-621` | ✅ No modification |
| `DIET_TYPE_HIERARCHY` filter | `meal_plan.py:310-314` | Updated — Eggetarian merged into Non-Vegetarian pool. Non-Veg patients: pool queries pull `['Non-Vegetarian', 'Eggetarian']` first, fall back to Vegetarian on exhaustion. Do NOT duplicate dishes until even Vegetarian pool is exhausted. Apply in R-2. |
| `BREAKFAST_SLOTS` + `ONE_POT_SLOTS` constants | `meal_generator.py:30-43` | ✅ Slot templates per PD-6 |
| `meal_templates` DB query + fallback chain | `meal_generator.py:252-292` | ✅ Composition detection unchanged |
| Medical tag filtering (avoid/prefer) | `meal_generator.py:601-621` | ✅ All 4 combo runs use same tag filter |
| Diet-type fallback chain | `meal_generator.py:507-519` | ✅ Per-slot logic unchanged |
| Non-veg weekly budget allocation | `meal_generator.py:202-218` | ✅ Applied before combo loop |
| Factor/`scaled_calories` math | `meal_generator.py:340-363` | ✅ Per dish per combo |
| Pin preference weighting | `meal_generator.py:601-604` (prefer_sort) | ✅ Pinned dish IDs prepended to `prefer_sort` ORDER BY — surfaces in 1-2 combos naturally (see §3.4) |
| Allergy substring filter (`_pick()`) | `meal_generator.py:633-643` | ✅ Applied per combo run |
| `BLOCKLIST_PATTERNS` on protected slots | `meal_generator.py:563-565` | ✅ Applied per combo run |

---

### 3.4 Pin as preference signal (replaces forced injection)

**Old behavior (v1, `meal_generator.py:377-415`):** One pinned dish hard-injected per slot via `dishes.pop()` + `dishes.insert(0, pinned_dish)`. Removed in v2.

**New behavior (v2):** Pinned dish IDs are added to the `prefer_sort` ORDER BY for the relevant `slot_type` pool query, alongside the existing `prefer_tags` boost (`meal_generator.py:601-604`). This surfaces pinned dishes near the top of the pool so they naturally land in 1-2 of the 4 combos without forcing slot composition.

```python
# In _build_pool_query(), extend prefer_sort:
prefer_sort = or_(
    *[FoodItem.prefer_tags.contains([tag]) for tag in patient_prefer_tags],
    FoodItem.id.in_(pinned_food_ids_for_this_slot_type)  # NEW
).desc()
```

`pinned_food_ids_for_this_slot_type` = food_item_ids from `patient_dish_preferences` WHERE `preference_type='pin'` AND the pin's food_item `slot_type` matches the current slot. If a pinned dish fails the `avoid_tags` filter, the calorie window, or has wrong `meal_time_tags`, it simply doesn't surface — no injection, no error, no warning.

**Slot composition safety:** Since pins are never force-inserted, they cannot produce duplicate `slot_type` entries (e.g., two `main_dish` rows) or calorie-doubled slots. The amber >10% calorie divergence warning is retained for doctor PATCH combo-edit operations (manual edits can still produce divergence — that's intentional and surfaced to the doctor).

---

### 3.5 Doctor approval gate

**Mechanism:** `recommendations.approval_status` column (Section 2). New-model generations write `'draft'`. Patient-facing endpoints (`GET /meal-plan/week`) filter to only return combos where `recommendations.approval_status = 'approved'`.

**State transitions:**
- `'draft'` → `'approved'`: Doctor calls `PUT /doctor/patients/{id}/weekly-plan/{week_start}/approve` (R-3 new endpoint).
- `'approved'` → `'draft'`: Doctor can re-open (un-approve) while week has not yet started. Not needed after week goes active.
- No other transitions. `is_active` flag continues to indicate the current active week (unchanged).

---

### 3.6 Scheduling mechanism — APScheduler job

**Trigger:** Saturday night auto-generation for the following Sunday–Saturday week.

**Job spec:**
```python
# In app/main.py alongside existing daily cron jobs (app/main.py:157-179 area)
scheduler.add_job(
    func=auto_generate_weekly_plans,
    trigger="cron",
    day_of_week="sat",
    hour=21,       # 9pm UTC = Saturday ~2:30am IST (Sunday morning)
    minute=0,
    id="weekly_plan_generation",
    replace_existing=True,
)
```

**`auto_generate_weekly_plans()` logic:**
1. Query all patients where `subscription_status='active'` AND `doctor_id IS NOT NULL`.
2. For each patient: check if a `recommendations` row already exists for next week (`week_start_date = next_sunday`). Skip if yes.
3. If no plan exists: call `DietPlanService.generate_diet_plan()` with `generation_version=2`. Write `approval_status='draft'`.
4. Exception handling: catch per-patient errors, log, continue to next patient. A single patient failure does not abort the job.
5. First week exception: if a patient has zero recommendations, skip auto-generation (first week must be doctor-triggered per PD-2).

**If doctor hasn't approved previous week:** Auto-generate next week anyway (OQ-2 resolved). The new week is in `'draft'` state. Doctor now has two pending approvals. `GET /doctor/pending-approvals` surfaces both. No auto-approval timeout — doctor must explicitly approve. Patient continues seeing the previous approved plan (OQ-3 fallback rule).

---

### 3.7 Personalization seed (PD-4)

**Concrete mechanism:**

At next-week generation start, query the previous week's patient choices:
```sql
SELECT 
    pmcd.food_item_id,
    COUNT(*) AS times_selected,
    (
        SELECT COUNT(DISTINCT wc2.id) 
        FROM weekly_combos wc2
        WHERE wc2.recommendation_id = :prev_recommendation_id
          AND EXISTS (
            SELECT 1 FROM jsonb_array_elements(wc2.dishes) d
            WHERE (d->>'food_id')::int = pmcd.food_item_id
          )
    ) AS times_offered
FROM patient_meal_choice_dishes pmcd
JOIN patient_meal_choices pmc ON pmc.id = pmcd.choice_id
WHERE pmc.patient_id = :patient_id
  AND pmc.date BETWEEN :prev_week_start AND :prev_week_end
GROUP BY pmcd.food_item_id;
```

**Result processing:**
```python
preferred_food_ids = {
    row.food_item_id 
    for row in results 
    if row.times_selected >= 2  # selected 2+ times = preferred
}
avoided_food_ids = {
    row.food_item_id 
    for row in results 
    if row.times_offered >= 3 and row.times_selected == 0  # offered 3+ times, never selected
}
```

**How these feed into generation:**
- `preferred_food_ids` → added to `prefer_sort` ORDER BY in base pool query (alongside existing `prefer_tags` boost from `meal_generator.py:601-604`):
  ```python
  prefer_sort = or_(
      *[FoodItem.prefer_tags.contains([tag]) for tag in patient_prefer_tags],
      FoodItem.id.in_(preferred_food_ids)   # new: patient-choice boost
  ).desc()
  ```
- `avoided_food_ids` → added to Level 1 exclusion alongside `weekly_used_ids` (soft exclusion — may still appear if Level 1 pool is exhausted and Level 2 fallback runs):
  ```python
  level1_exclusion = weekly_used_ids | avoided_food_ids  # set union
  ```

No schema changes required beyond `patient_meal_choices.weekly_combo_id` (already in Section 2).

---

### 3.8 Bowl Size (PD-9, now active)

- Patient selects S/M/L when confirming a combo.
- Fixed multipliers: S=0.7×, M=1.0×, L=1.3× of `cal_per_serving`.
- `actual_calories = bowl_multiplier × cal_per_serving`, stored on `patient_meal_choices`.
- System nudges patient toward medium if consistently eating large or small (app-level nudge only — no auto-TDEE adjustment).
- Doctor sees planned vs actual calorie graph in weekly summary tab (R-4).
- Personalization seed (R-7) uses `actual_calories`, not `planned_calories`.
- Schema impact: `patient_meal_choices` gains `bowl_size VARCHAR(6)` and `actual_calories NUMERIC` — add to R-1 migration scope.
- Sessions impacted: R-1 (schema), R-5 (API), R-6 (app), R-4 (doctor graph), R-7 (seed).

---

## 4. Doctor Dashboard Delta

**Status:** Modified — existing controls reused; new: multi-combo view, approval flow, weekly summary tab.

---

### 4.1 New API endpoints (all in `app/routers/doctor.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/doctor/patients/{id}/weekly-plan/{week_start}` | Returns 4 combos per slot. `week_start` = ISO date (Sunday). v1 fallback: returns existing `GET /patients/{id}/plan` data. |
| `PUT` | `/doctor/patients/{id}/weekly-plan/{week_start}/approve` | Transitions `recommendations.approval_status = 'approved'`. Patient can now see the week. |
| `PATCH` | `/doctor/patients/{id}/weekly-plan/{week_start}/combos/{combo_id}` | Swap/remove/add a dish within a specific combo. Edits `weekly_combos.dishes` JSONB. Writes `DoctorMealOverride`. Recalculates `weekly_combos.total_calories`. |
| `POST` | `/doctor/patients/{id}/weekly-plan/generate` | Doctor manually triggers first-week generation (PD-2). Body: `{"week_start": "2026-06-22"}`. |
| `GET` | `/doctor/patients/{id}/weekly-summary/{week_start}` | Returns `weekly_patient_summary.summary_data`. Computes and caches if not yet computed. |
| `GET` | `/doctor/pending-approvals` | Lists all patients whose latest `recommendations` has `approval_status='draft'`. For doctor dashboard notification/badge. |

**Response shape for `GET /doctor/patients/{id}/weekly-plan/{week_start}`:**
```json
{
  "recommendation_id": 42,
  "generation_version": 2,
  "approval_status": "draft",
  "week_start": "2026-06-22",
  "days": {
    "2026-06-22": {
      "Breakfast": {
        "slot_composition": ["main_dish", "accompaniment"],
        "combos": [
          {"combo_id": 101, "combo_index": 0, "total_calories": 412.3, "contains_doctor_pick": true, "pinned_dish_ids": [185], "dishes": [...]},
          {"combo_id": 102, "combo_index": 1, "total_calories": 408.7, "contains_doctor_pick": false, "pinned_dish_ids": [], "dishes": [...]},
          {"combo_id": 103, "combo_index": 2, "total_calories": 415.0, "contains_doctor_pick": false, "pinned_dish_ids": [], "dishes": [...]},
          {"combo_id": 104, "combo_index": 3, "total_calories": 410.2, "contains_doctor_pick": false, "pinned_dish_ids": [], "dishes": [...]}
        ]
      },
      "Lunch": { ... },
      "Dinner": { ... }
    }
  }
}
```

---

### 4.2 Reused unchanged — explicit confirmation

| Component | Endpoint | Status |
|-----------|----------|--------|
| Pin mechanism | `POST /doctor/patients/{id}/dishes/pin` | ✅ Reused; pin now acts as preference signal — dish surfaces in 1-2 combos naturally via pool ordering boost, not forced injection |
| Block mechanism | `POST /doctor/patients/{id}/dishes/block` | ✅ Reused; blocks from all 4 combos (hard exclusion unchanged) |
| TDEE split override | `PATCH /doctor/patients/{id}/meal-config` | ✅ Reused unchanged |
| Amber divergence warning | `PlanTab.tsx` — `|Total - Target| / Target > 10%` | ✅ Reused; W3 guardrail added via §3.4 |
| Custom dish submission | `POST /doctor/patients/{id}/plan/meals/{date}/{meal_type}/add` | ✅ Reused for v1; v2 uses combo-level PATCH |
| Recipe tagging | `PATCH /doctor/recipes/{id}/tags` | ✅ No change |
| Doctor meal overrides (RL corpus) | `doctor_meal_overrides` table | ✅ Written by combo PATCH endpoint |

**Note:** The existing `PATCH /patients/{id}/plan/meals/{date}/{meal_type}/dishes/{dish_index}` endpoint (dish-level edit on `recommendations.meals` JSONB) is **retained for v1 patients**. v2 patients use the new `PATCH /weekly-plan/.../combos/{combo_id}` endpoint. Version detection in the frontend is via `recommendation.generation_version`.

---

### 4.3 Approval flow

**Granularity:** Doctor approves the entire week at once (not per meal type, not per day). PD-2 says "doctor reviews the full week before patient sees it." One `PUT /approve` call transitions the entire `recommendations` row.

**State transition on approval:**
1. Set `recommendations.approval_status = 'approved'`.
2. Patient immediately sees the plan (no other trigger needed — patient's `GET /meal-plan/week` checks `approval_status`).
3. No Firebase push to patient at approval time (patient polls on app open). Push can be added in a later session.

**UI requirement for R-4:** Doctor dashboard needs a prominent "Approve Week" button on the weekly plan view, disabled until doctor has opened and viewed all 3 meal types. A "pending approvals" badge on the patient list shows how many patients have draft plans.

---

### 4.4 Weekly summary tab

**Data fields shown to doctor:**
- Per-day: confirmed / not confirmed for each of Breakfast/Lunch/Dinner (7×3 grid)
- Per-day: planned calories vs confirmed calories (from `patient_meal_choices.calories`)
- Overall adherence %: `confirmed_slots / total_slots × 100`
- Most selected dish this week (food_item_id, recipe_name, N times selected)
- Least selected dish (food_item_id, recipe_name, 0 or 1 times)
- Dish frequency table: all dishes offered, with times_offered and times_selected columns
- Next-week personalization preview: "Preferred this week" (boosted next week) and "Avoided this week" (softly excluded next week)

**Endpoint:** `GET /doctor/patients/{id}/weekly-summary/{week_start}` (Section 4.1)

**UI location:** New "Weekly Summary" tab on `PatientDetail.tsx`, alongside existing Plan / Activity / Notes / Visits / Meal Config tabs.

---

## 5. Patient App Delta

**Status:** Modified — confirm-choice flow reused; week view changes; suggestions endpoint becomes legacy/fallback.

---

### 5.1 New: week view (4 combos per slot)

**Current screen:** `meals.tsx` — for today/future slots, renders `SuggestionSlot` which calls `GET /meal-plan/suggestions/{date}/{meal_type}` on-demand, renders `ComboCard` components (`system_architecture.md §6.2`).

**Target screen:** For v2 patients, `GET /meal-plan/week` now returns combos pre-stored in `weekly_combos`. The week view reads these stored combos instead of calling the suggestions endpoint.

**Updated `GET /meal-plan/week` response (version-adaptive):**
```json
{
  "generation_version": 2,
  "approval_status": "approved",
  "2026-06-22": {
    "Breakfast": {
      "slot_composition": ["main_dish", "accompaniment"],
      "combos": [
        {"combo_id": 101, "combo_index": 0, "total_calories": 412.3, "contains_doctor_pick": true, "pinned_dish_ids": [185], "dishes": [...]}
      ],
      "confirmed_combo_id": null  
    }
  }
}
```

For v1 patients (`generation_version: 1`), response shape unchanged (no `combos` key). Patient app checks `generation_version` at top level of response to determine which view to render.

**`meals.tsx` changes for v2:**
- Remove the `GET /suggestions` call from `SuggestionSlot` for v2 patients.
- Render `ComboCard[]` directly from `weekData[date][mealType].combos` (already stored in week response).
- `ComboCard` already exists from Session 22F (`system_architecture.md §6.2`). Updates: (1) add `combo_id` to the select action for `confirm-choice` payload; (2) render "Doctor's pick" badge when `contains_doctor_pick=true`; (3) optionally highlight the specific dish in `pinned_dish_ids` within the combo card.

**For future days (not yet `today`):** Patient can see and select combos for upcoming days. Selection is allowed (PD-3: "The week is fixed once the doctor approves it" — patient can pre-select). `patient_meal_choices.date` records the actual date.

---

### 5.2 Reused unchanged — confirm-choice flow

**`POST /meal-plan/confirm-choice`** (`meal_plan.py`, added Session 22E): Accepts `food_item_ids: list[int]`. Upserts parent `patient_meal_choices` row + child `patient_meal_choice_dishes` rows atomically. `system_architecture.md §4.3`.

**Delta for v2:** Add `weekly_combo_id: int | null` to request body. When provided, set `patient_meal_choices.weekly_combo_id = weekly_combo_id`. Existing logic (delete-then-insert atomicity, blocked-dish check) unchanged.

**Why confirm-choice schema stays intact:** The child table already holds all dish food_item_ids. `weekly_combo_id` is purely a pointer for analytics (which of the 4 combos was chosen). The calorie math path (`patient_meal_choices.calories = sum(food_items.cal_per_serving)`) is unchanged.

---

### 5.3 Legacy fallback (v1 patients)

Patients with `recommendations.generation_version = 1` continue using the current flow:
- `GET /meal-plan/week` returns existing JSONB structure (no `combos` key).
- Patient sees `SuggestionSlot` with on-demand `GET /suggestions/{date}/{meal_type}` call.
- `ComboCard` renders suggestions as before.
- `POST /confirm-choice` works without `weekly_combo_id`.

**Detection:** `GET /meal-plan/week` response top-level field `generation_version`. Patient app checks:
```typescript
if (weekResponse.generation_version === 2 && weekResponse.approval_status === 'approved') {
  // render stored combos from weekResponse[date][mealType].combos
} else if (weekResponse.generation_version === 1) {
  // existing SuggestionSlot → GET /suggestions flow
}
// No 'pending' branch: patient always sees the last approved plan.
// If no approved plan exists for current week, endpoint falls back to most
// recent approved plan regardless of week boundary (OQ-3 resolution).
```

**Fallback rule (OQ-3):** `GET /meal-plan/week` filters by `approval_status='approved' AND is_active=True`. If no approved plan exists for the current week (doctor hasn't approved yet), the endpoint falls back to the most recent approved plan for this patient regardless of its `week_start_date`. This ensures the Meals tab is never empty for a patient with at least one approved plan. Only a brand-new patient with zero approved plans ever sees the empty state — in that case, show "Your doctor is setting up your meal plan" (one-time, not a recurring state).

---

### 5.4 Suggestions endpoint fate (PD-10 + recommendation)

**Current:** `GET /meal-plan/suggestions/{date}/{meal_type}` (Session 22F). On-demand combo building. Returns up to 4 combos.

**Recommendation:** Keep as option (b) — **"refresh my options" premium feature** — rather than retiring.

**Rationale:**
- v1 patients need it as their primary meal selection path until migrated.
- v2 patients may eventually want "I don't like any of these 4, show me more" — this is a natural upgrade from the stored-combo model.
- The 22F implementation is already correct (diet-type filter, slot composition detection, round-robin construction). Retiring and rebuilding later is wasteful.
- Rename conceptually to "refresh options" in the doctor dashboard controls (doctor can allow/disallow per patient if needed).

**What changes:** For v2 patients, this endpoint becomes secondary (not called on initial render). It's invoked only if patient explicitly requests "show more options" — a UI affordance to be added in a later session (not in scope of this rebuild).

---

## 6. Weekly Cycle Orchestration (New Layer)

This layer does not exist today (`system_architecture.md §7.2`).

---

### 6.1 State machine

```
UNSTARTED → GENERATING → DRAFT → APPROVED → ACTIVE → COMPLETED
```

**State definitions:**
- `UNSTARTED`: No `recommendations` row for this week for this patient.
- `GENERATING`: Background task running (ephemeral — no DB state, just async task).
- `DRAFT`: `recommendations` row exists, `generation_version=2`, `approval_status='draft'`. Patient cannot see plan.
- `APPROVED`: `approval_status='approved'`. Patient can see and select combos.
- `ACTIVE`: `is_active=True` AND current date is within the week range. Patient is actively selecting.
- `COMPLETED`: Week has passed. `is_active` set to False by cron. `weekly_patient_summary` computed.

---

### 6.2 State transitions

#### UNSTARTED → GENERATING → DRAFT

**First week (doctor-triggered, PD-2):**
- Trigger: Doctor calls `POST /doctor/patients/{id}/weekly-plan/generate`
- Code: `DietPlanService.generate_diet_plan()` called with `generation_version=2` flag
- DB: INSERT `recommendations` (approval_status='draft', generation_version=2) + 84 `weekly_combos` rows, in one transaction
- Doctor sees: plan in `GET /doctor/patients/{id}/weekly-plan/{week_start}` with `approval_status='draft'`
- Patient sees: nothing (approval_status='draft')

**Subsequent weeks (auto-triggered, PD-2):**
- Trigger: APScheduler cron job (Saturday 9pm UTC)
- Code: `auto_generate_weekly_plans()` iterates active patients, calls `DietPlanService` per patient
- DB: Same as above
- Doctor sees: new `GET /doctor/pending-approvals` shows this patient
- Patient sees: nothing until approved

#### DRAFT → APPROVED

- Trigger: Doctor calls `PUT /doctor/patients/{id}/weekly-plan/{week_start}/approve`
- Code: UPDATE `recommendations SET approval_status='approved'` WHERE id=:rec_id
- DB: Single row update, immediate commit
- Doctor sees: plan status changes from "Pending" to "Approved" in UI
- Patient sees: `GET /meal-plan/week` now returns combos (approval_status check passes). Before approval, patient sees the previous week's approved plan (OQ-3 fallback).

#### APPROVED → ACTIVE

- Trigger: Calendar date enters the `week_start_date`..`week_start_date+6` range
- Code: No explicit trigger needed — `GET /meal-plan/week` derives this from the date
- DB: No state change — `is_active=True` was set at generation time
- Doctor sees: plan shows "Active Week" indicator
- Patient sees: today's combos are actionable (can select/confirm)

#### ACTIVE → COMPLETED

- Trigger: APScheduler cron job (Sunday morning, at week-end)
- Code: `complete_expired_plans()` — new cron job alongside existing token-expiry job:
  ```python
  scheduler.add_job(
      func=complete_expired_plans,
      trigger="cron",
      day_of_week="sun",
      hour=1,    # 1am UTC = early Sunday morning
      minute=0,
      id="complete_weekly_plans",
  )
  ```
- DB: UPDATE `recommendations SET is_active=False` WHERE `week_start_date + 7 <= today()` AND `is_active=True`
- Also: Compute `weekly_patient_summary` for completed weeks (or defer until doctor requests — see §6.3)
- Doctor sees: completed week moved to history; new week (if auto-generated) shows as pending approval
- Patient sees: `GET /meal-plan/week` returns next week's plan (if approved) or "plan pending" state

---

### 6.3 Weekly summary computation

**When:** On-demand when doctor calls `GET /doctor/patients/{id}/weekly-summary/{week_start}`. Cache result in `weekly_patient_summary.summary_data`. Re-compute if the week is still `ACTIVE` (patient may confirm more meals after first doctor view).

**Personalization handoff (PD-4 concrete data flow):**
1. Week N completes (Sunday morning cron or doctor queries summary).
2. Summary query (Section 2, `weekly_patient_summary` schema) runs, produces `dish_frequency[]`.
3. Result written to `weekly_patient_summary.summary_data`.
4. Week N+1 generation (Saturday night cron) reads previous summary:
   ```python
   prev_summary = await db.execute(
       select(WeeklyPatientSummary)
       .where(WeeklyPatientSummary.patient_id == patient_id)
       .order_by(WeeklyPatientSummary.week_start_date.desc())
       .limit(1)
   )
   dish_freq = prev_summary.summary_data.get("dish_frequency", [])
   preferred_food_ids = {r["food_item_id"] for r in dish_freq if r["times_selected"] >= 2}
   avoided_food_ids   = {r["food_item_id"] for r in dish_freq if r["times_offered"] >= 3 and r["times_selected"] == 0}
   ```
5. These sets are passed to `MealGenerator.generate_meal_plan()` and applied per §3.7.

---

### 6.4 Error states

| Error | Handling |
|-------|---------|
| Generation fails mid-week (exception in APScheduler job) | Log error per patient, continue job for other patients. Patient stays in UNSTARTED. Doctor's `GET /pending-approvals` does NOT show this patient (no DRAFT row). Doctor must manually trigger via dashboard. |
| Doctor never approves | Patient remains in DRAFT state indefinitely. No automatic approval. Patient sees "plan pending" state. After N days (product owner decision, likely 2 days), send reminder email to doctor. Not in rebuild scope — flag for operational runbook. |
| Patient never confirms any meal all week | Week completes normally at ACTIVE → COMPLETED. `weekly_patient_summary` records `confirmed_slots=0, adherence_pct=0`. No personalization seed generated (empty `preferred_food_ids`, empty `avoided_food_ids`). Next week generates fresh with only standard preference/avoidance signals. |
| Auto-generation collision (two jobs fire for same patient) | `UNIQUE (patient_id, week_start_date)` constraint on... wait — `recommendations` has no such constraint currently. Recommend adding: `CREATE UNIQUE INDEX uq_rec_patient_week ON recommendations (patient_id, week_start_date) WHERE generation_version = 2`. APScheduler is single-process so collision is low-risk, but the index provides safety. |

---

## 7. Known Gaps: Rebuild vs Defer

### Resolved by rebuild

| Gap | How resolved |
|-----|-------------|
| Doctor weekly summary — NOT BUILT (`system_architecture.md §5.3`) | `weekly_patient_summary` table + doctor API endpoint built in R-3 |
| Patient choice → plan feedback loop — NOT BUILT (`system_architecture.md §7.2`) | `patient_meal_choices.weekly_combo_id` + personalization seed mechanism in §3.7 |
| Auto-plan generation not weekly (`system_architecture.md §7.2`) | APScheduler weekly job in §3.6 |
| Multi-combo patient interface (suggestions as primary, not pre-stored) | v2 patient app reads stored `weekly_combos` in R-6 |
| Budget ring not adaptive (`system_architecture.md §7.2`) | `calories_remaining_today` via confirm-choice; combo pre-sized at generation. Full adaptive sizing (resize combos to remaining budget) is a future session — current combos are all calorie-equivalent per PD-8. |

### Addressed alongside rebuild (bundle in R-0 pre-rebuild pass)

| Gap | Bundle in |
|-----|----------|
| Backlog A: ~27 biryani/pulao missing `avoid_diabetes` (`system_architecture.md §3.3`, §8) | R-0: dedicated tagging pass |
| 7 test artifact food_items (IDs 3698–3716 "Doctor2 Private Dal") (`system_architecture.md §8`) | R-0: manual DB cleanup |
| W3 pin guardrail missing (`system_architecture.md §5.3`) | R-2: 5-line guard in `_inject_pinned_dishes()` |
| `confirm-choice` lacks `meal_time_tags` validation (`system_architecture.md §4.3`, §8) | R-5: add `meal_time_tags` check when `weekly_combo_id` is present (v2 only) |

### Deferred — schedule after rebuild

| Gap | Reason for deferral |
|-----|---------------------|
| 582 recipes with bad `quantity_g` (`system_architecture.md §8`) | Data quality pass — independent of rebuild. Doesn't block any rebuild session. |
| Dish rename script 22% done (`system_architecture.md §8`) | Operational, checkpointed, safe to resume anytime. |
| Ingredient deduplication (`system_architecture.md §8`) | Data quality — Layer 3 derivation is correct despite duplicates. Cosmetic issue only. |
| Beverage data errors (id 591, 2447) (`system_architecture.md §8`) | Hidden by `cal < 300` guard. Fix data in situ — 2 rows, 1 SQL update. |
| `meal_templates` rationalization | Post-rebuild cleanup when shadow override behavior can be replaced cleanly. |
| Pre-existing TypeScript errors (`system_architecture.md §8`) | PlanTab.tsx:888 `meal.id`, Recipes.tsx `submit_to_global`. Fix in R-4 (doctor UI session) as a zero-cost bundling. |

### Deferred — no plan yet

| Gap | Notes |
|-----|-------|
| Allergy substring match weak (`system_architecture.md §8`) | Needs compound allergen mapping ("Dairy / Lactose" → ["milk", "curd", "paneer", ...]). Design session needed. |
| `avoid_pcos` / `avoid_gout` — 0 food_items (`system_architecture.md §3.1`) | Requires LLM tagging pass for PCOS/Gout-relevant dishes. Data effort, not architecture. |
| Portion size selector (PD-9) | Explicitly deferred per PD-9. Additive when built. |
| Rating-driven personalization (`system_architecture.md §7.2`) | Phase 8 Tier 0. Data collection ongoing. Algorithm TBD. |
| `plan_type_tags` rationalization (`system_architecture.md §1.2`) | Currently a no-op filter (all 2143 share same tags). Remove or repurpose. Design session needed. |
| Water/steps native health sync (`system_architecture.md §6.3`) | HealthKit / Health Connect. Platform integration project, independent. |
| Doctor app (mobile) for push notifications | Not in scope. Doctor currently web-only. Operational risk noted in §1. |

---

## 8. Implementation Roadmap

### Session R-0 — Pre-Rebuild Data Pass
**Status:** ✅ COMPLETE — 2026-06-16. See BUILD_TRACKER.md "R-0 — Pre-Rebuild Data Pass (COMPLETE)" for full detail. Note: actual scope executed deviated from this spec in two ways — (1) 30 dishes tagged (not ~27) after clinical review of ambiguous cases, 12 dishes intentionally exempted as low-GI; (2) test artifact rows 3698–3716 were NOT deleted (session command explicitly overrode the DELETE below) — 13/19 confirmed unreachable, but 6 ("Doctor2 Private Dal") were found reachable by `meal_generator.py`'s pool query (missing `is_verified` filter) — a new gap for R-2 to consider.
**Depends on:** Nothing (safe to run any time)  
**Type:** Data-pass  
**Scope:** Fix the 27 biryani/pulao dishes missing `avoid_diabetes` (Backlog A). Clean 7 test artifact food_items. These are data problems that must be resolved before generation produces medically safe results for diabetic patients.  
**Reuses from current system:** `scripts/derive_recipe_tags.py` logic, `tag_utils.py` tag constants, direct DB queries.  
**Produces:** SQL script or Python script that: (a) adds `avoid_diabetes` to ~27 biryani/pulao `food_items.avoid_tags`; (b) DELETEs food_items IDs 3698–3716 (test artifacts with empty `meal_time_tags`).  
**Verification:** `SELECT count(*) FROM food_items WHERE recipe_name ILIKE '%biryani%' OR recipe_name ILIKE '%pulao%' AND NOT (avoid_tags @> '["avoid_diabetes"]')` returns 0. `SELECT count(*) FROM food_items WHERE id BETWEEN 3698 AND 3716` returns 0.  
**Do not start until:** Nothing. Run first.

---

### Session R-1 — Schema Expansion (Phase 1)
**Depends on:** R-0 complete  
**Type:** Implementation (migrations only, no logic changes)  
**Scope:** Write and run 4 Alembic migrations: (1) add `generation_version` + `approval_status` to `recommendations`; (2) create `weekly_combos` table; (3) create `weekly_patient_summary` table and add `weekly_combo_id` to `patient_meal_choices`; (4) add `patient_condition_snapshot`, `edit_reason`, `doctor_note` to `doctor_meal_overrides`. All additive — existing rows unaffected.  
**Reuses from current system:** Existing Alembic setup, existing ORM in `app/models/db_models.py`.  
**Produces:** 4 migration files (`alembic/versions/`), 3 new ORM model classes (`WeeklyCombo`, `WeeklyPatientSummary`, updated `PatientMealChoice`), updated `DoctorMealOverride` ORM model with 3 new columns. Schema verified with `alembic upgrade head`.  
**Verification:** `SELECT column_name FROM information_schema.columns WHERE table_name='recommendations'` includes `generation_version` and `approval_status`. `SELECT to_regclass('weekly_combos')` returns non-null. `SELECT column_name FROM information_schema.columns WHERE table_name='doctor_meal_overrides'` includes `edit_reason`. Existing `recommendations` rows have `generation_version=1, approval_status='approved'`.  
**Do not start until:** R-0 complete (to avoid tagging migration running against stale data).

---

### Session R-2 — Generation Layer (4 combos + W3 guardrail)
**Depends on:** R-1 complete  
**Type:** Implementation  
**Scope:** Modify `MealGenerator.generate_meal_plan()` to produce 4 combos per slot. Add `combo_slot_used_ids` accumulation logic. Replace pin injection logic with preference-signal pool boost (pinned dish IDs prepended to `prefer_sort` ORDER BY per §3.4). Modify `DietPlanService.store_diet_plan()` to bulk-insert `weekly_combos` rows. Set `generation_version=2, approval_status='draft'` on new-model recommendations.  
**Reuses from current system:** All pool queries (`meal_generator.py:567-660`), slot template system (`meal_generator.py:252-292`), factor math (`meal_generator.py:340-363`), `DIET_TYPE_HIERARCHY` (extend from suggestions-only to generation pool queries), all tag filter logic.  
**Produces:** Modified `meal_generator.py`, modified `diet_plan_service.py`, modified `diet_plans.py` (validation update: 21 slots still correct, 84 combos NEW). Tested via `POST /diet-plans/generate` for Priya — confirms 84 `weekly_combos` rows in DB, `generation_version=2`, `approval_status='draft'`.  
**Verification:** `SELECT count(*) FROM weekly_combos WHERE recommendation_id=:new_rec_id` = 84. `SELECT count(DISTINCT slot_date, meal_type, combo_index) FROM weekly_combos WHERE recommendation_id=:new_rec_id` = 84. All combo_index values 0-3 present for each (slot_date, meal_type). No dish appears twice within the same (recommendation_id, slot_date, meal_type) group.  
**Do not start until:** R-1 complete (tables must exist before INSERT).

---

### Session R-3 — Doctor API (weekly plan + approval + summary)
**Depends on:** R-2 complete  
**Type:** Implementation  
**Scope:** Add 6 new endpoints to `doctor.py`: weekly plan view, approve, combo edit PATCH, generate trigger, weekly summary, pending approvals. Add APScheduler weekly generation job. Add `complete_expired_plans()` cron. Personalization seed query (reads `weekly_patient_summary` for prior week). Combo edit PATCH must write `patient_condition_snapshot`, `edit_reason`, and optional `doctor_note` to `doctor_meal_overrides` (R-1 columns). Weekly plan view response JOIN with `patient_dish_preferences` to populate `contains_doctor_pick` and `pinned_dish_ids` per combo.  
**Reuses from current system:** `DietPlanService`, existing auth/JWT middleware, `DoctorIsolationMiddleware`, `DoctorMealOverride` write path in existing PATCH endpoint.  
**Produces:** 6 new doctor endpoints, 2 new APScheduler jobs, modified `DietPlanService.generate_diet_plan()` to accept `personalization_seed` param.  
**Verification:** Call `POST /doctor/patients/{priya_id}/weekly-plan/generate` → 200, 84 `weekly_combos` rows. Call `GET /doctor/patients/{priya_id}/weekly-plan/{week_start}` → 4 combos per slot. Call `PUT /doctor/.../approve` → `approval_status='approved'`. Call `GET /doctor/.../weekly-summary/{week_start}` → summary_data non-empty (even if adherence 0% since no choices yet).  
**Do not start until:** R-2 complete (generation must write weekly_combos before doctor can view them).

---

### Session R-4 — Doctor Dashboard UI (multi-combo view + approval)
**Depends on:** R-3 complete  
**Type:** Implementation  
**Scope:** Update `PlanTab.tsx` to render 4 combo cards per slot for v2 patients. Add "Approve Week" button. Add "Weekly Summary" tab. Add "Pending Approvals" badge on patient list. Fix pre-existing TypeScript errors (`PlanTab.tsx:888`, `Recipes.tsx submit_to_global`).  
**Reuses from current system:** Existing `PatientDetail.tsx` tab structure, existing `DishCard` component, existing `RecipeSearchModal`, React Query hooks.  
**Produces:** Updated `PlanTab.tsx`, updated `PatientDetail.tsx` (new tab), new `WeeklySummaryTab.tsx`, updated patient list with pending badge.  
**Verification:** Browser E2E — open doctor dashboard, navigate to Priya's Plan tab, confirm 4 combo cards visible for each slot. Click "Approve Week" → page refreshes with approval_status='approved'. Navigate to Weekly Summary tab — summary data renders.  
**Do not start until:** R-3 complete (API endpoints must exist for UI to call).

---

### Session R-5 — Patient API (week view v2 + confirm-choice update)
**Depends on:** R-3 complete (approval endpoint needed before patient can see anything)  
**Type:** Implementation  
**Scope:** Update `GET /meal-plan/week` to return `weekly_combos` data for v2 patients (check `generation_version`). Add fallback to most-recent approved plan when current week has no approved plan (OQ-3). Response assembly JOINs `patient_dish_preferences` to populate `contains_doctor_pick` and `pinned_dish_ids` per combo. Update `POST /meal-plan/confirm-choice` to accept optional `weekly_combo_id` and set the FK. Add `meal_time_tags` validation for v2 choices.  
**Reuses from current system:** Existing `meal_plan.py` router, existing `patient_meal_choices` upsert logic (22E), existing `patient_meal_choice_dishes` child insert.  
**Produces:** Updated `meal_plan.py`. Updated `GET /meal-plan/week` response (version-adaptive). Updated `POST /meal-plan/confirm-choice` request/response schemas.  
**Verification:** With Priya's v2 plan approved: `GET /meal-plan/week` returns `generation_version=2` and `combos[]` arrays per slot. `POST /meal-plan/confirm-choice` with `weekly_combo_id=101, food_item_ids=[...]` → 200, row in `patient_meal_choices` has `weekly_combo_id=101`.  
**Do not start until:** R-3 complete. R-4 can run in parallel with R-5.

---

### Session R-6 — Patient App (4-combo week view)
**Depends on:** R-5 complete  
**Type:** Implementation  
**Scope:** Update `meals.tsx` to detect `generation_version` in week response and render stored combos (not on-demand suggestions). For v2: render 4 `ComboCard` components per meal type per day. For v1: existing `SuggestionSlot` flow unchanged. Update `confirmMut` to pass `weekly_combo_id`. Update `ComboCard` to render "Doctor's pick" badge when `contains_doctor_pick=true`; optionally highlight the specific pinned dish within the card using `pinned_dish_ids`.  
**Reuses from current system:** `ComboCard` component (22F), existing confirm-choice mutation, existing `useWeekPlan` query hook, existing week-strip navigation, `queryKeys.ts`.  
**Produces:** Updated `meals.tsx`, updated `services/meals.ts` (types for v2 response), updated `types/index.ts` (add `combo_id` to `SuggestedCombo`).  
**Verification:** Patient app (Expo): Meals tab for v2 patient shows 4 combo cards per meal. Selecting a combo → confirm-choice fires → choice recorded in DB with `weekly_combo_id`. Past day shows confirmed combo name. V1 patient: no regression in existing flow.  
**Do not start until:** R-5 complete (API must return v2 shape before app can render it).

---

### Session R-7 — Weekly Cycle Automation + Personalization
**Depends on:** R-5 and R-6 complete (choices must be recordable before summary is meaningful)  
**Type:** Implementation  
**Scope:** Wire `complete_expired_plans()` cron to compute `weekly_patient_summary` at week-end. Verify personalization seed flows from `weekly_patient_summary` into next week's generation. Smoke-test the full Saturday-night auto-generation path.  
**Reuses from current system:** APScheduler setup (existing daily crons), `DietPlanService`, `MealGenerator`.  
**Produces:** Verified end-to-end weekly cycle: generate → approve → patient selects → week completes → summary computed → next week uses summary as seed. Verified by manually triggering the cron functions in a test session (not waiting for Saturday).  
**Verification:** After 7 simulated choice records for Priya: call `compute_weekly_summary(patient_id, week_start)` directly → `weekly_patient_summary` row written. Call `generate_meal_plan()` for next week with `personalization_seed` from prior summary → preferred dishes appear in combos. Log output shows personalization applied.  
**Do not start until:** R-6 complete.

---

### Session R-8 — Contract Phase (read paths switch to v2)
**Depends on:** All patients have at least one v2 plan (or: all doctors have approved at least one v2 week per patient)  
**Type:** Implementation  
**Scope:** Remove v1 branching code from `GET /meal-plan/week` once no active `generation_version=1` plans exist. Demote suggestions endpoint to "refresh options" (not primary path). Remove `SuggestionSlot` on-demand call from `meals.tsx` for v2 patients (already done in R-6, but any v1 residue cleaned here).  
**Gate condition:** `SELECT count(*) FROM recommendations WHERE generation_version=1 AND is_active=True` = 0.  
**Produces:** Cleaner `meal_plan.py` (no v1 branch), cleaner `meals.tsx`.  
**Do not start until:** R-7 complete AND v1 active plans = 0.

---

### Session R-9 — Cleanup
**Depends on:** R-8 complete  
**Type:** Cleanup  
**Scope:** Drop temporary compatibility code. Rationalize `meal_templates` DB (document shadow override, add comment to `meal_generator.py`). Remove orphaned `water-log.tsx` screen. Clean `plan_type_tags` tech debt (if product owner approves full removal).  
**Produces:** Cleaner codebase, updated CLAUDE.md, final BUILD_TRACKER entry.

---

### Critical Path

Minimum sequence to reach working new-model state end-to-end for one patient:

```
R-0 → R-1 → R-2 → R-3 → R-5 → R-6
```

This gives: doctor generates → approves → patient sees 4 options → patient confirms → `weekly_combo_id` recorded.

Weekly summary visible to doctor: add R-3 (already on critical path) + data from at least one confirmed choice.

R-4 (Doctor UI) and R-7 (Automation) are not on the critical path — manual verification via API calls and Expo app suffices for the first end-to-end test. Add R-4 before showing the rebuild to the product owner.

**Parallel work possible:**
- R-4 and R-5 can run simultaneously (both depend on R-3, not on each other).
- R-0 can run at any time before R-2.

---

## 9. Open Questions

All open questions from v1.0 have been resolved by the product owner (2026-06-15).
See v1.1 changelog for resolution summary. No blocking decisions remain before R-0.

---

*End of Rebuild Spec v1.1.*
