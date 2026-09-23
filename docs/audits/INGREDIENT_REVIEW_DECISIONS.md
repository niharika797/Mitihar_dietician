# Ingredient Tag Review Decisions — Session 18B

Manual review decisions for tags in `docs/INGREDIENT_REVIEW.md` (confidence 0.25–0.84).
Promoted tags were written to the ingredients table.
Rejected tags were NOT written to the DB.

---

## PROMOTED (written to DB)

See `scripts/_task1_v2.py` and `scripts/_task2_promotes.py` for full audit trail.
High-level summary: 76 ingredient rows updated across A and U–Y review entries.

---

## REJECTED (do not write to DB)

| Ingredient | Tag | Confidence | Reason |
|------------|-----|------------|--------|
| Aamras | `avoid_gout` | 0.50 | Indirect fructose → uric acid mechanism; confidence too low for an avoid tag |
| Achari masala | `gut_friendly` | 0.50 | Composite spice blend with inconsistent composition; confidence too low |
| Active dry yeast | `gut_friendly` | 0.70 | Reasoning flaw — yeast cells die at baking temperatures; no live probiotic benefit |
| All spice powder | `heart_friendly` | 0.70 | Trace spice used in negligible quantities; cardiovascular evidence too weak for tag |
| Almond milk | `calcium_rich` | 0.70 | Fortification-dependent; not guaranteed in Indian home-cooking context; unreliable |
| Almonds | `iron_rich` | 0.60 | Non-heme iron with poor bioavailability due to phytate binding; 0.60 below threshold |
| Arbi | `cholesterol_friendly` | 0.50 | Confidence too low |
| Arbi | `gut_friendly` | 0.50 | Confidence too low |
| Arhar dal | `avoid_kidney` | 0.40 | Confidence critically low for an avoid tag; plant phosphorus poorly absorbed |
| Avarekai | `gut_friendly` | 0.70 | Legume FODMAP risk (GOS); not low-FODMAP; positive gut tag not clinically supported |
| Banana | `avoid_kidney` | 0.50 | Confidence too low for an avoid tag; potassium concern only at very high intake |
| Urad dal papad | ALL tags | — | Processed condiment product; papad processing (frying, roasting) negates base dal nutritional profile |
| Wheat grass powder | `gluten_free` | 0.80 | Clinically reversed to `avoid_gluten` (Task 1). Cross-contamination risk makes gluten_free unsafe for celiac patients in Indian context regardless of botanical classification |
| Yellow bell pepper | `gut_friendly` | 0.70 | Moderate FODMAP (fructose); portion-sensitive; positive tag not clinically reliable |
| Yellow bell pepper | `heart_friendly` | 0.60 | Confidence too low; antioxidant benefit from bell pepper does not reach heart_friendly threshold |
| White peas | `iron_rich` | 0.60 | Non-heme iron with low bioavailability; confidence too low |
| White peas | `avoid_kidney` | 0.50 | Confidence too low for an avoid tag |
| Vinegar | `gut_friendly` | 0.70 | Regular/white vinegar lacks ACV probiotic properties; not equivalent |
| White vinegar | `gut_friendly` | 0.70 | Same reason as Vinegar above |
| Water chestnut flour | `gut_friendly` | 0.60 | Insufficient evidence; confidence too low |
| Whole wheat berries | `diabetes_friendly` | 0.70 | GI ~70 — too high for a positive diabetes_friendly tag |
| Whole wheat berries | `iron_rich` | 0.60 | Phytate-bound iron with low bioavailability; 0.60 below threshold |
| Whole cashews | `calcium_rich` | 0.60 | Poor bioavailability; confidence too low |
| Whole cashews | `iron_rich` | 0.50 | Poor bioavailability due to phytates; 0.50 critically low |
| Whole black pepper | `gut_friendly` | 0.60 | Can irritate gut lining at typical cooking quantities; positive tag unjustified |
| Urad dal flour | `gut_friendly` | 0.60 | Urad dal causes bloating; borderline FODMAP; positive tag not supported |
| Multigrain flour | `gluten_free` | 0.50 | Unknown composition; may contain wheat; confidence too low; unsafe to tag GF |
| Papad | `gluten_free` | 0.50 | Composition varies by manufacturer; wheat-based papad common; unsafe to tag GF |
| Papads | `gluten_free` | 0.70 | Same reason as Papad; composition not guaranteed GF |
| Tortillas | `gluten_free` | 0.60 | Wheat flour tortillas common; composition unknown; unsafe to tag GF |

---

## DATA QUALITY FLAGS (not in scope for Session 18B — follow-up required)

| Ingredient | Issue | Action |
|------------|-------|--------|
| Boondi (ID 173) | Has `avoid_gluten` in avoid_tags from Layer 1 auto-accept run (confidence ≥0.85). Clinically INCORRECT — boondi is made from chickpea/besan which is genuinely gluten-free. Contradicted by `gluten_free` in prefer_tags (added Session 18B). | Remove `avoid_gluten` from avoid_tags in a future data quality pass |
| / 2 teaspoon amchoor powder (ID 60) | Measurement-phrase artifact tagged with liver_friendly and gut_friendly via amchoor pattern. No calories_per_100g. Low impact but noisy. | Dedup/cleanup pass |
| / 2 cups avarekalu / lilva beans (ID 5) | Measurement-phrase artifact tagged via avarekai pattern | Dedup/cleanup pass |
| 1/2 cups vellai poosanikai (ID 10) | Measurement-phrase artifact tagged via poosanikai pattern | Dedup/cleanup pass |

---

## TECHNICAL NOTE: Boondi avoid_gluten

The Layer 1 tagging script auto-accepted `avoid_gluten` for Boondi at ≥0.85 confidence, which is clinically incorrect. Boondi is made from besan (chickpea flour), explicitly listed in the ingredient tagging KB as gluten_free. This is an example of the Layer 1 auto-accept run producing a high-confidence wrong answer. Session 18B added `gluten_free` to prefer_tags — the contradiction now exists in DB. Resolution: remove `avoid_gluten` from Boondi avoid_tags. Awaiting product owner decision.
