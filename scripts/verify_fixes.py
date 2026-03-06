import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')
import inspect

from app.core.security import get_current_patient
from app.core.middleware import SubscriptionCheckMiddleware, DoctorIsolationMiddleware
from app.services.progress_service import log_meal
from app.schemas.progress import MealLogCreate
from app.routers import meal_plan as mp_mod

results = []

# 1. Subscription gate removed from get_current_patient — check for the raise, not the word
src = inspect.getsource(get_current_patient)
if '402' not in src and 'PAYMENT_REQUIRED' not in src:
    results.append("PASS: subscription gate (HTTP 402) removed from get_current_patient")
else:
    results.append("FAIL: subscription gate still present in get_current_patient")

# 2. Middleware no longer opens DB sessions
mw_src = inspect.getsource(SubscriptionCheckMiddleware)
if 'AsyncSessionLocal' not in mw_src:
    results.append("PASS: SubscriptionCheckMiddleware — no DB session")
else:
    results.append("FAIL: SubscriptionCheckMiddleware still opens DB session")

if 'sub_status' in mw_src:
    results.append("PASS: SubscriptionCheckMiddleware reads sub_status from JWT claim")
else:
    results.append("FAIL: sub_status claim not read")

dr_mw_src = inspect.getsource(DoctorIsolationMiddleware)
if 'AsyncSessionLocal' not in dr_mw_src:
    results.append("PASS: DoctorIsolationMiddleware — no DB session")
else:
    results.append("FAIL: DoctorIsolationMiddleware still opens DB session")

if 'doctor_id' in dr_mw_src and 'payload.get' in dr_mw_src:
    results.append("PASS: DoctorIsolationMiddleware reads doctor_id from JWT claim")
else:
    results.append("FAIL: doctor_id claim not read")

# 3. fiber_g now logged
log_src = inspect.getsource(log_meal)
if 'fiber_g' in log_src:
    results.append("PASS: log_meal() now sets fiber_g")
else:
    results.append("FAIL: fiber_g missing from log_meal")

# 4. MealLogCreate has fiber field
fields = list(MealLogCreate.model_fields.keys())
if 'fiber' in fields:
    results.append(f"PASS: MealLogCreate.fiber field present — fields: {fields}")
else:
    results.append(f"FAIL: MealLogCreate missing fiber — fields: {fields}")

# 5. age derived from date_of_birth in meal_plan.py
mp_src = inspect.getsource(mp_mod)
if 'date_of_birth' in mp_src and '30  # age placeholder' not in mp_src:
    results.append("PASS: meal_plan.py derives age from date_of_birth")
else:
    results.append("FAIL: meal_plan.py still uses hardcoded age")

print("\nFINAL VERIFICATION")
print("=" * 52)
for r in results:
    print(f"  {r}")
print("=" * 52)
fails = [r for r in results if r.startswith("FAIL")]
print(f"\n  {'✅ All checks passed.' if not fails else f'❌ {len(fails)} check(s) failed.'}")
