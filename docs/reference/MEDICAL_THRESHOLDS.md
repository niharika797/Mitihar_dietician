# Medical nutrition thresholds — tag derivation spec

Clinical cutoffs for `derive_medical_tags.py` (Phase E). Derived from published guidelines,
mapped to **per-serving** dish thresholds. Tags are dish properties set on the base recipe
serving (`*_per_serving`), computed once — the generator later rescales dishes per patient
(factor 0.5–3.0), so a tag reflects the recipe's nutrient *density*, not a patient-specific dose.

**Sodium (hypertension/kidney) is intentionally excluded** — added salt is not modeled in the
ingredient chain, so computed per-dish sodium is unreliable. Those conditions stay on the
existing tags until salt is modeled.

## Sources
- **Free sugars** — WHO 2015 *Guideline: Sugars intake for adults and children*: <10% of total
  energy (strong), <5% (~25 g/6 tsp) for additional benefit. SACN/Diabetes Canada: for T2DM,
  keep free/sucrose ≤10% (ideally <5%) of energy; >10% can raise glucose & triglycerides.
- **Saturated fat** — American Heart Association: <6% of calories for high cholesterol
  (~13 g/day on a 2000-kcal diet); WHO general <10%.
- **RDAs (Indian)** — ICMR-NIN 2020: Calcium 1000 mg/d (1200 for ≥60 / lactating); Iron
  Men 19, Women 29 mg/d; "rich" = ≥20% of RDA per serving (FDA labeling convention).

## Daily → per-meal budget
Reference sedentary adult ≈ 2000 kcal (ICMR-NIN: man 2110, woman 1660). 3 meals/day.
- Free-sugar diabetic cap: 5% × 2000 = ~25 g/day → ~8 g/meal.
- Saturated-fat high-chol cap: 6% × 2000 = ~13 g/day → ~4–5 g/meal.

## Per-serving tagging thresholds (tunable constants in derive_medical_tags.py)

| Tag | Condition(s) | Rule (on base serving) | Rationale |
|-----|--------------|------------------------|-----------|
| `avoid_diabetes` | T2 Diabetes, Pre-diabetes | `free_sugars_per_serving > 10 g` | >~40% of the 25 g/day diabetic cap in one dish |
| `avoid_pcos` | PCOS/PCOD | `free_sugars_per_serving > 10 g` | insulin-resistance: same sugar limit |
| `diabetes_friendly` (prefer) | Diabetes, Pre-diabetes | `free_sugars < 5 g AND fiber_per_serving ≥ 3 g` | low-sugar + fibre blunts glycaemic response |
| `avoid_highchol` | High Cholesterol | `saturated_fat_per_serving > 5 g` | ~1 meal's worth of the AHA 13 g/day cap |
| `avoid_heart` | Heart Disease | `saturated_fat_per_serving > 5 g` | same sat-fat basis |
| `heart_friendly` (prefer) | Hypertension, Heart, High-chol | `saturated_fat_per_serving < 2 g` | low sat-fat dish |
| `calcium_rich` (prefer) | Osteoporosis | `calcium_per_serving ≥ 200 mg` | ≥20% of 1000 mg RDA = "rich" |
| `iron_rich` (prefer) | Anemia | `iron_per_serving ≥ 3.5 mg` | ≥~20% of adult iron RDA |

## Coverage gate
Only derive a tag for a dish whose relevant `*_per_serving` value is **non-NULL** (i.e. it
cleared the 0.60 gram-weighted coverage gate in `compute_dish_micronutrients.py`). A NULL means
the dish's nutrient is unknown — never tag/exclude on missing data.

## Notes / to ratify
- Thresholds are on the **base serving**; consider revisiting once real serving sizes are audited.
- `avoid_diabetes` currently keys on free sugars only. Glycaemic load also depends on refined
  starch / low fibre — a future refinement could combine `free_sugars` high OR (`STARCH` high AND
  `fiber` low). Out of scope for v1.
- A registered dietitian should ratify these cutoffs before production.
