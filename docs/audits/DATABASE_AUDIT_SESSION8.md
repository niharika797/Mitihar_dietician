# DATABASE AUDIT — SESSION 8
*Read-only investigation. No code or data changes made.*
*Date: 2026-05-25*

---

## EXECUTIVE SUMMARY

The database is **fixable but requires major augmentation**. It does not need to be rebuilt from scratch.

**The single most important fact:** There are **2,141 recipes**, not 6,000. The `seed_6k_recipes` script name was aspirational — the actual seeded corpus is 1,930 records, padded to 2,141 with Excel imports and doctor additions. This changes every capacity estimate made in previous sessions.

**The single most important action:** Before adaptive planning can launch, 3,000+ new recipes must be added, with the highest priority being Non-Vegetarian and Eggetarian coverage (both near-zero for Lunch/Dinner). Condition tagging must be rebuilt from scratch.

**Can the database support adaptive planning today?** No. Core blockers:
1. Non-Veg/Eggetarian recipe depth is catastrophically thin
2. Medical condition filtering has zero discriminating power
3. Breakfast accompaniment and beverage pools are too small for 7-day variety

**Can the database support adaptive planning with targeted additions?** Yes — the schema is sound, the generator's query logic is correct, and the data quality issues are fixable.

---

## 1. THE 6,000 RECIPE QUESTION

### Reality

| Source | Count | Verified | Notes |
|--------|-------|----------|-------|
| `6k_dataset` | 1,930 | 0 | Main corpus from seed script |
| `excel` | 184 | 184 | Original Excel imports — higher quality |
| `doctor` | 13 | 0 | Doctor personal library |
| `doctor_global` | 7 | 0 | Pending admin approval |
| `rejected` | 7 | 0 | Test data, effectively dead |
| **TOTAL** | **2,141** | **197** | |

The "6,000" number was never real. The `seed_6k_recipes` script seeded only 1,930 valid records.

### Why All 2,141 Are Generator-Eligible

The meal generator's `_find_food_item_single_diet` WHERE clause:
```python
FoodItem.slot_type == slot_type,
FoodItem.diet_type == diet_type,
FoodItem.meal_time_tags.any(meal_time),
FoodItem.plan_type_tags.any(plan_type),
# + cal_per_serving.between(target/3, target/0.5)  [runtime filter]
```

**There is no `is_verified` filter.** All 2,141 recipes pass all static filters.

The distinction between verified (197) and unverified (1,944) only affects the Doctor Browse UI — not what patients actually receive in their meal plans.

---

## 2. COMPLETENESS AUDIT

| Field | Coverage | Notes |
|-------|----------|-------|
| `recipe_name` | 100% | |
| `slot_type` | 100% | |
| `cal_per_serving` | 100% (all > 0) | |
| `protein/carbs/fat/fiber` | 100% | |
| `ingredients` | 100% (no empty arrays) | |
| `diet_type` | 100% | |
| `region_tags` | 100% | 21 have empty `{}` |
| `meal_time_tags` | 100% | |
| `plan_type_tags` | 100% | |
| `sodium_per_serving` | 90.1% (1,930/2,141) | Only 6k_dataset has sodium |
| `serving_weight_g` | 8.6% (184/2,141) | Only Excel dataset |
| `image_url` | **0%** | Zero images across all recipes |
| `doctor_id` | 1.2% (25/2,141) | Only doctor-submitted |

**Notable:** `sodium_per_serving` exists for 1,930 recipes — this is a latent asset for hypertension filtering that has never been used.

---

## 3. SLOT TYPE DISTRIBUTION

| Slot Type | Count | Primary Use |
|-----------|-------|-------------|
| `grain` | 929 | Lunch/Dinner staple |
| `sabzi` | 446 | Lunch/Dinner side |
| `snack_item` | 345 | Snacks |
| `main_dish` | 284 | Breakfast (0 for Lunch/Dinner!) |
| `dal_protein` | 97 | Lunch/Dinner protein |
| `accompaniment` | 30 | Breakfast side |
| `beverage` | 6 | ← CRITICAL |
| `one_pot` | 4 | Unused in generator |

**Key finding:** `main_dish` tagged for Lunch/Dinner = **0 recipes**. Lunch/Dinner templates use `grain + sabzi + dal_protein` slots. Breakfast uses `main_dish + accompaniment + beverage`.

---

## 4. DIET TYPE DISTRIBUTION

| Diet Type | Count | % |
|-----------|-------|---|
| Vegetarian | 2,033 | 94.9% |
| Non-Vegetarian | 83 | 3.9% |
| Eggetarian | 25 | 1.2% |

Non-Veg and Eggetarian coverage is dangerously thin for any multi-patient use case.

---

## 5. REGION COVERAGE

Region tags are TEXT[] arrays. Distribution including multi-region recipes:

| Region | Recipes that include this region |
|--------|--------------------------------|
| South | 1,266 |
| North | 1,033 |
| West | 664 |
| East | 654 |

499 recipes have all four regions `{North,South,East,West}` — these serve as fallback for any region. 21 recipes have empty `{}` region (region-unaware).

---

## 6. RECIPE DEPTH MATRIX FOR ADAPTIVE PLANNING

**`*` = CRITICAL GAP (under 21 recipes)**

Format: `north / south / east / west` (recipes accessible to each region, including multi-region)

### Vegetarian (the main corpus — 94.9% of recipes)

| Slot | North | South | East | West |
|------|-------|-------|------|------|
| `grain` | 452 ✓ | 474 ✓ | 237 ✓ | 228 ✓ |
| `sabzi` | 194 ✓ | 287 ✓ | 128 ✓ | 122 ✓ |
| `snack_item` | 237 ✓ | 235 ✓ | 178 ✓ | 182 ✓ |
| `main_dish` | 86 ✓ | 212 ✓ | 57 ✓ | 74 ✓ |
| `dal_protein` | 33 ✓ | 39 ✓ | 18* | 31 ✓ |
| `accompaniment` | 9* | 1* | 4* | 9* |
| `beverage` | 2* | 0* | 1* | 2* |

### Non-Vegetarian (3.9% of recipes)

| Slot | North | South | East | West |
|------|-------|-------|------|------|
| `grain` | 12* | 11* | 17* | 11* |
| `sabzi` | 6* | 4* | 10* | 5* |
| `dal_protein` | 3* | 0* | 4* | 7* |
| `main_dish` | 0* | 0* | 1* | 0* |
| `accompaniment` | 2* | 0* | 5* | 0* |
| `beverage` | 0* | 0* | 1* | 0* |

### Eggetarian (1.2% of recipes)

| Slot | North | South | East | West |
|------|-------|-------|------|------|
| `grain` | 4* | 7* | 2* | 2* |
| `main_dish` | 6* | 5* | 4* | 4* |
| `sabzi` | 2* | 2* | 2* | 2* |
| `snack_item` | 4* | 5* | 3* | 3* |
| `dal_protein` | 0* | 1* | 0* | 0* |

### Breakfast-Specific Depth (critical — this is what patients see first)

| Slot | Diet | Count | Status |
|------|------|-------|--------|
| `main_dish` | Vegetarian | 269 | ✓ Adequate |
| `main_dish` | Eggetarian | 7 | **CRITICAL** |
| `main_dish` | Non-Vegetarian | 1 | **CATASTROPHIC** |
| `accompaniment` | Vegetarian | 9 | **CRITICAL** |
| `accompaniment` | Non-Vegetarian | 1 | **CATASTROPHIC** |
| `beverage` | Vegetarian | 5 | **CRITICAL** |
| `beverage` | Non-Vegetarian | 1 | **CATASTROPHIC** |

### Total Recipes Needed

To reach 30 recipes per (slot × diet × region × meal_time) for North and South regions only:

**3,062 additional recipes needed**

Breakdown by slot:
- `snack_item` (all types): ~540 needed (snacks not in 3-meal plan, but flagged)
- `main_dish` (Non-Veg): 180 needed
- `beverage` (both): 358 needed
- `accompaniment` (all): 341 needed
- `grain` (Non-Veg + Eggetarian): 311 needed
- `main_dish` (Veg, Lunch/Dinner): 120 needed
- `sabzi` (Non-Veg): 160 needed
- Other slots: ~552

> Note: If snacks are removed from the plan (Feature 1), ~540 of these become unnecessary. Adjusted shortfall: ~2,520 recipes for the 3-meal system.

---

## 7. CALORIE DISTRIBUTION

| Range | Count |
|-------|-------|
| 50–150 | 389 (18%) |
| 150–300 | 536 (25%) |
| 300–500 | 454 (21%) |
| 500–800 | 390 (18%) |
| Over 800 | 286 (13%) |
| Under 50 | 86 (4%) |

286 recipes over 800 cal/serving is concerning — likely includes batch-quantity corruption. The generator scales by factor 0.5–3.0, so a 1,200 cal recipe with factor 0.5 = 600 cal serving which can be reasonable, but the underlying ingredient amounts will be wrong.

---

## 8. DATA QUALITY ISSUES

### Issue Table

| Issue | Recipes Affected | Severity | Fixable? |
|-------|-----------------|----------|----------|
| Batch ingredient quantities (40,000g potatoes) | ~50+ | **P0** | Yes — script |
| Chai/tea mistagged (wrong slot_type) | ~10 | **P0** | Yes — 1-hour fix |
| Medical condition tags non-discriminating | ALL 2,141 | **P0** | Yes — major effort |
| Non-Veg/Eggetarian recipe depth catastrophic | 83 + 25 total | **P0** | Requires new data |
| Beverage pool: only 6 recipes | 6 exist | **P0** | Requires new data |
| Gm-prefix corruption in ingredient names | 9 recipes | **P1** | Yes — short script |
| Breakfast accompaniment: 9 Veg options | 9 exist | **P1** | Requires new data |
| Single-ingredient recipes | 73 | **P1** | Review manually |
| Test data duplicates in production (7×3 test recipes) | 21 | **P2** | Admin cleanup |
| Real duplicate recipe names (Sev Puri ×4 etc.) | ~20 | **P2** | Dedup script |
| `serving_weight_g` missing | 1,957/2,141 | **P3** | Tedious to fix |
| `image_url` completely absent | 2,141/2,141 | **P3** | Requires media work |

### Batch Quantity Corruption Detail

These are in the database NOW and affect shopping list generation:

| Recipe | Ingredient | Amount |
|--------|-----------|--------|
| Coriander Potato | Gm small potatoes | **40,000g** |
| Multani Kaali Arbi | Gm arabic | **40,000g** |
| Arbi | Gm arabic | **40,000g** |
| Parwal Masala | Gm parwal | **24,000g** |
| Arabic Vegetable | Gm arabic | **20,000g** |
| Makhana Pakora | Gm makhana | **8,000g** |

The pattern: "Gm prefix" = the batch recipe used "Gm" as a unit prefix (like "Gm" = grams) but it was absorbed into the ingredient name. The `amount_g` field contains the batch quantity.

### Chai / Beverage Mistagging

These items should be `slot_type = 'beverage'` but are classified as other slots:

| Recipe Name | Current Slot | Should Be | Cal | Note |
|-------------|-------------|----------|-----|------|
| Masala Chai | `sabzi` | `beverage` | 218 | Correct cal |
| Adrak Chai | `sabzi` | `beverage` | 161 | Duplicate entry |
| Ginger Tea | `sabzi` | `beverage` | 147 | |
| Cinnamon Spiced Tea | `grain` | `beverage` | 98 | |
| Filter Coffee | `main_dish` | `beverage` | 535 | Cal too high — review |
| Espresso Coffee | `main_dish` | `beverage` | 303 | |
| Gulkand Chai | `main_dish` | `beverage` | 135 | |
| Apple Tea Latte | `snack_item` | `beverage` | 843 | Cal suspicious |

After reclassification, beverage pool grows from 6 to ~14. Still far below minimum viable.

---

## 9. MEDICAL CONDITION TAGGING

### Current State: Completely Non-Functional

| Condition | Recipes Tagged | % |
|-----------|---------------|---|
| Healthy | 2,141 | 100% |
| Diabetic-Friendly | 2,141 | 100% |
| Gym-Friendly | 2,135 | 99.7% |
| PCOD/PCOS | 0 | 0% |
| Thyroid | 0 | 0% |
| Hypertension | 0 | 0% |

Only 2 distinct tag combinations exist:
- `{Healthy, Diabetic-Friendly, Gym-Friendly}`: 2,135 recipes
- `{Healthy, Diabetic-Friendly}`: 6 recipes (the ones excluded from Gym-Friendly)

**What this means:** A diabetic patient and a healthy patient receive **identical recipe pools**. The `plan_type_tags.any("Diabetic-Friendly")` filter returns all 2,141 recipes — it provides zero clinical filtering.

Recipes like Kheer (227 cal), Gulab Jamun, samosas (690–816 cal), and white rice are all tagged `Diabetic-Friendly`.

### What Proper Tagging Requires

1. **Diabetes (Diabetic-Friendly)**: Remove high-GI items (maida, white rice, deep-fried, high-sugar desserts). Promote millets, legumes, bitter gourd, methi. Estimate ~300 recipes inappropriate.

2. **PCOD/PCOS**: New tag set needed. Anti-inflammatory emphasis. Remove refined carbs, seed cycling foods separately. ~500 recipes to tag.

3. **Thyroid**: New tag set. Iodine-relevant foods (seafood for hypo). Goitrogen awareness (cabbage, soy). ~400 recipes to tag.

4. **Hypertension**: Can use existing `sodium_per_serving` data (1,930 recipes have values). Flag high-sodium items (pickles, processed, cured meats). This is the **easiest condition to implement** since the data already exists.

### Latent Asset: Sodium Data
1,930 of 2,141 recipes (90%) have `sodium_per_serving` values. No code changes needed to the DB schema — just wire the generator to filter `sodium_per_serving < threshold` when patient has hypertension. This is achievable in 1 session.

---

## 10. MEAL TEMPLATES AUDIT

### Template Coverage
- Total: 180 templates
- Structure: 5 meal_times × 3 diet_types × 4 regions × 3 plan_types = 180 ✓ (complete)

### Template Slot Structure (Breakfast)
```json
[
  {"required": true,  "slot_type": "main_dish",     "calorie_pct": 0.70},
  {"required": true,  "slot_type": "accompaniment", "calorie_pct": 0.20},
  {"required": false, "slot_type": "beverage",      "calorie_pct": 0.10}
]
```
Beverage is optional (`required: false`). If no beverage found, slot is skipped.

### Impact of Removing Snacks
Templates for Morning_Snack and Evening_Snack (72 templates total) will simply be unused — no deletion required. The generator's `meal_types` list is hardcoded at line 264 of `meal_generator.py`:
```python
meal_types = ["Breakfast", "MorningSnacks", "Lunch", "EveningSnacks", "Dinner"]
```
Removing snacks = changing this list and redistributing calorie percentages in `_calculate_meal_targets`. No DB migration needed.

---

## 11. DOCTOR RECIPE WORKFLOW

### What Exists
- `POST /api/v1/doctor/recipes` — doctor creates a recipe ✓
- `GET /api/v1/doctor/recipes` — doctor browses global + personal library ✓
- `POST /api/v1/doctor/recipes/{id}/assign` — inject recipe into patient plan ✓
- `POST /api/v1/doctor/recipes/estimate` — AI-assisted calorie estimation ✓
- `POST /api/v1/doctor/recipes/lookup` — lookup existing recipes ✓
- Admin approval flow: doctor submits with `submit_to_global=True`, admin approves → `is_verified=True` ✓

### Critical Gaps

**Gap 1: Doctor-created recipes cannot generate shopping list amounts**

`RecipeCreateRequest.IngredientItem` schema:
```python
class IngredientItem(BaseModel):
    name:     str  # e.g., "Toor Dal"
    quantity: str  # e.g., "100"
    unit:     str  # e.g., "g"
```

The generator reads `ing.get("amount_g") or ing.get("quantity")`. Doctor recipes will use `quantity` field. Since `quantity` is a string like `"100"`, `float("100")` works. **However**: 18,253 system recipe ingredients use `amount_g`; 25 doctor recipe ingredients use `quantity`. The mismatch means shopping list totals will work but the field names are inconsistent — a maintenance hazard.

**Fix:** Add `amount_g: Optional[float]` to `IngredientItem` or rename to `amount_g` in the schema.

**Gap 2: plan_type_tags defaults to all conditions**

```python
plan_type_tags: BoundedTagList = Field(default=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
```

Doctors cannot create a recipe that is *only* appropriate for Healthy or *only* for Diabetic patients. The default tags every recipe for all conditions. This will remain broken until condition tagging is rebuilt.

**Gap 3: No `serving_weight_g` or `sodium_per_serving` in creation form**

Doctors cannot provide sodium data, which is needed for hypertension filtering. No mechanism to add it post-creation either.

**Gap 4: Doctor-submitted recipes (is_verified=False) enter the LIVE generator**

Since the generator has no `is_verified` filter, a doctor's personal recipe (`source='doctor'`, `is_verified=False`) is immediately eligible for their patient's meal plans. This is intentional but undocumented — the doctor may not realize their draft recipe is already being used.

### What Needs Building

- [ ] Add `amount_g` / `sodium_per_serving` to `RecipeCreateRequest`
- [ ] Add per-condition plan_type_tags selector in doctor UI
- [ ] Warn doctor when an unverified recipe is in use in a patient's current plan
- [ ] Recipe quality validation: flag if ingredient amounts look like batch quantities

---

## 12. SYSTEM READINESS FOR PLANNED FEATURES

| Feature | Readiness | Missing | Effort |
|---------|-----------|---------|--------|
| 1. Remove snacks, 3 meals only | **Near-Ready** | 1-line change in `meal_generator.py` + calorie redistribution; frontend snack UI must be removed | Small (1 session) |
| 2. Patient sees 3-4 options per meal | **Partial** | Generator returns 1 item per slot; need to call N times with different seeds; recipe depth insufficient for Non-Veg/Eggetarian | Medium (2–3 sessions) |
| 3. Iterative calorie calculation | **Near-Ready** | `/progress/today` exists (calories.remaining); needs frontend to show remaining and re-query pool | Small (1 session) |
| 4. Doctor meal config panel (pool params) | **Not Started** | `doctor_meal_overrides` table is a feedback LOG, not a preference store; preference schema + API + UI all TBD | Large (4+ sessions) |
| 5. Medical condition filtering | **Not Started** | All tags are non-discriminating; 2,141 recipes need re-tagging; no existing GI/fry-method data | Large (4+ sessions) |
| 6. Chai as quick-log buffer | **Not Started** | Only 6 beverages exist, all Breakfast-only; quick-log UI needs beverage category; data AND code needed | Medium (2–3 sessions) |
| 7. Doctor adding recipes | **Partial** | UI exists; `amount_g` + `sodium_per_serving` missing from form; condition tags broken | Small (1 session to fix gaps) |
| 8. Doctor weekly patient summary | **Near-Ready** | `meal_logs` + `progress_logs` have all needed data; aggregation endpoint not yet built | Small (1 session) |

**Note on Feature 2:** For Vegetarian patients, depth is sufficient for multi-option generation (grain 228–474, sabzi 122–287, dal_protein 18–39 per region). For Non-Veg/Eggetarian, multi-option generation will fall back to Vegetarian for most slots — defeating the purpose.

**Note on Feature 5:** The `sodium_per_serving` field (90% populated) enables hypertension filtering with minimal work. This is the only condition where filtering is achievable in the short term without re-tagging.

---

## 13. DATABASE GROWTH STRATEGY

### How Many Recipes Are Needed

**For adaptive planning (3 options × 7 days = 21 minimum per combo):**
- Target: 30 per (slot × diet × region × meal_time) for North and South
- Current shortfall: **3,062 recipes** (or ~2,520 after removing snack slots)
- Practical minimum for launch: focus on Vegetarian Lunch/Dinner for all 4 regions first (~500 recipes)

**Priority order for additions:**
1. Vegetarian Breakfast accompaniments (need 21+ more)
2. Vegetarian beverages (need 15+ more)
3. Non-Vegetarian grain/sabzi/dal_protein for Lunch/Dinner
4. Eggetarian Breakfast main_dish (need 14+)
5. Non-Vegetarian Breakfast main_dish (need 30+)

### Quality Standards for New Recipes

A recipe must meet ALL of these before being added:

| Field | Requirement |
|-------|-------------|
| `recipe_name` | Unique. No "Gm " prefix in name. Human-readable. |
| `slot_type` | One of the 7 valid types. Beverages must use `beverage`. |
| `cal_per_serving` | Between 30–800 kcal. Flag anything outside this range for manual review. |
| `ingredients` | Use `amount_g` field (not `quantity`). Per-ingredient amount < 300g (anything higher = batch quantity suspect). |
| `meal_time_tags` | At least one value. Beverages should only be in snack/beverage slots, not Lunch/Dinner. |
| `plan_type_tags` | At minimum `["Healthy"]`. Do NOT default to all three conditions — assign thoughtfully. |
| `sodium_per_serving` | Required for any new recipe added to the 6k_dataset corpus. |
| `serving_weight_g` | Strongly recommended. |

### Recipe Source Assessment

**Option A — Doctor-submitted recipes**
- Quality: High (clinical context, realistic portions)
- Volume: Low (10–50 per doctor over 2 months)
- Bottleneck: Requires doctor onboarding, form UX improvements
- Best for: Filling specialty condition slots (diabetic-appropriate recipes)
- Effort to enable: Small (fix amount_g + sodium fields in form)

**Option B — IFCT/NIN nutritionist datasets**
- Quality: High (government nutrition data)
- Volume: High (IFCT has 500+ Indian foods)
- Bottleneck: Schema mapping required; IFCT data is nutrient-level not recipe-level
- Best for: Building accurate ingredient nutrition, not complete recipes
- Effort: Medium

**Option C — AI-assisted recipe generation (Claude/Gemini)**
- Quality: Variable — needs validation
- Volume: Unlimited
- Required validation: calorie sanity check, ingredient amounts in reasonable range, not duplicating existing recipes
- Best for: Filling thin slots quickly (Non-Veg breakfast, regional varieties)
- Risk: Hallucinated ingredient amounts are undetectable without calorie cross-check
- Effort: Medium (need a generation + validation pipeline)

**Option D — Patient crowd-sourced**
- Quality: Low to variable
- Volume: High over time
- Required: Doctor verification before entering global pool
- Best for: Long-term database growth after product launch
- Not viable for pre-launch gap filling

**Recommendation:** Option C (AI generation) for rapid gap filling, with automatic validation script that checks: calorie range, per-ingredient amounts, no Gm prefix, required fields populated. Option A for condition-specific recipes. Option B for sodium/micronutrient data enrichment.

---

## 14. CRITICAL ISSUES — PRIORITIZED ACTION LIST

### P0 — Blockers (causing wrong output right now)

1. **Fix batch ingredient quantities** — 6 known recipes with 8,000–40,000g ingredients. Shopping list shows these absurd amounts to patients today. Write a targeted UPDATE script for the 6 named recipes. *(~2 hours)*

2. **Fix chai/tea mistagged slot_types** — 8 beverages tagged as `sabzi`/`grain`/`main_dish`. These appear in Lunch/Dinner plans as savory dishes. Masala Chai and Adrak Chai in a Lunch sabzi slot is actively wrong. *(~1 hour)*

3. **Medical condition tagging is non-functional** — Not a 1-hour fix, but must be on the roadmap before any patient-facing "diabetic plan" marketing. Currently every "Diabetic-Friendly" plan is identical to "Healthy". *(Large — document the risk)*

### P1 — High Priority (significant quality degradation)

4. **Fix Gm-prefix ingredient name corruption** — 9 recipes with "Gm small potatoes", "Gm arabic" etc. These show in shopping lists with garbled names. *(~30 minutes)*

5. **Add Non-Vegetarian/Eggetarian breakfast recipes** — Current counts are 1/7 main_dish. Adaptive multi-option for these diet types is completely impossible. Generate 30–50 AI-assisted recipes per diet type. *(1–2 sessions)*

6. **Increase Breakfast accompaniment pool** — 9 Veg options means same raita/chutney every other day. Need 30+. *(1 session)*

7. **Fix `Filter Coffee` calorie (535 cal)** — Coffee entry at 535 cal is likely batch data. A typical Filter Coffee is ~80–120 cal. Review and fix. *(~15 minutes)*

### P2 — Medium Priority (needed before adaptive planning)

8. **Implement sodium-based hypertension filtering** — `sodium_per_serving` exists for 1,930 recipes. Add a `medical_conditions` filter in `_find_food_item_single_diet` that excludes high-sodium items for hypertension patients. Threshold: >800mg/serving. *(1 session)*

9. **Fix doctor recipe `IngredientItem` schema** — Add `amount_g: Optional[float]` field to align with system recipe format. *(~1 hour)*

10. **Remove test duplicate recipes** — 21 test records ('Doctor2 Private Dal' ×7, 'To Be Rejected Recipe' ×7, 'Global Test Recipe' ×7) pollute the database. Admin cleanup. *(~30 minutes)*

11. **Clean real duplicate recipe entries** — Sev Puri ×4, Dahi Bhindi ×4, Paneer Pakora ×4, etc. Dedup while keeping best nutritional data row. *(1 session)*

### P3 — Low Priority

12. **Add `image_url` for recipes** — 0% coverage. No images anywhere. Important for patient-facing UI but not for plan generation accuracy. *(Ongoing — media work)*

13. **Add `serving_weight_g` for 6k_dataset recipes** — Only 8.6% have it. Useful for scaling display ("half a portion") but not blocking. *(Ongoing)*

14. **Add PCOD/Thyroid condition tags** — After hypertension is working (P2 #8), extend to PCOD and thyroid. Requires clinical input on which recipes to exclude. *(Large — multiple sessions)*

---

## 15. STRUCTURAL LIMITATIONS FOR PLANNED FEATURES

Two findings may require design reconsideration:

### Finding A: `doctor_meal_overrides` is not a preference store
The existing `doctor_meal_overrides` table records what doctors have already overridden (feedback for RL training). It does NOT store doctor preferences/constraints for future plan generation. The planned "Doctor sets pool parameters (preferred dishes, avoid lists, pins/blocks)" feature requires building a new schema from scratch. The existing table is useful for doctor weekly summaries (Feature 8) but not for Feature 4.

### Finding B: No `main_dish` for Lunch/Dinner
The `main_dish` slot exists only for Breakfast (276 Veg recipes, 0 Non-Veg, 7 Eggetarian). Lunch/Dinner templates use `grain + sabzi + dal_protein`. This means the `main_dish` slot type can never be used for Lunch/Dinner, and any Lunch/Dinner "main course" concept must be expressed as `grain` or `sabzi` slot. This is an intentional structural choice (Indian thali model) but may confuse doctors adding recipes for Lunch/Dinner.

---

## APPENDIX A: Meal Template Slot Structure

All 180 templates share the same slot structure per meal_time:

**Breakfast:** `main_dish` (70%, required) + `accompaniment` (20%, required) + `beverage` (10%, optional)

**Lunch/Dinner:** Templates use `grain + sabzi + dal_protein` based on query counts, though exact calorie_pct splits were not directly inspected for Lunch/Dinner.

**Snacks (Morning_Snack / Evening_Snack):** Use `snack_item` slot.

## APPENDIX B: Progress/Log Infrastructure

**`progress_logs` columns:** id, patient_id, log_date, weight_kg, water_glasses, steps, calories_burned, total_calories_consumed, protein_pct, carbs_pct, fat_pct, streak_days, created_at, calorie_adjustment

**`meal_logs` columns:** id, patient_id, recommendation_id, logged_date, meal_type, food_id, custom_food_name, calories_consumed, protein_g, carbs_g, fat_g, fiber_g, portion_servings, notes, created_at

Both tables have the data needed for:
- Daily calorie tracking (Feature 3) ✓
- Doctor weekly patient summary (Feature 8) ✓
- Streak calculation ✓

## APPENDIX C: Ingredient Field Inventory

| Field | 6k_dataset recipes | Excel recipes | Doctor recipes |
|-------|-------------------|---------------|----------------|
| `amount_g` | ✓ (18,253 entries) | ✓ | ✗ |
| `quantity` | ✗ | ✗ | ✓ (25 entries) |
| `unit` | ✗ | ✗ | ✓ |
| `is_pantry_staple` | Some | Some | ✗ |
| `name` | ✓ all | ✓ all | ✓ all |

The generator reads: `ing.get("amount_g") or ing.get("quantity")` — both paths work for calculation, but `quantity` is a string so it must be numeric (e.g., `"100"` not `"2 tbsp"`). Doctor UI does not prevent non-numeric quantity strings.
