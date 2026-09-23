"""
Seed 50 test patients across all medical condition profiles.
Idempotent — checks by email before creating.

Run:
    python -m tests.performance.seed_test_patients

Outputs:
    tests/performance/test_manifest.json

Next step after seeding:
    For plan quality tests, generate plans for all patients first:
    POST /api/v1/diet-plans/generate  (as each patient, or via admin script)
"""

import asyncio
import json
import secrets
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.db_models import Doctor, Patient, PatientVisit

MANIFEST_PATH = Path(__file__).parent / "test_manifest.json"

TEST_PASSWORD = "TestPat@2026"
DOCTOR_PASSWORD = "DoctorTest@2026"

DOCTOR_DEFS = [
    {"email": "dr.ashok.mehta@mityahar-perf.com",  "name": "Dr. Ashok Mehta"},
    {"email": "dr.priya.sharma@mityahar-perf.com", "name": "Dr. Priya Sharma"},
    {"email": "dr.rahul.verma@mityahar-perf.com",  "name": "Dr. Rahul Verma"},
    {"email": "dr.sunita.nair@mityahar-perf.com",  "name": "Dr. Sunita Nair"},
    {"email": "dr.amit.joshi@mityahar-perf.com",   "name": "Dr. Amit Joshi"},
    {"email": "dr.kavita.reddy@mityahar-perf.com", "name": "Dr. Kavita Reddy"},
]

# fmt: off
# (idx, condition_label, diet_type, region, age, weight_kg, height_cm,
#  gender, activity_level, medical_conditions, nonveg_per_week, health_goals)
PATIENT_PROFILES = [
    # Healthy ×5
    (1,  "Healthy",              "Vegetarian",    "North", 28, 62.0, 165, "Female", "MA", [],                                   0, ["Weight Loss"]),
    (2,  "Healthy",              "Non-Vegetarian","South", 32, 75.0, 178, "Male",   "LA", [],                                   5, []),
    (3,  "Healthy",              "Eggetarian",    "East",  25, 58.0, 162, "Female", "VA", [],                                   0, ["Muscle Gain"]),
    (4,  "Healthy",              "Vegetarian",    "West",  45, 80.0, 172, "Male",   "S",  [],                                   0, []),
    (5,  "Healthy",              "Non-Vegetarian","North", 38, 70.0, 170, "Male",   "MA", [],                                   4, []),
    # Diabetic ×5
    (6,  "Diabetic",             "Vegetarian",    "South", 52, 78.0, 163, "Male",   "LA", ["Type 2 Diabetes"],                  0, []),
    (7,  "Diabetic",             "Eggetarian",    "North", 47, 68.0, 160, "Female", "S",  ["Type 2 Diabetes"],                  0, []),
    (8,  "Diabetic",             "Non-Vegetarian","East",  55, 85.0, 175, "Male",   "MA", ["Type 2 Diabetes"],                  3, []),
    (9,  "Diabetic",             "Vegetarian",    "West",  43, 72.0, 158, "Female", "LA", ["Type 2 Diabetes"],                  0, []),
    (10, "Diabetic",             "Vegetarian",    "South", 50, 88.0, 173, "Male",   "S",  ["Pre-diabetes"],                     0, []),
    # PCOS ×5
    (11, "PCOS",                 "Vegetarian",    "North", 24, 65.0, 162, "Female", "MA", ["PCOS/PCOD"],                        0, []),
    (12, "PCOS",                 "Eggetarian",    "South", 27, 70.0, 158, "Female", "LA", ["PCOS/PCOD"],                        0, []),
    (13, "PCOS",                 "Vegetarian",    "East",  30, 75.0, 165, "Female", "S",  ["PCOS/PCOD"],                        0, []),
    (14, "PCOS",                 "Non-Vegetarian","West",  22, 60.0, 160, "Female", "VA", ["PCOS/PCOD"],                        3, []),
    (15, "PCOS",                 "Vegetarian",    "North", 28, 68.0, 163, "Female", "MA", ["PCOS/PCOD"],                        0, []),
    # Hypothyroid ×5
    (16, "Hypothyroid",          "Vegetarian",    "South", 35, 72.0, 162, "Female", "LA", ["Hypothyroidism"],                   0, []),
    (17, "Hypothyroid",          "Eggetarian",    "North", 40, 78.0, 165, "Female", "S",  ["Hypothyroidism"],                   0, []),
    (18, "Hypothyroid",          "Vegetarian",    "East",  45, 82.0, 160, "Female", "MA", ["Hypothyroidism"],                   0, []),
    (19, "Hypothyroid",          "Non-Vegetarian","West",  38, 68.0, 163, "Male",   "LA", ["Hypothyroidism"],                   3, []),
    (20, "Hypothyroid",          "Vegetarian",    "South", 32, 74.0, 158, "Female", "S",  ["Hypothyroidism"],                   0, []),
    # High Cholesterol ×5
    (21, "High_Cholesterol",     "Vegetarian",    "North", 48, 80.0, 170, "Male",   "S",  ["High Cholesterol"],                 0, []),
    (22, "High_Cholesterol",     "Non-Vegetarian","South", 52, 85.0, 175, "Male",   "LA", ["High Cholesterol"],                 2, []),
    (23, "High_Cholesterol",     "Vegetarian",    "East",  45, 75.0, 165, "Female", "MA", ["High Cholesterol"],                 0, []),
    (24, "High_Cholesterol",     "Eggetarian",    "West",  55, 90.0, 173, "Male",   "S",  ["High Cholesterol"],                 0, []),
    (25, "High_Cholesterol",     "Vegetarian",    "North", 50, 78.0, 168, "Female", "LA", ["High Cholesterol"],                 0, []),
    # Gout ×5
    (26, "Gout",                 "Non-Vegetarian","South", 55, 88.0, 172, "Male",   "S",  ["Gout"],                             3, []),
    (27, "Gout",                 "Vegetarian",    "North", 48, 78.0, 168, "Male",   "LA", ["Gout"],                             0, []),
    (28, "Gout",                 "Eggetarian",    "East",  52, 82.0, 170, "Male",   "S",  ["Gout"],                             0, []),
    (29, "Gout",                 "Non-Vegetarian","West",  60, 92.0, 175, "Male",   "MA", ["Gout"],                             4, []),
    (30, "Gout",                 "Vegetarian",    "South", 45, 75.0, 165, "Male",   "LA", ["Gout"],                             0, []),
    # IBS ×4
    (31, "IBS",                  "Vegetarian",    "North", 30, 58.0, 162, "Female", "MA", ["IBS/IBD"],                          0, []),
    (32, "IBS",                  "Eggetarian",    "South", 35, 65.0, 165, "Female", "LA", ["IBS/IBD"],                          0, []),
    (33, "IBS",                  "Vegetarian",    "East",  28, 62.0, 160, "Female", "S",  ["IBS/IBD"],                          0, []),
    (34, "IBS",                  "Non-Vegetarian","West",  38, 72.0, 172, "Male",   "MA", ["IBS/IBD"],                          2, []),
    # Hypertension ×4
    (35, "Hypertension",         "Vegetarian",    "North", 50, 82.0, 170, "Male",   "S",  ["Hypertension"],                     0, []),
    (36, "Hypertension",         "Eggetarian",    "South", 55, 78.0, 165, "Female", "LA", ["Hypertension"],                     0, []),
    (37, "Hypertension",         "Non-Vegetarian","East",  48, 88.0, 175, "Male",   "S",  ["Hypertension"],                     3, []),
    (38, "Hypertension",         "Vegetarian",    "West",  52, 75.0, 162, "Female", "MA", ["Hypertension"],                     0, []),
    # Anemia ×4
    (39, "Anemia",               "Vegetarian",    "North", 25, 52.0, 158, "Female", "MA", ["Anemia"],                           0, []),
    (40, "Anemia",               "Eggetarian",    "South", 28, 55.0, 160, "Female", "LA", ["Anemia"],                           0, []),
    (41, "Anemia",               "Vegetarian",    "East",  22, 50.0, 155, "Female", "S",  ["Anemia"],                           0, []),
    (42, "Anemia",               "Non-Vegetarian","West",  35, 60.0, 162, "Female", "MA", ["Anemia"],                           3, []),
    # Kidney Disease ×3
    (43, "Kidney_Disease",       "Vegetarian",    "North", 55, 68.0, 165, "Male",   "S",  ["Kidney Disease"],                   0, []),
    (44, "Kidney_Disease",       "Vegetarian",    "South", 60, 72.0, 168, "Male",   "LA", ["Kidney Disease"],                   0, []),
    (45, "Kidney_Disease",       "Eggetarian",    "East",  50, 65.0, 162, "Female", "S",  ["Kidney Disease"],                   0, []),
    # Healthy + Gym ×3
    (46, "Healthy_Gym",          "Non-Vegetarian","West",  28, 78.0, 178, "Male",   "VA", [],                                   5, ["Muscle Gain"]),
    (47, "Healthy_Gym",          "Eggetarian",    "North", 25, 70.0, 172, "Male",   "VA", [],                                   0, ["Muscle Gain"]),
    (48, "Healthy_Gym",          "Non-Vegetarian","South", 30, 75.0, 175, "Male",   "VA", [],                                   5, ["Muscle Gain"]),
    # Diabetic + Hypertension ×2 (spec says 3, but 5+5+5+5+5+5+4+4+4+3+3+3=51; using 2 to cap at 50)
    (49, "Diabetic_Hypertension","Vegetarian",    "East",  58, 80.0, 168, "Male",   "S",  ["Type 2 Diabetes","Hypertension"],   0, []),
    (50, "Diabetic_Hypertension","Eggetarian",    "West",  55, 75.0, 163, "Female", "LA", ["Type 2 Diabetes","Hypertension"],   0, []),
]
# fmt: on

ACTIVITY_MULTIPLIERS = {"S": 1.2, "LA": 1.375, "MA": 1.55, "VA": 1.725, "SA": 1.9}

CONDITION_TO_HEALTH = {
    "Diabetic":              "Healthy",
    "PCOS":                  "Healthy",
    "Hypothyroid":           "Healthy",
    "High_Cholesterol":      "Healthy",
    "Gout":                  "Healthy",
    "IBS":                   "Healthy",
    "Hypertension":          "Healthy",
    "Anemia":                "Healthy",
    "Kidney_Disease":        "Healthy",
    "Healthy_Gym":           "Healthy",
    "Diabetic_Hypertension": "Healthy",
}


def _calc_metrics(gender, weight_kg, height_cm, age, activity_level):
    if gender == "Male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    tdee = bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)  # matches calculations.py default
    bmi = weight_kg / ((height_cm / 100) ** 2)
    return round(bmr, 2), round(tdee, 2), round(bmi, 2)


async def _get_or_create_doctors_via_api(base_url: str, admin_token: str) -> dict:
    """Create test doctors via POST /api/v1/admin/doctors (exercises real API + Pydantic validation).
    On 409 (already exists), falls back to a read-only ORM lookup to retrieve the existing ID."""
    import httpx
    doctor_map = {}
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        for d in DOCTOR_DEFS:
            r = await client.post(
                "/api/v1/admin/doctors",
                json={"email": d["email"], "name": d["name"], "password": DOCTOR_PASSWORD, "specialization": "General Dietetics"},
                headers=headers,
            )
            if r.status_code == 201:
                doc_id = r.json()["id"]
                print(f"  [CREATE] Doctor {d['email']} id={doc_id}")
                doctor_map[d["email"]] = doc_id
            elif r.status_code == 409:
                # Already exists — read-only ORM lookup (no write, no validation bypass)
                async with AsyncSessionLocal() as rs:
                    result = await rs.execute(select(Doctor).where(Doctor.email == d["email"]))
                    doc = result.scalars().first()
                    if doc:
                        print(f"  [EXISTS] Doctor {d['email']} id={doc.id}")
                        doctor_map[d["email"]] = doc.id
                    else:
                        print(f"  [WARN  ] Doctor {d['email']} → 409 but not found in DB")
            else:
                print(f"  [FAIL  ] Doctor {d['email']} → {r.status_code} {r.text}")
    return doctor_map


async def _seed_patient(session, profile, doctor_id) -> dict:
    (idx, condition, diet_type, region, age, weight_kg, height_cm,
     gender, activity_level, medical_conditions, nonveg_per_week, health_goals) = profile

    email = f"testpatient{idx:03d}@mityahar.test"
    result = await session.execute(select(Patient).where(Patient.email == email))
    existing = result.scalars().first()

    bmr, tdee, bmi = _calc_metrics(gender, weight_kg, height_cm, age, activity_level)
    dob = date(date.today().year - age, 6, 15)
    health_condition = CONDITION_TO_HEALTH.get(condition, "Healthy")

    if existing is None:
        patient = Patient(
            email=email,
            hashed_password=get_password_hash(TEST_PASSWORD),
            name=f"Test Patient {idx:03d}",
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            activity_level=activity_level,
            diet_type=diet_type,
            region=region,
            health_condition=health_condition,
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            medical_conditions=medical_conditions,
            food_allergies=[],
            health_goals=health_goals,
            nonveg_meals_per_week=nonveg_per_week,
            date_of_birth=dob,
            doctor_id=doctor_id,
            user_type="doctor_assigned",
            subscription_status="active",
            token_1_active=True,
            token_1_expiry=datetime.now(timezone.utc) + timedelta(days=30),
            disclaimer_accepted_at=datetime.now(timezone.utc),
            is_email_verified=True,
            meals_per_day=3,
        )
        session.add(patient)
        await session.flush()
        patient.token_1 = f"PERF-{patient.id:05d}"

        result_pv = await session.execute(
            select(PatientVisit).where(
                PatientVisit.patient_id == patient.id,
                PatientVisit.doctor_id == doctor_id,
            )
        )
        if result_pv.scalars().first() is None:
            now = datetime.now(timezone.utc)
            session.add(PatientVisit(
                patient_id=patient.id,
                doctor_id=doctor_id,
                token_2=secrets.token_hex(8).upper(),
                cycle_start=now,
                cycle_expiry=now + timedelta(days=30),
                visit_counter=0,
            ))
        await session.flush()
        print(f"  [CREATE] P{idx:03d} {email} ({condition}) id={patient.id}")
    else:
        patient = existing
        print(f"  [EXISTS] P{idx:03d} {email} ({condition}) id={patient.id}")

    return {
        "index": idx,
        "patient_id": patient.id,
        "email": email,
        "condition": condition,
        "diet_type": diet_type,
        "region": region,
        "doctor_id": doctor_id,
        "medical_conditions": medical_conditions,
        "tdee": float(patient.tdee or tdee),
        "health_condition": health_condition,
    }


async def main():
    import httpx
    import os

    print("=== Mityahar Performance Test Patient Seeder ===\n")

    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8001")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@mityahar.com")
    admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "")
    if not admin_password:
        print("[ERROR] ADMIN_SEED_PASSWORD not set in .env — cannot create doctors via API.")
        print("        Ensure backend is running and seed_admin has been run first.")
        sys.exit(1)

    print("[0/4] Authenticating as admin...")
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        r = await client.post(
            "/api/v1/auth/admin/login",
            data={"username": admin_email, "password": admin_password},
        )
        if r.status_code != 200:
            print(f"[ERROR] Admin login failed: {r.status_code} {r.text}")
            sys.exit(1)
        admin_token = r.json()["access_token"]
        print(f"  [OK] Admin token obtained")

    print("\n[1/4] Setting up test doctors via admin API...")
    doctor_map = await _get_or_create_doctors_via_api(base_url, admin_token)
    if not doctor_map:
        print("[ERROR] No doctors created or found — aborting.")
        sys.exit(1)
    doctor_ids = list(doctor_map.values())

    print(f"\n[2/4] Seeding {len(PATIENT_PROFILES)} test patients...")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            manifest_patients = []
            for i, profile in enumerate(PATIENT_PROFILES):
                doctor_id = doctor_ids[i % len(doctor_ids)]
                record = await _seed_patient(session, profile, doctor_id)
                manifest_patients.append(record)

    print(f"\n[3/4] Writing manifest → {MANIFEST_PATH}")
    manifest = {
        "total": len(manifest_patients),
        "patient_password": TEST_PASSWORD,
        "doctors": [
            {"email": e, "id": i, "doctor_id": i, "password": DOCTOR_PASSWORD}
            for e, i in doctor_map.items()
        ],
        "patients": manifest_patients,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\n[4/4] Done: {len(manifest_patients)} patients, {len(doctor_map)} doctors.")
    print("\nNext: python -m tests.performance.benchmark_api")


if __name__ == "__main__":
    asyncio.run(main())
