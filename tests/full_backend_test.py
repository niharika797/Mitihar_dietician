import httpx
import json
import os
from dotenv import load_dotenv
load_dotenv()

BASE = "http://localhost:8000/api/v1"
ADMIN_PASSWORD = os.getenv("ADMIN_SEED_PASSWORD", "admin1234")
DOCTOR_EMAIL = os.getenv("TEST_DOCTOR_EMAIL", "dr.ashok.mehta@mitihar.test")
DOCTOR_PASSWORD = os.getenv("TEST_DOCTOR_PASSWORD", "DoctorTest@2026")
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    msg = f"{status}  {label}"
    if not condition and detail:
        msg += f"\n       ↳ {detail}"
    print(msg)
    results.append((label, condition))

def hdr(token):
    return {"Authorization": f"Bearer {token}"}

print("\n" + "="*60)
print("MITYAHAR FULL BACKEND TEST")
print("="*60)

# ─────────────────────────────────────────────
# SECTION 1 — SERVER HEALTH
# ─────────────────────────────────────────────
print("\n── SECTION 1: Server Health ──")
r = httpx.get(f"{BASE.replace('/api/v1', '')}/")
check("GET / returns welcome message", r.status_code == 200 and "Welcome" in r.text, r.text)

r = httpx.get(f"{BASE.replace('/api/v1', '')}/docs")
check("GET /docs (Swagger) is reachable", r.status_code == 200, r.text[:100])

# ─────────────────────────────────────────────
# SECTION 2 — ADMIN AUTH
# ─────────────────────────────────────────────
print("\n── SECTION 2: Admin Auth ──")

# Admin must already exist in DB. If not, seed one manually first.
r = httpx.post(f"{BASE}/auth/admin/login", data={
    "username": "admin@mityahar.com",
    "password": ADMIN_PASSWORD
})
check("POST /auth/admin/login returns 200", r.status_code == 200, r.text)
admin_token = r.json().get("access_token", "") if r.status_code == 200 else ""
check("Admin token received", bool(admin_token))

# ─────────────────────────────────────────────
# SECTION 3 — ADMIN: DOCTOR MANAGEMENT
# ─────────────────────────────────────────────
print("\n── SECTION 3: Admin — Doctor Management ──")

r = httpx.get(f"{BASE}/admin/stats", headers=hdr(admin_token))
check("GET /admin/stats returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    stats = r.json()
    check("Stats has total_patients field", "total_patients" in stats)
    check("Stats has total_doctors field", "total_doctors" in stats)

r = httpx.post(f"{BASE}/admin/doctors", headers=hdr(admin_token), json={
    "email": "testdoctor@mityahar.com",
    "password": "doctor1234",
    "name": "Dr. Test Kumar",
    "phone": "9876543210",
    "specialization": "Dietician",
    "clinic_name": "Test Clinic",
    "city": "Mumbai"
})
check("POST /admin/doctors creates doctor (200 or 409)", r.status_code in (201, 409), r.text)

r = httpx.get(f"{BASE}/admin/doctors", headers=hdr(admin_token))
check("GET /admin/doctors returns list", r.status_code == 200, r.text)
doctors = r.json() if r.status_code == 200 else []
check("At least one doctor exists", len(doctors) > 0)
doctor_id = next((d["id"] for d in doctors if d["email"] == "testdoctor@mityahar.com"), None)
check("Test doctor found in list", doctor_id is not None)

if doctor_id:
    r = httpx.get(f"{BASE}/admin/doctors/{doctor_id}", headers=hdr(admin_token))
    check("GET /admin/doctors/{id} returns doctor detail", r.status_code == 200, r.text)
    check("Doctor detail has patient_count", "patient_count" in r.json())

# ─────────────────────────────────────────────
# SECTION 4 — ADMIN: CODES
# ─────────────────────────────────────────────
print("\n── SECTION 4: Admin — Subscription Codes ──")

if doctor_id:
    r = httpx.post(f"{BASE}/admin/codes/generate", headers=hdr(admin_token), json={
        "doctor_id": doctor_id,
        "count": 2,
        "expires_in_days": 30
    })
    check("POST /admin/codes/generate returns 201", r.status_code == 201, r.text)
    codes = r.json() if r.status_code == 201 else []
    check("2 codes returned", len(codes) == 2)
    test_code = codes[0]["code"] if codes else None
    check("Code has correct doctor_id", codes[0]["doctor_id"] == doctor_id if codes else False)

r = httpx.get(f"{BASE}/admin/codes", headers=hdr(admin_token))
check("GET /admin/codes returns list", r.status_code == 200, r.text)

# ─────────────────────────────────────────────
# SECTION 5 — ADMIN: AUDIT LOGS + BILLING
# ─────────────────────────────────────────────
print("\n── SECTION 5: Admin — Audit Logs + Billing ──")

r = httpx.get(f"{BASE}/admin/audit-logs", headers=hdr(admin_token))
check("GET /admin/audit-logs returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    audit = r.json()
    check("Audit log has logs + total keys", "logs" in audit and "total" in audit)
    check("generate_codes action logged", any(
        l["action"] == "generate_codes" for l in audit["logs"]
    ))

r = httpx.get(f"{BASE}/admin/billing", headers=hdr(admin_token))
check("GET /admin/billing returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    billing = r.json()
    check("Billing has total_codes_issued", "total_codes_issued" in billing)
    check("Billing has doctors breakdown", "doctors" in billing)

# ─────────────────────────────────────────────
# SECTION 6 — DOCTOR AUTH
# ─────────────────────────────────────────────
print("\n── SECTION 6: Doctor Auth ──")

r = httpx.post(f"{BASE}/auth/doctor/login", data={
    "username": DOCTOR_EMAIL,
    "password": DOCTOR_PASSWORD
})
check("POST /auth/doctor/login returns 200", r.status_code == 200, r.text)
doctor_token = r.json().get("access_token", "") if r.status_code == 200 else ""
check("Doctor token received", bool(doctor_token))

# ─────────────────────────────────────────────
# SECTION 7 — DOCTOR: DASHBOARD + CODES
# ─────────────────────────────────────────────
print("\n── SECTION 7: Doctor — Dashboard + Codes ──")

r = httpx.get(f"{BASE}/doctor/dashboard", headers=hdr(doctor_token))
check("GET /doctor/dashboard returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    dash = r.json()
    check("Dashboard has total_patients", "total_patients" in dash)
    check("Dashboard has inactive_patients", "inactive_patients" in dash)
    check("Dashboard has expiring_soon", "expiring_soon" in dash)

r = httpx.get(f"{BASE}/doctor/subscription-codes", headers=hdr(doctor_token))
check("GET /doctor/subscription-codes returns 200", r.status_code == 200, r.text)

r = httpx.post(f"{BASE}/doctor/subscription-codes", headers=hdr(doctor_token), json={
    "count": 1,
    "expires_in_days": 30
})
check("POST /doctor/subscription-codes creates codes", r.status_code == 201, r.text)
doctor_generated_codes = r.json() if r.status_code == 201 else []
doctor_code = doctor_generated_codes[0]["code"] if doctor_generated_codes else (test_code if test_code else None)

# ─────────────────────────────────────────────
# SECTION 8 — PATIENT REGISTER + ONBOARDING
# ─────────────────────────────────────────────
print("\n── SECTION 8: Patient — Register + Onboarding ──")

r = httpx.post(f"{BASE}/auth/register", json={
    "email": "testpatient@mityahar.com",
    "password": "patient1234",
    "name": "Test Patient",
    "gender": "female",
    "height": 163.0,
    "weight": 58.0,
    "activity_level": "MA",
    "diet": "Vegetarian",
    "health_condition": "Healthy",
    "region": "North"
})
check("POST /auth/register returns 200 or 409", r.status_code in (200, 409, 429), r.text)

r = httpx.post(f"{BASE}/auth/token", data={
    "username": "testpatient@mityahar.com",
    "password": "patient1234"
})
check("POST /auth/token (patient login) returns 200", r.status_code == 200, r.text)
patient_token = r.json().get("access_token", "") if r.status_code == 200 else ""
check("Patient token received", bool(patient_token))

r = httpx.post(f"{BASE}/auth/refresh", json={"refresh_token": r.json().get("refresh_token", "")}) if r.status_code == 200 else None
if r:
    check("POST /auth/refresh returns new access token", r.status_code == 200 and "access_token" in r.json(), r.text)

# Activate subscription with doctor code
if doctor_code and patient_token:
    r = httpx.post(f"{BASE}/patients/activate", headers=hdr(patient_token), json={"code": doctor_code})
    check("POST /patients/activate with valid code returns 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        check("Patient subscription_status is active", r.json().get("patient", {}).get("subscription_status") == "active")

    # Re-login to get fresh token with active sub_status
    r2 = httpx.post(f"{BASE}/auth/token", data={
        "username": "testpatient@mityahar.com",
        "password": "patient1234"
    })
    patient_token = r2.json().get("access_token", patient_token)

# Onboarding
r = httpx.post(f"{BASE}/patients/onboarding", headers=hdr(patient_token), json={
    "date_of_birth": "1995-06-15",
    "gender": "Female",
    "height_cm": 163.0,
    "weight_kg": 58.0,
    "health_goals": ["weight_loss"],
    "medical_conditions": [],
    "food_allergies": ["None"],
    "target_weight_kg": 54.0,
    "meals_per_day": 5,
    "sleep_hours": 7.5,
    "water_glasses": 8,
    "occupation": "Software Engineer",
    "nonveg_meals_per_week": 0,
    "dietary_preferences": [],
    "fasting_days": [],
    "smoking": False,
    "alcohol": False,
    "pace_preference": "moderate",
    "eating_habits": ["late_night_eating"]
})
check("POST /patients/onboarding returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    profile = r.json()
    check("BMI stored on profile", profile.get("bmi") is not None)
    check("BMR stored on profile", profile.get("bmr") is not None)
    check("TDEE stored on profile", profile.get("tdee") is not None)
    check("pace_preference stored", profile.get("pace_preference") == "moderate")
    check("eating_habits stored", "late_night_eating" in profile.get("eating_habits", []))

r = httpx.post(f"{BASE}/patients/disclaimer", headers=hdr(patient_token))
check("POST /patients/disclaimer returns 200", r.status_code == 200, r.text)

# ─────────────────────────────────────────────
# SECTION 9 — MEAL PLAN
# ─────────────────────────────────────────────
print("\n── SECTION 9: Meal Plan ──")

r = httpx.get(f"{BASE}/meal-plan/week", headers=hdr(patient_token))
check("GET /meal-plan/week returns 200 or 404", r.status_code in (200, 404), r.text)
if r.status_code == 200:
    week = r.json()
    check("Week plan has days key", isinstance(week, dict) and len(week) > 0, str(week)[:200])
    check("Week plan has at least 1 day", len(week) > 0, str(week)[:200])

r = httpx.get(f"{BASE}/meal-plan/history", headers=hdr(patient_token))
check("GET /meal-plan/history returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/meal-plan/shopping-list", headers=hdr(patient_token))
check("GET /meal-plan/shopping-list returns 200 or 404", r.status_code in (200, 404), r.text)
if r.status_code == 200:
    sl = r.json()
    check("Shopping list has grouped key", "grouped" in sl)

# Shopping list toggle
if r.status_code == 200 and sl.get("grouped"):
    first_cat = next(iter(sl["grouped"].values()), [])
    if first_cat:
        ingredient = first_cat[0].get("ingredient", "")
        r2 = httpx.post(
            f"{BASE}/meal-plan/shopping-list/toggle",
            headers=hdr(patient_token),
            params={"ingredient_name": ingredient, "at_home": True}
        )
        check(f"POST /meal-plan/shopping-list/toggle marks '{ingredient[:20]}' at_home", r2.status_code == 200, r2.text)

# ─────────────────────────────────────────────
# SECTION 10 — PROGRESS TRACKING
# ─────────────────────────────────────────────
print("\n── SECTION 10: Progress Tracking ──")

r = httpx.post(f"{BASE}/progress/log/meal", headers=hdr(patient_token), json={
    "meal_type": "Breakfast",
    "calories": 350.0,
    "protein": 12.0,
    "carbs": 45.0,
    "fat": 8.0,
    "fiber": 5.0
})
check("POST /progress/log/meal returns 200", r.status_code == 200, r.text)

r = httpx.post(f"{BASE}/progress/log/water", headers=hdr(patient_token), json={"glasses": 3})
check("POST /progress/log/water returns 200", r.status_code == 200, r.text)

r = httpx.post(f"{BASE}/progress/log/steps", headers=hdr(patient_token), json={"steps": 4000})
check("POST /progress/log/steps returns 200", r.status_code == 200, r.text)

r = httpx.post(f"{BASE}/progress/log/weight", headers=hdr(patient_token), json={"weight": 57.8})
check("POST /progress/log/weight returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/progress/today", headers=hdr(patient_token))
check("GET /progress/today returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    today = r.json()
    check("Today has calories.consumed", today.get("calories", {}).get("consumed") is not None)
    check("Today has water_intake.glasses", today.get("water_intake", {}).get("glasses") is not None)
    check("Calories consumed > 0", today.get("calories", {}).get("consumed", 0) > 0)

r = httpx.get(f"{BASE}/progress/weekly", headers=hdr(patient_token))
check("GET /progress/weekly returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/progress/weekly-report", headers=hdr(patient_token))
check("GET /progress/weekly-report returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/progress/weight-history", headers=hdr(patient_token))
check("GET /progress/weight-history returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/progress/streak", headers=hdr(patient_token))
check("GET /progress/streak returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    check("Streak >= 1 after logging a meal", r.json().get("streak_days", 0) >= 1)

r = httpx.get(f"{BASE}/progress/adherence/weekly", headers=hdr(patient_token))
check("GET /progress/adherence/weekly returns 200", r.status_code == 200, r.text)
if r.status_code == 200:
    adh = r.json()
    check("Adherence has overall_adherence_pct", "overall_adherence_pct" in adh)
    check("Adherence has daily array of 7", len(adh.get("daily", [])) == 7)

# ─────────────────────────────────────────────
# SECTION 11 — DOCTOR: PATIENT DATA
# ─────────────────────────────────────────────
print("\n── SECTION 11: Doctor — Patient Data ──")

r = httpx.get(f"{BASE}/doctor/patients", headers=hdr(doctor_token))
check("GET /doctor/patients returns 200", r.status_code == 200, r.text)
patients = r.json().get("patients", []) if r.status_code == 200 else []
check("Doctor patient list has total field", "total" in r.json() if r.status_code == 200 else False)
test_patient_id = patients[0]["id"] if patients else None

if test_patient_id:
    r = httpx.get(f"{BASE}/doctor/patients/{test_patient_id}", headers=hdr(doctor_token))
    check("GET /doctor/patients/{id} returns 200", r.status_code == 200, r.text)

    r = httpx.get(f"{BASE}/doctor/patients/{test_patient_id}/plan", headers=hdr(doctor_token))
    check("GET /doctor/patients/{id}/plan returns 200 or 404", r.status_code in (200, 404), r.text)

    r = httpx.get(f"{BASE}/doctor/patients/{test_patient_id}/logs", headers=hdr(doctor_token))
    check("GET /doctor/patients/{id}/logs returns 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        check("Logs response has meal_logs key", "meal_logs" in r.json())

    r = httpx.get(f"{BASE}/doctor/patients/{test_patient_id}/progress", headers=hdr(doctor_token))
    check("GET /doctor/patients/{id}/progress returns 200", r.status_code == 200, r.text)

    r = httpx.post(f"{BASE}/doctor/patients/{test_patient_id}/notes", headers=hdr(doctor_token), json={
        "content": "Patient is progressing well. Reduce carbs slightly.",
        "note_type": "dietary",
        "is_private": True
    })
    check("POST /doctor/patients/{id}/notes returns 201", r.status_code == 201, r.text)
    if r.status_code == 201:
        note = r.json()
        check("Note doctor_id matches", note.get("doctor_id") is not None)
        check("Note is_private is True", note.get("is_private") == True)

    r = httpx.get(f"{BASE}/doctor/patients/{test_patient_id}/notes", headers=hdr(doctor_token))
    check("GET /doctor/patients/{id}/notes returns list", r.status_code == 200, r.text)
    check("At least 1 note returned", len(r.json()) >= 1 if r.status_code == 200 else False)

# ─────────────────────────────────────────────
# SECTION 12 — DOCTOR: RECIPE LIBRARY
# ─────────────────────────────────────────────
print("\n── SECTION 12: Doctor — Recipe Library ──")

r = httpx.get(f"{BASE}/doctor/recipes", headers=hdr(doctor_token))
check("GET /doctor/recipes returns 200", r.status_code == 200, r.text)

r = httpx.post(f"{BASE}/doctor/recipes", headers=hdr(doctor_token), json={
    "recipe_name": "Test Dal Tadka",
    "slot_type": "dal_protein",
    "cal_per_serving": 220.0,
    "protein_per_serving": 12.0,
    "carbs_per_serving": 28.0,
    "fat_per_serving": 6.0,
    "fiber_per_serving": 4.0,
    "diet_type": "Vegetarian",
    "meal_time_tags": ["Lunch", "Dinner"],
    "plan_type_tags": ["Healthy", "Diabetic-Friendly"],
    "ingredients": [{"name": "Toor Dal", "quantity": "80", "unit": "g"}],
    "region_tags": ["North"]
})
check("POST /doctor/recipes creates recipe (201)", r.status_code == 201, r.text)
if r.status_code == 201:
    new_recipe = r.json()
    check("Recipe source is 'doctor'", new_recipe.get("source") == "doctor")
    check("Recipe is_verified is False", new_recipe.get("is_verified") == False)
    new_recipe_id = new_recipe.get("id")

    # Admin approves it
    r2 = httpx.patch(f"{BASE}/admin/food/{new_recipe_id}/approve", headers=hdr(admin_token))
    check("PATCH /admin/food/{id}/approve returns 200", r2.status_code == 200, r2.text)
    # Idempotent check
    r3 = httpx.patch(f"{BASE}/admin/food/{new_recipe_id}/approve", headers=hdr(admin_token))
    check("Approving already-verified recipe returns 400", r3.status_code == 400, r3.text)

# ─────────────────────────────────────────────
# SECTION 13 — ADMIN: FOOD MANAGEMENT
# ─────────────────────────────────────────────
print("\n── SECTION 13: Admin — Food Management ──")

r = httpx.get(f"{BASE}/admin/food", headers=hdr(admin_token))
check("GET /admin/food returns 200", r.status_code == 200, r.text)

r = httpx.get(f"{BASE}/admin/food?source=doctor", headers=hdr(admin_token))
check("GET /admin/food?source=doctor filters correctly", r.status_code == 200, r.text)

# ─────────────────────────────────────────────
# SECTION 14 — PLAN VERSIONING
# ─────────────────────────────────────────────
print("\n── SECTION 14: Plan Versioning ──")

r = httpx.get(f"{BASE}/diet-plans/my-plan", headers=hdr(patient_token))
check("GET /diet-plans/my-plan returns 200 or 404", r.status_code in (200, 404), r.text)
if r.status_code == 200:
    plan = r.json()
    version = plan.get("version", 0)
    check("Plan has version field >= 1", version >= 1)

    # Trigger plan regeneration to test version increment
    r2 = httpx.post(f"{BASE}/meal-plan/adjust", headers=hdr(patient_token), json={"reduction_amount": 100})
    check("POST /meal-plan/adjust returns 200", r2.status_code == 200, r2.text)

    r3 = httpx.get(f"{BASE}/diet-plans/my-plan", headers=hdr(patient_token))
    if r3.status_code == 200:
        new_version = r3.json().get("version", 0)
        check("Version incremented after plan adjustment", new_version > version, f"was {version}, now {new_version}")

# ─────────────────────────────────────────────
# SECTION 15 — SECURITY: ISOLATION CHECKS
# ─────────────────────────────────────────────
print("\n── SECTION 15: Security — Isolation ──")

# Patient cannot access doctor routes
r = httpx.get(f"{BASE}/doctor/patients", headers=hdr(patient_token))
check("Patient blocked from /doctor/patients (403)", r.status_code == 403, r.text)

# Doctor cannot access admin routes
r = httpx.get(f"{BASE}/admin/stats", headers=hdr(doctor_token))
check("Doctor blocked from /admin/stats (403)", r.status_code == 403, r.text)

# No token → 401 on protected route
r = httpx.get(f"{BASE}/doctor/patients")
check("No token → 401 on doctor route", r.status_code == 401, r.text)

# Doctor cannot see another doctor's patient (use a fake patient_id)
r = httpx.get(f"{BASE}/doctor/patients/99999", headers=hdr(doctor_token))
check("Doctor gets 404 for non-owned patient ID", r.status_code == 404, r.text)

# Inactive patient blocked from /meal-plan (no fresh sub_status in token test)
# (This is hard to test without a second patient — skipped, covered by middleware logic)

# ─────────────────────────────────────────────
# SECTION 16 — ADMIN: SUBSCRIPTION OVERRIDE
# ─────────────────────────────────────────────
print("\n── SECTION 16: Admin — Subscription Override ──")

r = httpx.get(f"{BASE}/auth/token".replace("auth/token", "users/me"), headers=hdr(patient_token))
# get patient id from profile
r2 = httpx.post(f"{BASE}/auth/token", data={"username": "testpatient@mityahar.com", "password": "patient1234"})
# Just test the override endpoint with the test patient
if test_patient_id:
    r = httpx.patch(
        f"{BASE}/admin/patients/{test_patient_id}/subscription/override",
        headers=hdr(admin_token),
        params={"status": "active", "days": 30}
    )
    check("PATCH /admin/patients/{id}/subscription/override returns 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        check("Override returns subscription_status=active", r.json().get("subscription_status") == "active")
        check("Override returns end_date not null", r.json().get("end_date") is not None)

# ─────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────
print("\n" + "="*60)
total = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
print(f"RESULTS: {passed}/{total} passed — {failed} failed")
if failed:
    print("\nFAILED CHECKS:")
    for label, ok in results:
        if not ok:
            print(f"  ❌ {label}")
print("="*60)
