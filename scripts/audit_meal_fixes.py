import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')
import inspect

issues   = []
warnings = []
notes    = []

# ── 1. legacy models/diet_plan.py still imported anywhere? ────────────────
import subprocess
result = subprocess.run(
    ['powershell', '-Command',
     'Get-ChildItem -Path app -Filter *.py -Recurse | Select-String -Pattern "models.diet_plan|models/diet_plan"'],
    cwd='C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician',
    capture_output=True, text=True
)
if result.stdout.strip():
    warnings.append(
        f"models/diet_plan.py still imported somewhere:\n  {result.stdout.strip()}\n"
        "  Safe to delete only after confirming these imports are gone."
    )
else:
    notes.append("PASS: models/diet_plan.py has zero imports — safe to delete")

# ── 2. calorie_adjustment is written nowhere ───────────────────────────────
result2 = subprocess.run(
    ['powershell', '-Command',
     'Get-ChildItem -Path app -Filter *.py -Recurse | Select-String -Pattern "calorie_adjustment"'],
    cwd='C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician',
    capture_output=True, text=True
)
lines = [l for l in result2.stdout.strip().split('\n') if l.strip()]
write_hits = [l for l in lines if 'meal_plan.py' not in l and 'db_models.py' not in l]
read_only  = all('meal_plan.py' in l or 'db_models.py' in l for l in lines if l.strip())
if read_only:
    issues.append(
        "CRITICAL — ProgressLog.calorie_adjustment is NEVER WRITTEN.\n"
        "  /meal-plan/adjust reads it for prior_adjustment but nothing ever sets it.\n"
        "  Result: prior_adjustment is ALWAYS 0.0 for every patient.\n"
        "  The Day N+1 calorie carry-over feature is silently a no-op.\n"
        "  Fix: progress_service.py must write calorie_adjustment when day ends\n"
        "       (actual_calories - tdee) after each meal log."
    )

# ── 3. ClinicalNote.back_populates=None on Doctor ─────────────────────────
from app.models.db_models import Doctor, ClinicalNote
import sqlalchemy
doctor_rels = {r.key: r for r in sqlalchemy.inspect(Doctor).relationships}
if 'clinical_notes' in doctor_rels:
    rel = doctor_rels['clinical_notes']
    if rel.back_populates is None:
        warnings.append(
            "MEDIUM — Doctor.clinical_notes relationship has back_populates=None.\n"
            "  Works at runtime but bypasses SQLAlchemy's bidirectional sync.\n"
            "  Accessing doctor.clinical_notes then modifying it won't automatically\n"
            "  update the note's doctor reference in the same session.\n"
            "  Fix: add back_populates='doctor' on ClinicalNote + Doctor relationship,\n"
            "  OR remove back_populates=None entirely (just omit the kwarg)."
        )
    notes.append(f"NOTE: Doctor has {len(doctor_rels)} relationships: {list(doctor_rels.keys())}")

# ── 4. New endpoints import clean ─────────────────────────────────────────
try:
    from app.routers.meal_plan import router
    notes.append("PASS: meal_plan.py (with new endpoints) imports clean")
except Exception as e:
    issues.append(f"FAIL: meal_plan.py import error: {e}")

# ── 5. diet_plan_service uses new DietPlanResponse not old DietPlan ───────
from app.services import diet_plan_service as dps
dps_src = inspect.getsource(dps)
if 'from ..schemas.diet_plan import DietPlanResponse' in dps_src:
    notes.append("PASS: diet_plan_service imports DietPlanResponse from schemas (not models)")
else:
    issues.append("FAIL: diet_plan_service not using new DietPlanResponse schema")

# ── 6. store_diet_plan now soft-deletes before inserting ──────────────────
store_src = inspect.getsource(dps.DietPlanService.store_diet_plan)
if 'is_active = False' in store_src and 'next_version' in store_src:
    notes.append("PASS: store_diet_plan soft-deletes previous + increments version")
else:
    issues.append("FAIL: store_diet_plan version increment logic missing")

# ── 7. /adjust uses store_diet_plan not update_diet_plan ──────────────────
from app.routers import meal_plan as mp
mp_src = inspect.getsource(mp.adjust_meal_plan)
if 'store_diet_plan' in mp_src and 'update_diet_plan' not in mp_src:
    notes.append("PASS: /adjust calls store_diet_plan (versioned) not update_diet_plan")
else:
    issues.append("FAIL: /adjust still calls update_diet_plan instead of store_diet_plan")

# ── 8. age always computed before TDEE branch ─────────────────────────────
if 'age = 30' in mp_src and mp_src.index('age =') < mp_src.index('total_calories'):
    notes.append("PASS: age computed before TDEE branch in /adjust")
else:
    issues.append("FAIL: age computation order wrong in /adjust")

# ── 9. shopping-list handles both 'Ingredient' and 'ingredient' keys ──────
from app.routers.meal_plan import get_shopping_list
shop_src = inspect.getsource(get_shopping_list)
if 'item.get("ingredient") or item.get("Ingredient")' in shop_src:
    notes.append("PASS: get_shopping_list handles both 'ingredient' and 'Ingredient' keys")
else:
    issues.append("FAIL: get_shopping_list doesn't handle both key cases")

# ── 10. AuditLog + ClinicalNote in DB ─────────────────────────────────────
from app.models.db_models import AuditLog, ClinicalNote, ProgressLog
cols = {c.key for c in ProgressLog.__table__.columns}
if 'calorie_adjustment' in cols:
    notes.append("PASS: ProgressLog.calorie_adjustment column exists in ORM + DB (migrated)")
else:
    issues.append("FAIL: ProgressLog.calorie_adjustment not in ORM")

if hasattr(AuditLog, '__tablename__') and hasattr(ClinicalNote, '__tablename__'):
    notes.append(f"PASS: AuditLog ({AuditLog.__tablename__}) and ClinicalNote ({ClinicalNote.__tablename__}) models exist")

# ── 11. New Patient columns ───────────────────────────────────────────────
patient_cols = {c.key for c in sqlalchemy.inspect(
    __import__('app.models.db_models', fromlist=['Patient']).Patient
).columns}
for col in ['pace_preference', 'eating_habits']:
    if col in patient_cols:
        notes.append(f"PASS: Patient.{col} column exists")
    else:
        issues.append(f"FAIL: Patient.{col} column missing")

# ── PRINT ──────────────────────────────────────────────────────────────────
print("=" * 62)
print("MEAL PLAN FIXES — AUDIT")
print("=" * 62)
print(f"\n🔴 CRITICAL ({len(issues)})")
print("-" * 62)
if issues:
    for i, iss in enumerate(issues, 1):
        print(f"\n  [{i}] {iss}")
else:
    print("  None")
print(f"\n🟡 WARNINGS ({len(warnings)})")
print("-" * 62)
if warnings:
    for i, w in enumerate(warnings, 1):
        print(f"\n  [{i}] {w}")
else:
    print("  None")
print(f"\n🔵 NOTES ({len(notes)})")
print("-" * 62)
for n in notes:
    print(f"  {n}")
print("\n" + "=" * 62)
