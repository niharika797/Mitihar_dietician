import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')

from app.models.db_models import (
    Patient, MealLog, ProgressLog, Recommendation,
    Doctor, Admin, PatientRequest, SubscriptionCode, FoodItem
)

issues = []
warnings = []

print("All 8 new ORM models import successfully\n")

def cols(model):
    return {c.key: c for c in model.__table__.columns}

def rels(model):
    from sqlalchemy import inspect
    return {r.key: r for r in inspect(model).relationships}

# 1. Patient required columns
p = cols(Patient)
required = ['id','email','hashed_password','name','gender','height_cm','weight_kg',
            'activity_level','diet_type','region','health_condition',
            'bmi','bmr','tdee','nonveg_meals_per_week','role','user_type',
            'subscription_status','subscription_end_date','is_active',
            'disclaimer_accepted_at','doctor_id']
for f in required:
    if f not in p:
        issues.append(f"Patient MISSING column: {f}")

# 2. Nullable audit
must_not_be_nullable = [
    (Patient, 'email'), (Patient, 'hashed_password'), (Patient, 'name'),
    (Patient, 'gender'), (Patient, 'height_cm'), (Patient, 'weight_kg'),
    (Patient, 'activity_level'), (Patient, 'diet_type'), (Patient, 'region'),
    (MealLog, 'patient_id'), (MealLog, 'logged_date'),
    (ProgressLog, 'patient_id'), (ProgressLog, 'log_date'),
    (Recommendation, 'patient_id'), (Recommendation, 'meals'),
]
for model, field in must_not_be_nullable:
    c = cols(model)
    if field not in c:
        issues.append(f"{model.__tablename__}.{field} MISSING")
    elif c[field].nullable:
        issues.append(f"NULLABLE MISMATCH: {model.__tablename__}.{field} should be NOT NULL")

# 3. Default value audit
defaults_to_check = [
    (Patient, 'health_condition', 'Healthy'),
    (Patient, 'user_type', 'standalone'),
    (Patient, 'subscription_status', 'inactive'),
    (Patient, 'role', 'patient'),
    (Patient, 'nonveg_meals_per_week', 3),
    (Patient, 'meals_per_day', 5),
    (Patient, 'water_glasses', 8),
    (Doctor,  'role', 'doctor'),
    (Admin,   'role', 'admin'),
    (Recommendation, 'is_active', True),
    (Recommendation, 'generated_by', 'system'),
    (Recommendation, 'version', 1),
    (ProgressLog, 'streak_days', 0),
]
for model, field, expected in defaults_to_check:
    c = cols(model)
    if field not in c:
        issues.append(f"{model.__tablename__}.{field} column MISSING")
        continue
    col = c[field]
    if col.default is None and col.server_default is None:
        warnings.append(f"DEFAULT missing at ORM level: {model.__tablename__}.{field} (expected {expected!r})")

# 4. FK integrity
fk_checks = [
    (Patient, 'doctor_id', 'doctors.id'),
    (Recommendation, 'patient_id', 'patients.id'),
    (MealLog, 'patient_id', 'patients.id'),
    (MealLog, 'recommendation_id', 'recommendations.id'),
    (MealLog, 'food_id', 'food_items.id'),
    (ProgressLog, 'patient_id', 'patients.id'),
    (PatientRequest, 'patient_id', 'patients.id'),
    (PatientRequest, 'doctor_id', 'doctors.id'),
    (SubscriptionCode, 'doctor_id', 'doctors.id'),
    (SubscriptionCode, 'used_by_patient_id', 'patients.id'),
]
for model, field, expected_target in fk_checks:
    c = cols(model)
    if field not in c:
        issues.append(f"FK MISSING column: {model.__tablename__}.{field}")
        continue
    fks = list(c[field].foreign_keys)
    if not fks:
        issues.append(f"NO FK CONSTRAINT: {model.__tablename__}.{field} -> {expected_target}")
    else:
        actual = str(list(fks)[0].target_fullname)
        if actual != expected_target:
            issues.append(f"FK WRONG TARGET: {model.__tablename__}.{field} -> {actual} (expected {expected_target})")

# 5. Relationships
rel_checks = [
    (Patient, ['doctor','recommendations','meal_logs','progress_logs','patient_requests']),
    (Doctor,  ['patients','patient_requests','subscription_codes']),
    (Recommendation, ['patient','meal_logs']),
    (MealLog, ['patient','recommendation','food_item']),
    (ProgressLog, ['patient']),
]
for model, expected_rels in rel_checks:
    r = rels(model)
    for rel_name in expected_rels:
        if rel_name not in r:
            warnings.append(f"RELATIONSHIP MISSING: {model.__tablename__}.{rel_name}")

# 6. PatientRequest.requested_at no server_default
pr = cols(PatientRequest)
if 'requested_at' in pr:
    col = pr['requested_at']
    if col.server_default is None and col.default is None:
        issues.append(
            "PatientRequest.requested_at has no default/server_default. "
            "Every INSERT must pass it explicitly or it will be NULL. Fix: server_default=func.now()"
        )

# 7. ProgressLog.streak_days nullable
pl = cols(ProgressLog)
if 'streak_days' in pl and pl['streak_days'].nullable:
    warnings.append("ProgressLog.streak_days is nullable in DB — should be NOT NULL default=0")

# PRINT RESULTS
print("COLUMN COUNT SUMMARY")
print("="*55)
for model in [Patient, Doctor, Admin, Recommendation, MealLog, ProgressLog, PatientRequest, SubscriptionCode]:
    print(f"  {model.__tablename__:25s}: {len(cols(model))} columns")

print("\nISSUES (fix before Step 3)")
print("="*55)
if issues:
    for i in issues:
        print(f"  FAIL: {i}")
else:
    print("  PASS: None found")

print("\nWARNINGS (fix before Phase 1)")
print("="*55)
if warnings:
    for w in warnings:
        print(f"  WARN: {w}")
else:
    print("  PASS: None found")
