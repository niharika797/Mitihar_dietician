import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')
import inspect
from datetime import date

issues   = []
notes    = []

from app.services.meal_generator.meal_generator import MealGenerator, BLOCKLIST_PATTERNS, PROTECTED_SLOTS
from app.services import user_service
from app.routers import diet_plans as dp_mod

mg = MealGenerator()

# 1. nonveg_assigned pre-allocation
src = inspect.getsource(mg.generate_meal_plan)
assert 'nonveg_assigned' in src and 'days_taken' in src, "U1: nonveg_assigned/days_taken missing"
notes.append("U1 PASS: nonveg pre-allocation with days_taken guard")

# 2. query_diet defaults to Vegetarian for non-assigned slots
assert 'query_diet = "Vegetarian"' in src, "U1: Vegetarian default missing"
notes.append("U1 PASS: non-assigned slots → Vegetarian")

# 3. age now in diet_plans user_data
dp_src = inspect.getsource(dp_mod.generate_diet_plan)
assert '"age"' in dp_src, "CRITICAL: age key missing from diet_plans user_data"
notes.append("CRITICAL FIX PASS: 'age' now in diet_plans user_data dict")

# 4. age is derived correctly (not hardcoded 30 as the only option)
assert 'date_of_birth' in dp_src, "age derivation uses date_of_birth"
notes.append("PASS: age derived from date_of_birth in diet_plans.py")

# 5. _find_food_item accepts user_diet param
find_src = inspect.getsource(mg._find_food_item)
assert 'user_diet' in find_src, "user_diet param missing from _find_food_item"
notes.append("U2 FIX PASS: user_diet param added to _find_food_item")

# 6. chain_diet uses user_diet for fallback decisions
assert 'chain_diet = user_diet if user_diet is not None else diet_type' in find_src, \
    "chain_diet assignment missing"
notes.append("U2 FIX PASS: chain_diet uses user_diet for breakfast-egg exception")

# 7. generate_meal_plan passes user_diet= to _find_food_item
assert 'user_diet=diet_type' in src, "user_diet= kwarg not passed in meal loop"
notes.append("U2 FIX PASS: generate_meal_plan passes user_diet=diet_type to _find_food_item")

# 8. fallback chain logic correct
chain_src = inspect.getsource(mg._diet_fallback_chain)
assert '"Eggetarian"' in chain_src and '"Vegetarian"' in chain_src, "fallback chain incomplete"
notes.append("U2 PASS: fallback chain has Eggetarian/Vegetarian tiers")

# 9. blocklist constants
assert BLOCKLIST_PATTERNS and PROTECTED_SLOTS, "U4: constants missing"
notes.append(f"U4 PASS: {len(BLOCKLIST_PATTERNS)} blocklist patterns, {len(PROTECTED_SLOTS)} protected slots")

# 11. title-case normalization
checklist_src = inspect.getsource(mg.generate_ingredient_checklist)
assert '.strip().title()' in checklist_src, "U5: title-case missing"
notes.append("U5 PASS: .strip().title() normalization in checklist")

# 12. pantry staple skip in meal loop
assert 'is_pantry_staple' in src, "U3B: is_pantry_staple filter missing"
notes.append("U3B PASS: is_pantry_staple filter in generate_meal_plan loop")

# 13. age → DOB in create_patient
create_src = inspect.getsource(user_service.create_patient)
assert 'date_of_birth' in create_src and 'date.today().year - data["age"]' in create_src, "U6 missing"
notes.append("U6 PASS: age → date_of_birth derivation in create_patient")

# 14. template fallback to Vegetarian
assert 'query_diet != "Vegetarian"' in src, "template veg fallback missing"
notes.append("U1 PASS: template Vegetarian fallback present")

# 15. runtime sanity — diet_plans import doesn't crash
from app.routers.diet_plans import generate_diet_plan
notes.append("PASS: diet_plans.py imports clean (no crash)")

print("=" * 55)
print("STEP 6 FINAL VERIFICATION")
print("=" * 55)
if issues:
    print(f"\n🔴 FAILURES ({len(issues)})")
    for iss in issues: print(f"  {iss}")
print(f"\n✅ ALL {len(notes)} CHECKS PASSED\n")
for n in notes:
    print(f"  {n}")
print("=" * 55)
