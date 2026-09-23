# Meal Plan System — Investigation Report
**Date**: 2026-05-25  
**Status**: Read-only investigation, no changes made  
**Investigator**: Claude Code

---

## HOW THE SYSTEM WORKS (Current State)

### The Full Pipeline

**1. Patient triggers plan generation**  
When a patient with an active subscription requests their meal plan, the API calls `diet_plan_service.generate_diet_plan()`, which passes user data to `MealGenerator.generate_meal_plan()` in `app/services/meal_generator/meal_generator.py`.

**2. System calculates nutritional targets**  
From the patient's profile (height, weight, gender, age, activity level), the system computes:
- **BMR** via Mifflin-St Jeor formula
- **TDEE** = BMR × activity multiplier (1.2 to 1.9)
- **Per-meal calorie targets** = TDEE × fixed percentages:
  - Breakfast: 25%, MorningSnacks: 5%, Lunch: 30%, EveningSnacks: 5%, Dinner: 25%

For Priya Sharma (patient #5): TDEE = 1775.81 kcal  
→ Breakfast = 443.95 kcal, Lunch = 532.74 kcal, Dinner = 443.95 kcal

**3. System selects dishes using meal templates**  
Each meal has a template (stored in `meal_templates` table) that defines meal "slots". A Breakfast template for West/Vegetarian/Healthy has 3 slots:
- `main_dish`: 70% of breakfast calories (= 310.8 kcal for Priya)
- `accompaniment`: 20% (= 88.8 kcal)
- `beverage`: 10% (= 44.4 kcal)

For each slot, the system queries `food_items` for a recipe matching:
- `slot_type` = grain / main_dish / accompaniment / etc.
- `diet_type` = Vegetarian / Non-Vegetarian / Eggetarian
- `meal_time_tags` contains the current meal (Breakfast, Lunch, etc.)
- `cal_per_serving` within [slot_target / 3.0, slot_target × 2.0] ← calorie proximity filter
- Not already used today / this week (variety control)
- Not on the patient's allergy list

**4. System calculates the scaling factor**  
For each selected food item:
```
factor = patient_slot_target_cal / food_item.cal_per_serving
factor = max(0.5, min(3.0, factor))   ← capped to prevent extreme scaling
```

Example (real data, Priya's breakfast main_dish slot):
```
Slot target: 310.8 kcal
Recipe "Barley Rava Idli": cal_per_serving = 313.98
factor = 310.8 / 313.98 = 0.99
```

**5. System scales ingredients**  
For every ingredient in the recipe:
```
scaled_amount_g = ingredient.amount_g × factor
```
These scaled amounts are stored in the `Ingredients Scaling` dict and accumulated into a weekly shopping list (`ingredient_checklist`).

**6. Plan is stored as JSON**  
The generated plan (35 meals × 7 days) is stored in the `recommendations` table as a JSONB blob in the `meals` column. Each meal entry looks like:
```json
{
  "Date": "2026-05-24",
  "Meal Type": "Breakfast",
  "Menu Names": "Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk",
  "Total Calories": 443.95,
  "Total Protein": 12.8,
  "Total Carbs": 67.4,
  "Total Fat": 14.2,
  "Ingredients Scaling": {
    "Sooji": 98.3,
    "Curd": 121.6,
    "Milk": 207.5,
    ...
  }
}
```

**7. Patient sees the shopping list**  
The `ingredient_checklist` sums `Ingredients Scaling` across ALL 35 meals for the week. This is the screen where "Green Chillies: 2887g" appeared.

---

## THE INGREDIENT QUANTITY PROBLEM

### Root Cause 1 — Batch recipe data entered as single-serving data (most impactful)

The `food_items.ingredients` JSONB field is documented as `[{"name": str, "amount_g": float}]` — meaning grams for **one serving for one person**. However, many recipes were entered with quantities for a **family batch** (4–8 servings).

**Confirmed examples from the database:**

| Recipe | Ingredient | Stored amount_g | Realistic single-serving |
|--------|-----------|-----------------|--------------------------|
| Aloo Parwal Sabzi | Parwal | **1200g** | ~150g |
| Aloo Parwal In Poppy Seed Masala | Parwal | **1200g** | ~150g |
| Achari Aloo Parwal | Dry red chillies | **240g** | ~3g |
| Aloo Parwal | Dry red chillies | **240g** | ~3g |
| Barley Rava Idli | Green chilli | **80g** | ~5g |
| Sabsige Soppu Paddu | Green chilli | **80g** | ~5g |
| Sabsige Soppu Paddu | Idli dosa batter | **480g** | ~120g |

These amounts match what you'd prepare for 4–8 people, not one. The calorie data (`cal_per_serving`) was apparently entered correctly for one person — only the ingredient amounts are wrong. Because the scaling formula uses `cal_per_serving` (which is correct), the factor stays near 1.0, and the raw batch-size ingredient amounts go straight to the patient.

**The Parwal 2694g trace:**
- Recipe "Aloo Parwal Sabzi": Parwal stored as 1200g (batch amount)  
- Dinner grain slot factor ≈ 1.12 (155 kcal target / 138 kcal per serving)  
- Scaled: 1200 × 1.12 = **1347g per meal**  
- This dish appears in 2 separate dinners (May 27 + May 28)  
- Weekly total: 1347 × 2 = **2694g** ← matches the shopping list exactly

**The Green Chillies trace:**
- Multiple recipes have 80–240g of green/dry chillies stored as "per serving"  
- These accumulate across 10–15 meals in the 7-day plan  
- Weekly total of all chilli variants: ~3613g

### Root Cause 2 — Import corruption ("Gm" prefix recipes)

A subset of recipes was imported from a source where the column format was "Gm [ingredient name]" (meaning "grams of [ingredient]"). The import script extracted the ingredient name but did not strip the "Gm" prefix, and imported the numeric value as-is from a large-batch source.

**Confirmed examples:**

| Recipe | Ingredient name in DB | Stored amount_g |
|--------|----------------------|-----------------|
| Parwal Masala | Gm parwal | **24,000g** (24 kg) |
| Multani Kaali Arbi | Gm arabic | **40,000g** (40 kg) |
| Coriander Potato | Gm small potatoes | **40,000g** (40 kg) |
| Arbi | Gm arabic | **40,000g** (40 kg) |
| Makhana Pakora | Gm makhana | **8,000g** (8 kg) |

These values (40 kg of potatoes, 8 kg of lotus seeds) are nonsensical for any recipe context — they appear to be quantities sourced from institutional catering or a database with a different scale convention.

In total: **30+ ingredient entries** have `amount_g > 300g`, and **305 ingredient entries** have `amount_g > 500g` in the database.

### Root Cause 3 — Duplicate ingredient entries

Several recipes have the same ingredient listed multiple times in their `ingredients` JSONB array. The generator accumulates all entries, so duplicates multiply the final quantity.

**Confirmed examples from the database:**

| Recipe | Ingredient | Occurrences |
|--------|-----------|-------------|
| Chai/Coffee/Milk | Milk | **10×** |
| Salad | Cucumber | **10×** |
| Chawal | Rice | **10×** |
| Dahi | Curd | **7×** |
| Salad | Carrot | **8×** |

Example: Chai/Coffee/Milk has Milk listed 5–10 times at 75g each. At factor 0.55 for the beverage slot, total milk = 5 × 75 × 0.55 = **207g** (observed in Priya's plan) instead of ~41g.

### Is this a code bug or a data problem?

**Both, but mostly data.**

The scaling formula in `meal_generator.py` (lines 410–434) is **correctly designed**:
```python
factor = target_cal / food_item.cal_per_serving
factor = max(0.5, min(3.0, factor))
amt = float(raw_amt) * factor
```
If `amount_g` were correctly entered as per-person amounts, and there were no duplicates, the formula would produce reasonable results. The verified recipes (e.g., Doi chira, Bharbhara, Sattu Paratha) show amounts like 45–75g per ingredient — entirely normal.

The code has one minor issue: the `BETWEEN` filter (`cal_per_serving.between(target_cal / 3.0, target_cal / 0.5)`) accepts recipes with cal_per_serving up to 2× the slot target. For those recipes, factor = 0.5 (the floor), but this only partially compensates for wrong ingredient amounts.

---

## DATA QUALITY FINDINGS

### Summary

| Metric | Value |
|--------|-------|
| Total recipes | 2,141 |
| Has `serving_weight_g` populated | 184 (8.6%) |
| Missing `serving_weight_g` | 1,957 (91.4%) |
| Avg `cal_per_serving` | 406.5 kcal |
| Recipes with 0 or null calories | 0 |
| Ingredient entries with `amount_g > 500g` | 305 |
| Ingredient entries with `amount_g > 200g` | 2,369 |
| Average `amount_g` across all ingredients | 96.4g |
| Max `amount_g` in any ingredient entry | 40,000g |
| Recipe/ingredient pairs with duplicates | 15+ confirmed |

### Notable data issues

**Calorie outliers** (likely wrong):
- Palak paneer stored as 47.1 kcal/serving (should be ~200–300 kcal)
- Prawn Malai Curry stored as 48.95 kcal/serving (should be ~200+ kcal)
- Berry Smoothie at 46 kcal/serving (plausible if very small)

**Structural data problems** in ingredient names (corrupted import):
- "Gm [vegetable]" — unit label embedded in name
- "/ 2 tsp garam masala powder" — fraction notation in name field
- "Of fenugreek seeds" — partial phrase (missing leading fraction)
- "Long" — ingredient name truncated (likely "Long red peppers" or similar)

**serving_weight_g**: 91.4% null means the system has no way to sanity-check whether scaled ingredient totals are reasonable for a meal's weight. A "300g serving" with 1200g of main vegetable is clearly impossible, but the system has no validation for this.

---

## THE DESIGN QUESTION — For Product Owner

The shopping list currently shows weekly totals for all ingredients. The individual meal view shows per-meal ingredient quantities. Both are derived from the same `Ingredients Scaling` data.

Below are the five options and what each would require technically:

---

### OPTION A — Show gram quantities (fixed, correct per-serving)

> "Breakfast: Spinach 50g, Paneer 100g, Tomato 80g"

**What it requires:**
1. A data cleanup pass across all 2,141 recipes to identify and correct batch-size ingredient amounts → significant manual work or AI-assisted correction
2. Deduplication of the 15+ recipes with duplicate ingredient entries (scriptable)
3. No code changes — the generator already outputs grams

**Current data state:** ~1,000+ recipes likely have batch quantities. The 184 with `serving_weight_g` populated could be used to auto-detect outliers (sum of ingredient amounts should roughly equal `serving_weight_g`).

**Honest assessment:** Requires a significant data cleanup project before the feature is trustworthy.

---

### OPTION B — Show household measures

> "Breakfast: 2 cups milk, 1 small bowl paneer, 1 tsp oil"

**What it requires:**
1. Add a `unit` and optional `household_measure` field to every ingredient entry in `food_items.ingredients`
2. Build or source a gram-to-household-measure conversion table (e.g., 240g milk = 1 cup)
3. New display logic in the mobile app to show household measures instead of grams
4. Re-enter or migrate all 18,798 ingredient entries

**Current data state:** No `unit` field exists. All ingredients are stored as `{name, amount_g}`. Complete data restructuring required.

**Honest assessment:** Highest technical cost. Requires both schema changes and full data re-entry.

---

### OPTION C — Show only macro targets, no ingredients

> "Breakfast: 444 kcal · 22g protein · 58g carbs · 14g fat"

**What it requires:**
1. Remove ingredient display from the mobile app's meal detail screen
2. No data changes — macros are already stored correctly in `Ingredients Scaling`... wait, actually macros are stored as `Total Protein`, `Total Carbs`, etc. in the meal object (already correct)
3. The shopping list tab becomes unavailable or optional

**Current data state:** Macros are stored correctly. No data cleanup needed.

**Honest assessment:** Lowest technical cost. Eliminates the quantity problem entirely but also eliminates recipe value — patient cannot cook the meal from the app.

---

### OPTION D — Show serving count only

> "Breakfast: 1 serving of Poha Upma"

**What it requires:**
1. Define what "1 serving" means consistently across all 2,141 recipes
2. The factor from the generator is already computed — the display would show `factor` instead of per-ingredient amounts
3. `serving_weight_g` would help define serving visually (e.g., "200g serving") but is null for 91.4% of recipes
4. Mobile app change to show "X servings" instead of ingredient list

**Current data state:** Factor is already computed (stored implicitly via the scaled macros). `serving_weight_g` mostly missing.

**Honest assessment:** Low code cost. Gives patients a quantity reference but doesn't help with cooking (they don't know what "1 serving of Poha Upma looks like"). Works best alongside photos.

---

### OPTION E — Show ingredients as proportions

> "Breakfast: Poha (large portion), Peanuts (small handful), Oil (1 tsp)"

**What it requires:**
1. Add a `category` to each ingredient: `main` / `secondary` / `condiment` / `oil`
2. Map gram ranges to prose labels (e.g., 80–200g = "large portion", 10–40g = "small portion", <10g = "pinch/tsp")
3. Display logic to render these labels instead of grams
4. No full data re-entry needed — can be auto-generated from existing `amount_g` values

**Current data state:** Could be partially auto-generated from existing gram values. `is_pantry_staple` is already tagged for 3,956 ingredients (provides one useful category).

**Honest assessment:** Medium code cost. Avoids the exact-quantity problem. Risk: "large portion" is ambiguous for people unfamiliar with the dish.

---

## RECOMMENDED NEXT STEPS (Engineer's View)

- **Fix the duplicate entries first** — this is a scriptable 1-hour fix. Deduplicating ingredient entries within the same recipe (keep first occurrence) will immediately fix Chai/Coffee/Milk, Salad, Chawal, and a dozen other recipes. No risk of data loss.

- **Add a `serving_weight_g` validation check** — for recipes where `serving_weight_g` is populated, verify that the sum of non-pantry ingredient amounts is within 2× of `serving_weight_g`. Any recipe where sum of ingredients > 3× serving weight is almost certainly a batch-entry error. Run this as a report, not an auto-fix.

- **Decide on the product direction (Option A–E) before cleaning the data** — if the team chooses Option C (macros only) or D (serving count), the ingredient cleanup becomes optional. If the team chooses A or B, the data cleanup is a prerequisite. Doing the cleanup before the product direction is decided risks cleaning data for the wrong schema.
