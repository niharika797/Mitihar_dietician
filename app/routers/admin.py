from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_admin, get_password_hash
from ..models.db_models import Admin, Doctor, Patient, Recommendation
from ..schemas.admin import CreateDoctorRequest, DoctorAdminView, PlatformStats

router = APIRouter()


# ─── POST /api/v1/admin/doctors ───────────────────────────────────────────

@router.post("/doctors", response_model=DoctorAdminView, status_code=201)
async def create_doctor(
    body: CreateDoctorRequest,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Create a new doctor account with hashed password."""
    doctor = Doctor(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        name=body.name,
        phone=body.phone,
        specialization=body.specialization,
        clinic_name=body.clinic_name,
        city=body.city,
        is_active=True,
    )
    session.add(doctor)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return doctor


# ─── GET /api/v1/admin/doctors ────────────────────────────────────────────

@router.get("/doctors", response_model=list[DoctorAdminView])
async def list_doctors(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Doctor).order_by(Doctor.created_at.desc())
    )
    return result.scalars().all()


# ─── GET /api/v1/admin/stats ──────────────────────────────────────────────

@router.get("/stats", response_model=PlatformStats)
async def get_stats(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    total_patients = (await session.execute(
        select(func.count(Patient.id))
    )).scalar()

    active_subs = (await session.execute(
        select(func.count(Patient.id)).where(
            Patient.subscription_status == "active"
        )
    )).scalar()

    total_doctors = (await session.execute(
        select(func.count(Doctor.id))
    )).scalar()

    total_plans = (await session.execute(
        select(func.count(Recommendation.id)).where(
            Recommendation.is_active == True
        )
    )).scalar()

    return PlatformStats(
        total_patients=total_patients,
        active_subscriptions=active_subs,
        total_doctors=total_doctors,
        total_plans_generated=total_plans,
    )


# ─── PATCH /api/v1/admin/doctors/{id}/deactivate ──────────────────────────

@router.patch("/doctors/{doctor_id}/deactivate")
async def deactivate_doctor(
    doctor_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not doctor.is_active:
        raise HTTPException(status_code=400, detail="Doctor already deactivated")

    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(is_active=False)
    )
    await session.flush()
    return {"message": f"Doctor {doctor_id} deactivated"}
