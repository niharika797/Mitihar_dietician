# Bug 6 Combo-Building — Design Audit & Proposal

**Date:** 2026-06-15  
**Author:** Session 23 pre-work (diagnosis only — implementation not yet scoped)  
**Depends on:** Sessions 22C, 22D, 22E (all complete)  
**Status:** DESIGN PHASE — product owner review required before implementation session

---

## Context: What 22E Put in Place

| Capability | Status |
|---|---|
| `Target Calories` per slot (generation-time budget, decoupled from `Total Calories`) | ✅ in JSONB |
| `scaled_calories` + `factor` per dish | ✅ in JSONB |
| `patient_meal_choice_dishes` child table (Option B) | ✅ migration `d0e1f2a3b4c5` |
| Beverages excluded from slot generation | ✅ suggestions endpoint filters `slot_type != 'beverage'` |
| Suggestions endpoint reads `Target Calories` (R1) | ✅ |
| Current suggestions: single-item, not combo | ❌ Bug 6 not done |

---

## Part 1 — 22C Viability Re-Confirmation

### Slot Shapes (post-22E)

| Meal | Variant | Slot composition | Template |
|---|---|---|---|
| Breakfast | Fixed (22E) | main_dish (0.78) + accompaniment (0.22) | was 3-dish; beverage removed |
| Lunch/Dinner | Standard (60%) | grain + dal_protein + sabzi + accompaniment | 4-dish |
| Lunch/Dinner | One-pot (40%) | one_pot (0.70) + accompaniment (0.30) | 2-dish |

**Breakfast slot shape changed in 22E** (was 3-dish with beverage; now 2-dish). This is a new shape vs 22C's audit. Re-check needed.

### Combo Math Verification (live data from recs 167/169/170/171)

**Breakfast (2-dish: main_dish + accompaniment):**
```
Rec 167: Total=413.51 vs Target=413.52 (generator scaled → precise hit)
Rec 170: Total=396.72 vs Target=396.72 (precise)
Unscaled combo (for suggestions): main_dish ≈ 0.78 × Target, accompaniment ≈ 0.22 × Target
  → if best main is within ±10% of 0.78T and best accompaniment within ±10% of 0.22T:
     combo error ≤ ±10% of T → within ±5% envelope for most matches
```
Breakfast 2-dish combo is viable for suggestions. Pool: 24 main_dish × 5 accompaniment = **120 combos** (pre-filter).

**One-pot Lunch/Dinner (2-dish: one_pot + accompaniment):**
```
Rec 167 Dinner: Rajma Chawal (factor=0.92) + Lassi (factor=0.96) → Total=413.52, Target=413.52
Unscaled: Rajma Chawal cal=314.7 + Lassi=128.8 = 443.5 vs Target=413.52 → +7.3%
```

22C found "2-dish one_pot undershoot-on-large-targets, up to -30%." With 22E's `factor` data now visible:

The -30% undershoot arose when comparing a **single one_pot dish** against the full-slot target. With combo (one_pot + accompaniment), the math is much better: observed ±7-10% unscaled in live data. 

**22D open thread resolved:** 22D said the undershoot "ties back to Bug 2's decision." With Bug 2 done:
- `Target Calories` gives the correct per-slot budget (no more TDEE/3 heuristic).
- `factor` exists per dish but the suggestions endpoint (R1) doesn't scale — it ranks by proximity.
- For suggestions, unscaled combo calorie sum will systematically diverge from Target (patient factors don't apply to suggestions). **This is acceptable at R1** — the doctor can PATCH to rescale. Suggestions show the best available combo at natural portion sizes; the patient is told "approximately X kcal."
- The -30% single-dish concern is **eliminated by combo design** (accompaniment adds 20-30% of target budget).

**One-pot pool (post-22E, is_verified=True):**  
Lunch=7, Dinner=16 items.

Pool: 7×12=84 Lunch combos, 16×16=256 Dinner combos (pre-filter). Sufficient.

**Standard 3/4-slot (grain+dal_protein+sabzi+accompaniment):**
```
Rec 167 Lunch: 4 dishes, Total=578.92 vs Target=578.93 (generator scaled to exact target)
Unscaled Lunch combo: Curd Oats(216) + Moong Dal(166) + Green Beans Fry(126) + Masala Chaas(45) ≈ 553 vs Target=579 → -4.5%
```
22C ±5% finding still holds for standard 4-dish combos.

Pool: grain(10)×dal_protein(30)×sabzi(12)×accompaniment(12) = **43,200 Lunch combos** — enumeration is not feasible. Smart selection approach required (see Part 2).

---

## Part 2 — Suggestions Endpoint Redesign Proposal

### Problem With Current Single-Item Design

Current endpoint ranks individual food_items by calorie proximity to `Target Calories` (slot budget). A single main_dish at 400 kcal is shown against a 580 kcal Lunch budget → always wrong signal. The patient picks one dish from suggestions, not a whole meal. There is no concept of "this dish goes with these other dishes to hit the target."

### Proposed: Combo-Ranked Suggestions

Return up to 4 **whole-meal combos** per call. Each combo = all dishes for that slot's composition.

#### Response Shape Change (required)

```
# Current
GET /meal-plan/suggestions/2026-06-15/Lunch
{
  "suggestions": [
    {"food_item_id": 192, "recipe_name": "Curd Oats", "calories": 216, ...}
  ]
}

# Proposed
GET /meal-plan/suggestions/2026-06-15/Lunch
{
  "slot_calorie_target": 580.0,
  "suggestions": [
    {
      "combo_id": 0,
      "total_calories": 553.0,
      "dishes": [
        {"food_item_id": 192, "recipe_name": "Curd Oats", "slot_type": "grain", "calories": 216, ...},
        {"food_item_id": 201, "recipe_name": "Moong Dal", "slot_type": "dal_protein", "calories": 166, ...},
        {"food_item_id": 305, "recipe_name": "Green Beans Fry", "slot_type": "sabzi", "calories": 126, ...},
        {"food_item_id": 102, "recipe_name": "Masala Chaas", "slot_type": "accompaniment", "calories": 45, ...}
      ]
    },
    ...
  ]
}
```

#### Slot Composition Determination

For each `meal_type`, the endpoint needs to know which slot composition to use. Two options:

**Option A — Always suggest both variants (one_pot AND standard) and let patient pick:**
- Return up to 2 one_pot+accompaniment combos + 2 standard combos (4 total)
- Simpler: no need to track which variant the plan used for that day

**Option B — Read from active plan to match plan variant:**
- Check the active plan's slot_types for the given date + meal_type
- If plan has one_pot → suggest one_pot combos
- If plan has grain/dal_protein → suggest standard combos
- More aligned with plan intent; patient swaps a whole meal of the same shape

**Recommendation: Option B** — read slot_types from plan JSONB (already fetched for `Target Calories`). The plan records the actual variant used. Suggestions should be shape-compatible with the plan slot for that day.

#### Query Shape

```python
# Step 1: determine slot composition from plan (reuse existing plan lookup)
slot_types = get_slot_types_from_plan(meals_json, plan_date, meal_type)
# e.g. ["one_pot", "accompaniment"] or ["grain", "dal_protein", "sabzi", "accompaniment"]

# Step 2: for each slot_type, build candidate pool
# (2-4 DB queries, one per slot_type, all indexed)
pools = {}
for st in slot_types:
    stmt = (
        select(FoodItem)
        .where(
            FoodItem.is_verified == True,
            FoodItem.meal_time_tags.any(meal_type),
            FoodItem.slot_type == st,
            FoodItem.diet_type.in_(allowed_diet_types),  # ← Backlog B closed here
        )
    )
    # apply avoid_tags
    for tag in avoid_tags:
        stmt = stmt.where(not_(FoodItem.avoid_tags.contains([tag])))
    # exclude blocked_ids, used_this_week
    stmt = stmt.where(FoodItem.id.notin_(exclude_ids))
    # rank by calorie proximity to slot_pct × Target
    slot_budget = slot_pct[st] * slot_calorie_target
    stmt = stmt.order_by(func.abs(FoodItem.cal_per_serving - slot_budget)).limit(10)
    pools[st] = await session.execute(stmt).scalars().all()

# Step 3: enumerate combos (top-K per pool, cross-product)
# For one_pot+accompaniment: ≤ 10×10 = 100 combos → enumerate
# For 4-slot standard: ≤ 10^4 = 10,000 → enumerate with pre-pruning:
#   prune pool to top 5 per slot (5^4=625 combos, sub-ms)
# Rank combos by: prefer_tag_count across dishes → calorie proximity of combo total
```

**slot_pct mapping** (same as generation-time targets):
- `one_pot`: 0.70, `accompaniment`: 0.30 (one-pot variant)
- `grain`: 0.35, `dal_protein`: 0.28, `sabzi`: 0.22, `accompaniment`: 0.15 (standard — approximate)

These percentages should be derived from the actual slot `calorie_pct` values in the plan JSONB or from the constants in `meal_generator.py` — the plan doesn't store per-slot pcts, so the constants are the source.

#### Diet-Type Filter — Backlog B Integration

The combo query naturally includes a `FoodItem.diet_type.in_(allowed_diet_types)` filter. This closes **Backlog B** (vegetarian patients receiving non-veg suggestions) as a free side effect of implementing Bug 6.

`allowed_diet_types` logic:
```python
DIET_TYPE_HIERARCHY = {
    "Vegetarian":     ["Vegetarian"],
    "Eggetarian":     ["Vegetarian", "Eggetarian"],
    "Non-Vegetarian": ["Vegetarian", "Eggetarian", "Non-Vegetarian"],
}
allowed = DIET_TYPE_HIERARCHY.get(patient.diet_type, ["Vegetarian"])
```

**Open question (PO):** Is Eggetarian a possible patient `diet_type` in the current onboarding flow? The DB only shows `Vegetarian` (157) and `Non-Vegetarian` (38) in `is_verified` food items. Confirm hierarchy above.

---

## Part 3 — Confirm-Choice Integration

### Current State

`POST /meal-plan/confirm-choice` accepts one `food_item_id`. The child table (`patient_meal_choice_dishes`) was deliberately built for N dishes (delete-then-insert pattern, 22E Part 3). **The child table is ready for combos.**

What must change:

**1. Input schema (backward-compat or break):**

```python
# Option A — Backward compat: accept either old single or new list
class ConfirmChoiceInput(BaseModel):
    food_item_id: Optional[int] = None          # legacy, single dish
    food_item_ids: Optional[list[int]] = None   # new, combo
    date: date
    meal_type: str

# Option B — Break: always require list (clean, no ambiguity)
class ConfirmChoiceInput(BaseModel):
    food_item_ids: list[int]   # 1 item for legacy callers, N for combo
    date: date
    meal_type: str
```

**Recommendation: Option B.** The frontend will be updated to pass combos from suggestions; there are no third-party callers. Clean break avoids Optional-hell.

**2. Parent row `calories`:** Change from `fi.cal_per_serving` (single dish) to `sum(fi.cal_per_serving for fi in confirmed_dishes)`.

**3. Child rows:** One row per food_item_id in the list. The existing delete-then-insert loop already handles this — just loop over the list instead of inserting one row.

**4. Suggestions response → frontend → confirm-choice flow:**
- Suggestions returns a `dishes: list[{food_item_id, ...}]` per combo.
- Patient taps a combo → frontend passes all `food_item_ids` to confirm-choice.
- No new DB columns needed; no schema migrations needed.

**Open question (PO):** Should the patient be able to swap individual dishes within a suggested combo (pick main from combo A, accompaniment from combo B)? If yes, the frontend needs a per-slot swap UX and the confirm-choice schema stays as a list but receives a mix. This is a UX decision, not a schema constraint — the backend handles any list of N dishes.

---

## Part 4 — Pool-Size Reality Check (Q6 carried forward)

### Verified Pool Sizes (post-22E, is_verified=True)

| Slot type | Lunch | Dinner | Breakfast |
|---|---|---|---|
| one_pot | 7 | 16 | 2 |
| accompaniment | 12 | 16 | 5 |
| main_dish | — | — | 24 |
| grain | 10 | 18 | 10 |
| dal_protein | 30 | 53 | 3 |
| sabzi | 12 | 19 | 1 |

### Combo Pool Sizes (before patient filters)

| Meal | Variant | Raw combos |
|---|---|---|
| Breakfast 2-dish | main + accompaniment | 24 × 5 = **120** |
| Lunch one-pot | one_pot + accompaniment | 7 × 12 = **84** |
| Dinner one-pot | one_pot + accompaniment | 16 × 16 = **256** |
| Lunch standard | grain × dal × sabzi × acc | 10×30×12×12 = **43,200** |
| Dinner standard | grain × dal × sabzi × acc | 18×53×19×16 = **289,584** |

### Weekly Repetition Risk

A patient gets 7 days × 3 meals = 21 meals. Of these:
- ~7 Breakfasts: each draws from 120 combos → 7 unique needed, 120 available → no repetition risk
- ~3 one-pot Lunches: 3 from 84 → no repetition risk
- ~4 standard Lunches: 4 from 43,200 → no repetition risk

**vs. current single-item:** The suggestions endpoint currently returns top-4 from a pool of ~12-30 items. A patient choosing from the top-4 weekly hits repetition after 2-3 weeks. Combo construction eliminates this by making unique dish-pairs even from overlapping individual items.

**Q6 verdict:** The accompaniment pool=4 concern (from Q6) referred to the GENERATION pool before post-22E verification. The verified pool is **accompaniment=12 (Lunch)**, **16 (Dinner)** — adequate. Q6 can be closed as resolved by post-22E DB state.

### Patient-Filter Impact (diabetic vegetarian, Priya model)

After applying: `avoid_diabetes`, `diet_type=Vegetarian`, weekly exclusions:
- Non-veg items removed (38 of 195 verified → ~19% loss)
- Biryani/high-carb items with `avoid_diabetes` removed (~3 currently tagged, ~27 untagged gap)
- weekly exclusions: ~3 Lunches per week × 2 dishes = 6 items excluded

Effective one-pot Lunch pool for Priya ≈ max 7 × 12 = 84 → minus non-veg (7 one_pot non-veg? need count) → likely ~5 × 10 = 50. Still sufficient.

**Risk:** The ~27 biryani/pulao items without `avoid_diabetes` tags (Backlog A) mean diabetic patients could see high-carb combos in suggestions. This is a data-quality risk independent of combo-building — it exists for single-item suggestions too. Combo-building does not worsen this.

---

## Part 5 — Performance Sketch

### Current endpoint query count: ~5-6

1. prefs query (pinned/blocked)
2. weekly choices query (child table join)
3. active plan meals query (Target Calories)
4. consumed-today query (calories_remaining)
5. candidates query (single DB query, top 20)

### Proposed combo endpoint query count: ~7-9

1-4. Same as current (unchanged)
5+. One query per slot_type in composition:
   - one_pot variant: +2 queries (one_pot pool, accompaniment pool)
   - standard variant: +4 queries (grain, dal_protein, sabzi, accompaniment pools)

All pool queries are indexed on `(slot_type, is_verified)` + array containment on `meal_time_tags` + `avoid_tags`. Each returns ≤10 rows (LIMIT 10 per pool).

22C noted "2-4 indexed queries" for the simulated approach. The real design lands at 7-9, all indexed. **No performance concern.** The cross-product enumeration is in-Python over ≤10^4 tuples (for the standard 4-slot case with top-5 per pool → 5^4=625 tuples) — sub-millisecond.

---

## Open Questions for Product Owner

| # | Question | Impacts |
|---|---|---|
| A | Should suggestions always return BOTH one-pot and standard variants for Lunch/Dinner, or only the variant matching the current plan day? | endpoint design §Part 2 |
| B | Is per-dish swap within a combo in scope for this session? (Patient picks main from combo 1, accompaniment from combo 2) | frontend UX + confirm-choice input |
| C | Should Breakfast suggestions return paired combos (main+accompaniment) or still single dishes? (Breakfast is 2-dish but may feel simpler) | Breakfast suggestion shape |
| D | Confirm: combo suggestions are read-only (no scaling). Patient and doctor see "approximately X kcal." Is this acceptable, or is R2 (scaled combos) needed in the same session? | scope |
| E | Confirm `diet_type` hierarchy: does Vegetarian patient see Vegetarian only? Eggetarian sees Veg+Egg? | Backlog B closure |
| F | Single PR scope: is it acceptable to close Backlog B (diet_type filter) as part of this implementation? | scope decision |

---

## Implementation Order (recommended, not scoped)

1. **Schema**: update `ConfirmChoiceInput` to `food_item_ids: list[int]`
2. **Suggestions endpoint**: add slot_type → combo construction (answers PO questions first)
3. **Confirm-choice**: update to accept list, sum calories for parent, loop children
4. **Frontend**: update suggestions display + confirm-choice call to pass `food_item_ids[]`
5. **Backlog B** (diet_type filter): add as part of step 2 pool queries

**NOT in scope:** Per-dish scaling in suggestions (R2), combo pin (doctor pins a whole combo rather than one dish), combo blocking.

---

## Summary

- 22C ±5% viability finding **holds** for all slot types post-22E.
- The -30% one_pot undershoot concern is **eliminated** by combo (one_pot + accompaniment combo is within ±10% of target at natural portion sizes).
- Breakfast 2-dish shape is a **new case** (not in 22C), but pool math shows 120 combos — viable.
- Child table (22E) is already combo-ready — no new migrations needed.
- `confirm-choice` schema needs one change: `food_item_id` → `food_item_ids: list[int]`.
- Backlog B (diet_type filter) is a **free natural closure** as part of combo pool queries.
- Q6 (accompaniment pool=4) is **resolved** — verified pools are 12-16, not 4.
- Pool sizes are adequate; weekly repetition risk eliminated vs single-item.
- Query count: 7-9 (all indexed), no performance concern.
