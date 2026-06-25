"""
seed_test_patients.py — Idempotent dev fixture for test patient accounts.

Ensures priya.test@mityahar.com and testaudit@mityahar.com exist with
the canonical Test@1234 password and active subscriptions.

  If patient EXISTS  → updates hashed_password only (all other data preserved)
  If patient MISSING → creates with full subscription setup

Run after clean_patients.py or any DB wipe:
    python -m scripts.seed_test_patients

Safe to re-run at any time — existing data is never clobbered beyond the hash.

Requires:
    seed_test_doctor.py already run (needs dr.ashok.mehta@mitihar.test in DB)
"""
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select, update as sa_update
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.db_models import Doctor, Patient, SubscriptionCode


DOCTOR_EMAIL = "dr.ashok.mehta@mitihar.test"
PASSWORD = "Test@1234"

# Canonical test patient specs — must match BUILD_TRACKER.md credentials table
TEST_PATIENTS = [
    {
        "email": "testaudit@mityahar.com",
        "name": "Testaudit Patient",
        "gender": "Female",
        "height_cm": 160.0,
        "weight_kg": 60.0,
        "activity_level": "LA",
        "diet_type": "Vegetarian",
        "region": "North",
        "medical_conditions": [],
        "subscription_code": "ASHOK1",
    },
    {
        "email": "priya.test@mityahar.com",
        "name": "Priya Test",
        "gender": "Female",
        "height_cm": 163.0,
        "weight_kg": 65.0,
        "activity_level": "LA",
        "diet_type": "Vegetarian",
        "region": "North",
        "medical_conditions": ["Type 2 Diabetes"],
        "subscription_code": "ASHOK2",
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            doc_result = await session.execute(
                select(Doctor).where(Doctor.email == DOCTOR_EMAIL)
            )
            doctor = doc_result.scalars().first()
            if doctor is None:
                print(f"[error] Doctor {DOCTOR_EMAIL!r} not found.")
                print("        Run 'python -m scripts.seed_test_doctor' first.")
                return

            new_hash = get_password_hash(PASSWORD)
            expiry = datetime.now(timezone.utc) + timedelta(days=365)

            for spec in TEST_PATIENTS:
                email = spec["email"]
                result = await session.execute(
                    select(Patient).where(Patient.email == email)
                )
                existing = result.scalars().first()

                if existing:
                    if verify_password(PASSWORD, existing.hashed_password):
                        print(f"[ok]      {email} — password already correct, no change")
                    else:
                        await session.execute(
                            sa_update(Patient)
                            .where(Patient.id == existing.id)
                            .values(hashed_password=new_hash)
                        )
                        print(f"[updated] {email} — hashed_password reset to Test@1234")
                else:
                    code_str = spec.get("subscription_code")
                    code_row = None
                    if code_str:
                        code_result = await session.execute(
                            select(SubscriptionCode).where(SubscriptionCode.code == code_str)
                        )
                        code_row = code_result.scalars().first()

                    patient = Patient(
                        email=email,
                        hashed_password=new_hash,
                        name=spec["name"],
                        gender=spec["gender"],
                        height_cm=spec["height_cm"],
                        weight_kg=spec["weight_kg"],
                        activity_level=spec["activity_level"],
                        diet_type=spec["diet_type"],
                        region=spec["region"],
                        health_condition="Healthy",
                        medical_conditions=spec.get("medical_conditions", []),
                        user_type="doctor_assigned",
                        doctor_id=doctor.id,
                        subscription_status="active",
                        token_1_active=True,
                        token_1_expiry=expiry,
                        is_email_verified=True,
                        disclaimer_accepted_at=datetime.now(timezone.utc),
                    )
                    session.add(patient)
                    await session.flush()

                    if code_row:
                        code_row.is_used = True
                        code_row.used_at = datetime.now(timezone.utc)
                        code_row.used_by_patient_id = patient.id
                        print(f"[created] {email} (id={patient.id}) — code {code_str} consumed")
                    else:
                        print(f"[created] {email} (id={patient.id}) — subscription set active directly")

    print("\nDone. Test@1234 is the canonical password for both accounts.")


if __name__ == "__main__":
    asyncio.run(seed())
