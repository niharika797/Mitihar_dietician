# Recipe Dataset Investigation — Session 9
> **Date:** 2026-05-25 | **Status:** Investigation complete, read-only
> **Purpose:** Understand the 6,000+ Indian Food Recipes Dataset, trace why only 1,930 recipes entered the DB, assess whether a clean re-import can solve the depth crisis.

---

## WHAT THE DOCS SAID

No planning document explicitly names the zip file or discusses the import plan in detail. What the docs DO reveal:

**Phase 0 Journal (`docs/journal.txt`):**
- Step 1: Deleted the original "eyantra" datasets (`app/services/datasets for eyantra/` folder) — these were small Excel files from an academic competition, now gone
- Step 6: `seed_food_items.py` ran against the remaining Excel files in `app/services/meal_generator/data/` (Breakfast.xlsx, Lunch.xlsx, Dinner.xlsx) — source='excel', is_verified=True, 184 rows
- Step 7: "Dataset final pass — DEFERRED (~20 dirty rows, condiment reclassification)" — this is the only mention of data quality problems

**Phase 1 Handoff (`docs/PHASE_1_HANDOFF.md`):**
- States "Dataset: 1,963 verified Indian recipes, avg 435 kcal, all below 1,200 kcal" — written *after* the initial seed ran, so the 6k seed had already run by this point

**The seed script (`scripts/seed_6k_recipes.py`):**
- Script exists, is complete, was run with USDA_API_KEY
- Expected CSV at: `Mitihar_dietician/6000+ Indian Food Recipes Dataset/IndianFoodDatasetCSV.csv` (inside project root)
- Had known calorie inflation bug (cup=240g for all ingredients regardless of density)

**The fix script (`scripts/fix_6k_calories.py`):**
- A v2 fix written to correct inflated calories in already-inserted 6k_dataset rows
- Expected CSV at: `Mitihar_dietician/data/6000+ Indian Food Recipes Dataset/IndianFoodDatasetCSV.csv`
- This file EXISTS — the data/ folder has a copy of the CSV (confirmed)
- Documents the calorie inflation root cause explicitly in the file header

**Conclusion:** The 6,000+ dataset WAS imported via `seed_6k_recipes.py`. Session 8's characterization of "seed_6k_recipes was aspirational" was partially wrong — the script ran, but 1,930 is the TRUE result of that run, not a failure or truncation. The import was designed to be selective (USDA confidence threshold + calorie cap).

---

## THE DATASET

### File Structure
```
6000+ Indian Food Recipes Dataset.zip  (9.35 MB, dated 2026-02-23)
└── 6000+ Indian Food Recipes Dataset/
    ├── IndianFoodDatasetCSV.csv   (23.0 MB)
    └── IndianFoodDatasetXLS.xlsx  (5.3 MB — same data, different format)
```

A copy of the CSV also exists at:
`Mitihar_dietician/data/6000+ Indian Food Recipes Dataset/IndianFoodDatasetCSV.csv`

### Total Record Count
**6,871 rows**

### Complete Field List

| Column | Type | Nulls | Description |
|--------|------|-------|-------------|
| Srno | int | 0 | Sequential row number |
| RecipeName | str | 0 | Original name (often Hindi-English transliteration) |
| TranslatedRecipeName | str | 0 | English name used by seed script |
| Ingredients | str | 6 | Original ingredient string |
| TranslatedIngredients | str | 6 | English ingredient string (parsed by seed script) |
| PrepTimeInMins | int | 0 | Preparation time |
| CookTimeInMins | int | 0 | Cooking time |
| TotalTimeInMins | int | 0 | Total time |
| Servings | int | 0 | Number of servings (1–12 range) |
| Cuisine | str | 0 | Cuisine type (North Indian Recipes, South Indian Recipes, etc.) |
| Course | str | 0 | Meal course (Lunch, Dinner, Snack, etc.) |
| Diet | str | 0 | Diet classification |
| Instructions | str | 0 | Cooking instructions |
| TranslatedInstructions | str | 0 | English instructions |
| URL | str | 0 | Recipe page URL (NOT an image URL) |

**⚠️ Critical: This dataset has NO calorie, macro, sodium, or nutrition data of any kind.**
All nutrition in food_items was computed externally via USDA FoodData Central API calls.

### Diet Distribution (all 6,871 rows)
| Diet | Count |
|------|-------|
| Vegetarian | 4,712 |
| High Protein Vegetarian | 705 |
| Non Vegeterian | 427 |
| Eggetarian | 344 |
| Diabetic Friendly | 260 |
| High Protein Non Vegetarian | 225 |
| No Onion No Garlic (Sattvic) | 73 |
| Vegan | 61 |
| Gluten Free | 50 |

### Sample Record
```
TranslatedRecipeName: Kerala Style Arabic Vegetable Recipe - Kerala Style Arbi Curry
Course: Side Dish
Cuisine: Kerala Recipes
Diet: Vegetarian
Servings: 4
TranslatedIngredients: 250 gm arabic - wash now, peel, 1 tamarind - Malabar, 
  salt - as per taste, 1/4 cup coconut - scrape, 1 teaspoon red chilli powder, 
  2 onions - peeled, 1 tablespoon coconut oil, 2 onions - peel and chop, 
  1 teaspoon mustard, 1 teaspoon cumin seeds, 2 dry red chillies - break, 
  7 curry leaves
URL: https://www.archanaskitchen.com/kerala-style-arbi-curry
```

Note: "arabic" here is the transliteration of "arbi" (colocasia/taro root) — a common Indian spelling variant.

---

## CONNECTION TO CURRENT DATABASE

### Is This the Original Source?
**YES — confirmed.**

The DB query shows source='6k_dataset' for 1,930 rows, matching the seed script's output. Average calorie: 435 kcal/serving at max 1,199.9 — exactly at the 1,200 kcal cap set by `fix_6k_calories.py`. The ingredient names in the DB ("Gm arabic", "Gm parwal", "Gm small potatoes") are directly traceable to specific rows in the CSV with "gm" unit abbreviations. Recipe name "Arbi" in DB matches the CSV recipe "Kerala Style Arabic Vegetable Recipe" where the main ingredient parses to "arabic" (colocasia).

### Why Only 1,930 of 6,871 Ended Up in DB

Starting from 6,871 rows, the seed script applied 5 stages of reduction:

| Stage | Filter | Remaining |
|-------|--------|-----------|
| Raw CSV | — | 6,871 |
| Indian cuisine filter | Contains Indian/North Indian/South Indian/Bengali/etc. | 4,238 |
| Meal course filter | Lunch/Dinner/Side Dish/Snack/Breakfast/Main Course/One Pot | 3,668 |
| Valid diet filter | Vegetarian/High Protein Veg/Non Veg/Eggetarian/Diabetic | 3,559 |
| Valid servings filter | Servings between 1–10 | **3,499 candidates** |
| USDA confidence ≥ 55% | Indian ingredient names fail USDA lookup at high rate | ~2,200 estimated |
| Calorie > 0 and ≤ 1,200 kcal | Cup density bug eliminated many | **~1,930 survived** |

**The USDA confidence threshold is the primary killer.** Indian ingredient names like "Karela", "Haldi", "Hing", "Besan", "Palak" have poor match rates in USDA FoodData Central (a US-centric database). Many recipes had less than 55% of their ingredients matched by the API, causing the entire recipe to be dropped.

Excluded courses (total 2,559 rows dropped by course filter):
- Dessert: 659 rows — would map to snack_item if included
- Appetizer: 639 rows — would map to snack_item or grain
- World Breakfast: 260 rows — non-Indian cuisines
- Continental: 1,021 recipes (Cuisine filter) — excluded entirely

### The "Gm" Prefix Bug — Root Cause Traced

**25 rows in the CSV use "gm" or "gms" as a unit abbreviation** (Indian informal shorthand for "gram"). The seed script's ingredient parser does not recognize "gm" in its `UNIT_TO_GRAMS` dict.

**Parse path for "250 gm arabic":**
```python
qty_str = "250"
unit_str = "gm"  # lowercased — NOT in UNIT_TO_GRAMS
name = "arabic"
# gm not found → prepend to name:
name = "gm arabic"
# fallback to piece weight:
grams_per_unit = UNIT_TO_GRAMS["piece"]  # = 80
total_grams = 250 × 80 = 20,000g  ← WRONG (should be 250g)
# After cleanup:
clean = "Gm arabic"  # .lower().capitalize() → capitalize first letter
```

**Results in DB:**
- "Arbi" recipe: ingredient "Gm arabic" at 40,000g (500 gm arabic × 80)
- "Arabic Vegetable": ingredient "Gm arabic" at 20,000g (250 gm arabic × 80)
- "Parwal Masala": ingredient "Gm parwal" at 24,000g (300 gm parwal × 80)
- "Makhana Pakora": ingredient "Gm makhana" at 8,000g (100 gm makhana × 80)

**Fix:** Add to `UNIT_TO_GRAMS` in seed_6k_recipes.py:
```python
"gm": 1, "gms": 1  # Indian gram abbreviations
```

### The Batch-Quantity Bug — Root Cause Traced

In `seed_6k_recipes.py`, `compute_recipe_nutrition()` correctly divides macros by servings for `cal_per_serving`, `protein_per_serving`, etc. **But the `ingredients` JSONB list stores the total-recipe gram amounts, not per-serving amounts.**

```python
parsed_ingredients.append({"name": name, "amount_g": round(grams, 1)})
# total_grams = qty × grams_per_unit  ← this is WHOLE RECIPE amount
# nutrition is divided by servings → correct
# ingredients JSONB amount_g is NOT divided → WRONG
```

A recipe serving 4 with "2 cups spinach" (2 × 240g = 480g total) stores `amount_g: 480`, but should store `amount_g: 120` (per serving). This causes the shopping list to show 4× the correct ingredient amounts.

**The `fix_6k_calories.py` v2 does NOT fix this bug** — it re-parses ingredient strings and stores the same total-recipe amounts without dividing by servings.

---

## FIELD MAPPING TABLE

| food_items column | Dataset field | Match status | Transform needed |
|------------------|--------------|-------------|-----------------|
| recipe_name | TranslatedRecipeName | Direct | Strip whitespace only |
| slot_type | Course (inferred) | Partial | COURSE_TO_SLOT dict (covers 9 course types, defaults "grain") |
| cal_per_serving | **NONE** | **MISSING** | Must compute via external API |
| protein_per_serving | **NONE** | **MISSING** | Must compute via external API |
| carbs_per_serving | **NONE** | **MISSING** | Must compute via external API |
| fat_per_serving | **NONE** | **MISSING** | Must compute via external API |
| fiber_per_serving | **NONE** | **MISSING** | Must compute via external API |
| sodium_per_serving | **NONE** | **MISSING** | Must compute via external API |
| serving_weight_g | **NONE** | **MISSING** | Not in dataset — stays NULL |
| diet_type | Diet | Needs map | Simple 6-entry dict (already in seed script) |
| region_tags | Cuisine (inferred) | Inferred | CUISINE_TO_REGION dict (good coverage; generic "Indian" → all 4 regions) |
| meal_time_tags | Course (inferred) | Inferred | course_to_meal_time_tags() function (already in seed script) |
| plan_type_tags | **NONE** | Default only | Hardcoded ["Healthy","Diabetic-Friendly","Gym-Friendly"] — non-discriminating |
| ingredients | TranslatedIngredients | Parse + compute | Regex parse → name extraction → USDA lookup → JSONB. **Must divide by servings.** |
| source | N/A | Fixed | "6k_dataset" |
| is_verified | N/A | Fixed | False |
| image_url | URL | **WRONG TYPE** | URL is recipe page URL, not image URL. Stays NULL. |
| doctor_id | N/A | Fixed | NULL |

**Summary:** 8 of 18 columns require external API computation (the nutrition fields). 3 require inference from other fields. 5 are fixed values or direct matches. Zero are fully clean direct mappings that include nutrition.

---

## WHAT A PROPER IMPORT WOULD NEED

### Required Code Fixes in `seed_6k_recipes.py`

**Fix 1 — Gm unit (1 line):**
```python
UNIT_TO_GRAMS = {
    ...
    "gm": 1, "gms": 1,  # ADD: Indian gram abbreviations (25 recipes affected)
    ...
}
```

**Fix 2 — Batch-quantity bug (in compute_recipe_nutrition, 1 line):**
```python
# Replace:
parsed_ingredients.append({"name": name, "amount_g": round(grams, 1)})
# With:
parsed_ingredients.append({"name": name, "amount_g": round(grams / servings, 1)})
```

**Fix 3 — Improve USDA matching (medium complexity):**
Indian ingredient strings often include parenthetical English names: "Karela (Bitter Gourd/ Pavakkai)". 
The parser should extract the parenthetical English name for USDA lookup instead of the Indian name:
```python
# "Karela (Bitter Gourd/ Pavakkai)" → USDA lookup: "Bitter Gourd"
# vs current behavior → USDA lookup: "Karela" (often not found)
```
This alone would likely raise the USDA confidence rate from ~55% to ~70%+.

**Fix 4 — Additional courses (optional, adds ~1,300 more candidates):**
- Appetizer (639 rows): could map to `snack_item`
- Dessert (659 rows): could map to `snack_item` with meal_time = Evening_Snack

### Alternative to USDA API

USDA FoodData Central is US-centric and fails on many Indian ingredients. Alternatives with better Indian coverage:
- **Edamam Recipe Nutrition API** — per-recipe analysis from ingredient strings, no per-ingredient lookup needed
- **OpenFoodFacts** — open source, includes Indian products, free
- **IFCT (Indian Food Composition Tables)** — NIN India database, best for traditional Indian ingredients, requires manual download

Using Edamam's recipe analysis API would be the most practical improvement: send the full ingredient string, receive complete nutrition for the whole recipe, divide by servings. Eliminates the per-ingredient confidence problem entirely.

### Fields That Require Inference (No Dataset Equivalent)

| Column | Inference approach | Complexity |
|--------|-------------------|------------|
| slot_type | From Course field | Simple (dict mapping) |
| region_tags | From Cuisine field | Simple (keyword matching) |
| meal_time_tags | From Course field | Simple (dict mapping) |
| plan_type_tags | Cannot infer | **All recipes get all 3 tags** — this is the existing non-discriminating pattern |

### Estimated Re-Import Scale

| Scenario | Estimated recipes added |
|----------|------------------------|
| Re-run with Gm fix + batch fix only (USDA unchanged) | +~100 (Gm bug affected 25 rows; some were already excluded for other reasons) |
| Re-run with USDA matching improved (parenthetical extraction) | +400–600 (from better confidence rates) |
| Re-run with Edamam/OpenFoodFacts instead of USDA | +700–1,000 (from removing confidence filter bottleneck) |
| Re-run including Appetizer + Dessert courses | Additional +600–900 |
| **Best-case total:** All fixes + Edamam + extra courses | **~1,500–2,000 new recipes** |
| **New DB total (best case):** | **~3,400–3,900** |

---

## CRITICAL GAPS THAT REMAIN AFTER FULL IMPORT

Even with a perfect best-case re-import:

### Gap 1 — Non-Veg/Eggetarian Depth Is Structurally Limited
The dataset itself has limited non-veg Indian content:
- Total non-veg/eggetarian candidates (after 4-step filter): **350 rows**
  - Non Vegeterian: 168
  - High Protein Non Vegetarian: 107
  - Eggetarian: 75
- After USDA/nutrition filtering (even at 70% rate): ~245 recipes
- **Current DB has 83 non-veg from 6k_dataset** — re-import would add at most ~162 more
- Session 8 target: 30 per slot per diet per region = ~960 non-veg slots needed
- This dataset can provide at most ~245 total non-veg recipes, far short of target

### Gap 2 — plan_type_tags Remain Non-Discriminating
The dataset has no medical condition information. All recipes will continue to be tagged for all three plan types (Healthy, Diabetic-Friendly, Gym-Friendly). The 100% tagging problem identified in Session 8 cannot be fixed from this dataset alone.

### Gap 3 — No Image URLs
The URL column contains recipe page URLs (archanaskitchen.com). No image URLs are available. image_url stays NULL for all 6k_dataset rows.

### Gap 4 — Beverage Slot Remains Empty
No beverage recipes exist in this dataset. The critical gap identified in Session 8 (6 total beverages in DB) cannot be addressed from this source.

### Gap 5 — Breakfast Depth Remains Inadequate
Even with re-import, breakfast recipes from this dataset are limited. The Course filter captures South Indian Breakfast (260), North Indian Breakfast (123), Indian Breakfast (101) = 484 breakfast rows. After diet + servings filter: ~400. After nutrition filtering: ~280 recipes maximum. Session 8 found 309 breakfast recipes already in DB — net gain would be modest.

### Gap 6 — Total Volume Still Below 5,000 Target
Best-case re-import produces ~3,400–3,900 total recipes. Session 8 calculated ~5,203 needed for minimum viable adaptive planning. **The gap of ~1,300–1,800 recipes cannot be filled from this dataset.**

---

## RECOMMENDATION

**Option B: Clean and re-import with specific fixes, treated as a base layer — not a complete solution.**

### Specific Action Plan

**Immediate (1-2 days):**
1. Fix `seed_6k_recipes.py` — add "gm"/"gms" to UNIT_TO_GRAMS and divide amount_g by servings in ingredients JSONB
2. Switch nutrition source from USDA to Edamam Recipe Analysis API or OpenFoodFacts (avoids per-ingredient confidence problem)
3. Add parenthetical extraction to ingredient parser (use English name in parentheses for nutrition lookup)
4. Include Appetizer and Dessert courses as snack_item (adds ~1,300 candidates)
5. DELETE all current source='6k_dataset' rows and re-seed with corrected script
6. Expected result: ~2,800–3,400 recipes from 6k_dataset (up from 1,930)

**Medium-term (2-4 weeks):**
7. For non-veg depth: use AI-assisted recipe generation (Gemini API prompted with dish names from NIN database, generating quantity-correct recipes with nutritional values)
8. For plan_type_tags discrimination: implement sodium-based rule (sodium_per_serving < 400mg → Diabetic-Friendly) using the already-populated `sodium_per_serving` field from the re-import

**Why not Option A (complete re-import as-is):**
The dataset is the correct source, already partially imported, but the script has fixable bugs. A wholesale re-import without the nutrition source switch would reproduce the same USDA confidence problem and yield only marginally more recipes (~50-100 more than current 1,930).

**Why not Option C (different approach entirely):**
The dataset's TranslatedIngredients field is well-structured English text, suitable for any nutrition API. The structural problems (slot/region/meal_time inference) are already solved in the seed script. Building from a different dataset would require re-solving those problems. This dataset is the right foundation — it just needs better nutrition computation.

**Bottom line:** This dataset can bring the DB from 2,141 to ~3,400–3,900 recipes. Closing the remaining ~1,200–1,800 recipe gap requires AI generation or additional licensed datasets, specifically targeting non-veg, eggetarian, and beverage slots.

---

## APPENDIX — Script Reference

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/seed_6k_recipes.py` | Initial import from CSV via USDA API | Has Gm bug + batch-quantity bug |
| `scripts/fix_6k_calories.py` | Corrects calorie inflation post-import | Has same batch-quantity bug; path uses data/ folder copy |
| `scripts/seed_food_items.py` | Imports from Excel eyantra files | Clean; produced source='excel' 184 rows |
| `scripts/seed_meal_templates.py` | Seeds meal slot templates | Not related to food_items |

**CSV file locations:**
- Original zip: `C:\Users\Lenovo\Desktop\Code\2026\Nutria\6000+ Indian Food Recipes Dataset.zip`
- Extracted copy (for fix script): `Mitihar_dietician\data\6000+ Indian Food Recipes Dataset\IndianFoodDatasetCSV.csv`
- fix_6k_calories.py looks for CSV at: `Mitihar_dietician\data\6000+ Indian Food Recipes Dataset\IndianFoodDatasetCSV.csv` ✓ EXISTS
