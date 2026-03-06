from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_admin, get_password_hash
from ..models.db_models import Admin, Doctor, Patient, Recommendation, SubscriptionCode, AuditLog, FoodItem
from ..schemas.admin import (
    CreateDoctorRequest, DoctorAdminView, PlatformStats,
    DoctorDetailView, AuditLogEntry, PaginatedAuditLogs,
    GenerateCodesAdminRequest, CodeAdminView, FoodAdminView,
)
from ..services.audit_service import log_action

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


# ─── GET /api/v1/admin/doctors/{doctor_id} ────────────────────────────────

@router.get("/doctors/{doctor_id}", response_model=DoctorDetailView)
async def get_doctor_detail(
    doctor_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Full doctor profile including patient count."""
    doctor_result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doctor_result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    patient_count = (await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == doctor_id)
    )).scalar() or 0

    view = DoctorDetailView.model_validate(doctor)
    view.patient_count = patient_count
    return view


# ─── DELETE /api/v1/admin/doctors/{doctor_id} ─────────────────────────────

@router.delete("/doctors/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Remove a doctor. All their patients are set to standalone + inactive.
    The doctor row is soft-deleted (is_active=False, not physical delete).
    Action is audit-logged.
    """
    doctor_result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doctor_result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Disconnect all patients
    await session.execute(
        update(Patient)
        .where(Patient.doctor_id == doctor_id)
        .values(doctor_id=None, user_type="standalone", subscription_status="inactive")
    )

    # Soft-delete the doctor
    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(is_active=False)
    )
    await session.flush()

    await log_action(
        session,
        actor_id=admin.id,
        actor_role="admin",
        action="delete_doctor",
        entity_type="doctor",
        entity_id=doctor_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": f"Doctor {doctor_id} deleted and patients disconnected"}


# ─── GET /api/v1/admin/audit-logs ─────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedAuditLogs)
async def get_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    actor_role: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Paginated audit log viewer with optional filters."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_stmt = select(func.count(AuditLog.id))

    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
        count_stmt = count_stmt.where(AuditLog.actor_role == actor_role)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
        count_stmt = count_stmt.where(AuditLog.action.ilike(f"%{action}%"))

    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    result = await session.execute(stmt.offset(offset).limit(page_size))
    logs = result.scalars().all()
    return PaginatedAuditLogs(logs=logs, total=total, page=page, page_size=page_size)


import secrets, string
from datetime import datetime


def _gen_code(length: int = 12) -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))


# ─── POST /api/v1/admin/codes/generate ───────────────────────────────────

@router.post("/codes/generate", response_model=list[CodeAdminView], status_code=201)
async def admin_generate_codes(
    body: GenerateCodesAdminRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Generate a batch of subscription codes for a specific doctor."""
    from datetime import timezone, timedelta

    doctor_result = await session.execute(select(Doctor).where(Doctor.id == body.doctor_id))
    if doctor_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=body.expires_in_days)
    created = []

    for _ in range(body.count):
        for _ in range(10):
            candidate = _gen_code()
            exists = (await session.execute(
                select(SubscriptionCode.id).where(SubscriptionCode.code == candidate)
            )).scalars().first()
            if exists is None:
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique code")

        code = SubscriptionCode(
            doctor_id=body.doctor_id,
            code=candidate,
            is_used=False,
            expires_at=expiry,
        )
        session.add(code)
        created.append(code)

    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="generate_codes", entity_type="doctor",
                     entity_id=body.doctor_id, detail={"count": body.count})
    return created


# ─── GET /api/v1/admin/codes ──────────────────────────────────────────────

@router.get("/codes", response_model=list[CodeAdminView])
async def list_all_codes(
    doctor_id: Optional[int] = Query(default=None),
    is_used: Optional[bool] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """View all subscription codes. Optional filter by doctor or used status."""
    stmt = select(SubscriptionCode).order_by(SubscriptionCode.created_at.desc())
    if doctor_id:
        stmt = stmt.where(SubscriptionCode.doctor_id == doctor_id)
    if is_used is not None:
        stmt = stmt.where(SubscriptionCode.is_used == is_used)
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── PATCH /api/v1/admin/patients/{patient_id}/subscription/override ──────

@router.patch("/patients/{patient_id}/subscription/override")
async def override_subscription(
    patient_id: int,
    status: str = Query(..., description="active | inactive"),
    days: int = Query(default=30, ge=1, le=365),
    request: Request = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Manually override a patient's subscription status.
    Used for dispute resolution or manual activation.
    """
    from datetime import timezone, timedelta
    if status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'inactive'")

    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    new_end = datetime.now(timezone.utc) + timedelta(days=days) if status == "active" else None

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(subscription_status=status, subscription_end_date=new_end)
    )
    await session.flush()

    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="override_subscription", entity_type="patient",
                     entity_id=patient_id, detail={"status": status, "days": days})
    return {"patient_id": patient_id, "subscription_status": status, "end_date": new_end.isoformat() if new_end else None}


# ─── GET /api/v1/admin/food ───────────────────────────────────────────────

@router.get("/food", response_model=list[FoodAdminView])
async def list_food_items(
    source: Optional[str] = Query(default=None, description="manual | doctor"),
    is_verified: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Food database management view. Filter by source and verified status."""
    stmt = select(FoodItem).order_by(FoodItem.created_at.desc())
    if source:
        stmt = stmt.where(FoodItem.source == source)
    if is_verified is not None:
        stmt = stmt.where(FoodItem.is_verified == is_verified)
    offset = (page - 1) * page_size
    result = await session.execute(stmt.offset(offset).limit(page_size))
    return result.scalars().all()


# ─── PATCH /api/v1/admin/food/{food_id}/approve ───────────────────────────

@router.patch("/food/{food_id}/approve")
async def approve_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Approve a doctor-submitted recipe. Makes it available for meal generation."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    if food.is_verified:
        raise HTTPException(status_code=400, detail="Already verified")

    await session.execute(
        update(FoodItem).where(FoodItem.id == food_id).values(is_verified=True)
    )
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="approve_food", entity_type="food_item", entity_id=food_id)
    return {"message": f"Food item {food_id} approved", "recipe_name": food.recipe_name}


# ─── PATCH /api/v1/admin/food/{food_id}/reject ────────────────────────────

@router.patch("/food/{food_id}/reject")
async def reject_food_item(
    food_id: int,
    request: Request,
    reason: Optional[str] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Reject and soft-delete a doctor-submitted recipe."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    # Soft-delete by marking source as "rejected" — preserves row for audit
    await session.execute(
        update(FoodItem).where(FoodItem.id == food_id).values(source="rejected")
    )
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="reject_food", entity_type="food_item", entity_id=food_id,
                     detail={"reason": reason})
    return {"message": f"Food item {food_id} rejected"}


# ─── DELETE /api/v1/admin/food/{food_id} ─────────────────────────────────

@router.delete("/food/{food_id}")
async def delete_food_item(
    food_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Permanently delete a food item from the database."""
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == food_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Food item not found")

    await session.delete(food)
    await session.flush()
    await log_action(session, actor_id=admin.id, actor_role="admin",
                     action="delete_food", entity_type="food_item", entity_id=food_id)
    return {"message": f"Food item {food_id} permanently deleted"}


# ─── GET /api/v1/admin/billing ────────────────────────────────────────────

from ..models.db_models import MealLog, ProgressLog, ClinicalNote, Recommendation as Rec


@router.get("/billing")
async def billing_overview(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Platform-wide billing overview.
    Returns total codes issued, redeemed, and per-doctor code usage breakdown.
    """
    # Platform totals
    total_codes = (await session.execute(
        select(func.count(SubscriptionCode.id))
    )).scalar() or 0

    used_codes = (await session.execute(
        select(func.count(SubscriptionCode.id)).where(SubscriptionCode.is_used == True)
    )).scalar() or 0

    # Per-doctor breakdown
    stmt = (
        select(
            Doctor.id,
            Doctor.name,
            Doctor.email,
            func.count(SubscriptionCode.id).label("total"),
            func.count(SubscriptionCode.id).filter(SubscriptionCode.is_used == True).label("used"),
        )
        .outerjoin(SubscriptionCode, SubscriptionCode.doctor_id == Doctor.id)
        .where(Doctor.is_active == True)
        .group_by(Doctor.id, Doctor.name, Doctor.email)
        .order_by(func.count(SubscriptionCode.id).desc())
    )
    rows = (await session.execute(stmt)).all()

    doctors = [
        {
            "doctor_id": row.id,
            "name": row.name,
            "email": row.email,
            "codes_issued": row.total,
            "codes_used": row.used,
        }
        for row in rows
    ]

    return {
        "total_codes_issued": total_codes,
        "total_codes_used": used_codes,
        "unused_codes": total_codes - used_codes,
        "doctors": doctors,
    }


# ─── DELETE /api/v1/admin/patients/{patient_id} ──────────────────────────

from sqlalchemy import delete as sa_delete


@router.delete("/patients/{patient_id}")
async def erase_patient_data(
    patient_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    DPDP Act compliance — right to erasure.
    1. Anonymises PII (name, email, phone, etc.) but keeps the row for aggregate stats.
    2. Hard-deletes all associated logs: MealLog, ProgressLog, ClinicalNote, Recommendation.
    3. Audit-logs the action.
    """
    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 1. Anonymise PII
    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            name=f"erased_{patient_id}",
            email=f"erased_{patient_id}@deleted.local",
            phone=None,
            food_allergies=[],
            medical_conditions=[],
            dietary_preferences=[],
            eating_habits=[],
            fasting_days=[],
            health_goals=[],
            occupation=None,
            subscription_status="inactive",
            is_active=False,
        )
    )

    # 2. Hard-delete all associated data
    await session.execute(sa_delete(MealLog).where(MealLog.patient_id == patient_id))
    await session.execute(sa_delete(ProgressLog).where(ProgressLog.patient_id == patient_id))
    await session.execute(sa_delete(ClinicalNote).where(ClinicalNote.patient_id == patient_id))
    await session.execute(sa_delete(Rec).where(Rec.patient_id == patient_id))

    await session.flush()

    await log_action(
        session,
        actor_id=admin.id,
        actor_role="admin",
        action="erase_patient_data",
        entity_type="patient",
        entity_id=patient_id,
        ip_address=request.client.host if request.client else None,
        detail={"compliance": "DPDP_Act"},
    )
    return {"message": f"Patient {patient_id} data erased (DPDP compliance)"}
