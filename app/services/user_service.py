"""
Patient-centric user service — pure PostgreSQL via AsyncSession.

Exports:
    create_patient, get_patient_by_email, get_patient_by_id,
    authenticate_patient, update_patient,
    get_current_user  (alias for get_current_patient — backward compat)
"""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import verify_password, get_password_hash, get_current_patient
from ..models.db_models import Patient


# ---------------------------------------------------------------------------
# Backward-compatible alias  —  every router that does
#   from ..services.user_service import get_current_user
# will get get_current_patient from security.py
# ---------------------------------------------------------------------------

get_current_user = get_current_patient


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

async def create_patient(session: AsyncSession, *, data: dict) -> int:
    """Insert a new Patient row. Returns the auto-generated PK (id)."""
    password = data.pop("password", None)
    if password is None:
        raise ValueError("password is required")

    patient = Patient(
        email=data["email"],
        hashed_password=get_password_hash(password),
        name=data["name"],
        gender=data.get("gender", ""),
        height_cm=data.get("height", data.get("height_cm", 0)),
        weight_kg=data.get("weight", data.get("weight_kg", 0)),
        activity_level=data.get("activity_level", "S"),
        diet_type=data.get("diet", data.get("diet_type", "Vegetarian")),
        region=data.get("region") or "North",
        health_condition=data.get("health_condition", "Healthy"),
    )
    # Optional fields
    if data.get("phone"):
        patient.phone = data["phone"]
    if data.get("date_of_birth"):
        patient.date_of_birth = data["date_of_birth"]
    # ── Upgrade 6: derive DOB from age if no date_of_birth provided ───────
    elif isinstance(data.get("age"), int) and data["age"] > 0:
        patient.date_of_birth = date(date.today().year - data["age"], 1, 1)

    session.add(patient)
    await session.flush()  # assigns patient.id
    return patient.id


async def get_patient_by_email(
    session: AsyncSession, email: str
) -> Optional[Patient]:
    result = await session.execute(select(Patient).where(Patient.email == email))
    return result.scalars().first()


async def get_patient_by_id(
    session: AsyncSession, patient_id: int
) -> Optional[Patient]:
    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    return result.scalars().first()


async def authenticate_patient(
    session: AsyncSession, email: str, password: str
) -> Optional[Patient]:
    patient = await get_patient_by_email(session, email)
    if patient is None:
        return None
    if not verify_password(password, patient.hashed_password):
        return None
    return patient


async def update_patient(
    session: AsyncSession, patient_id: int, data: dict
) -> bool:
    patient = await get_patient_by_id(session, patient_id)
    if patient is None:
        return False
    for key, value in data.items():
        if hasattr(patient, key):
            setattr(patient, key, value)
    await session.flush()
    return True