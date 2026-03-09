# Meal Plan Adjustment Fixes

The integration test script highlighted four regressions related to meal plan adjustment and ingredient handling. The following fixes were deployed to resolve all standard endpoints:

## 1. `KeyError: 'age'` in `/meal-plan/adjust`
### Problem
The [adjust](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py#21-106) endpoint conditionalized the definition of the `age` variable based purely on whether a user's BMR needed manual calculation. If the user already had a saved TDEE, the block defining `age` was skipped. The fallback to the meal generator then failed, as it mandates `"age"` directly.
### Fix
Safely extrapolated the computation of `age` externally into the method root. This ensures that the `"age"` parameter natively exists for the `user_data` dictionary downstream regardless of `current_user.tdee` preconditions.

## 2. 'Unknown' Missing Ingredient Failure
### Problem
Changes in the meal generator caused it to return `{"Ingredient": "Name"}` instead of `{"ingredient": "Name"}`. Due to case sensitivity, the `/shopping-list` aggregator failed to map these lists properly, assigning `"Unknown"` values.
### Fix
* Updated [get_shopping_list](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py#161-232) to utilize `item.get("Ingredient")` safely. 
* Updated `/shopping-list/toggle` logic to accommodate capitalized mappings alongside existing alternatives.
* *Note: Also updated the default data output generation in `app/services/meal_generator.py` internally to standard lowercase schema generation `{ "ingredient": string }` to preserve cross-app compatibility.*

## 3. Diet Plan Versioning 
### Problem
The automated assertion measuring plan increment versions (`Version incremented after plan adjustment`, previously `0` -> `0`) failed because modifications to the diet plan were using [update_diet_plan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#121-139), which operates as an in-place mutation. 
### Fix
* Added `version: int = 1` field to the Pydantic schema definition [DietPlanResponse](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/diet_plan.py#5-17).
* Updated [get_diet_plan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#99-120) in the DietService model to explicitly attach active `rec.version` states upon lookup.
* Changed the logic in `/meal-plan/adjust` to invoke [store_diet_plan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#63-98) instead. [store_diet_plan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#63-98) soft-deletes the prior active `Recommendation` mapping and inserts a formally incremental version `+ 1` record, which aligns correctly with tracked plan histories.

## Result
**98/98 Integration Tests Successfully Passed.**
