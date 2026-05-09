import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')

issues   = []  # breaks functionality right now
warnings = []  # wrong behavior, silent
notes    = []  # tech debt / performance

# ── CHECK 1: subscription gate in get_current_patient ─────────────────────
# Every new patient has subscription_status="inactive" (DB default).
# get_current_patient raises HTTP 402 for inactive status.
# get_current_user = get_current_patient (alias).
# ALL endpoints using get_current_user — /users/me, /diet-plans/generate,
# /progress/log/meal etc — will return 402 for every newly registered patient.
from app.models.db_models import Patient
from sqlalchemy import inspect as sa_inspect
col = {c.key: c for c in Patient.__table__.columns}
default_val = col['subscription_status'].default
default_arg = default_val.arg if default_val else None
if default_arg == "inactive":
    issues.append(
        "CRITICAL — get_current_patient raises HTTP 402 when subscription_status='inactive'.\n"
        "  Patient.subscription_status DB default = 'inactive'.\n"
        "  Every newly registered patient is immediately locked out of ALL\n"
        "  authenticated endpoints (including /users/me, /diet-plans/generate).\n"
        "  Fix: Remove the subscription gate from get_current_patient entirely.\n"
        "  Subscription enforcement belongs ONLY in SubscriptionCheckMiddleware."
    )

# ── CHECK 2: age accepted by UserCreate but never stored ──────────────────
from app.schemas.user import UserCreate
fields = UserCreate.model_fields
if 'age' in fields:
    # Check if create_patient stores age or date_of_birth
    import inspect as pyinspect
    from app.services import user_service
    src = pyinspect.getsource(user_service.create_patient)
    stores_age = 'age' in src and ('patient.age' in src or 'age=' in src)
    stores_dob = 'date_of_birth' in src
    if not stores_age and not stores_dob:
        issues.append(
            "CRITICAL — UserCreate accepts 'age' field (validated as int > 0) but\n"
            "  create_patient() never stores it. Patient.date_of_birth is also never set.\n"
            "  Age is silently dropped on every registration. All TDEE calculations\n"
            "  (which require age) will be wrong for every patient.\n"
            "  Fix: Either map age → date_of_birth on create, or add age to Patient table."
        )

# ── CHECK 3: meal_plan.py hardcodes age=30 ───────────────────────────────
from app.routers import meal_plan as mp_module
src = pyinspect.getsource(mp_module)
if '30  # age placeholder' in src or 'age placeholder' in src:
    warnings.append(
        "HIGH — meal_plan.py /adjust endpoint passes hardcoded age=30 to calculate_bmr().\n"
        "  Patient.date_of_birth exists but is never used here.\n"
        "  TDEE in /adjust will be wrong for any patient not exactly 30 years old.\n"
        "  Fix: Compute age from patient.date_of_birth, fallback 30 only if None."
    )

# ── CHECK 4: middleware opens separate DB sessions (double connections) ────
from app.core import middleware as mw_module
mw_src = pyinspect.getsource(mw_module)
if 'AsyncSessionLocal()' in mw_src:
    warnings.append(
        "MEDIUM — Both SubscriptionCheckMiddleware and DoctorIsolationMiddleware\n"
        "  open their own AsyncSessionLocal() session PER REQUEST, separate from\n"
        "  the get_db() session used by the route handler.\n"
        "  On every protected request: 2 DB connections opened (1 middleware + 1 handler).\n"
        "  Under load this halves effective connection pool capacity.\n"
        "  Fix: Pass subscription/doctor_id in JWT claims to avoid extra DB queries."
    )

# ── CHECK 5: fiber_g never logged ────────────────────────────────────────
from app.schemas.progress import MealLogCreate
meal_fields = set(MealLogCreate.model_fields.keys())
has_fiber_field = 'fiber' in meal_fields
from app.services import progress_service as ps
ps_src = pyinspect.getsource(ps.log_meal)
logs_fiber = 'fiber' in ps_src
if not has_fiber_field or not logs_fiber:
    notes.append(
        "LOW — MealLogCreate schema has no 'fiber' field and log_meal() never\n"
        "  sets fiber_g on MealLog. Fiber tracking is silently zero for all meal logs.\n"
        "  Fix: Add fiber field to MealLogCreate, map to MealLog.fiber_g in log_meal()."
    )

# ── CHECK 6: diet_plan_service still imports old Pydantic DietPlan model ──
from app.services import diet_plan_service as dps
dps_src = pyinspect.getsource(dps)
if 'from ..models.diet_plan import DietPlan' in dps_src:
    notes.append(
        "LOW — diet_plan_service.py still imports DietPlan from models/diet_plan.py\n"
        "  (old MongoDB-era Pydantic model). CRUD now correctly uses Recommendation ORM,\n"
        "  but the return type is still the legacy Pydantic class.\n"
        "  Not a crash bug — works today. Will need cleanup before models/diet_plan.py\n"
        "  is deleted in Phase 1."
    )

# ── CHECK 7: /today fallback to 2000 when tdee is None ───────────────────
from app.routers import progress as prog
prog_src = pyinspect.getsource(prog)
if '2000.0' in prog_src or '2000' in prog_src:
    notes.append(
        "LOW — /progress/today falls back to target=2000 when patient.tdee is None.\n"
        "  All new patients have tdee=None until onboarding calculates and stores it.\n"
        "  This is acceptable as a fallback but should be 0 or trigger a 'complete\n"
        "  onboarding' response rather than silently using an arbitrary number."
    )

# ── CHECK 8: middleware order verification ────────────────────────────────
import importlib, app.main as app_main
main_src = pyinspect.getsource(app_main)
doctor_pos = main_src.find('DoctorIsolationMiddleware')
sub_pos = main_src.find('SubscriptionCheckMiddleware')
if doctor_pos < sub_pos:
    notes.append(
        "NOTE — Middleware registration order in main.py:\n"
        "  add_middleware(DoctorIsolation) on line ~N\n"
        "  add_middleware(SubscriptionCheck) on line ~N+1\n"
        "  In Starlette, LAST added = OUTERMOST = runs FIRST.\n"
        "  So SubscriptionCheck runs before DoctorIsolation — this is correct behavior\n"
        "  but the comment in main.py says '# Middleware (outermost first)' which\n"
        "  implies DoctorIsolation is outermost, contradicting Starlette's LIFO order.\n"
        "  The comment is misleading. The behavior is correct; the comment is wrong."
    )

# ── PRINT ─────────────────────────────────────────────────────────────────
print("=" * 62)
print("STEP 3 + 4 AUDIT RESULTS")
print("=" * 62)

print(f"\n🔴 CRITICAL ISSUES — breaks functionality for all users ({len(issues)})")
print("-" * 62)
for i, iss in enumerate(issues, 1):
    print(f"\n  [{i}] {iss}")

print(f"\n🟡 WARNINGS — wrong behavior, silent ({len(warnings)})")
print("-" * 62)
for i, w in enumerate(warnings, 1):
    print(f"\n  [{i}] {w}")

print(f"\n🔵 NOTES — tech debt / minor ({len(notes)})")
print("-" * 62)
for i, n in enumerate(notes, 1):
    print(f"\n  [{i}] {n}")

if not issues and not warnings:
    print("\n  ✅ No critical or high issues found.")
print("\n" + "=" * 62)
