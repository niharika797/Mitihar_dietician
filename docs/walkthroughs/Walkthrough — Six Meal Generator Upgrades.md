# Walkthrough — Six Meal Generator Upgrades

## Files Modified

### [meal_generator.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py)

| Upgrade | What Changed |
|---|---|
| **5 — Ingredient normalization** | [generate_ingredient_checklist()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#567-593) now normalizes ingredient names to `.strip().title()` before grouping, collapsing "curd"/"Curd"/"CURD" into one entry |
| **4 — Slot quality blocklist** | Added `BLOCKLIST_PATTERNS` + `PROTECTED_SLOTS` constants. [_find_food_item_single_diet()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#494-566) fetches top 5 candidates ordered by calorie proximity and skips blocklisted names (chutney, powder, pickle…) in protected slots (grain, dal_protein, main_dish, sabzi) |
| **2 — Diet fallback chain** | New [_diet_fallback_chain()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#441-454) static method returns ordered diet types to try. [_find_food_item()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#455-493) now wraps the 4-level waterfall and iterates through the chain: Non-Veg → Eggetarian → Vegetarian |
| **1 — Non-veg weekly budget** | Before the 7-day loop, pre-assigns 3-4 non-veg slots at Lunch/Dinner only (no two on same day). All other slots use `query_diet = "Vegetarian"`. Template lookup and food item queries now use `query_diet` instead of global `diet_type` |
| **3B — Pantry staple filter** | In the ingredient scaling loop, ingredients with `is_pantry_staple == True` are skipped from the shopping list |

### [user_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/user_service.py)

| Upgrade | What Changed |
|---|---|
| **6 — Age → DOB** | [create_patient()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/user_service.py#34-64) now derives `date_of_birth = date(today.year - age, 1, 1)` when `age` is provided but `date_of_birth` is not |

### [tag_pantry_staples.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/scripts/tag_pantry_staples.py) [NEW]

| Upgrade | What Changed |
|---|---|
| **3A — Pantry staple tagging** | Migration script that tags every ingredient in `food_items.ingredients` JSONB with `is_pantry_staple: true/false`. Processes in batches of 100 |

## Verification Results

```
Test: --diet Non-Vegetarian --region North --plan Gym-Friendly --gender male --age 25 --weight 80 --height 180 --activity VA

✅ Total meals generated:  35 / 35 expected
✅ Avg daily calories:     3114 kcal (TDEE target: 3114)
✅ Daily range:            3114 – 3114 kcal
✅ Unique dishes:          79 / 91 total slots
✅ All 35 meal slots filled successfully

Repeated dishes (6 — all reasonable repeats):
  • Tea / Cofee / Milk — 4×        (morning snack, expected)
  • Curd Chutney — 3×              (side item)
  • Lassi — 3×                     (evening snack)
  • Vegetable raita — 3×           (side item)
  • Egg Bhurji — 3×                (eggetarian breakfast)
  • Coconut Ladoo — 2×             (snack)

Pantry staple migration: Tagged 3,956 staples across 2,114 recipes
```
