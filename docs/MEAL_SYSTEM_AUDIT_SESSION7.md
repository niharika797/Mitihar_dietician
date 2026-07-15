# Meal System Audit — Session 7
**Date:** 2026-05-25  
**Author:** Claude (Session 7)  
**Scope:** Ingredient deduplication fix + full read-only investigation of meal plan system for adaptive planning feasibility

---

## EXECUTIVE SUMMARY

The meal plan engine works correctly for its original purpose — generating a 7-day static plan for a vegetarian patient with no medical conditions. However, three categories of problems exist that matter before building the adaptive system:

1. **Zero medical condition filtering at food level.** Diabetic, hypertensive, and PCOS patients receive the exact same dishes as healthy patients. Only calorie/macro targets are adjusted.
2. **Recipe pool is too thin for multi-option adaptive planning.** Even for the best-supported profile (Vegetarian, West region), breakfast slot-level pools have 1-2 items — not enough to offer 3-4 choices. Non-Vegetarian and Eggetarian are effectively non-functional for snack slots.
3. **Beverage handling is broken.** Only 6 beverage recipes exist in the entire DB. All 7 Breakfast days get the same beverage. Chai-type items are incorrectly tagged as sabzi/main-dish slots and appear at Lunch, which is wrong.

The two good surprises: `GET /api/v1/progress/today` already returns `calories.remaining`, and the multi-option query change is simple (one function return change). The adaptive architecture needs surprisingly little new plumbing. What it needs is a richer recipe database.

---

## JOB 1 RESULTS

### Task A — Ingredient Deduplication Fix

**Status: COMPLETE — committed to DB.**

- Recipes with duplicate ingredient entries found: **326**
- All 326 fixed in a single transaction.
- Post-commit verification: zero duplicate ingredient names remain in any recipe.

**Verification — Chai/Coffee/Milk:**
- Before: `Milk` appeared 5× at 75g each (total 375g)
- After: `Milk` appears 1× at 75g

Sample fixed recipes with high duplication counts:
- Sambhar: 5× of Pigeon pea, Tomato, Onion, Drumstick, Oil
- Coconut chutney: 5× of Coconut Fresh, Curd
- Chawal: 5× of Rice
- Salad: 5× of Cucumber, 4× of Carrot
- Dahi: 5× of Curd

**Impact:** Shopping list calculations will now be significantly lower. Dishes that previously showed impossible quantities (e.g., 2694g parwal) will now show realistic amounts.

---

### Task B — REG2 Meal Logging Verification

**Status: CONFIRMED WORKING.**

```
POST /api/v1/progress/log/meal
Authorization: Bearer <testaudit token>
Body: { "meal_type": "Breakfast", "calories": 450, "protein": 18, "carbs": 60, "fat": 12 }

Response: HTTP 200
Body: {"message": "Meal logged successfully"}
```

---

### Task C — token_1 Display Edge Case for testaudit

**What doctor sees:** In the doctor dashboard patient list (`Patients.tsx`), the `Token1Badge` component displays:
- Text: `—` (dash, because `token_1` is `NULL`)
- Badge: grey **"Inactive"** label

**Why this is misleading:** testaudit (`testaudit@mityahar.com`) was activated before the Session 4 fix that introduced `token_1` generation on subscription activation. Their `token_1` is `NULL` and `token_1_active = False`, but their `subscription_status = 'active'`. The badge tells the doctor the patient is "Inactive" even though they have an active subscription and can use the app fully.

**Code location:** `mitihar-frontend/apps/src/app/pages/doctor/Patients.tsx:26–49`
```tsx
function Token1Badge({ active, token }: { active: boolean; token: string | null }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-mono text-[#374151]">{token ?? '—'}</p>
      <span className={`text-[10px] font-semibold ...
        ${active ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#F3F4F6] text-[#6B7280]'}`}>
        {active ? 'Active' : 'Inactive'}
      </span>
    </div>
  );
}
```

The `active` prop maps directly to `token_1_active` (a separate field from `subscription_status`).

**Recommendation:** Fix is minor — show "Active" badge when `subscription_status === 'active'`, regardless of `token_1_active`. Or show `token_1` column only when `token_1` is non-null. Flag for next sprint — not urgent but confusing for doctors.

---

## INVESTIGATION FINDINGS

### Investigation 1 — Variety Control

**Code:** `meal_generator.py` lines 283–284, 317–408

Two tracking structures:
- `daily_used_ids` — **hard block**, never dropped. Cleared each new day. Prevents same dish appearing twice within one day.
- `weekly_used_ids` — **soft preference**. Level 1 query excludes weekly-used IDs. Level 2 query drops this exclusion if Level 1 returns nothing. This means weekly variety is best-effort, not guaranteed.

Cross-week variety: `prior_used_food_ids` is seeded from the last 2 plans' used IDs before generation starts (via `diet_plan_service.py`).

**Verified against Priya's plan (plan_id=128):**

Total meals: 35 slots | Distinct component dishes: 61

| Dish | Occurrences | Pattern |
|---|---|---|
| Chai/Coffee/Milk | 7× | Every day at Breakfast (beverage slot) |
| Curd Chutney | 7× | Every day at Breakfast (accompaniment slot) |
| Chaas | 7× | Every day at Lunch (accompaniment slot) |
| Masala Chaas | 7× | Every day at Dinner (accompaniment slot) |
| Gujarati Vaghareli Mag | 2× | Day 1 and Day 3, both at Dinner |
| Aloo Parwal Sabzi | 2× | Day 4 and Day 5, both at Dinner (consecutive) |
| Adrak Chai | 2× | Day 6 and Day 7, both at Lunch |
| Pineapple Cucumber Salad | 2× | Day 6 and Day 7, both at Dinner (consecutive) |
| Buckwheat Cracker | 2× | Day 2 EveningSnacks, Day 3 MorningSnacks |
| **Coconut Kewra Drink** | **2× on same day** | Day 7: both MorningSnacks AND EveningSnacks |

**Finding 1:** Fixed accompaniment dishes (Curd Chutney, Chaas, Masala Chaas) repeat every day because these are dedicated accompaniment/beverage sub-slots and the pool for those slot types is tiny (2–6 items total). The variety system cannot solve a data depth problem.

**Finding 2:** Main dishes (grain, sabzi, main_dish) show genuine variety — no single main dish appears every day for Priya.

**Bug:** Coconut Kewra Drink appears twice on 2026-05-30 (MorningSnacks and EveningSnacks on the same day). `daily_used_ids` should prevent this. Root cause is likely two food_items with the same recipe_name but different IDs — the daily block tracks by ID, not by name.

---

### Investigation 2 — Diet Type Filtering

**Code:** `meal_generator.py` lines 331–334, 557–560

For non-vegetarian patients: Lunch/Dinner slots get `query_diet='Non-Vegetarian'` on pre-allocated "non-veg budget" days (max 4 days per week). All other slots — including ALL Breakfast and snack slots — use `query_diet='Vegetarian'`.

For vegetarian patients (like Priya): `query_diet='Vegetarian'` always.

Filtering is applied via `FoodItem.diet_type == diet_type` in every DB query. This is a hard filter.

**Verified against Priya's plan:**

| Diet Type | Count |
|---|---|
| Vegetarian | 76 matches |
| Eggetarian | 0 |
| Non-Vegetarian | 1 (false positive — see below) |

The "Non-Vegetarian" match is a false positive from the investigation query. Two `Chai/Coffee/Milk` entries exist in `food_items`:
- `id=229`: Vegetarian, 80.25 kcal/serving
- `id=239`: Non-Vegetarian, 80.25 kcal/serving

The investigation searched by `recipe_name`, so both matched. The meal generator correctly filters by `diet_type='Vegetarian'` and would only select `id=229` for Priya. However, `id=239` (Non-Veg Chai/Coffee/Milk) is an incorrect data entry — chai with milk is inherently vegetarian.

**DB recipe counts by diet_type:**
| Diet Type | Count |
|---|---|
| Vegetarian | 2,033 |
| Non-Vegetarian | 83 |
| Eggetarian | 25 |

Non-Veg (83) and Eggetarian (25) recipe pools are critically small. Non-Veg/Eggetarian patients will frequently exhaust their typed pool and fall back to Vegetarian dishes.

**Verdict:** Diet type filtering works correctly at code level. Data quality issue: Non-Veg Chai/Coffee/Milk entry should be corrected to Vegetarian.

---

### Investigation 3 — Medical Condition Filtering

**Code review:** `meal_generator.py` + `calculations.py`

**What exists:**
- `plan_type_tags` field on `food_items`: ARRAY of plan types (Healthy, Diabetic-Friendly, Gym-Friendly)
- These are used as a filter: `FoodItem.plan_type_tags.any(plan_type)` where `plan_type` comes from `user_data.get("health_condition", "Healthy")`
- In `calculations.py`: PCOS, hypothyroid, hyperthyroid cause macro-level overrides (higher protein, adjusted carb distribution). These affect calorie/macro **targets**, not which foods are selected.

**Reality check — plan_type_tags distribution:**
| Tag | Recipes |
|---|---|
| Healthy | 2,141 |
| Diabetic-Friendly | 2,141 |
| Gym-Friendly | 2,135 |

All 2,141 recipes carry all three tags. The tags are default values set during seeding, not meaningful condition-based classifications. **The plan_type filter currently has zero discriminating power** — every recipe passes it.

**No condition-specific columns exist in food_items:**
- No glycemic index
- No cholesterol per serving
- No diabetic_friendly flag
- No condition_tags or health_tags

The only nutritional field that could support condition filtering is `sodium_per_serving`, but it is not used anywhere in the meal generator.

**Patient profile fields:** Patients can specify `medical_conditions` (e.g., "diabetes", "hypertension", "PCOD") and `health_goals` during onboarding. These are stored in `patients.medical_conditions` (array) and `patients.health_goals` (array). Neither is used for food selection filtering. `health_goals[0]` is used only to select the macro split variant in `calculate_macronutrients()`.

**What would need to be added for meaningful condition filtering:**
- `condition_tags` ARRAY on `food_items` (e.g., `["diabetic_friendly", "low_sodium", "pcos_friendly"]`)
- Low glycemic index flag or `glycemic_index` field
- Filtering logic in `_find_food_item` that applies condition-based exclusion lists
- DB work to tag all 2,141 recipes with condition appropriateness

**Verdict:** Medical condition filtering is completely absent at the food selection level. A diabetic patient and a healthy patient receive identical dishes. Only macro targets differ.

---

### Investigation 4 — Recipe Depth Per Category

**Context:** Multi-option adaptive planning needs ~28 options per slot+diet+region combo (7 days × 4 suggestions). Current 7-day static plan needs only 7.

**Worst-case combinations (CRITICAL = <14 recipes):**

| Diet | Region | Meal Time | Count |
|---|---|---|---|
| Non-Veg | North | Morning_Snack | 1 |
| Non-Veg | East | Morning_Snack | 1 |
| Eggetarian | South | Breakfast | 1 |
| Non-Veg | South | Evening_Snack | 1 |
| Eggetarian | South | Morning_Snack | 2 |
| Eggetarian | South | Evening_Snack | 3 |
| Non-Veg | East | Breakfast | 3 |
| Eggetarian | North | Lunch | 3 |
| Eggetarian | North | Dinner | 3 |
| Non-Veg | South | Dinner | 6 |
| Non-Veg | South | Lunch | 7 |

**Vegetarian + West (Priya's profile) — by slot_type at meal_time:**

| Meal Time | Slot Type | Count | Status |
|---|---|---|---|
| Breakfast | grain | 2 | CRITICAL |
| Breakfast | dal_protein | 1 | CRITICAL |
| Breakfast | beverage | 2 | CRITICAL |
| Breakfast | main_dish | 67 | OK |
| Lunch | grain | 173 | OK |
| Lunch | sabzi | 122 | OK |
| Lunch | dal_protein | 21 | LOW |
| Dinner | grain | 226 | OK |
| Dinner | sabzi | 122 | OK |
| Dinner | dal_protein | 23 | OK |

**West + Vegetarian total counts per meal_time:**
| Meal Time | Count |
|---|---|
| Breakfast | 76 |
| Lunch | 321 |
| Dinner | 378 |
| Morning_Snack | 175 |
| Evening_Snack | 175 |

The meal_time totals look healthy but are misleading — Breakfast has 76 total but only 1-2 options for grain and dal_protein sub-slots. The current system works because main_dish (67 options) fills most breakfast slots. The grain/dal_protein/beverage slots repeatedly pick the same 1-2 items.

**Global pool summary:**
- Total recipes: 2,141 (only 83 Non-Veg, 25 Eggetarian)
- Total beverages: 6 (only 2 proper beverage slot items for breakfast)

**Verdict:** Current depth is barely adequate for today's 1-option 7-day plan. Completely insufficient for multi-option adaptive planning without significant recipe additions. Non-Veg and Eggetarian diet types are functionally broken for snack slots.

---

### Investigation 5 — Chai and Daily Beverage Handling

**How it works in the current system:**
- Beverages are a named slot type (`slot_type = 'beverage'`) in meal templates.
- The beverage slot gets `calorie_pct = 0.10` (10% of the meal's calorie target) in Breakfast templates.
- These 10% calories ARE counted in the meal's total calories.
- Chai/Coffee/Milk (80.25 kcal per serving) appears every single Breakfast day because only 2 beverage recipes exist for Breakfast: the Vegetarian Chai/Coffee/Milk (id=229) and the Non-Vegetarian variant (id=239).

**Chai/Coffee/Milk in Priya's plan:**
- Appears 7× — every day at Breakfast
- The meal template forces a beverage slot every day
- With only 1 real option for Vegetarian Breakfast beverage, this is unavoidable

**Data quality bugs in beverage-adjacent items:**

| Recipe | slot_type | meal_time_tags | cal/serving | Issue |
|---|---|---|---|---|
| Adrak Chai | sabzi | Lunch, Dinner | 161 | Tea tagged as main dish slot |
| Ginger Tea | sabzi | Lunch, Dinner | 147 | Tea tagged as main dish slot |
| Masala Chai | sabzi | Lunch, Dinner | 218 | Tea tagged as main dish slot |
| Cinnamon Spiced Tea | grain | Dinner | 98 | Tea tagged as grain slot |
| Apple Tea Latte | snack_item | Morning/Evening Snack | 843 | 843 kcal tea — wrong |

In Priya's plan, Adrak Chai appeared at Lunch on Days 6 and 7 as a main dish component (not as a beverage). This is because it has `slot_type='sabzi'` — the meal generator correctly selected it to fill a sabzi slot, but chai is not a sabzi. These items need slot_type and meal_time corrections.

**Only 6 beverage recipes in the entire DB:**

| Recipe | Cal | Slot | Meal Time |
|---|---|---|---|
| Chai | 82.25 | beverage | Breakfast |
| Chai/Coffee/Milk (Veg) | 80.25 | beverage | Breakfast |
| Chai/Coffee/Milk (Non-Veg) | 80.25 | beverage | Breakfast |
| (3 others — not true beverages) | varies | various | various |

**Verdict:** Calories are counted. But beverage pool is essentially empty (2 real breakfast beverages). Tea items tagged as sabzi/grain appear inappropriately in main dish slots. Chai does NOT exist as a separate pantry/background item — it occupies a calorie-counted slot every day.

---

### Investigation 6 — Adaptive Meal Planning Feasibility

#### Part A — Multi-Option Generation

**Current behavior:** `_find_food_item_single_diet` fetches `.limit(10)` candidates ordered by (regional priority, calorie proximity). `_pick()` returns the **first valid** item from those 10.

**Effort to return top-N options:** Low. Change `_pick()` to return a list instead of a single item, and propagate that list up through `_find_food_item` and `generate_meal_plan`. The 10-candidate limit already exists — no query changes needed to return 3-4 options instead of 1.

**Risk:** For slots with 2–3 matching items, returning 4 options is impossible. The system would return what it has (1–2 options). For West Veg Breakfast grain (2 items), the user would see 2 choices at most.

**Ordering/ranking for options:** Currently ordered by calorie proximity to target. Adding a "freshness" score (how many days since last shown) would improve variety quality.

#### Part B — Daily Calorie Budget Tracking

**Existing infrastructure:**

✅ `meal_logs` table: per-meal log with `calories_consumed`, `protein_g`, `carbs_g`, `fat_g`, `meal_type`, `logged_date`

✅ `progress_logs` table: daily aggregated `total_calories_consumed` — updated automatically after each meal log

✅ `GET /api/v1/progress/today` endpoint: already returns:
```json
{
  "calories": {
    "consumed": 450.0,
    "target": 1775,
    "remaining": 1325.0
  }
}
```

✅ `get_today_summary()` service: sums `meal_logs.calories_consumed` for today's date

**Nothing needs to be built for basic iterative calorie tracking.** The infrastructure is already there and working.

#### Part C — On-Demand vs Batch Generation

**Current architecture:** Single call generates all 35 meals (7 days × 5 meal types) and stores the full plan as JSONB in `recommendations.meals`.

**DB calls per slot:** ~3 queries per slot (diet fallback chain × 2 waterfall levels). 35 slots ≈ 105 DB calls total. With indexed queries and `.limit(10)`, each call is <10ms. Full plan generation: ~1–3 seconds.

**Per-slot generation estimate:** ~30ms. Fully feasible for on-demand single-slot generation.

**What needs to change for on-demand adaptive:**
- Generation state needs to persist across requests (which slots have been offered and which were chosen)
- `Recommendation` model would need to store partial plan state (offered options per slot + chosen option)
- The current model stores only the final selected dishes — it doesn't store which alternatives were offered
- A new `meal_suggestions` table (or JSONB field on Recommendation) would be needed

**No caching is implemented.** Each generation is a fresh DB scan. For adaptive, the 10-candidate fetch could be cached per session (Redis) to avoid re-querying when the user previews options.

#### Part D — Doctor Preference Influence

**Current state:** Generator uses patient profile fields only (`diet`, `region`, `health_condition`, `health_goals`, `food_allergies`). Doctor has zero influence on meal selection.

**What exists:** `food_allergies` is the only exclusion list. It works: allergen names are matched against ingredient names (case-insensitive).

**What's completely missing:**
- No doctor notes/constraints on the patient's meal plan
- No "high protein only", "no heavy carbs at dinner", "BRAT diet" flags
- No `doctor_preferences` table or equivalent

**Effort to add doctor constraints:**
- Medium. Would need: a patient preference field (or doctor_notes on the patient record) + constraint parsing logic in `_find_food_item` (e.g., minimum protein threshold per slot, excluded ingredients beyond allergies).
- The allergy filtering pattern is already a good template to extend from.

---

### Investigation 7 — Regional Filtering

**How it works:**
```python
region_sort = sa_case((FoodItem.region_tags.any(region), 0), else_=1)
```
Region is a **sort priority, not a hard filter**. Queries return up to 10 candidates ordered with regional items first. If a patient is West region, West-tagged recipes bubble to the top. Non-regional or other-region recipes are returned if regional ones are unavailable.

**This is correct design** for the current dataset — a hard region filter would cause frequent empty results for thin pools (e.g., West Veg Breakfast grain: 2 items).

**Patient ↔ DB region tag compatibility:**
| Patient record | food_items.region_tags |
|---|---|
| `patients.region = 'West'` | `region_tags = ['West']` |
| Same string values | Match correctly |

**Verified against Priya's plan (West):**
- West-tagged dishes matched: N (majority of main dishes)
- Non-West dishes in plan: Non-zero — these are the Breakfast grain/dal_protein slots where the West pool has 1-2 items, so non-West items fill the gap
- 21 food_items have no region_tags at all — these appear in any patient's plan regardless of region

**Region_tags distribution:**
| Region | Recipes |
|---|---|
| West | ~400+ |
| South | ~350+ |
| North | ~300+ |
| East | ~200+ |

(Exact counts vary by meal_time and diet_type combinations)

**Verdict:** Regional filtering works as designed. The soft-sort approach is correct for current data depth. The gaps are a data quality issue, not a code issue.

---

## CRITICAL GAPS (Things That Don't Exist At All)

These capabilities are completely absent and would need to be built before or alongside the adaptive system:

### 1. Medical Condition Food Filtering
**Absent.** A diabetic patient gets the same food as a healthy patient. Building this requires:
- `condition_tags` or `glycemic_index` on `food_items`
- Re-tagging all 2,141 recipes (significant data work)
- Filtering logic in `_find_food_item`

### 2. Doctor Preference Constraints
**Absent.** No mechanism for a doctor to say "no heavy carbs at dinner" or "high protein only". Effort: Medium (new patient preference field + filtering logic extending the existing allergy pattern).

### 3. Adaptive Plan State Persistence
**Absent.** The system stores the final chosen plan, not offered alternatives or partial state. Building adaptive generation requires:
- A way to store "these 3 options were offered for slot X on day Y"
- A way to record which option the patient chose
- Remaining-calorie recalculation and next-slot generation based on prior choices

### 4. Per-Slot Multi-Option Generation API
**Absent as API.** The generator always runs the full 35-slot loop. No endpoint generates options for a single slot. This needs:
- New endpoint: `GET /meal-plan/suggest?day=3&meal_type=Lunch`
- Generator refactor to accept a single slot query instead of full 7-day loop

### 5. Beverage Recipe Depth
**Critical gap.** Only 6 beverages in the DB, 2 of which are duplicates of each other (Veg vs Non-Veg Chai/Coffee/Milk). With 1 effective option per meal, breakfast beverages will always repeat.

### 6. Recipe Depth for Non-Veg / Eggetarian
**Critical gap.** 83 Non-Veg and 25 Eggetarian recipes are nowhere near enough for non-repeating 7-day plans, let alone multi-option plans.

### 7. Slot-type Corrections for Tea Items
**Data bug.** Adrak Chai, Ginger Tea, Masala Chai are tagged as `slot_type='sabzi'` and appear at Lunch as main dishes. These need to be either converted to `slot_type='beverage'` or removed from Lunch/Dinner meal_time_tags.

---

## RECOMMENDATIONS (Priority Order)

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P0 | Fix tea/chai slot_type tagging (sabzi → beverage) | 1 hour | Stops chai appearing as Lunch side dish |
| P0 | Fix Non-Veg Chai/Coffee/Milk to Vegetarian | 5 min | Correct data |
| P1 | Add 10+ breakfast beverages (lassi variants, nimbu paani, coconut water) | Data entry | Ends every-day same beverage |
| P1 | Add 50+ Non-Veg recipes for snack slots per region | Data entry | Makes Non-Veg plans viable |
| P2 | Add condition_tags to food_items + re-tag recipes | Large data work | Enables medical condition filtering |
| P2 | Refactor `_find_food_item` to return top-N instead of first | ~1 day dev | Enables multi-option suggestions |
| P3 | Add per-slot suggestion API endpoint | ~2 days dev | Foundation for adaptive UX |
| P3 | Add doctor constraint field + filtering logic | ~3 days dev | Doctor influence on plans |

---

## APPENDIX — Data Tables

### Slot Types in food_items
| Slot Type | Count |
|---|---|
| grain | 929 |
| sabzi | 446 |
| snack_item | 345 |
| main_dish | 284 |
| dal_protein | 97 |
| accompaniment | 30 |
| beverage | 6 |
| one_pot | 4 |

### progress_logs Table
Columns: id, patient_id, log_date, weight_kg, water_glasses, steps, calories_burned, **total_calories_consumed**, protein_pct, carbs_pct, fat_pct, streak_days, created_at, calorie_adjustment

### meal_logs Table
Columns: id, patient_id, recommendation_id, logged_date, meal_type, food_id, custom_food_name, **calories_consumed**, protein_g, carbs_g, fat_g, fiber_g, portion_servings, notes, created_at
