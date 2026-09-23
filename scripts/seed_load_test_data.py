"""
Seed load-test accounts (default 10 doctors x 100 patients) and publish the
manifest to GCS.

Why this exists alongside tests/performance/seed_test_patients.py:
that script is local-only. `tests/` is excluded by .dockerignore and the
Dockerfile copies only app/, alembic/, and scripts/, so it does not exist
inside the deployed image and cannot run as a Cloud Run job. Staging Cloud SQL
is private-IP-only, so a Cloud Run job is the *only* way to seed it. This
module lives under scripts/ so it ships in the image.

Two other deliberate differences from the local seeder:
  - Doctors are created via the ORM, not via POST /admin/doctors. The job holds
    DATABASE_URL but no admin credentials or API base URL, and adding both just
    to create ten rows is not worth it.
  - The shared test password is hashed ONCE. The local seeder calls
    get_password_hash per patient; at bcrypt cost 12 (~250ms) that is ~4-5
    minutes for 1000 patients, which overruns the job timeout and rolls the
    whole transaction back. Every seeded patient uses the same password, so one
    hash is equivalent and finishes in milliseconds.

Run as a Cloud Run job (staging):
    gcloud run jobs execute mityahar-seed-runner --region asia-south1 --wait

Run locally against the dev DB:
    python -m scripts.seed_load_test_data --doctors 2 --patients-per-doctor 5 --no-gcs
"""

import argparse
import asyncio
import json
import secrets
import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import select

# Must precede the app.core.database import — that module reads DATABASE_URL
# from os.environ at import time. No-op on Cloud Run, where it is a real env var.
load_dotenv()

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash
from app.models.db_models import Doctor, Patient, PatientVisit

TEST_PASSWORD = "TestPat@2026"
DOCTOR_PASSWORD = "DoctorTest@2026"

DEFAULT_BUCKET = "mityahar-staging-test-artifacts"
DEFAULT_OBJECT = "load-test/test_manifest.json"

ACTIVITY_MULTIPLIERS = {"S": 1.2, "LA": 1.375, "MA": 1.55, "VA": 1.725, "SA": 1.9}

# Doctor name pool. Cycled and suffixed if --doctors exceeds the pool size.
DOCTOR_NAMES = [
    "Dr. Ashok Mehta", "Dr. Priya Sharma", "Dr. Rahul Verma",
    "Dr. Sunita Nair", "Dr. Amit Joshi", "Dr. Kavita Reddy",
    "Dr. Vikram Rao", "Dr. Meera Iyer", "Dr. Sanjay Gupta", "Dr. Anjali Desai",
]

# fmt: off
# (condition_label, diet_type, region, age, weight_kg, height_cm,
#  gender, activity_level, medical_conditions, nonveg_per_week, health_goals)
# Mirrors tests/performance/seed_test_patients.py:51-114. Cycled to reach the
# requested patient count so the condition/diet/region mix the meal generator
# branches on stays representative instead of collapsing to one archetype.
PATIENT_ARCHETYPES = [
    ("Healthy",              "Vegetarian",    "North", 28, 62.0, 165, "Female", "MA", [],                                   0, ["Weight Loss"]),
    ("Healthy",              "Non-Vegetarian","South", 32, 75.0, 178, "Male",   "LA", [],                                   5, []),
    ("Healthy",              "Eggetarian",    "East",  25, 58.0, 162, "Female", "VA", [],                                   0, ["Muscle Gain"]),
    ("Healthy",              "Vegetarian",    "West",  45, 80.0, 172, "Male",   "S",  [],                                   0, []),
    ("Healthy",              "Non-Vegetarian","North", 38, 70.0, 170, "Male",   "MA", [],                                   4, []),
    ("Diabetic",             "Vegetarian",    "South", 52, 78.0, 163, "Male",   "LA", ["Type 2 Diabetes"],                  0, []),
    ("Diabetic",             "Eggetarian",    "North", 47, 68.0, 160, "Female", "S",  ["Type 2 Diabetes"],                  0, []),
    ("Diabetic",             "Non-Vegetarian","East",  55, 85.0, 175, "Male",   "MA", ["Type 2 Diabetes"],                  3, []),
    ("Diabetic",             "Vegetarian",    "West",  43, 72.0, 158, "Female", "LA", ["Type 2 Diabetes"],                  0, []),
    ("Diabetic",             "Vegetarian",    "South", 50, 88.0, 173, "Male",   "S",  ["Pre-diabetes"],                     0, []),
    ("PCOS",                 "Vegetarian",    "North", 24, 65.0, 162, "Female", "MA", ["PCOS/PCOD"],                        0, []),
    ("PCOS",                 "Eggetarian",    "South", 27, 70.0, 158, "Female", "LA", ["PCOS/PCOD"],                        0, []),
    ("PCOS",                 "Vegetarian",    "East",  30, 75.0, 165, "Female", "S",  ["PCOS/PCOD"],                        0, []),
    ("PCOS",                 "Non-Vegetarian","West",  22, 60.0, 160, "Female", "VA", ["PCOS/PCOD"],                        3, []),
    ("PCOS",                 "Vegetarian",    "North", 28, 68.0, 163, "Female", "MA", ["PCOS/PCOD"],                        0, []),
    ("Hypothyroid",          "Vegetarian",    "South", 35, 72.0, 162, "Female", "LA", ["Hypothyroidism"],                   0, []),
    ("Hypothyroid",          "Eggetarian",    "North", 40, 78.0, 165, "Female", "S",  ["Hypothyroidism"],                   0, []),
    ("Hypothyroid",          "Vegetarian",    "East",  45, 82.0, 160, "Female", "MA", ["Hypothyroidism"],                   0, []),
    ("Hypothyroid",          "Non-Vegetarian","West",  38, 68.0, 163, "Male",   "LA", ["Hypothyroidism"],                   3, []),
    ("Hypothyroid",          "Vegetarian",    "South", 32, 74.0, 158, "Female", "S",  ["Hypothyroidism"],                   0, []),
    ("High_Cholesterol",     "Vegetarian",    "North", 48, 80.0, 170, "Male",   "S",  ["High Cholesterol"],                 0, []),
    ("High_Cholesterol",     "Non-Vegetarian","South", 52, 85.0, 175, "Male",   "LA", ["High Cholesterol"],                 2, []),
    ("High_Cholesterol",     "Vegetarian",    "East",  45, 75.0, 165, "Female", "MA", ["High Cholesterol"],                 0, []),
    ("High_Cholesterol",     "Eggetarian",    "West",  55, 90.0, 173, "Male",   "S",  ["High Cholesterol"],                 0, []),
    ("High_Cholesterol",     "Vegetarian",    "North", 50, 78.0, 168, "Female", "LA", ["High Cholesterol"],                 0, []),
    ("Gout",                 "Non-Vegetarian","South", 55, 88.0, 172, "Male",   "S",  ["Gout"],                             3, []),
    ("Gout",                 "Vegetarian",    "North", 48, 78.0, 168, "Male",   "LA", ["Gout"],                             0, []),
    ("Gout",                 "Eggetarian",    "East",  52, 82.0, 170, "Male",   "S",  ["Gout"],                             0, []),
    ("Gout",                 "Non-Vegetarian","West",  60, 92.0, 175, "Male",   "MA", ["Gout"],                             4, []),
    ("Gout",                 "Vegetarian",    "South", 45, 75.0, 165, "Male",   "LA", ["Gout"],                             0, []),
    ("IBS",                  "Vegetarian",    "North", 30, 58.0, 162, "Female", "MA", ["IBS/IBD"],                          0, []),
    ("IBS",                  "Eggetarian",    "South", 35, 65.0, 165, "Female", "LA", ["IBS/IBD"],                          0, []),
    ("IBS",                  "Vegetarian",    "East",  28, 62.0, 160, "Female", "S",  ["IBS/IBD"],                          0, []),
    ("IBS",                  "Non-Vegetarian","West",  38, 72.0, 172, "Male",   "MA", ["IBS/IBD"],                          2, []),
    ("Hypertension",         "Vegetarian",    "North", 50, 82.0, 170, "Male",   "S",  ["Hypertension"],                     0, []),
    ("Hypertension",         "Eggetarian",    "South", 55, 78.0, 165, "Female", "LA", ["Hypertension"],                     0, []),
    ("Hypertension",         "Non-Vegetarian","East",  48, 88.0, 175, "Male",   "S",  ["Hypertension"],                     3, []),
    ("Hypertension",         "Vegetarian",    "West",  52, 75.0, 162, "Female", "MA", ["Hypertension"],                     0, []),
    ("Anemia",               "Vegetarian",    "North", 25, 52.0, 158, "Female", "MA", ["Anemia"],                           0, []),
    ("Anemia",               "Eggetarian",    "South", 28, 55.0, 160, "Female", "LA", ["Anemia"],                           0, []),
    ("Anemia",               "Vegetarian",    "East",  22, 50.0, 155, "Female", "S",  ["Anemia"],                           0, []),
    ("Anemia",               "Non-Vegetarian","West",  35, 60.0, 162, "Female", "MA", ["Anemia"],                           3, []),
    ("Kidney_Disease",       "Vegetarian",    "North", 55, 68.0, 165, "Male",   "S",  ["Kidney Disease"],                   0, []),
    ("Kidney_Disease",       "Vegetarian",    "South", 60, 72.0, 168, "Male",   "LA", ["Kidney Disease"],                   0, []),
    ("Kidney_Disease",       "Eggetarian",    "East",  50, 65.0, 162, "Female", "S",  ["Kidney Disease"],                   0, []),
    ("Healthy_Gym",          "Non-Vegetarian","West",  28, 78.0, 178, "Male",   "VA", [],                                   5, ["Muscle Gain"]),
    ("Healthy_Gym",          "Eggetarian",    "North", 25, 70.0, 172, "Male",   "VA", [],                                   0, ["Muscle Gain"]),
    ("Healthy_Gym",          "Non-Vegetarian","South", 30, 75.0, 175, "Male",   "VA", [],                                   5, ["Muscle Gain"]),
    ("Diabetic_Hypertension","Vegetarian",    "East",  58, 80.0, 168, "Male",   "S",  ["Type 2 Diabetes","Hypertension"],   0, []),
    ("Diabetic_Hypertension","Eggetarian",    "West",  55, 75.0, 163, "Female", "LA", ["Type 2 Diabetes","Hypertension"],   0, []),
]
# fmt: on


def _calc_metrics(gender, weight_kg, height_cm, age, activity_level):
    if gender == "Male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    tdee = bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    bmi = weight_kg / ((height_cm / 100) ** 2)
    return round(bmr, 2), round(tdee, 2), round(bmi, 2)


def _doctor_name(i: int) -> str:
    base = DOCTOR_NAMES[i % len(DOCTOR_NAMES)]
    # Only suffix once the pool wraps, so the common 10-doctor case stays clean.
    return base if i < len(DOCTOR_NAMES) else f"{base} {i // len(DOCTOR_NAMES) + 1}"


async def _seed_doctors(session, count: int, hashed_pw: str) -> list[dict]:
    """Get-or-create by email so re-runs reuse existing rows instead of colliding."""
    out = []
    for i in range(count):
        email = f"loadtest.doctor{i + 1:02d}@mityahar-perf.com"
        existing = (
            await session.execute(select(Doctor).where(Doctor.email == email))
        ).scalars().first()

        if existing is None:
            doctor = Doctor(
                email=email,
                hashed_password=hashed_pw,
                name=_doctor_name(i),
                specialization="Dietetics",
                is_active=True,
                is_accepting=True,
                role="doctor",
            )
            session.add(doctor)
            await session.flush()
            print(f"  [CREATE] doctor {email} id={doctor.id}", flush=True)
        else:
            doctor = existing
            print(f"  [EXISTS] doctor {email} id={doctor.id}", flush=True)

        out.append({"email": email, "id": doctor.id, "password": DOCTOR_PASSWORD})
    return out


async def _seed_patient(session, idx: int, archetype, doctor_id: int, hashed_pw: str) -> dict:
    (condition, diet_type, region, age, weight_kg, height_cm,
     gender, activity_level, medical_conditions, nonveg_per_week, health_goals) = archetype

    # 4-wide so ordering stays lexicographic past 999.
    email = f"loadtest{idx:04d}@mityahar-perf.com"
    existing = (
        await session.execute(select(Patient).where(Patient.email == email))
    ).scalars().first()

    bmr, tdee, bmi = _calc_metrics(gender, weight_kg, height_cm, age, activity_level)

    if existing is None:
        now = datetime.now(timezone.utc)
        patient = Patient(
            email=email,
            hashed_password=hashed_pw,
            name=f"Load Test {idx:04d}",
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            activity_level=activity_level,
            diet_type=diet_type,
            region=region,
            health_condition="Healthy",
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            medical_conditions=medical_conditions,
            food_allergies=[],
            health_goals=health_goals,
            nonveg_meals_per_week=nonveg_per_week,
            date_of_birth=date(date.today().year - age, 6, 15),
            doctor_id=doctor_id,
            user_type="doctor_assigned",
            subscription_status="active",
            token_1_active=True,
            token_1_expiry=now + timedelta(days=30),
            disclaimer_accepted_at=now,
            is_email_verified=True,
            meals_per_day=3,
        )
        session.add(patient)
        await session.flush()
        # PK-derived, so it cannot collide across the batch.
        patient.token_1 = f"LOAD-{patient.id:06d}"
        session.add(PatientVisit(
            patient_id=patient.id,
            doctor_id=doctor_id,
            token_2=secrets.token_hex(8).upper(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=30),
            visit_counter=0,
        ))
    else:
        patient = existing

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
        "health_condition": "Healthy",
    }


def _publish(manifest: dict, bucket: str, obj: str) -> None:
    from google.cloud import storage

    blob = storage.Client().bucket(bucket).blob(obj)
    blob.upload_from_string(json.dumps(manifest, indent=2), content_type="application/json")
    print(f"manifest -> gs://{bucket}/{obj}", flush=True)


async def main() -> int:
    ap = argparse.ArgumentParser(description="Seed load-test doctors and patients.")
    ap.add_argument("--doctors", type=int, default=10)
    ap.add_argument("--patients-per-doctor", type=int, default=100)
    ap.add_argument("--gcs-bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--gcs-path", default=DEFAULT_OBJECT)
    ap.add_argument("--no-gcs", action="store_true", help="Print the manifest instead of uploading.")
    args = ap.parse_args()

    total = args.doctors * args.patients_per_doctor
    print(f"seeding {args.doctors} doctors x {args.patients_per_doctor} = {total} patients", flush=True)

    # Hashed once and shared. See module docstring — per-patient bcrypt is what
    # makes this job time out.
    patient_pw = get_password_hash(TEST_PASSWORD)
    doctor_pw = get_password_hash(DOCTOR_PASSWORD)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            doctors = await _seed_doctors(session, args.doctors, doctor_pw)

            patients = []
            for i in range(total):
                doctor_id = doctors[i // args.patients_per_doctor]["id"]
                archetype = PATIENT_ARCHETYPES[i % len(PATIENT_ARCHETYPES)]
                patients.append(
                    await _seed_patient(session, i + 1, archetype, doctor_id, patient_pw)
                )
                if (i + 1) % 100 == 0:
                    print(f"  ...{i + 1}/{total}", flush=True)

    manifest = {
        "total": len(patients),
        "patient_password": TEST_PASSWORD,
        "doctors": doctors,
        "patients": patients,
    }

    if args.no_gcs:
        print(json.dumps({k: v for k, v in manifest.items() if k != "patients"}, indent=2))
    else:
        _publish(manifest, args.gcs_bucket, args.gcs_path)

    print(f"DONE doctors={len(doctors)} patients={len(patients)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
