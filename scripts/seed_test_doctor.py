"""
seed_test_doctor.py
====================
Creates a fully-seeded test doctor in the database that is visible in:
  - Patient app  → Find a Doctor / Activate Subscription
  - Doctor web dashboard → localhost:5173 (login as this doctor)
  - Admin web dashboard → admin panel → Doctors section

Run from project root:
    python -m scripts.seed_test_doctor

Credentials created:
  Doctor login:  dr.ashok.mehta@mitihar.test  / DoctorTest@2026
  Admin login:   admin@mitihar.test            / Admin@2026  (created if absent)
"""

import asyncio
import sys
import os

# Make sure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.db_models import Doctor, Admin, SubscriptionCode


DOCTOR = {
    "email":           "dr.ashok.mehta@mitihar.test",
    "password":        "DoctorTest@2026",
    "name":            "Dr. Ashok Mehta",
    "phone":           "+91-98200-12345",
    "specialization":  "Dietician & Nutritionist",
    "clinic_name":     "Mehta Nutrition Clinic",
    "clinic_address":  "203, Shree Apartments, SV Road, Andheri West",
    "city":            "Mumbai",
    "state":           "Maharashtra",
    "experience_years": 12,
    "fee_per_month":   800,
    "rating":          4.9,
    "review_count":    128,
    "is_accepting":    True,
    "is_active":       True,
    "mfa_enabled":     False,
}

ADMIN = {
    "email":    "admin@mitihar.test",
    "password": "Admin@2026",
    "name":     "Mitihar Admin",
}

# 5 pre-seeded subscription codes that patients can use to activate
CODES = [
    "ASHOK1",
    "ASHOK2",
    "ASHOK3",
    "ASHOK4",
    "ASHOK5",
]


async def seed():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # ── 1. Upsert Admin ────────────────────────────────────────────
            existing_admin = (await session.execute(
                select(Admin).where(Admin.email == ADMIN["email"])
            )).scalars().first()

            if existing_admin:
                print(f"[admin]  Already exists: {ADMIN['email']}")
            else:
                admin = Admin(
                    email=ADMIN["email"],
                    hashed_password=get_password_hash(ADMIN["password"]),
                    name=ADMIN["name"],
                    is_active=True,
                    mfa_enabled=False,
                    allowed_ips=[],
                )
                session.add(admin)
                print(f"[admin]  Created: {ADMIN['email']}")

            # ── 2. Upsert Doctor ───────────────────────────────────────────
            existing_doc = (await session.execute(
                select(Doctor).where(Doctor.email == DOCTOR["email"])
            )).scalars().first()

            if existing_doc:
                doctor = existing_doc
                # Update public fields in case they changed
                doctor.specialization  = DOCTOR["specialization"]
                doctor.clinic_name     = DOCTOR["clinic_name"]
                doctor.clinic_address  = DOCTOR["clinic_address"]
                doctor.city            = DOCTOR["city"]
                doctor.state           = DOCTOR["state"]
                doctor.experience_years= DOCTOR["experience_years"]
                doctor.fee_per_month   = DOCTOR["fee_per_month"]
                doctor.rating          = DOCTOR["rating"]
                doctor.review_count    = DOCTOR["review_count"]
                doctor.is_accepting    = DOCTOR["is_accepting"]
                print(f"[doctor] Updated: {DOCTOR['email']} (id={doctor.id})")
            else:
                doctor = Doctor(
                    email=DOCTOR["email"],
                    hashed_password=get_password_hash(DOCTOR["password"]),
                    name=DOCTOR["name"],
                    phone=DOCTOR["phone"],
                    specialization=DOCTOR["specialization"],
                    clinic_name=DOCTOR["clinic_name"],
                    clinic_address=DOCTOR["clinic_address"],
                    city=DOCTOR["city"],
                    state=DOCTOR["state"],
                    experience_years=DOCTOR["experience_years"],
                    fee_per_month=DOCTOR["fee_per_month"],
                    rating=DOCTOR["rating"],
                    review_count=DOCTOR["review_count"],
                    is_accepting=DOCTOR["is_accepting"],
                    is_active=DOCTOR["is_active"],
                    mfa_enabled=DOCTOR["mfa_enabled"],
                )
                session.add(doctor)
                await session.flush()  # get doctor.id
                print(f"[doctor] Created: {DOCTOR['email']} (id={doctor.id})")

            # ── 3. Seed Subscription Codes ─────────────────────────────────
            expiry = datetime.now(timezone.utc) + timedelta(days=365)
            codes_created = 0
            for code_str in CODES:
                exists = (await session.execute(
                    select(SubscriptionCode).where(SubscriptionCode.code == code_str)
                )).scalars().first()
                if exists:
                    print(f"[code]   Already exists: {code_str}")
                    continue
                code = SubscriptionCode(
                    doctor_id=doctor.id,
                    code=code_str,
                    is_used=False,
                    expires_at=expiry,
                )
                session.add(code)
                codes_created += 1
                print(f"[code]   Created: {code_str}")

            print(f"\n{'='*50}")
            print("✅ Seed complete!")
            print(f"{'='*50}")
            print(f"\nDoctor Dashboard Login:")
            print(f"  URL:      http://localhost:5173")
            print(f"  Email:    {DOCTOR['email']}")
            print(f"  Password: {DOCTOR['password']}")
            print(f"\nAdmin Dashboard Login:")
            print(f"  URL:      http://localhost:5173")
            print(f"  Email:    {ADMIN['email']}")
            print(f"  Password: {ADMIN['password']}")
            print(f"\nSubscription Codes (use on patient app → Activate):")
            for c in CODES:
                print(f"  {c}")
            print(f"\nPatient App → Find a Doctor → will show 'Dr. Ashok Mehta'")
            print(f"Patient App → Activate → enter any code above (e.g. ASHOK1)")


if __name__ == "__main__":
    asyncio.run(seed())
