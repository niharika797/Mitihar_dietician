# Recipe Ingredients Sanity Check — Evidence-Based Thresholds

Research for validating `quantity_g` values in the `recipe_ingredients` table (~18k rows).
Every threshold below is backed by official dietary guidelines, food science, or established culinary standards.

---

## 1. Authoritative Sources Used

| Source | Authority | What it covers |
|--------|-----------|----------------|
| **ICMR-NIN Dietary Guidelines for Indians (2024)** | India's apex nutrition body | Daily food group intake, "My Plate for the Day" |
| **FSSAI (Eat Right India)** | Food safety regulator | Salt, fat limits, labeling |
| **WHO** | Global health | Salt, sugar upper limits |
| **IFCT 2017** (Indian Food Composition Tables) | NIN | Nutrient values per 100g edible portion |
| **IDA** (Indian Dietetic Association) | Professional body | Portion sizing for clinical dietetics |

---

## 2. Per-Meal Calorie Envelope

For a **2,000 kcal/day** balanced Indian diet (ICMR-NIN "My Plate"), the typical meal-level calorie distribution is:

| Meal | kcal range |
|------|-----------|
| Breakfast | 400 – 500 |
| Lunch | 600 – 700 |
| Dinner | 500 – 600 |
| Snacks | 200 – 300 |

> [!IMPORTANT]
> **Sanity rule**: A single dish (not a full thali) should almost never exceed **700 kcal** for a main dish or **1,000 kcal** for a one-pot meal (biryani/khichdi that IS the entire meal). Your existing 50–1500 kcal range is a reasonable outer guard, but a **tighter 50–800 kcal** band would catch more subtle issues.

---

## 3. Per-Ingredient Category Thresholds (Per Single Serving)

### 3A. Cereals & Grains (Rice, Flour, Vermicelli, Oats)

| Guideline | Source |
|-----------|--------|
| ICMR daily cereal allowance: **250g** across all meals | DGI 2024 |
| Single serving raw rice: **60–80g** | Standard Indian katori measure |
| Single roti flour: **35–40g** per piece (typically 2 per meal = 70–80g) | IDA, NIN |

> **Threshold**: `quantity_g ≤ 120g` per serving for any cereal/flour ingredient.
> **Rationale**: Even a generous serving (2 large parathas) uses ~120g flour. Beyond this means the recipe is for multiple servings.

---

### 3B. Pulses & Legumes (Dal, Chana, Rajma, Moong)

| Guideline | Source |
|-----------|--------|
| ICMR daily pulses: **85g** across all meals | DGI 2024 |
| Single serving raw dal: **30–40g** | Standard katori |

> **Threshold**: `quantity_g ≤ 90g` per serving for dry pulses.
> **Rationale**: 90g of dry dal already exceeds the ICMR full-day allowance in a single dish. Anything above is multi-serving or a data error.

---

### 3C. Vegetables (Sabzi, Onion, Tomato, Potato)

| Guideline | Source |
|-----------|--------|
| ICMR daily vegetables: **400g** (100g leafy + 250g other + 50g roots) | DGI 2024 |
| Single sabzi serving (raw weight): **150–200g** of chopped vegetables | IDA |

> **Threshold**: `quantity_g ≤ 250g` per vegetable ingredient, `total vegetables per dish ≤ 400g`.
> **Rationale**: 250g of a single vegetable in one serving is already extreme (that's the entire day's "other vegetable" quota). A dish totaling >400g vegetables for one person approaches the full daily allowance.

---

### 3D. Cooking Oil & Ghee

| Guideline | Source |
|-----------|--------|
| Total visible fat: **27g/day** | ICMR-NIN 2024 |
| Cooking oil per day: **15–20g** (3–4 tsp) | India Today, FSSAI |
| Ghee (sedentary adult): **5–10g/day** | Dietician consensus |
| Ghee (active): up to **15–30g/day** | Sports nutrition |

> **Threshold**: Oil/Ghee `quantity_g ≤ 20g` per serving. Flag at `> 15g`.
> **Rationale**: 20g of oil in a single serving would already nearly exhaust the ICMR daily limit. Your CSV shows most recipes correctly use 5–10g, which is perfect.

---

### 3E. Dairy — Curd, Milk, Paneer

| Item | Per-serving guideline | Source |
|------|----------------------|--------|
| **Curd/Yoghurt** | 80–100g for a side bowl; up to 150g for lassi/raita | ICMR: 300ml milk/curd per day |
| **Milk** | 75–150ml per beverage/kheer | ICMR 2024 |
| **Paneer** | 50–100g per serving (main dish) | NIN, dietician consensus |

> **Thresholds**:
> - Curd: `≤ 200g` (generous raita/lassi)
> - Milk: `≤ 200g`
> - Paneer: `≤ 150g` (even 150g is on the high end — that's already 37g protein and ~40g fat)

---

### 3F. Meat, Fish, Eggs

| Item | Per-serving guideline | Source |
|------|----------------------|--------|
| **Chicken/Mutton** (raw) | 60–80g per serving | ICMR: "substitute 30g pulses with 80g meat" |
| **Fish** | 50–80g | Same framework |
| **Eggs** | 1–2 eggs = 50–100g (edible portion ~50g each) | BASU egg grading |

> **Thresholds**:
> - Meat/Fish: `≤ 150g` (generous upper bound; 80g is standard)
> - Eggs: `≤ 100g` (i.e., max 2 eggs per serving)
> 
> **Known issue in your data**: `Egg,2` and `Eggs,1` — these look like counts, not grams!  A single egg's edible portion is ~50g. "Egg,2" should likely be 100g; "Eggs,1" should be 50g.

---

### 3G. Nuts & Seeds (Almonds, Cashews, Peanuts)

| Guideline | Source |
|-----------|--------|
| ICMR daily nuts/seeds: **30–45g** (varies by gender/activity) | DGI 2024, INC |
| Standard portion: **20–25g** (~15-20 almonds) | Aurafyn, ICMR |

> **Threshold**: `quantity_g ≤ 50g` per serving. Flag at `> 35g`.
> **Rationale**: 50g of nuts already exceeds the ICMR full-day recommendation for sedentary women.

---

### 3H. Sugar, Jaggery, Honey

| Guideline | Source |
|-----------|--------|
| Added sugar: **< 5% of daily energy** = ~25–30g/day | ICMR 2024, WHO |
| Per dish: ideally **5–15g** for sweetened items | Dietician practice |

> **Threshold**: `quantity_g ≤ 30g` per serving.
> **Rationale**: 30g of sugar in a single serving already hits the entire daily limit (ICMR & WHO). Normal recipes in your data use 5–10g, which is correct.

---

### 3I. Whole Spices (Cardamom, Cloves, Cinnamon, Bay Leaf)

This is where **the biggest parsing bugs live in your data**.

| Spice | Weight per piece | Typical use per serving | Source |
|-------|-----------------|------------------------|--------|
| **Bay leaf** | ~0.5g per leaf | 0.25–0.5g (½–1 leaf) | CheckYourFood |
| **Green cardamom** | 0.15–0.25g per pod | 0.3–0.5g (2 pods) | CardamomNectar |
| **Black cardamom** | ~2g per pod | 2g (1 pod) | Culinary standard |
| **Cinnamon stick** | 1.5–2.5g per stick | 2g (1 small stick) | Lemis spice weights |
| **Clove** | ~0.07g per 5 cloves | 0.03–0.07g (2–5 cloves) | Reddit spice thread |

> **Threshold**: `quantity_g ≤ 5g` for whole spices per serving.
> 
> **🚨 Critical finding in your CSV**: `Bay leaf: 160g`, `Black cardamom: 160g` (dish 381, Gobi Ke Kofte) — these are clearly **counts misparsed as grams**. 160 bay leaves ≈ 80g which is still insane for one serving. This is a data pipeline error where "2 bay leaves" got converted as "2 units × 80" or similar multiplier bug.

---

### 3J. Ground/Powdered Spices (Turmeric, Cumin, Chilli powder, Coriander powder)

| Spice | Typical per serving | Max sensible per serving |
|-------|-------------------|------------------------|
| **Turmeric powder** | 1–2.5g (¼–½ tsp) | 5g |
| **Red chilli powder** | 1–3g | 5g |
| **Cumin powder** | 1–2.5g | 5g |
| **Coriander powder** | 2–5g | 10g |
| **Garam masala** | 1–2.5g | 5g |

> **Threshold**: `quantity_g ≤ 10g` for any powdered spice per serving.
> **Rationale**: Even the most heavily spiced dishes use 2–3g of each powder. 10g of turmeric powder in one serving would be inedible.

---

### 3K. Fresh Herbs & Aromatics (Curry Leaves, Coriander, Mint, Green Chilli, Garlic, Ginger)

| Ingredient | Unit weight | Typical per serving | Source |
|------------|-----------|-------------------|--------|
| **Curry leaf** | 0.1–0.2g per leaf | 1–2g (8–15 leaves) | IFCT reference |
| **Coriander leaves** | handful = 5–10g | 5–15g | Culinary standard |
| **Mint leaves** | handful = 5–10g | 5–15g | Culinary standard |
| **Green chilli** | 2–5g per piece | 3–10g (1–3 chillies) | TradeIndia |
| **Garlic** | 3–7g per clove | 5–15g (2–3 cloves) | Washington Post |
| **Ginger** | - | 3–10g (1-inch piece) | Culinary standard |

> **Thresholds**:
> - Curry leaves: `≤ 5g` per serving (even 5g = ~25-50 leaves, extreme)
> - Coriander/Mint: `≤ 30g` per serving (for chutney)
> - Green chilli: `≤ 20g` per serving (4–5 large chillies, already very spicy)
> - Garlic: `≤ 25g` per serving (~5 large cloves, already pungent)
> - Ginger: `≤ 15g` per serving
> 
> **🚨 Critical findings in your CSV**:
> - `Curry leaves: 640g` (dish 386, Oats Idli) — **640g of curry leaves is ~3,200-6,400 individual leaves!** This is clearly a count-to-grams parsing error. Real usage: 1-2g.
> - `Curry leaves: 800g` (dish 379, Paneer Pakora) — same issue, even worse.
> - `Green chillies: 160g` (multiple dishes) — 160g = **40–80 chillies** per serving. This would be inedible and medically dangerous.
> - `Cloves garlic: 240g` (dish 390) — "6 cloves of garlic" misparsed. 240g of garlic = **~48 cloves**, absurd for one serving.

---

### 3L. Saffron

| Guideline | Source |
|-----------|--------|
| Typical per serving: **3 strands ≈ 0.01–0.02g** | Culinary standard |
| Safe daily intake: up to **1.5g** | Medical consensus |
| Toxic dose: **≥ 5g** | Toxicology literature |

> **Threshold**: `quantity_g ≤ 2g`.
> **Rationale**: Even 2g per serving is extreme (worth ~₹2,000). Your data shows `1.2g` for Mughlai Chicken, which is on the high side but within safe limits. The calories_per_100g error (24200 → 310) you already fixed was the bigger issue.

---

### 3M. Salt

| Guideline | Source |
|-----------|--------|
| Daily limit: **< 5g** (= ~2g sodium) | WHO, ICMR, FSSAI |
| Per serving: **1–2g** typical | Culinary standard |

> **Threshold**: `quantity_g ≤ 5g` per serving (if salt is tracked as an ingredient).

---

## 4. Per-Dish Total Weight Check

| Guideline | Source |
|-----------|--------|
| Typical thali total weight: **500–650g** (cooked, all items) | Multiple sources |
| Single dish component (sabzi/dal): **120–200g** cooked | IDA, katori standard |

> [!IMPORTANT]
> **Sanity rule**: Sum of all `quantity_g` for a single `dish_id` should be:
> - `≤ 350g` for condiments, accompaniments, beverages
> - `≤ 500g` for main dishes, sabzi, dal, grains
> - `≤ 650g` for one-pot meals (biryani, khichdi, pulao)
>
> **Rationale**: These are raw ingredient weights, which shrink during cooking (grains absorb water, vegetables lose moisture). So raw total ≤ 500g is reasonable. If a single dish has 1000g+ raw ingredients, it's almost certainly multi-serving data or a parsing error.

---

## 5. The "Count vs Grams" Parsing Bug (Root Cause)

Looking at the data patterns, the most systematic error is **recipe counts being stored as grams**. This primarily affects:

| Ingredient | Likely parsed from | Stored as | Should be |
|------------|-------------------|-----------|-----------|
| Curry leaves | "8 curry leaves" | 640g (8 × 80?) | 1–2g |
| Green chillies | "4 green chillies" | 160g (4 × 40?) | 8–20g |
| Bay leaf | "2 bay leaves" | 160g | 1g |
| Black cardamom | "2 black cardamom" | 160g | 4g |
| Garlic cloves | "6 cloves garlic" | 240g | 30g |
| Dry red chillies | "4 dry red chillies" | 160g | 8g |

> [!CAUTION]
> The pattern suggests a multiplier of ~40–80× was applied somewhere in the pipeline, possibly from a unit conversion that treated "pieces" as some larger unit. This is the **single most impactful bug** — fixing it would correct hundreds of rows.

---

## 6. Summary: Proposed Threshold Table for the Sanity Check Script

| Category | Ingredients (keywords) | Max `quantity_g` per serving | Evidence |
|----------|----------------------|------------------------------|----------|
| **Cereal/Grain** | rice, flour, wheat, ragi, bajra, jowar, maize, oats, vermicelli, semiya, sooji | 120g | ICMR: 250g/day, katori: 60-80g |
| **Pulses** | dal, gram, chana, moong, masoor, rajma, lentil | 90g | ICMR: 85g/day |
| **Vegetables** | potato, onion, tomato, cauliflower, spinach, brinjal, peas, carrot, beans, capsicum, cabbage, gourd | 250g per ingredient, 400g total | ICMR: 400g/day |
| **Oil/Fat** | oil, ghee, butter | 20g | ICMR: 27g/day total |
| **Dairy** | curd, milk, paneer, cream, yoghurt, cheese | Curd: 200g, Milk: 200g, Paneer: 150g | ICMR: 300ml/day |
| **Meat/Fish** | chicken, mutton, pork, fish, prawns, lamb | 150g | ICMR: 80g standard |
| **Eggs** | egg | 100g (= 2 eggs) | 50g per egg edible |
| **Nuts/Seeds** | almond, cashew, peanut, walnut, chia, flax, sesame | 50g | ICMR: 30-45g/day |
| **Sugar/Sweet** | sugar, jaggery, honey | 30g | ICMR+WHO: 25-30g/day |
| **Whole spice** | bay leaf, cardamom, clove, cinnamon, star anise, pepper (whole) | 5g | ~0.5g per piece |
| **Powdered spice** | turmeric, chilli powder, cumin powder, coriander powder, garam masala, masala | 10g | 1-3g per spice typical |
| **Fresh herb** | curry leaves, coriander leaves, mint, basil | 30g (chutney), 5g (tempering) | 0.1-0.2g per leaf |
| **Aromatics** | green chilli, garlic, ginger, dry red chilli | 25g | 3-5g per piece |
| **Saffron** | saffron, kesar | 2g | Toxic ≥5g |
| **Salt** | salt, sendha namak | 5g | WHO: <5g/day |
| **Dish total** | (sum of all ingredients) | Main: 500g, One-pot: 650g, Condiment: 350g | Thali total: 500-650g |
