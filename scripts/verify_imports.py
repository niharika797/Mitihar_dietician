import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')

errors = []
imports = [
    "app.main",
    "app.routers.auth",
    "app.routers.users",
    "app.routers.calculations",
    "app.routers.diet_plans",
    "app.routers.progress",
    "app.routers.meal_plan",
    "app.services.user_service",
    "app.services.progress_service",
    "app.services.diet_plan_service",
    "app.core.security",
    "app.core.middleware",
    "app.models.db_models",
]

for mod in imports:
    try:
        __import__(mod)
        print(f"  OK  {mod}")
    except Exception as e:
        print(f"  FAIL {mod} — {e}")
        errors.append(mod)

print()
if errors:
    print(f"FAILED: {errors}")
else:
    print("ALL IMPORTS CLEAN — items 1 and 2 complete")
