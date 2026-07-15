# Mini-Pilot Verification — Session 18B
**Purpose:** Verify the 4 compact KB fixes from Session 18A pilot quality review.
**Recipes tested:** 10

## Pass/Fail Legend
- ✅ PASS — All required tags present, no forbidden tags assigned
- ❌ FAIL — Missing required tag or forbidden tag assigned

---

## ID=355 — Jowar roti  ✅ PASS
**Slot:** grain | **✓ Verified**
**Ingredients:** Jowar flour
**Expected:** must have `diabetes_friendly` | must NOT have `avoid_diabetes`, `avoid_pcos`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `diabetes_friendly` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Jowar is a whole-grain millet and is explicitly listed as diabetes_friendly. |
| `pcos_friendly` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Jowar is a whole-grain millet and is explicitly listed as pcos_friendly. |
| `gluten_free` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Jowar is a gluten-free millet. |
| `avoid_hypothyroid` | 0.40 ▓▓▓▓░░░░░░ | Jowar is listed as having a low confidence goitrogen effect when used as a main grain. |

---

## ID=359 — Bajra roti  ✅ PASS
**Slot:** grain | **✓ Verified**
**Ingredients:** Bajra  flour
**Expected:** must have `diabetes_friendly` | must NOT have `avoid_diabetes`, `avoid_pcos`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `diabetes_friendly` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Bajra is a whole-grain millet and is classified as diabetes_friendly. |
| `pcos_friendly` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Bajra is a whole-grain millet and is classified as pcos_friendly. |
| `avoid_hypothyroid` | 0.60 ▓▓▓▓▓▓░░░░ | Bajra is a goitrogen, applying a moderate confidence trigger for avoid_hypothyroid. |
| `gluten_free` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | Bajra is a gluten-free millet. |
| `calcium_rich` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Ragi (finger millet) is strongly calcium-rich, and Bajra is a millet providing mineral benefits. |
| `iron_rich` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Bajra is a millet and is listed as a strong source of iron. |

---

## ID=840 — Arbi Achaar  ❌ FAIL
**Slot:** sabzi | **○ Unverified**
**Ingredients:** Colocasia root, Ajwain, Cumin seeds, Methi seeds, Kalonji, Methi powder, Mustard powder, Red chilli powder, Turmeric powder, Asafoetida, Vinegar, Mustard oil
**Expected:** must have `avoid_hypertension` | must NOT have `gut_friendly`, `liver_friendly`, `diabetes_friendly`, `heart_friendly`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `avoid_hypertension` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | The presence of Achaar/Pickle triggers the override rule, mandating only avoid_hypertension. |
| `gut_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | Ajwain and Cumin seeds are featured ingredients that act as carminatives, supporting gut health. |
| `liver_friendly` | 0.60 ▓▓▓▓▓▓░░░░ | The dish contains turmeric, which is a featured spice beneficial for the liver. |

**Issues:**
- ❌ WRONG tag `gut_friendly` (conf=0.7) — must not be assigned
- ❌ WRONG tag `liver_friendly` (conf=0.6) — must not be assigned

---

## ID=1134 — Stuffed Mango Pickle  ✅ PASS
**Slot:** sabzi | **○ Unverified**
**Ingredients:** Mango, Methi seeds, Red chilli powder, Asafoetida
**Expected:** must have `avoid_hypertension` | must NOT have `diabetes_friendly`, `heart_friendly`, `gut_friendly`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `avoid_hypertension` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | The presence of pickle/achar triggers the override rule, mandating only avoid_hypertension. |

---

## ID=608 — Oats Moong Dal  ❌ FAIL
**Slot:** main_dish | **○ Unverified**
**Ingredients:** Instant oats, Rice, Green moong dal, Asafoetida, Green chillies, Ginger, Cabbage
**Expected:** must have `avoid_gluten` | must NOT have `gluten_free`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `diabetes_friendly` | 0.90 ▓▓▓▓▓▓▓▓▓░ | The combination of oats and moong dal provides low-GI, high-fiber components. |
| `pcos_friendly` | 0.85 ▓▓▓▓▓▓▓▓░░ | Oats and moong dal are insulin-sensitizing and anti-inflammatory. |
| `gut_friendly` | 0.80 ▓▓▓▓▓▓▓▓░░ | The dish is a combination of rice and dal, which is generally soothing and low FODMAP when using moong dal. |
| `cholesterol_friendly` | 0.75 ▓▓▓▓▓▓▓░░░ | Dal and oats provide soluble fiber which helps lower cholesterol. |
| `gluten_free` | 0.95 ▓▓▓▓▓▓▓▓▓░ | Oats are used, but since the recipe does not specify certified GF oats, we rely on the base ingredients (rice, dal) being GF, and oats are generally treated as GF unless specified otherwise in this context. |
| `avoid_ibs` | 0.50 ▓▓▓▓▓░░░░░ | Moong dal is a lower FODMAP legume, and the dish is not heavy in high-FODMAP ingredients like onion or cauliflower. |

**Issues:**
- ❌ MISSING required tag `avoid_gluten`
- ❌ WRONG tag `gluten_free` (conf=0.95) — must not be assigned

---

## ID=427 — Lauki Paneer  ✅ PASS
**Slot:** grain | **○ Unverified**
**Ingredients:** Bottle gourd, Paneer, Turmeric powder, Garam masala powder, Rajgira flour, Tomatoes, Green chillies, Bay leaf, Cinnamon stick, Cardamom, Coriander powder, Curd, Coriander
**Expected:** must have `—` | must NOT have `avoid_kidney`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `gut_friendly` | 0.80 ▓▓▓▓▓▓▓▓░░ | Lauki (bottle gourd) is listed as a gut-friendly ingredient. |
| `liver_friendly` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Lauki and Turmeric are listed as liver-friendly ingredients. |
| `diabetes_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | Lauki is a non-starchy vegetable, supporting diabetes management. |
| `pcos_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | Lauki is a non-starchy vegetable, supporting PCOS management. |
| `heart_friendly` | 0.80 ▓▓▓▓▓▓▓▓░░ | The dish contains vegetables and curd, which support heart health. |
| `cholesterol_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | The dish contains vegetables and curd, which support cholesterol management. |
| `calcium_rich` | 0.80 ▓▓▓▓▓▓▓▓░░ | Paneer and Curd are strong sources of calcium. |
| `gluten_free` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Rajgira flour is a gluten-free millet used in the recipe. |

---

## ID=316 — Karela bhujia  ✅ PASS
**Slot:** sabzi | **✓ Verified**
**Ingredients:** Bittergourd, Onion, Oil
**Expected:** must have `diabetes_friendly` | must NOT have `—`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `diabetes_friendly` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Karela (bitter gourd) is a strong trigger for diabetes friendliness. |
| `liver_friendly` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Bitter gourd is a strong signal for liver health. |
| `gut_friendly` | 0.60 ▓▓▓▓▓▓░░░░ | The dish is a sabzi, and lauki/tinda/bhindi are generally gut-friendly, though onion is present. |
| `avoid_hypertension` | 0.30 ▓▓▓░░░░░░░ | The presence of onion, while not a primary high-sodium trigger, is noted in the context of general health considerations. |

---

## ID=254 — Dal  ✅ PASS
**Slot:** dal_protein | **✓ Verified**
**Ingredients:** Green gram dal, Tomato, Onion, Oil
**Expected:** must have `diabetes_friendly` | must NOT have `—`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `diabetes_friendly` | 0.80 ▓▓▓▓▓▓▓▓░░ | Plain dal/lentil dishes are generally beneficial for blood sugar control. |
| `heart_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | Dal/legume dishes provide fiber which helps lower cholesterol. |
| `cholesterol_friendly` | 0.70 ▓▓▓▓▓▓▓░░░ | Dal/legume dishes are rich in soluble fiber. |
| `gut_friendly` | 0.60 ▓▓▓▓▓▓░░░░ | Dal dishes are generally soothing and aid digestion. |

---

## ID=257 — Luchi  ✅ PASS
**Slot:** grain | **✓ Verified**
**Ingredients:** Wheat flour, Oil
**Expected:** must have `avoid_diabetes`, `avoid_gluten` | must NOT have `—`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `avoid_gluten` | 1.00 ▓▓▓▓▓▓▓▓▓▓ | The recipe uses wheat flour, which contains gluten. |
| `avoid_diabetes` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Luchi is a deep-fried item made from refined wheat flour, triggering high-GI/fried warnings. |
| `avoid_pcos` | 0.90 ▓▓▓▓▓▓▓▓▓░ | Luchi is deep-fried and made from refined flour, triggering PCOS avoidance criteria. |
| `avoid_heart` | 0.80 ▓▓▓▓▓▓▓▓░░ | The deep-frying process and refined flour contribute to high saturated fat/high-GI risks. |
| `avoid_highchol` | 0.70 ▓▓▓▓▓▓▓░░░ | Deep-frying in oil increases the intake of saturated/trans fats. |

---

## ID=268 — Bhindi masala  ✅ PASS
**Slot:** sabzi | **✓ Verified**
**Ingredients:** Lady finger, Onion, Oil
**Expected:** must have `cholesterol_friendly` | must NOT have `—`

| Tag | Confidence | Reason |
|-----|-----------|--------|
| `cholesterol_friendly` | 0.80 ▓▓▓▓▓▓▓▓░░ | Bhindi (okra) dishes are listed as cholesterol-friendly. |
| `gut_friendly` | 0.50 ▓▓▓▓▓░░░░░ | It is a plain sabzi, which generally aligns with gut-friendly principles. |

---

## Summary

**8/10 PASS**

| ID | Recipe | Fix Tested | Result |
|----|--------|------------|--------|
| 355 | Jowar roti | Fix 1 — millet diabetes_friendly | ✅ |
| 359 | Bajra roti | Fix 1 — millet diabetes_friendly | ✅ |
| 840 | Arbi Achaar | Fix 2 — achaar override | ❌ |
| 1134 | Stuffed Mango Pickle | Fix 2 — achaar override | ✅ |
| 608 | Oats Moong Dal | Fix 3 — oats avoid_gluten | ❌ |
| 427 | Lauki Paneer | Fix 4 — self-contradiction guard | ✅ |
| 316 | Karela bhujia | Sanity check — karela | ✅ |
| 254 | Dal | Regression — plain dal | ✅ |
| 257 | Luchi | Regression — fried flatbread | ✅ |
| 268 | Bhindi masala | Regression — bhindi sabzi | ✅ |