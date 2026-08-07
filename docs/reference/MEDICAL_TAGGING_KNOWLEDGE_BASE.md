# Mityahar Medical Tagging Knowledge Base
**Version:** 1.0 (Session 18A, 2026-06-06)  
**Purpose:** System-prompt context injected into every recipe tagging LLM call. Do not truncate.  
**Maintainer:** Updated when clinical evidence or product decisions change.

---

## HOW TO USE THIS FILE

This knowledge base describes dietary rules for 14 medical conditions relevant to Indian patients. When tagging a recipe:

1. Read the recipe name and its full ingredient list.
2. For each condition, apply the rules below to determine whether the recipe warrants an avoid tag, a prefer tag, or neither.
3. Tags are **binary per condition** — a dish either gets the tag or it doesn't. Confidence expresses uncertainty, not degree.
4. Only assign tags from the **valid tag list** at the bottom of this file. No invented tags.
5. When in doubt about a borderline dish, assign a low confidence score (0.3–0.5) rather than omitting the tag entirely.
6. **Cooking method matters.** The same ingredient deep-fried vs. steamed behaves differently — apply method sensitivity rules where specified.

---

## VALID TAG LIST

```
avoid_diabetes         — recipe should be avoided by Type 2 Diabetic / Pre-diabetic patients
diabetes_friendly      — recipe is appropriate / beneficial for Type 2 Diabetic / Pre-diabetic patients
avoid_hypertension     — recipe should be avoided by hypertensive patients
heart_friendly         — recipe is appropriate for hypertensive / heart disease patients (shared tag)
avoid_hypothyroid      — recipe should be avoided by hypothyroid patients
thyroid_support        — recipe supports thyroid health
avoid_hyperthyroid     — recipe should be avoided by hyperthyroid patients
avoid_pcos             — recipe should be avoided by PCOS/PCOD patients
pcos_friendly          — recipe is appropriate / beneficial for PCOS/PCOD patients
avoid_highchol         — recipe should be avoided by high cholesterol patients
cholesterol_friendly   — recipe supports healthy cholesterol levels
avoid_kidney           — recipe should be avoided by kidney disease patients
avoid_gluten           — recipe contains gluten (Celiac / gluten-intolerant patients must avoid)
gluten_free            — recipe is confirmed gluten-free
avoid_ibs              — recipe should be avoided by IBS/IBD patients
gut_friendly           — recipe is gentle on the gut / supports gut health
avoid_fattyliver       — recipe should be avoided by fatty liver patients
liver_friendly         — recipe supports liver health
avoid_gout             — recipe should be avoided by gout patients
calcium_rich           — recipe provides meaningful calcium (Osteoporosis benefit)
iron_rich              — recipe provides meaningful iron (Anemia benefit)
avoid_heart            — recipe should be avoided by heart disease patients
```

**Note:** `heart_friendly` is shared between Hypertension and Heart Disease — a recipe tagged `heart_friendly` benefits both conditions.  
**Note:** `avoid_heart` and `avoid_hypertension` are separate tags. A dish may warrant one but not both (e.g., high-sodium dish gets `avoid_hypertension` but may not warrant `avoid_heart` unless it also has saturated fat or cholesterol concerns).

---

## CONDITION 1 — TYPE 2 DIABETES / PRE-DIABETES

**Tags:** `avoid_diabetes` | `diabetes_friendly`

### What it is
Type 2 diabetes is characterized by insulin resistance and impaired glucose uptake. Diet directly controls post-meal blood glucose spikes (postprandial glycemia). Pre-diabetes is the same mechanism at lower severity — dietary intervention can reverse it. The core dietary goal is glycemic control: minimize rapid glucose surges, maintain stable blood sugar, support insulin sensitivity.

### Glycemic Index (GI) Guidance
GI measures how fast a food raises blood glucose compared to pure glucose (GI=100). GL (Glycemic Load) = GI × carb content per serving / 100.

| GI Range | Category | Examples |
|----------|----------|---------|
| ≤55 | Low (preferred) | Most lentils, most vegetables, oats, barley |
| 56–69 | Medium (moderate) | Basmati rice, whole wheat, banana |
| ≥70 | High (avoid) | White rice (short grain), maida, sugar, white bread |

**Critical distinction:** Cooking method shifts GI. Overcooked rice has higher GI than al-dente. Cooling cooked rice increases resistant starch, lowering GI. Deep-frying increases calorie density without meaningful GI change but worsens insulin resistance through saturated/trans fat load.

### Ingredients / Foods to AVOID (assign `avoid_diabetes`)
- **White sugar, jaggery, honey, glucose** — direct glucose spike. Even small amounts in a main dish warrant caution. Exception: trace amounts of sugar used purely as a cooking agent (e.g., 1 tsp in a curry for color) don't typically warrant the tag.
- **Maida (refined white flour)** — GI ~70–85, spike-inducing. Any maida-heavy dish: puri, naan, paratha made with maida, samosa shell, kachori, bread (white), pasta (white).
- **White rice (short grain / polished)** — GI 70–80. Large-portion rice dishes, plain white rice, rice in pulao/biryani is borderline.
- **Refined oils in excess + deep frying** — deep-fried snacks (bhatura, poori, pakora, vada, samosa, kachori, jalebi) worsen insulin resistance via saturated fat load and calorie density.
- **High-sugar sweets** — halwa (suji/atta), kheer, payasam, gulab jamun, rasgulla, barfi, ladoo, jalebi.
- **Processed foods** — instant noodles, chips, biscuits — if present in ingredient list.
- **Full-fat dairy in large quantities** — cream-heavy curries, malai-heavy dishes.
- **High-GI fruits in large amounts** — ripe banana (as main component), mango (not as trace).
- **Cornstarch (corn flour) in large amounts** — used as thickener; if dominant, note.

### Ingredients / Foods BENEFICIAL (assign `diabetes_friendly`)
- **Lentils and legumes** — all dals (masoor, moong, chana, arhar), chana, rajma, lobiya. Low GI (20–40), high fiber, slow glucose release. Moong dal especially good — GI ~38.
- **Non-starchy vegetables** — palak, methi, karela (bitter gourd), lauki (bottle gourd), tinda, turai, beans, cabbage, cauliflower, broccoli (if used), drumstick (sahjan), curry leaves.
- **Whole grains** — atta (whole wheat), bajra, jowar, ragi (finger millet), oats. Bajra has GI ~55; ragi ~55; all better than maida.
- **Fenugreek (methi)** — both seeds and leaves. Seeds have been clinically shown to slow glucose absorption (contain galactomannan fiber). Seeds > leaves for glycemic effect, but leaves still beneficial.
- **Bitter gourd (karela)** — contains charantin and polypeptide-P, both shown to lower blood glucose. High confidence for `diabetes_friendly`.
- **Amla (Indian gooseberry)** — chromium content improves insulin sensitivity. Strong evidence.
- **Curry leaves** — alkaloid mahanimbine has anti-diabetic properties in multiple studies.
- **Turmeric (haldi)** — curcumin improves insulin sensitivity.
- **Cinnamon (dalchini)** — modest but meaningful blood sugar lowering (1–2 tsp/day range; as spice in a dish, assign if prominent).
- **Basmati rice (small portion)** — GI ~50–58, lower than regular white rice. Borderline; if portion is small and dish has dal/vegetable protein balance, can still be `diabetes_friendly`. Ambiguous — lower confidence.
- **Oats / barley (jau)** — beta-glucan fiber slows glucose absorption.
- **Nuts (moderate)** — almonds, walnuts — improve insulin sensitivity. If dish is nut-based snack, applicable.

### Indian-Specific Rules
- **Karela (bitter gourd)** any preparation: strong `diabetes_friendly` regardless of cooking method (including stuffed karela, karela sabzi, karela chips — even fried karela loses some benefit but retains the active compounds more than other vegetables would).
- **Methi (fenugreek) seeds in a dish** — e.g., methi seeds in tadka, methi thepla, methi paratha — `diabetes_friendly` leaning even though thepla has whole wheat.
- **Suji (semolina) dishes** — upma, suji halwa, rava idli. Suji GI ~60–70; without sugar it's borderline. Suji halwa with sugar = `avoid_diabetes`. Rava idli (fermented) or upma (vegetable-heavy) = borderline.
- **Idli/dosa/uttapam** — fermented; GI reduced by fermentation. Plain idli GI ~77 (still moderately high). Idli with sambar = combined GI lower. These are ambiguous; assign lower confidence.
- **Poha** — flattened rice, GI ~70. Poha dishes are borderline — vegetable poha is better than plain poha.
- **Rajma-chawal** — rajma (GI ~29) balances rice (GI ~72). Combined dish is borderline — medium confidence on avoid.
- **Biryani** — rice-heavy, high GI, often high fat. `avoid_diabetes` with high confidence.
- **Puri / bhatura / poori** — deep-fried maida: strong `avoid_diabetes`.
- **Chapati/roti (whole wheat)** — GI ~62; medium. Not an avoid. Can be `diabetes_friendly` if combined with dal/vegetable.

### Edge Cases and Ambiguous Foods
- Banana in a small quantity as garnish vs. banana as main ingredient in a smoothie/dessert.
- Rice with curd (dahi rice) — probiotic effect of dahi may slightly moderate GI response.
- Sabudana (tapioca) — GI ~70. Sabudana khichdi avoids `diabetes_friendly`; is borderline for avoid depending on portion.
- Corn (maize) — medium GI ~52; not a strong avoid but not beneficial.
- Peanuts — low GI, good fat; can be `diabetes_friendly` even though calorie-dense.
- Coconut (fresh) — medium-chain fatty acids; fiber; not an avoid for diabetes unless dish is very high-calorie.

---

## CONDITION 2 — HYPERTENSION

**Tags:** `avoid_hypertension` | `heart_friendly`

### What it is
Hypertension (high blood pressure) is driven primarily by sodium retention, arterial stiffness, and endothelial dysfunction. Diet intervention focuses on sodium reduction (DASH diet: <1500mg/day for hypertension), potassium increase (counteracts sodium), magnesium, and omega-3s. Secondary factor: saturated fats worsen arterial health.

### Ingredients / Foods to AVOID (assign `avoid_hypertension`)
- **High sodium foods** — pickles (achaar), papad, chips, salty snacks, preserved/processed meats, canned goods if visible.
- **Pickle (achaar)** — any achaar: mango achaar, lemon achaar, mixed achaar. Extremely high sodium. Strong `avoid_hypertension`.
- **Papad / Pappad** — very high sodium per serving.
- **Salty snacks** — namkeen, bhujia, sev, chakli — high sodium.
- **Excess table salt in recipes** — recipes described as "salty" or with large amounts of salt.
- **Processed cheese** — high sodium.
- **Soy sauce, sambar masala in large quantities** — both sodium-heavy if prominent ingredient.
- **Processed meats** — rare in this database but flag if present.
- **Deep-fried fatty foods** — worsens arterial health (secondary to sodium concern).

### Ingredients / Foods BENEFICIAL (assign `heart_friendly`)
- **Potassium-rich vegetables** — palak, tomato, potato (with skin — though cooking usually removes skin), banana (as side).
- **Garlic (lahsun)** — allicin shown to reduce blood pressure. Any dish with significant garlic is beneficial.
- **Leafy greens** — palak, methi, coriander (fresh) — magnesium, potassium, nitrates.
- **Flaxseeds (alsi)** — omega-3, lignans, blood pressure benefit.
- **Oats / barley (jau)** — beta-glucan lowers BP.
- **Low-sodium, vegetable-heavy dishes** — plain dal, sabzi without papad/pickle accompaniment.
- **Amla** — antioxidants, vasodilation.
- **Turmeric** — anti-inflammatory, modest BP benefit.
- **Coriander seeds / leaves** — mild diuretic effect.
- **Curd (dahi, low-fat)** — potassium, magnesium. Probiotic benefit for blood pressure.
- **Tomato** — lycopene, potassium.
- **Cucumber** — very low sodium, hydrating.

### Indian-Specific Rules
- **Achaar** — always `avoid_hypertension` regardless of the main dish. If a dish's name or ingredient list includes any kind of pickle/achaar, tag it.
- **Rasam** — tamarind, tomato base, significant salt. Borderline — traditional rasam can be high-sodium; assign low confidence avoid.
- **Sambar** — usually moderate sodium. Not strongly either direction. Avoid only if recipe description mentions heavy salt/papad accompaniment.
- **Buttermilk (chaas)** — potassium, probiotic; `heart_friendly`. Very low fat if made from low-fat curd.
- **Lassi (salted, sweet)** — salted lassi: borderline on sodium. Sweet lassi: not an avoid for hypertension specifically.
- **Coconut water (nariyal pani)** — potassium-rich; `heart_friendly`.
- **Sattu** — high fiber, minerals including potassium; beneficial.

### Edge Cases
- Tamarind (imli) — tangy, not high-sodium by itself; no tag solely for tamarind.
- Mustard seeds in tadka — trace sodium, beneficial phytochemicals; not an avoid.
- Indian bread (roti, chapati) without salt added — not an avoid.
- Biryani — typically moderate-high sodium from spice mixes; assign borderline avoid.

---

## CONDITION 3 — HYPOTHYROIDISM

**Tags:** `avoid_hypothyroid` | `thyroid_support`

### What it is
Hypothyroidism = underactive thyroid, insufficient T3/T4 hormone production. Often due to Hashimoto's (autoimmune) or iodine deficiency. Diet matters for: iodine sufficiency, avoiding goitrogens (compounds that inhibit thyroid hormone synthesis), selenium and zinc (cofactors for thyroid hormone production), and anti-inflammatory support for Hashimoto's.

### Goitrogens — The Core Issue
Goitrogens are compounds that interfere with iodine uptake or thyroid peroxidase activity. **Cooking significantly reduces goitrogenic activity** — raw goitrogenic foods are far more problematic than cooked ones. For Indian cuisine where most cruciferous vegetables are cooked, the concern is moderated but not eliminated.

**High-goitrogen foods (raw = strong problem; cooked = moderate):**
- Cruciferous vegetables: cauliflower (phool gobi), cabbage (patta gobi), broccoli, kale, Brussels sprouts, bok choy
- Soy-based foods: soy milk, tofu, edamame, soy flour, soy-heavy preparations
- Millet (bajra, jowar) — bajra contains goitrogenic flavonoids (C-glycosyl flavonoids). This is **significant** — heavy bajra consumption (e.g., bajra roti as staple) can worsen hypothyroidism.
- Turnip (shalgam)
- Radish (mooli) — moderate goitrogen in large raw amounts

**Moderate goitrogens (context-dependent):**
- Peanuts — contain goitrogens; in large daily amounts can be a concern
- Sweet potato — mild goitrogen; unlikely to be clinically significant in normal portions
- Peaches, strawberries — minor; rarely clinically relevant in Indian dishes

### Ingredients / Foods to AVOID (assign `avoid_hypothyroid`)
- **Raw cruciferous vegetables in large amounts** — most Indian dishes cook cruciferous veg, so assign only when raw (e.g., raw salad with cabbage, raw cauliflower).
- **Cooked cruciferous in very large portions** — gobi sabzi, cabbage subzi may warrant low-confidence avoid.
- **Bajra (pearl millet) as dominant grain** — bajra roti, bajra khichdi — moderate-confidence `avoid_hypothyroid` due to goitrogenic flavonoids.
- **Soy-heavy dishes** — tofu-heavy, soy milk-based — moderate confidence. Note: soy sauce in trace amounts (e.g., Indo-Chinese dishes) may not be clinically relevant.
- **Processed/refined foods** — worsen inflammation, worsen Hashimoto's. Maida-heavy, fried items are secondary avoid.

### Ingredients / Foods BENEFICIAL (assign `thyroid_support`)
- **Iodine sources** — seaweed/nori (rare in Indian cuisine), iodized salt (assumed in most dishes; not a strong signal). Fish if present.
- **Selenium-rich foods** — Brazil nuts (rare), eggs (if present), fish. Selenium is essential for T4→T3 conversion.
- **Zinc sources** — pumpkin seeds, chickpeas, lentils, meat.
- **Turmeric** — anti-inflammatory; beneficial for Hashimoto's.
- **Ashwagandha** — if present (some traditional dishes / churna); adaptogens support thyroid.
- **Coconut oil/coconut** — medium-chain fats support thyroid function and metabolism. Coconut-based curries can be mild `thyroid_support`.
- **Non-goitrogenic vegetables** — palak (spinach), drumstick (moringa/sahjan), tomato, carrot, beetroot; all fine.
- **Eggs** — selenium, zinc. `thyroid_support` if egg is main ingredient.
- **Lentils (non-goitrogenic legumes)** — moong dal, masoor dal, chana dal — generally fine; not goitrogenic. Can be `thyroid_support` for selenium/zinc contribution.
- **Brazil nuts** — extreme selenium density; unlikely in Indian recipes but flag if present.
- **Moringa (drumstick leaves / sahjan ke patte)** — concentrated micronutrients including selenium.

### Indian-Specific Rules
- **Bajra roti** — `avoid_hypothyroid` (moderate confidence, 0.6–0.7). Bajra is a staple in Rajasthan and Gujarat; should be limited for hypothyroid patients. This is the most clinically important Indian-specific rule for this condition.
- **Fenugreek (methi)** — generally beneficial; not a goitrogen concern. `thyroid_support` if featured.
- **Jowar (sorghum)** — also contains mild goitrogens. Jowar roti — lower confidence avoid than bajra.
- **Ragi (finger millet)** — contains goitrogens but less than bajra. Ragi dishes — very low confidence avoid (many nutritionists still recommend ragi for thyroid patients because other benefits outweigh mild goitrogen content when iodine is adequate).
- **Spinach (palak)** — raw spinach has oxalates that can slightly interfere with iodine uptake, but cooked palak is fine and beneficial. Palak sabzi = no concern.
- **Cabbage (patta gobi)** — cooked: mild concern, low confidence avoid. Raw in chaat/salad: moderate concern.
- **Cauliflower (phool gobi)** — cooked (gobi sabzi, aloo gobi): borderline. Most nutritionists say cooked cruciferous is fine in moderate amounts. Assign very low confidence if at all.

### Edge Cases
- Gobi aloo / gobi paratha — cooked cauliflower; in Indian context where it's always cooked, most practitioners don't restrict this. Low confidence avoid (0.3).
- Soybean curry — moderate avoid confidence (0.6).
- Mixed dals — no individual dal is a goitrogen; don't tag.

---

## CONDITION 4 — HYPERTHYROIDISM

**Tags:** `avoid_hyperthyroid`

### What it is
Hyperthyroidism = overactive thyroid producing excess T3/T4. Graves' disease is the most common cause. The dietary goal is to AVOID stimulating thyroid further: reduce iodine-rich foods (paradoxically, the foods that help hypothyroid hurt hyperthyroid), and include goitrogens as therapeutic foods (the opposite of hypothyroid).

### Ingredients / Foods to AVOID (assign `avoid_hyperthyroid`)
- **High-iodine foods** — seaweed, kelp (rare in Indian cuisine), fish (especially seafood), iodine-fortified foods. If seafood is a main ingredient, tag it.
- **Caffeine** — stimulates thyroid. Coffee, strong tea — but these are beverages, less relevant.
- **Alcohol** — if present.
- **Highly spiced foods that stimulate metabolism** — e.g., very heavy use of hot peppers, mustard in large amounts.
- **Soy in large amounts** — can affect hormone balance in hyperthyroid too (but rationale differs from hypothyroid — isoflavones block thyroid hormone uptake at high doses).
- **Iodized salt** — in theory, but reducing salt is hard to enforce via dish-level tagging. Only tag if recipe specifically mentions large salt quantities.

### Indian-Specific Rules
- **Fish curries / prawn dishes** — if seafood is present, `avoid_hyperthyroid` (iodine).
- **Cruciferous vegetables (gobi, cabbage)** — BENEFICIAL for hyperthyroid (goitrogens suppress excess hormone production), so AVOID tagging these with `avoid_hyperthyroid`. The opposite of hypothyroid.
- **Bajra / jowar dishes** — potentially beneficial for hyperthyroid (goitrogens), so no avoid tag.
- Most Indian vegetarian dishes do NOT warrant `avoid_hyperthyroid` because the primary concern is iodine. Apply only when seafood or very high-iodine foods are prominent.

### Note on avoid_hyperthyroid tagging
This tag will be the least commonly applied for standard Indian vegetarian cuisine. It is primarily for: seafood dishes, seaweed, kelp, and very high-caffeine preparations.

---

## CONDITION 5 — PCOS/PCOD

**Tags:** `avoid_pcos` | `pcos_friendly`

### What it is
Polycystic Ovary Syndrome is characterized by insulin resistance (in ~70% of cases), hormonal imbalance (elevated androgens), chronic low-grade inflammation, and metabolic dysfunction. Diet intervention: insulin sensitization (similar to pre-diabetes management), anti-inflammatory diet, support hormonal balance. PCOS-friendly diet heavily overlaps with diabetic-friendly diet but also emphasizes anti-inflammatory foods and phytoestrogenic foods.

### Ingredients / Foods to AVOID (assign `avoid_pcos`)
- **Refined carbohydrates** — maida, white sugar, white rice, instant noodles. Same as diabetes avoid list.
- **Deep-fried foods** — samosa, vada, pakora, bhatura, poori — inflammatory, worsen insulin resistance.
- **High-sugar sweets** — halwa, kheer, mithai, jalebi — insulin spike + androgen elevation.
- **Processed foods** — trans fats, preservatives, excess additives — worsen inflammation.
- **Full-fat dairy (in excess)** — controversial; some evidence links dairy to androgen elevation in PCOS. High-fat cream, malai-heavy dishes — moderate confidence avoid.
- **Soy in large amounts** — phytoestrogens in soy can worsen hormonal imbalance in PCOS (but evidence mixed — low confidence avoid, assign only for very soy-heavy dishes).
- **Red meat (if present)** — saturated fat, inflammatory; moderate confidence avoid if dominant ingredient.

### Ingredients / Foods BENEFICIAL (assign `pcos_friendly`)
- **Anti-inflammatory foods** — turmeric (curcumin), ginger, cinnamon, omega-3 sources.
- **High-fiber foods** — all lentils, legumes, vegetables. Fiber improves insulin sensitivity and reduces androgen impact.
- **Cinnamon (dalchini)** — clinically shown to improve menstrual regularity and insulin sensitivity in PCOS. Dishes with prominent cinnamon.
- **Spearmint (pudina)** — spearmint reduces androgens in PCOS. Pudina-heavy dishes, pudina chutney.
- **Fenugreek (methi)** — strong evidence for PCOS; regulates blood sugar and may reduce androgen levels. Methi seeds and leaves both beneficial.
- **Flaxseeds (alsi)** — lignans regulate estrogen metabolism. Flaxseed chutney, flaxseed in upma etc.
- **Walnuts** — anti-inflammatory omega-3, reduces sex hormone-binding globulin.
- **Almonds** — reduce fasting insulin. Dishes with almonds (not deep-fried).
- **Leafy greens** — palak, methi leaves — folate, magnesium; anti-inflammatory.
- **Berries / amla** — antioxidants; anti-inflammatory. Amla is particularly beneficial.
- **Whole grains** — jowar, bajra (moderate), ragi, oats — slow insulin response.
- **Chickpeas (chana)** — high protein, high fiber; excellent insulin regulation.
- **Moong dal / sprouts** — low GI, anti-inflammatory.
- **Ashwagandha** — if present; adaptogen, reduces cortisol, supports hormonal balance.

### Indian-Specific Rules
- **Fenugreek (methi)** is critical for PCOS — both seeds and leaves. Methi dal, methi paratha, methi sabzi → `pcos_friendly`.
- **Moringa (sahjan / drumstick)** — nutrient density, antioxidants; `pcos_friendly`.
- **Turmeric (haldi)** as prominent spice — any dish where turmeric is a featured ingredient (not just trace seasoning) can contribute to `pcos_friendly`.
- **Bajra** — for PCOS, bajra is not a strong avoid (unlike hypothyroid). It's a whole grain; moderate GI. Treat as neutral to mildly beneficial.
- **Biryani** — avoid_pcos (refined rice, high fat, often high calorie).
- **Curd (dahi)** — low-fat dahi is beneficial for PCOS (probiotic, reduces inflammation). Full-fat cream-heavy dishes: borderline avoid.
- **Soy** — the goitrogen concern doesn't apply here, but the phytoestrogen concern is real for PCOS. Large-quantity soy: assign low-confidence avoid_pcos. Trace soy (soy sauce in one dish): skip.

### Edge Cases
- Paneer — moderate dairy; some PCOS protocols avoid it, others allow low-fat paneer. Low confidence on either tag. Don't tag paneer dishes unless they are cream-heavy.
- Idli/dosa — fermented, lower GI; borderline. Not a strong avoid for PCOS.
- Rajma — high fiber, anti-inflammatory; lean toward `pcos_friendly`.

---

## CONDITION 6 — HIGH CHOLESTEROL (HYPERLIPIDEMIA)

**Tags:** `avoid_highchol` | `cholesterol_friendly`

### What it is
High LDL cholesterol and/or low HDL cholesterol increases cardiovascular risk. Dietary management: reduce saturated fat, eliminate trans fat, increase soluble fiber (binds cholesterol in gut), increase omega-3s (raise HDL, lower triglycerides), and reduce dietary cholesterol (eggs, full-fat dairy) in sensitive individuals.

### Ingredients / Foods to AVOID (assign `avoid_highchol`)
- **Saturated fat sources** — full-fat dairy (cream, malai, full-fat paneer), ghee in large amounts (ghee itself is not an avoid in moderation — nuance below), coconut oil/coconut cream in large quantities, palm oil.
- **Trans fats** — vanaspati (vegetable shortening / hydrogenated oil), commercially fried foods, commercial baked goods. Vanaspati is explicitly `avoid_highchol` — high confidence.
- **Deep-fried foods in any oil** — even if cooked in healthier oils; the oxidation products worsen lipid profiles.
- **High dietary cholesterol** — egg yolk in large amounts (one whole egg per day is generally fine; multiple yolks or egg-heavy dishes warrant tagging), organ meats if present.
- **High-sugar foods** — refined carbs raise triglycerides and lower HDL.
- **Red meat** — if present; saturated fat.

### Ingredients / Foods BENEFICIAL (assign `cholesterol_friendly`)
- **Soluble fiber** — oats (beta-glucan), barley (jau), all dals and legumes, okra (bhindi), eggplant (baingan), flaxseeds.
- **Omega-3 sources** — flaxseeds (alsi), walnuts, fish (if present).
- **Garlic** — significantly lowers LDL. Any dish with substantial garlic.
- **Onion** — quercetin; mild LDL-lowering. Supportive, not strongly sufficient alone.
- **Coriander seeds** — shown in studies to raise HDL and lower LDL. Dishes with coriander as prominent ingredient.
- **Fenugreek seeds** — saponins bind cholesterol in gut; meaningful effect.
- **Amla** — antioxidants prevent LDL oxidation; reduces triglycerides.
- **Turmeric** — curcumin reduces LDL oxidation.
- **Plant sterols** — found in chickpeas, rajma, all legumes — block cholesterol absorption in gut.
- **Nuts (almonds, walnuts)** — lower LDL; raise HDL. Dishes with almonds/walnuts as main ingredient (not deep-fried nuts).
- **Whole grains** — atta, oats, ragi.

### Indian-Specific Rules
- **Ghee** — nuance is critical. Ghee is saturated fat but contains butyrate and conjugated linoleic acid (CLA). 1–2 tsp on a roti is not an `avoid_highchol` trigger. A dish *cooked in large quantities of ghee* (halwa, ghee-drenched biryani) warrants the tag. The key signal: is ghee a main ingredient vs. trace condiment?
- **Coconut-based curries (Kerala, South Indian)** — coconut cream/milk in large amounts: moderate `avoid_highchol`. Fresh grated coconut in chutney: low concern, don't tag.
- **Dals (all types)** — strong `cholesterol_friendly`. Consistent across types.
- **Rajma (kidney beans)** — high soluble fiber; strong `cholesterol_friendly`.
- **Bhindi (okra)** — viscous mucilage fiber binds cholesterol in gut; `cholesterol_friendly`.
- **Baingan (eggplant/brinjal)** — chlorogenic acid inhibits lipid peroxidation; `cholesterol_friendly`.
- **Vanaspati** — if listed as an ingredient, strong `avoid_highchol`. Many older Indian recipes use vanaspati.
- **Full-fat paneer** — made from full-fat milk; moderate saturated fat. A paneer dish once in a while is not strongly `avoid_highchol` unless cream-heavy. Creamy paneer curries (shahi paneer, paneer butter masala) warrant moderate confidence avoid.

### Edge Cases
- Egg dishes — one egg (whole) as a minor ingredient: no tag. Multiple eggs or yolk-heavy dish: moderate confidence avoid.
- Almond halwa — almonds are beneficial, but if it's swimming in ghee and sugar, it's still `avoid_highchol`.

---

## CONDITION 7 — KIDNEY DISEASE (CHRONIC KIDNEY DISEASE, CKD)

**Tags:** `avoid_kidney`

### What it is
CKD involves progressive loss of kidney function. Damaged kidneys cannot filter waste products, fluid, electrolytes (potassium, phosphorus, sodium) efficiently. Dietary management is stage-dependent but generally: restrict potassium, phosphorus, sodium, and protein (to reduce waste load on kidneys). Oxalates also a concern (prevent kidney stones).

This is one of the most restrictive dietary conditions — many nutritious foods that are beneficial for other conditions must be avoided.

### Ingredients / Foods to AVOID (assign `avoid_kidney`)
- **High-potassium foods** — bananas, tomatoes, potatoes, sweet potatoes, spinach (palak), avocado, dried fruits, coconut water. **Note:** cooking and draining/discarding water reduces potassium content (by leaching). But for simplicity, flag high-K ingredient dishes.
- **High-phosphorus foods** — dairy (milk, paneer, dahi in large amounts), nuts, seeds, bran, whole grain bread, processed foods with phosphate additives.
- **High-protein concentration** — large amounts of meat, eggs, pulses (lentils, rajma, chana) in CKD reduce GFR if eaten in large quantities. **This is context-dependent by CKD stage.** For tagging purposes: heavily lentil/legume-dominant dishes warrant moderate-confidence avoid.
- **High-sodium foods** — see hypertension list; sodium worsens kidney fluid overload.
- **Oxalate-rich foods** — spinach (palak), beets (chukandar), nuts, chocolate, sweet potatoes, swiss chard. High-oxalate foods increase kidney stone risk.
- **Potassium-rich vegetables** — palak, tomato, potato; if dominant.

### Indian-Specific Rules
- **Palak (spinach) dishes** — palak paneer, saag — HIGH potassium AND high oxalate. Strong `avoid_kidney`.
- **Rajma** — high potassium, high phosphorus, high protein. `avoid_kidney` with high confidence.
- **Chana (chickpeas)** — high phosphorus and potassium. `avoid_kidney`.
- **Banana (as main ingredient)** — very high potassium. `avoid_kidney`.
- **Tomato-heavy dishes** — rasam, tomato sabzi; moderate potassium concern.
- **Full-fat dairy** — paneer, dahi, malai in large amounts — high phosphorus. Dairy-heavy dishes: `avoid_kidney`.
- **Dal (any)** — in CKD, even lentils are restricted because protein and phosphorus. Moderate confidence `avoid_kidney` for dal dishes.
- **Sattu** — very high potassium and protein; `avoid_kidney`.
- **Coconut water** — high potassium; `avoid_kidney`.
- **Lauki (bottle gourd)** — LOW in potassium and phosphorus; relatively safe for CKD. One of few vegetables that is NOT `avoid_kidney`. Don't tag lauki-based dishes.
- **White rice (plain)** — low potassium, low phosphorus, low protein. Actually recommended for CKD (refined, low-nutrient for this specific condition). Do NOT tag plain rice or simple rice dishes with `avoid_kidney`.
- **Cabbage (patta gobi)** — low in potassium; generally CKD-safe. Don't tag cabbage dishes.
- **Cucumber, radish, onion** — low potassium; CKD-safe.
- **Maida items** — moderate phosphorus concern (from refined flour). Low confidence avoid.

### Edge Cases
- Tamarind — high potassium; moderate confidence avoid.
- Amla — high Vitamin C but also potassium; low-moderate confidence avoid.
- Beetroot — very high potassium and oxalate; strong `avoid_kidney`.

---

## CONDITION 8 — CELIAC DISEASE / GLUTEN INTOLERANCE

**Tags:** `avoid_gluten` | `gluten_free`

### What it is
Celiac disease is an autoimmune disorder where gluten (a protein in wheat, barley, rye) triggers intestinal damage. Even trace amounts cause damage. Non-celiac gluten sensitivity has similar symptoms without autoimmune component. Strict zero-tolerance for gluten.

### Gluten-Containing Ingredients (assign `avoid_gluten`)
- **Wheat** in all forms: atta, maida, suji/rava (semolina), wheat flour, whole wheat flour.
- **Barley (jau)** — contains gluten (hordein). Barley water, barley-based dishes.
- **Rye** — rare in Indian cuisine.
- **Any bread, chapati, roti, paratha, puri, naan, bhatura** — made from wheat flour.
- **Suji/rava dishes** — upma, rava idli, rava dosa — all contain semolina (wheat-derived). **Important Indian rule.**
- **Seitan** — pure gluten; very rare but flag if present.
- **Soy sauce** — most commercial soy sauce contains wheat. If soy sauce is an ingredient, assign `avoid_gluten`.
- **Commercial masalas/spice mixes** — some use wheat as filler/binding agent. Moderate confidence if commercial masala is listed as ingredient.
- **Oats** — oats themselves don't contain gluten but are almost always cross-contaminated in Indian markets. Assign `avoid_gluten` to oat-based dishes unless "certified gluten-free oats" is specified.

### Gluten-Free Foods (assign `gluten_free`)
- **Naturally gluten-free grains** — rice, bajra, jowar, ragi, corn, sabudana, buckwheat (kuttu), amaranth (rajgira).
- **All lentils and legumes** — dal, rajma, chana, moong, masoor — gluten-free.
- **All fresh vegetables and fruits** — gluten-free.
- **All dairy (plain)** — milk, paneer, dahi, ghee — gluten-free.
- **Kuttu (buckwheat) dishes** — kuttu ki roti, kuttu ka atta — strongly `gluten_free`. Note: buckwheat is NOT wheat, despite the name.
- **Rajgira (amaranth)** — gluten-free; used in vrat (fasting) foods.
- **Sabudana dishes** — sabudana khichdi, sabudana vada — gluten-free (though vada is fried).
- **Rice dishes** — plain rice, biryani (if no wheat thickeners), pulao — `gluten_free`.
- **Idli, plain dosa (rice + urad dal batter)** — naturally gluten-free. **Important Indian rule.** But dosa at restaurants may use maida — tag if no maida in ingredient list.

### Indian-Specific Rules
- **Suji/rava** is semolina = wheat-derived. All rava/suji dishes: `avoid_gluten`. Rava idli, rava dosa, suji upma, suji halwa — all gluten-containing despite not looking like "bread."
- **Ragi (finger millet)** — naturally gluten-free. Ragi roti, ragi mudde — `gluten_free`.
- **Jowar (sorghum) roti** — `gluten_free`. Common in Maharashtra/Karnataka.
- **Bajra roti** — `gluten_free`.
- **Kuttu roti (navratri/vrat)** — `gluten_free`.
- **Besan (chickpea flour)** — naturally gluten-free. Besan chilla, besan kadhi — `gluten_free`.
- **Rajgira chikki, amaranth dishes** — `gluten_free`.
- **Poha (flattened rice)** — rice-derived; `gluten_free` unless rava is added.
- **Thepla** — typically made with atta (wheat) — `avoid_gluten`.
- **Missi roti** — besan + atta mix — `avoid_gluten` (contains atta).
- **Dhokla** — made from fermented rice and dal batter — `gluten_free`.
- **Khaman dhokla** — besan-based — `gluten_free`.
- **Aloo tikki (plain)** — potato, spices — usually `gluten_free`. If bound with maida/bread crumbs: `avoid_gluten`.

---

## CONDITION 9 — IBS / IBD (IRRITABLE BOWEL SYNDROME / INFLAMMATORY BOWEL DISEASE)

**Tags:** `avoid_ibs` | `gut_friendly`

### What it is
IBS = functional gut disorder with altered motility; symptoms: bloating, cramping, diarrhea, constipation. IBD = structural inflammation (Crohn's, Ulcerative Colitis). Both respond to dietary modification. The Low FODMAP diet is the gold standard for IBS management. For IBD: anti-inflammatory, low-fiber during flares, gentle foods.

### FODMAP — Key Concept
FODMAPs = Fermentable Oligosaccharides, Disaccharides, Monosaccharides, and Polyols. These are poorly absorbed short-chain carbohydrates that ferment in the colon, causing gas, bloating, and pain in sensitive individuals.

**High FODMAP (trigger for IBS — assign `avoid_ibs`):**
- Fructose in excess: mango, apple, honey, high fructose corn syrup (in large amounts)
- Lactose: fresh milk, paneer in large amounts, dahi in large amounts, ice cream
- Fructans: wheat/maida (yes, even from a FODMAP perspective), onion, garlic, leek, spring onion (the white part), shallots
- GOS (galacto-oligosaccharides): lentils, chickpeas, rajma, all dals — high FODMAP
- Polyols: stone fruits (peach, plum, cherry), mushrooms, cauliflower, avocado

**Low FODMAP (gut-friendly — assign `gut_friendly`):**
- Rice (all types), oats, polenta, quinoa
- Most herbs and spices (small quantities)
- Bell peppers, cucumber, carrot, zucchini, lettuce, cabbage (moderate)
- Citrus fruits, strawberries, blueberries
- Lactose-free dairy, firm cheeses (in small amounts), coconut milk (canned, small portions)
- Tofu (firm, drained)
- Plain proteins: eggs, chicken, fish

### Ingredients / Foods to AVOID (assign `avoid_ibs`)
- **Onion (kaanda/pyaaz)** — HIGH FODMAP (fructans). One of the biggest IBS triggers. Any dish with significant onion.
- **Garlic (lahsun)** — HIGH FODMAP (fructans). Major IBS trigger. Note: garlic-infused oil is actually LOW FODMAP (the FODMAP compounds don't dissolve in oil), but whole garlic in a dish is HIGH.
- **All lentils and legumes (large portions)** — dal, rajma, chana, moong — high GOS. The most difficult rule for Indian cuisine because dals are staples. Moderate confidence — small amounts of moong dal (which is lower FODMAP than others) may be tolerated.
- **Wheat-based dishes** — maida, atta — fructans. Double-tagged with gluten concern. Chapati, paratha, puri — avoid for IBS.
- **Milk (lactose)** — full-fat milk, dahi in large amounts, paneer in large amounts. Not an issue if dahi is well-fermented (bacteria consume lactose) — but this is variable.
- **Cauliflower** — moderate-high FODMAP (polyols). Gobi sabzi, aloo gobi — moderate confidence avoid.
- **Mushrooms** — high polyols if present.
- **Apple, pear, mango (large amounts)** — high fructose.
- **Honey** — high fructose; used in some Indian recipes as sweetener.
- **Fried foods** — trigger gut motility changes; worsen IBS regardless of FODMAP content.
- **Spicy foods (red chilli, chilli powder in large amounts)** — irritate gut lining; worsen IBD inflammation.
- **Deep-fried foods** — high fat slows gastric emptying, worsens IBS.
- **Excess fiber foods during IBD flare** — raw salads, very high-fiber legumes.

### Ingredients / Foods BENEFICIAL (assign `gut_friendly`)
- **Rice** — low FODMAP, easy to digest. Plain rice, khichdi.
- **Banana (ripe, small)** — LOW FODMAP in small servings (if unripe → moderate FODMAP). A half-banana or banana as garnish is okay.
- **Ginger (adrak)** — anti-inflammatory, carminative; reduces nausea and IBS symptoms. Dishes featuring ginger.
- **Cumin (jeera)** — carminative; reduces bloating. Jeera rice, jeera water.
- **Ajwain (carom seeds)** — powerful carminative; traditional remedy for bloating. Any dish with ajwain.
- **Curd/dahi (well-fermented)** — probiotic; helps gut motility. Low FODMAP if fermented well.
- **Moong dal (yellow, split)** — lowest FODMAP of all dals. Plain moong dal, moong dal khichdi — mildly `gut_friendly` (borderline, moderate confidence).
- **Lauki (bottle gourd)** — gentle, low-FODMAP, easy to digest.
- **Carrot** — low FODMAP; soothing.
- **Cucumber** — very low FODMAP.
- **Turmeric** — curcumin has anti-inflammatory effect on gut (particularly IBD).
- **Coconut milk (small portions)** — low FODMAP; soothing.

### Indian-Specific Rules
- **Dal (any type)** — HIGH FODMAP. This is the hardest rule for Indian cuisine. Assign `avoid_ibs` for heavily lentil-based dishes. But moong dal is LOWER FODMAP than other dals — assign low-confidence avoid for plain moong dal dishes.
- **Khichdi (rice + moong dal)** — despite containing moong dal, khichdi is traditionally the go-to "sick food" in India and is generally well-tolerated in IBS because moong dal is low-FODMAP and the dish is soft, easy to digest. Assign `gut_friendly` for plain khichdi (with moong dal). This is the most important exception.
- **Rajma chawal** — rajma is very HIGH FODMAP; `avoid_ibs` even if people love it.
- **Chole (chana)** — very HIGH FODMAP chickpeas; `avoid_ibs`.
- **Idli (fermented)** — rice and urad dal; urad dal has moderate FODMAP, but fermentation reduces it significantly. Idli is generally considered gut-friendly. Assign `gut_friendly` for idli.
- **Dosa** — similar to idli; fermented; `gut_friendly` for plain dosa.
- **Upma (suji/rava)** — wheat-derived (FODMAPs) + onion typically; `avoid_ibs`.
- **Poha** — rice-derived, low FODMAP, but often contains onion. If onion is listed as ingredient: `avoid_ibs`. Onion-free poha: `gut_friendly`.
- **Ajwain paratha** — contains atta (FODMAP) but ajwain is therapeutic for IBS. Mixed signals; moderate confidence `avoid_ibs` because wheat dominates.
- **Sattu** — chickpea-based; HIGH FODMAP; `avoid_ibs`.
- **Buttermilk (chaas) — thin, diluted dahi** — well-diluted, small amounts generally tolerated in IBS. Borderline. Low confidence on either tag.

---

## CONDITION 10 — FATTY LIVER (NON-ALCOHOLIC FATTY LIVER DISEASE, NAFLD)

**Tags:** `avoid_fattyliver` | `liver_friendly`

### What it is
NAFLD is accumulation of fat in liver cells in non-drinkers. Driven by insulin resistance, excess calories (especially fructose and saturated fat), and metabolic syndrome. Dietary management: calorie control, eliminate fructose/sugar, reduce saturated fat, increase antioxidants, support liver detoxification enzymes.

### Ingredients / Foods to AVOID (assign `avoid_fattyliver`)
- **Refined sugar and fructose** — white sugar, jaggery, honey, sugary drinks, sweets (halwa, kheer, mithai). Fructose is specifically hepatotoxic — metabolized only in liver, directly contributes to fat accumulation.
- **Refined carbohydrates** — maida, white rice in large amounts — convert to liver fat via de novo lipogenesis.
- **Saturated fats** — ghee in large amounts, cream, malai, full-fat paneer, coconut cream in large amounts.
- **Deep-fried foods** — excess calorie density; worsen NAFLD.
- **Trans fats** — vanaspati, commercial fried foods.
- **Alcohol** — not relevant for typical Indian restaurant dishes, but flag if present.
- **Processed foods** — preservatives can worsen liver inflammation.

### Ingredients / Foods BENEFICIAL (assign `liver_friendly`)
- **Coffee** — NOT typically a recipe ingredient but noted for completeness.
- **Leafy greens** — palak, methi, curry leaves — antioxidants support liver health.
- **Cruciferous vegetables** — gobi, cabbage — sulforaphane activates liver detox enzymes.
- **Garlic** — allicin reduces liver fat and inflammation.
- **Turmeric** — curcumin specifically reduces liver fat and inflammation; multiple clinical studies.
- **Amla** — one of the most potent liver protectants in Indian traditional medicine; high in Vitamin C and antioxidants.
- **Walnuts, flaxseeds** — omega-3s reduce liver triglycerides.
- **Oats, barley** — beta-glucan fiber; reduces liver fat.
- **Lentils (moderate protein, high fiber)** — dals; reduce liver fat via fiber and plant protein.
- **Bitter gourd (karela)** — reduces liver enzymes (SGOT, SGPT) in NAFLD studies.
- **Bottle gourd (lauki)** — hepatoprotective; used in traditional medicine.
- **Beets (chukandar)** — betalains are potent antioxidants protective of liver.
- **Lemon/lime** — Vitamin C, hepatoprotective. Dishes with prominent lemon.
- **Ginger** — anti-inflammatory, reduces liver fat.

### Indian-Specific Rules
- **Amla (Indian gooseberry)** — any amla preparation: amla chutney, amla pickle (if it's amla-based, though pickles are generally salty), amla juice as an ingredient — `liver_friendly`. Amla is in many traditional Indian recipes.
- **Turmeric milk (haldi doodh)** — `liver_friendly` if the milk is not too high-fat.
- **Dal-based dishes** — generally `liver_friendly` (plant protein, fiber, antioxidants).
- **Jaggery (gur)** — same fructose concern as white sugar for fatty liver. Jaggery is NOT safer than sugar for NAFLD despite its "healthy" reputation. Jaggery-heavy dishes: `avoid_fattyliver`.
- **Coconut-based curries** — coconut cream in large amounts: moderate `avoid_fattyliver` (saturated fat). Grated coconut in chutney: no concern.
- **Biryani** — rice-heavy, often high-fat; `avoid_fattyliver`.

---

## CONDITION 11 — GOUT

**Tags:** `avoid_gout`

### What it is
Gout is caused by hyperuricemia — excess uric acid in blood, which crystallizes in joints causing acute inflammation. Uric acid comes from purine metabolism. Dietary management: reduce purine intake, avoid fructose (fructose raises uric acid independently), increase hydration, avoid alcohol.

### Ingredients / Foods to AVOID (assign `avoid_gout`)
- **High-purine foods:**
  - Organ meats — liver, kidney, brain (rare in standard recipes but flag if present)
  - Red meat — lamb, beef, pork (moderate-high purines)
  - Shellfish — shrimp, crab, lobster, mussels (very high purines)
  - Certain fish — sardines, mackerel, herring, anchovies (very high purines)
  - Other fish — moderate purines; less severe than shellfish/sardines
  - Meat-based broths and gravies — high concentration of purines from cooking
- **Fructose** — refined sugar, high fructose corn syrup, sugary drinks. Fructose independently raises uric acid by stimulating purine synthesis.
- **Jaggery and honey** — fructose-containing sweeteners; moderate concern.
- **Alcohol** — not relevant for typical dishes.
- **Lentils/legumes (moderate purines)** — controversial. Older guidelines restricted all legumes for gout, but modern evidence suggests plant-based purines from lentils do NOT raise uric acid to the same degree as animal purines. Low confidence `avoid_gout` for legume-heavy dishes — do NOT tag with high confidence.
- **Spinach, asparagus, mushrooms** — moderate purines from plant sources. Same modern evidence suggests these don't significantly worsen gout in most patients.

### Ingredients / Foods BENEFICIAL (no prefer tag for gout, but these support management)
- **Low-purine vegetables** — most vegetables are safe. Carrot, cauliflower (actually moderate but generally fine), cabbage — no concern.
- **Dairy (low-fat)** — dairy reduces uric acid levels. This is counterintuitive but well-established. Low-fat dahi, skimmed milk — beneficial.
- **Cherries** — most potent anti-gout food (anthocyanins); rare in Indian dishes.
- **Vitamin C rich foods** — amla, citrus — reduce uric acid.
- **Water-rich foods** — cucumber, lauki, tinda — support kidney uric acid excretion.
- **Complex carbs** — rice, oats, bread (whole grain) — safe for gout.

### Indian-Specific Rules
- **Dal (any type)** — assign ONLY very low confidence `avoid_gout` (0.3 or below) for legume-based dishes, per modern evidence. Don't avoid-tag plain moong dal or masoor dal with high confidence.
- **Rajma** — slightly higher purines than other lentils. Low confidence avoid (0.3).
- **Mutton/chicken dishes** — if red meat or organ meat: moderate-high `avoid_gout`. Chicken is moderate-purine (not as bad as red meat).
- **Fish curry** — depends on fish type. Sardine/mackerel: high confidence `avoid_gout`. General fish: moderate confidence.
- **Tamarind (imli)** — trace fructose; no meaningful purine content. Don't tag.
- **Jaggery** — fructose pathway; moderate confidence `avoid_gout` for heavily jaggery-sweetened dishes.

---

## CONDITION 12 — OSTEOPOROSIS

**Tags:** `calcium_rich`

### What it is
Osteoporosis = low bone density from calcium deficiency, Vitamin D deficiency, or hormonal factors (post-menopausal). Diet intervention: maximize calcium intake, support calcium absorption (Vitamin D, Vitamin K2, magnesium), avoid calcium blockers (excessive caffeine, oxalates which inhibit absorption).

### Ingredients BENEFICIAL (assign `calcium_rich`)
- **Dairy** — milk, paneer, dahi, cheese — highest calcium density. ANY dish with substantial dairy content: `calcium_rich`.
  - Milk: ~120mg calcium per 100mL
  - Paneer: ~480mg per 100g
  - Dahi: ~120mg per 100g
- **Sesame seeds (til)** — highest plant-based calcium (~975mg per 100g). Til ladoo, til chikki, tahini — strongly `calcium_rich`. **This is the most calcium-dense plant food in Indian cuisine.**
- **Ragi (finger millet)** — second highest calcium among cereals (~344mg per 100g). Ragi mudde, ragi roti, ragi porridge — `calcium_rich`. **This is extremely important for Indian diet context.**
- **Leafy greens (cooked)** — palak, methi, curry leaves — significant calcium but with oxalate competition in palak. Methi and curry leaves have better calcium bioavailability.
- **Drumstick (sahjan/moringa) leaves** — exceptional calcium density (~440mg per 100g cooked). Drumstick sambar, moringa sabzi — `calcium_rich`.
- **Amaranth (rajgira)** — ~215mg calcium per 100g. Rajgira ladoo, rajgira roti.
- **Chickpeas (chana)** — ~100mg per 100g.
- **White beans** — high calcium.
- **Tofu (calcium-set)** — if tofu is set with calcium sulfate, very high calcium. Rare in traditional Indian cuisine.
- **Figs (anjeer)** — ~162mg calcium per 100g (dry figs).
- **Almonds** — ~264mg per 100g. Almond-prominent dishes.
- **Coconut (fresh)** — moderate calcium.

### Indian-Specific Rules
- **Ragi is critical.** Ragi mudde (a staple in Karnataka), ragi porridge, ragi dosa — STRONGLY `calcium_rich`. This is one of the best Indian foods for bone health.
- **Til (sesame) in any form** — til chikki, til ladoo, sesame chutney, sesame in any recipe — `calcium_rich`.
- **Drumstick leaves (sahjan ke patte)** — higher calcium than even dairy per gram. Moringa daal, sahjan sabzi — `calcium_rich`.
- **Paneer dishes** — always `calcium_rich`. Even a small amount of paneer in a mixed dish is significant.
- **Kheer / payasam (milk-based sweets)** — `calcium_rich` (despite being sugary, the milk base is genuine calcium source).
- **Dahi (curd)** — `calcium_rich` for dishes where dahi is a main ingredient.
- **Sattu** — chickpea-based; moderate calcium; borderline `calcium_rich`.

---

## CONDITION 13 — ANEMIA

**Tags:** `iron_rich`

### What it is
Anemia is most commonly iron-deficiency anemia (also B12 deficiency or folate deficiency, but iron is most prevalent in India). Iron comes in two forms: heme iron (animal-based, highly bioavailable ~25%) and non-heme iron (plant-based, less bioavailable ~5–15%). Vitamin C dramatically increases non-heme iron absorption (up to 3x). Inhibitors: tannins (tea/coffee), calcium, phytates, oxalates.

### Ingredients BENEFICIAL (assign `iron_rich`)
- **Heme iron (high bioavailability) — assign with high confidence:**
  - Red meat (lamb, beef) — ~3mg per 100g; if present in dish
  - Liver/organ meats — highest heme iron (~7mg per 100g)
  - Chicken — moderate (~1.5mg per 100g)
  - Fish — moderate (~1mg per 100g)
- **Non-heme iron (plant-based — assign with moderate confidence, better if Vitamin C present in same dish):**
  - Palak (spinach) — ~3mg per 100g (but oxalates reduce bioavailability significantly)
  - Methi (fenugreek leaves) — ~16mg per 100g (dried); even fresh methi is very iron-dense. **This is one of the best plant sources.**
  - Rajma — ~8mg per 100g
  - Chana/chickpeas — ~7mg per 100g
  - Masoor dal (red lentil) — ~7mg per 100g. All dals are good iron sources.
  - Moong dal — ~5mg per 100g
  - Jowar — ~4mg per 100g
  - Bajra — ~11mg per 100g. **One of the best plant iron sources.** Major advantage for vegetarians.
  - Ragi — ~3.9mg per 100g
  - Lotus seeds (makhana) — ~1.5mg per 100g; moderate
  - Pumpkin seeds — very high iron (~15mg per 100g) but rarely dominant in a dish
  - Dry fruits (dates/khajur, raisins/kishmish, apricots/khubani) — iron-rich; common in Indian recipes
  - Jaggery (gur) — ~11mg iron per 100g. This is notable — jaggery is both a sugar concern AND an iron source. For anemia: `iron_rich`. For diabetes/fatty liver: `avoid_*`.
  - Amla — Vitamin C which dramatically boosts iron absorption from concurrent plant foods
  - Beetroot (chukandar) — traditionally considered iron-rich but actually only ~0.8mg per 100g. The red color is NOT iron. However, folate in beets is good for megaloblastic anemia. Assign low-confidence `iron_rich`.
  - Sesame seeds (til) — ~14mg per 100g iron; very high.
  - Curry leaves — moderate iron.
- **Vitamin C in a dish enhances iron from plant sources:**
  - If a dish contains both iron-rich plant foods AND citrus/amla/tomato, the combined dish is more `iron_rich` than either component alone.

### Indian-Specific Rules
- **Methi (fenugreek)** — exceptionally iron-dense plant food. Methi sabzi, methi dal, methi paratha — `iron_rich` with high confidence.
- **Bajra (pearl millet)** — very high iron for a grain (~11mg). Bajra roti, bajra khichdi — `iron_rich`. One of the most important grains for anemia prevention.
- **Jaggery (gur)** — traditional remedy for anemia in India; contains ~11mg iron/100g. Jaggery-based sweets: `iron_rich` applies alongside any diabetes concern.
- **Dals** — all dals are significant iron sources for vegetarians. Dal-dominant dishes: `iron_rich`.
- **Palak** — despite the spinach-iron myth being partially debunked (oxalates reduce absorption), it still provides meaningful iron if combined with Vitamin C (lemon squeeze on palak sabzi). Palak dishes: moderate confidence `iron_rich`.
- **Til (sesame) dishes** — til ladoo, til chikki — `iron_rich` AND `calcium_rich`.
- **Rajma** — `iron_rich`; best assigned with medium-high confidence.
- **Dates (khajur)** — if dates are a prominent ingredient in a dessert/halwa; `iron_rich`.

---

## CONDITION 14 — HEART DISEASE (CORONARY ARTERY DISEASE, CVD)

**Tags:** `avoid_heart` | `heart_friendly`

### What it is
Heart disease encompasses coronary artery disease, atherosclerosis, heart failure. Dietary management overlaps significantly with hypertension and cholesterol management but emphasizes: reduce overall cardiovascular risk (saturated fat, trans fat, sodium, cholesterol), increase cardioprotective nutrients (omega-3, fiber, antioxidants, polyphenols).

### Ingredients / Foods to AVOID (assign `avoid_heart`)
- **Trans fats** — vanaspati, commercial fried foods. Highest priority `avoid_heart`.
- **Saturated fats in large amounts** — ghee (in excess), butter, full-fat dairy, cream, malai-heavy dishes, coconut cream in large quantities.
- **High sodium** — see hypertension list. Pickles, papad, namkeen — `avoid_heart`.
- **Deep-fried foods** — oxidized fats from repeated frying; all heavily fried items: samosa, vada, poori, bhatura, chakli.
- **High-sugar foods** — raise triglycerides and contribute to metabolic syndrome, increasing CVD risk. Halwa, kheer, mithai, jalebi, gulab jamun.
- **High dietary cholesterol** — organ meats, shellfish, egg yolk in large amounts.
- **Refined carbohydrates** — maida-heavy dishes; white rice in large portions; raise glycemic load and triglycerides.
- **Red meat** — if present; saturated fat.

### Ingredients / Foods BENEFICIAL (assign `heart_friendly`)
Note: `heart_friendly` is shared with hypertension. A dish tagged `heart_friendly` benefits BOTH conditions.

- **Omega-3 rich foods** — flaxseeds (alsi), walnuts, fatty fish (salmon, mackerel — if present).
- **Garlic** — reduces LDL, blood pressure, platelet aggregation. One of the most cardioprotective single ingredients.
- **Onion** — quercetin; anti-inflammatory and cardioprotective.
- **Turmeric** — anti-inflammatory; reduces oxidative stress on arteries.
- **Ginger** — anti-platelet aggregation; reduces inflammation.
- **Coriander (dhania seeds and leaves)** — cholesterol-lowering.
- **Soluble fiber** — oats, barley, all lentils and legumes; reduce LDL via gut binding.
- **Leafy greens** — palak, methi; nitrates support blood vessel dilation.
- **Tomato** — lycopene, antioxidant; reduces LDL oxidation.
- **Berries / amla** — polyphenols; reduce atherosclerosis.
- **Nuts (almonds, walnuts)** — reduce LDL, raise HDL; anti-inflammatory.
- **Olive oil** — if present; heart-protective. Rare in Indian cuisine.
- **Mustard oil** — commonly used in Indian cooking; contains omega-3 (ALA) and low saturated fat. Cardioprotective profile compared to refined oils.

### Indian-Specific Rules
- **Mustard oil** — unique to Indian cuisine. Has a favorable fatty acid profile (low saturated fat, moderate omega-3). In Indian context, mustard oil dishes are generally NOT `avoid_heart` unless heavily fried in large quantities.
- **Ghee** — same nuance as cholesterol section. Trace ghee ≠ `avoid_heart`. Heavy ghee use (halwa, ghee-drenched parathas) = `avoid_heart`.
- **Khichdi** — simple, low-fat, high-fiber (from dal); `heart_friendly`. A classic cardioprotective dish.
- **Dal dishes** — generally `heart_friendly` (fiber, plant protein, no saturated fat, antioxidants).
- **Amla** — `heart_friendly`; one of the most cardioprotective foods in Ayurvedic tradition with modern evidence.
- **Palak dishes (non-cream)** — `heart_friendly`.
- **Paneer butter masala / shahi paneer** — cream + butter + full-fat paneer; `avoid_heart`.
- **Biryani** — high calorie, often high saturated fat; `avoid_heart`.
- **Plain dosa / idli with sambar** — low fat, high fiber; `heart_friendly`.
- **Jowar / bajra roti** — whole grain; `heart_friendly`.
- **Sabudana khichdi** — low fiber, high GI, but not high in saturated fat or sodium; borderline. Not strongly heart-avoidable unless deep-fried (sabudana vada → moderate `avoid_heart`).

### Relationship Between `avoid_heart` and `avoid_hypertension`
- A dish may get both if it is high-sodium AND high-saturated-fat (e.g., a cream-based curry with papad).
- A dish may get only `avoid_hypertension` if it's high-sodium but low-fat (e.g., a simple rasam with lots of salt).
- A dish may get only `avoid_heart` if it's high-fat but low-sodium (e.g., deep-fried items in unsalted oil).

---

## COOKING METHOD SENSITIVITY RULES

These rules apply across all conditions where cooking method changes a food's profile:

| Method | Effect | Implications |
|--------|--------|-------------|
| Deep frying | Dramatically increases calorie density; generates oxidized fatty acids; changes GI profile slightly | Apply diabetes, cholesterol, heart, fatty liver avoids more aggressively to fried versions of borderline foods |
| Steaming / boiling | Preserves nutrients; reduces fat; lowers calorie density | May bring a borderline dish into "safe" territory |
| Fermentation | Reduces FODMAP content; increases probiotic value; lowers GI slightly | Idli/dosa, dahi, dhokla benefit from this — gut_friendly, diabetes_friendly more applicable |
| Roasting / dry heat | Moderate effect; some dehydration but no fat added | Generally safe; does not significantly change classification |
| Tempering (tadka) | Small oil amount; major change if ghee vs. mustard oil vs. refined oil | Ghee tadka does not typically warrant avoid tags unless very heavy |
| Pressure cooking | Reduces cooking time; preserves more nutrients than prolonged boiling | Generally positive; no special classification change |
| Cooling cooked starch | Increases resistant starch; reduces GI | Cold rice / cold roti → slightly lower GI than hot-served |

### Frying Escalation Rule
If the recipe name contains: "Fried", "Fry", "Vada", "Pakora", "Bhajia", "Samosa", "Kachori", "Poori/Puri", "Bhatura", "Tikki" (unless described as pan-fried or baked), "Bonda", "Cutlet" (unless described as baked) — apply the following at elevated confidence:
- `avoid_diabetes` (increased)
- `avoid_pcos` (increased)
- `avoid_heart` (increased)
- `avoid_fattyliver` (increased)
- `avoid_highchol` (increased)

---

## TAG INTERACTION NOTES

### Tags that commonly co-occur
- `diabetes_friendly` + `pcos_friendly` — significant overlap (both address insulin resistance)
- `heart_friendly` applies for both Hypertension and Heart Disease — assign once, covers both
- `avoid_heart` + `avoid_highchol` — significant overlap; deep-fried or cream-heavy dishes get both
- `iron_rich` + `calcium_rich` — sesame seeds (til) and ragi earn both; methi leaves earn `iron_rich`
- `avoid_fattyliver` + `avoid_diabetes` — sugar-heavy dishes get both
- `gluten_free` dishes often earn `pcos_friendly` and `diabetes_friendly` if they're also low-GI

### Tags that can conflict
- `avoid_kidney` vs `iron_rich` / `calcium_rich` — spinach, rajma, sesame are all both. For a CKD patient, the avoid tag takes priority (the doctor knows the patient's condition). Both tags can co-exist on the same dish.
- `avoid_hypothyroid` (for bajra) vs `iron_rich` (bajra is iron-rich) — both tags apply. Let the doctor/system handle priority.
- `jaggery dishes` — `iron_rich` (for anemia) + `avoid_diabetes` + `avoid_fattyliver`. These are not mutually exclusive; assign all applicable tags.

---

## CONFIDENCE CALIBRATION GUIDE

| Confidence | Meaning | Example |
|------------|---------|---------|
| 0.9–1.0 | Near certain | Samosa = `avoid_diabetes`; Karela sabzi = `diabetes_friendly` |
| 0.7–0.9 | High confidence | Biryani = `avoid_diabetes`; Dal tadka = `diabetes_friendly` |
| 0.5–0.7 | Moderate, one or two signals present | Rajma chawal = `avoid_diabetes` (rice up, rajma down); Gobi sabzi = `avoid_hypothyroid` |
| 0.3–0.5 | Low, borderline | Plain idli = `avoid_diabetes` (GI ~77 but fermented); Bajra roti = `avoid_kidney` (moderate potassium) |
| Below 0.3 | Skip — not worth tagging | Trace turmeric alone = `thyroid_support` would be too weak |

**Default behavior: Err on the side of safety.** If uncertain between avoid and not-avoid for a high-stakes condition (kidney disease, celiac), lean toward assigning the avoid tag with lower confidence rather than omitting it.
