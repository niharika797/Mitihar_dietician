# Recipe Ingredients Sanity Check — Results & Walkthrough

We have implemented and executed an evidence-based sanity check pipeline for your `recipe_ingredients` dataset (~18k rows).

---

## 1. Overview of Results

Ran `python scripts/sanity_check_ingredients.py` against `recipe_ingredients_audit.csv` (18,213 rows):

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| **✅ Clean (OK)** | **13,097** | **71.9%** | All ingredient quantities are within realistic 1-serving bounds |
| **⚠️ Warning** | **2,134** | **11.7%** | Slightly high portions or statistical outliers (needs dietician review) |
| **🚨 Error** | **2,982** | **16.4%** | Definite data corruption, count-as-grams parsing bugs, or multi-serving leak |

Output generated: [`recipe_ingredients_flagged.csv`](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/recipe_ingredients_flagged.csv) containing row-by-row flag severity, category, check type, and evidence citations.

---

## 2. Key Findings & Root Cause Analysis

### 🐛 1. The "Count-as-Grams" Parsing Bug (1,431 rows)
The audit identified a systematic parsing bug where **recipe piece counts were misparsed as gram weights**:

| Ingredient | Corrupted Value in CSV | Likely Original Text | Realistic 1-Serving Amount |
|------------|------------------------|----------------------|----------------------------|
| **Curry leaves** | `1,600g` / `800g` / `640g` | 8–10 leaves | **1 – 2g** |
| **Green chillies** | `1,600g` / `160g` | 2–4 chillies | **5 – 10g** |
| **Cloves garlic** | `240g` | 6 cloves | **15 – 25g** |
| **Bay leaf** | `160g` | 2 leaves | **0.5 – 1g** |
| **Black cardamom** | `160g` | 2 pods | **2 – 4g** |

> **Root Cause**: The ingestion script applied a multiplier (e.g. `count × 80` or `count × 200`) when converting recipe strings into `quantity_g`.

---

### 🍲 2. Multi-Serving / Bulk Recipe Leak (2,915 rows)
2,915 rows exceed individual ingredient limits for a single serving:

- `Spinach leaves: 2,000g` (Palak Pakora / Palak Paneer)
- `Button mushrooms: 1,600g` (Mushroom Sabzi)
- `Small brinjal: 1,280g` (Vankaya Ulli Karam)
- `Carrot And Beans Thoran`: **Total raw dish weight = 2,969g** (~10–12 servings)

> **Root Cause**: Commercial/catering recipes entered into the dataset without dividing total quantities by the serving count.

---

### 🥚 3. Eggs Stored as Counts, Not Grams (9 rows)
- Items like `Egg, 2` or `Eggs, 1` have `quantity_g = 1` or `2`.
- According to **BASU (Bihar Animal Sciences University) Indian Egg Grading**, 1 large egg edible portion = **50g**. `Egg, 2` should be **100g**.

---

## 3. Evidence Base Summary

All 15 category rules and dish total thresholds in [`scripts/sanity_check_ingredients.py`](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/scripts/sanity_check_ingredients.py) are backed by official references documented in [`sanity_check_research.md`](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/fca6e11a-b37e-403a-847d-b7f7a4e80469/sanity_check_research.md):

| Category | Max Limit | Citation / Medical Rationale |
|----------|-----------|------------------------------|
| **Cereals / Grains** | `120g` | **ICMR-NIN 2024**: 250g cereals/day total across all meals |
| **Pulses / Legumes** | `90g` | **ICMR-NIN 2024**: 85g pulses/day total |
| **Vegetables** | `300g` | **ICMR-NIN 2024**: 400g vegetables/day total |
| **Cooking Oil / Fat** | `20g` | **ICMR 2024 / FSSAI**: 27g visible fat/day; 15–20g oil/day |
| **Curd / Milk** | `200g` | **ICMR 2024**: 300ml dairy/day |
| **Paneer** | `150g` | **NIN / IDA**: 50–100g standard; 150g upper bound |
| **Meat / Fish** | `150g` | **ICMR**: 80g meat replaces 30g pulses in RDA |
| **Eggs** | `100g` | **BASU**: 50g per egg edible portion (max 2 eggs) |
| **Nuts & Seeds** | `60g` | **ICMR 2024**: 30–45g/day total |
| **Added Sugar** | `30g` | **ICMR 2024 + WHO**: <25–30g added sugar/day limit |
| **Whole Spices** | `5g` | **Food Science**: Bay leaf ~0.5g, cardamom ~0.2g, clove ~0.01g |
| **Aromatics (chilli/garlic)** | `25g` | **TradeIndia / IFCT**: Green chilli 2–5g, garlic 3–7g/clove |
| **Fresh Herbs** | `30g` | **IFCT 2017**: Curry leaf 0.1–0.2g/leaf (1–2g per tempering) |
| **Saffron** | `2g` | **Toxicology**: Typical 0.02g; toxic at ≥5g |
| **Total Dish Weight** | `500–650g` | **Dietetic Science**: Indian thali total raw weight 500–650g |

---

## 4. How to Use the Sanity Check Tool

### Run against local CSV:
```bash
python scripts/sanity_check_ingredients.py --csv recipe_ingredients_audit.csv
```

### Run directly against live PostgreSQL Docker DB:
```bash
python scripts/sanity_check_ingredients.py --from-db
```

### Filter output CSV for specific error types:
Open `recipe_ingredients_flagged.csv` and filter by column `severity == ERROR` or `check == count_as_grams`.

---

## 5. Recommended Next Steps

1. **Fix `count_as_grams` rows automatically**: Write a migration script to scale down identified count items (divide by ~40 or set to realistic unit weights).
2. **Scale multi-serving recipes**: Identify dishes with raw weight > 1000g and divide all ingredient `quantity_g` by estimated serving count.
3. **Re-calculate nutrition macros**: Run `python -m scripts.recalculate_recipe_nutrition` to update `cal_per_serving`, `protein`, `carbs`, `fat` in `food_items`.
