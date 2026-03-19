from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_admin, get_password_hash
from ..models.db_models import Admin, Doctor, Patient, Recommendation, SubscriptionCode, AuditLog, FoodItem, PatientVisit
from ..schemas.admin import (
    CreateDoctorRequest, DoctorAdminView, PlatformStats,
    DoctorDetailView, AuditLogEntry, PaginatedAuditLogs,
    GenerateCodesAdminRequest, CodeAdminView, FoodAdminView,
    AdminPatientView, PaginatedAdminPatients,
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

    expiring_soon_count = (await session.execute(
        select(func.count(Patient.id)).where(Patient.expiring_soon == True)
    )).scalar()

    pending_renewals_count = (await session.execute(
        select(func.count(Patient.id)).where(Patient.renewal_requested == True)
    )).scalar()

    from datetime import datetime, timezone
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_consultations_this_month = (await session.execute(
        select(func.sum(PatientVisit.visit_counter)).where(
            PatientVisit.cycle_start >= month_start
        )
    )).scalar() or 0

    return PlatformStats(
        total_patients=total_patients,
        active_subscriptions=active_subs,
        total_doctors=total_doctors,
        total_plans_generated=total_plans,
        expiring_soon_count=expiring_soon_count,
        pending_renewals_count=pending_renewals_count,
        total_consultations_this_month=int(total_consultations_this_month),
    )


# ─── GET /api/v1/admin/patients ──────────────────────────────────────────

@router.get("/patients", response_model=PaginatedAdminPatients)
async def list_patients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Platform-wide patient list with optional name/email search and pagination."""
    from sqlalchemy import or_
    stmt = select(Patient)
    count_stmt = select(func.count(Patient.id))
    if search:
        pattern = f"%{search.strip()}%"
        filt = or_(Patient.name.ilike(pattern), Patient.email.ilike(pattern))
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    result = await session.execute(
        stmt.order_by(Patient.created_at.desc()).offset(offset).limit(page_size)
    )
    patients = result.scalars().all()
    return PaginatedAdminPatients(patients=patients, total=total, page=page, page_size=page_size)


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


# ─── POST /api/v1/admin/billing/{doctor_id}/mark-paid ─────────────────────────

class BillingMarkPaidRequest(BaseModel):
    amount: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)
    period: Optional[str] = Field(default=None, description="e.g. '2026-03'")


@router.post("/billing/{doctor_id}/mark-paid")
async def mark_doctor_paid(
    doctor_id: int,
    body: BillingMarkPaidRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Record that a doctor has paid their invoice.
    Stored as an audit log entry — no billing table yet (Phase 4 Razorpay will replace this).
    """
    doctor_result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = doctor_result.scalars().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    await log_action(
        session,
        actor_id=admin.id,
        actor_role="admin",
        action="mark_paid",
        entity_type="doctor",
        entity_id=doctor_id,
        ip_address=request.client.host if request.client else None,
        detail={
            "amount": body.amount,
            "notes": body.notes,
            "period": body.period,
            "doctor_name": doctor.name,
            "doctor_email": doctor.email,
        },
    )
    return {
        "message": f"Payment recorded for Dr. {doctor.name}",
        "doctor_id": doctor_id,
        "amount": body.amount,
        "period": body.period,
        "recorded_by_admin_id": admin.id,
    }


# ─── GET /api/v1/admin/consultations ─────────────────────────────────────

@router.get("/consultations")
async def get_consultations(
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Platform-wide consultation stats.
    Per-doctor: patient count, visits this month, revenue (×₹1200), royalty (×6%).
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    doctors_result = await session.execute(
        select(Doctor).where(Doctor.is_active == True)
    )
    doctors = doctors_result.scalars().all()

    per_doctor = []
    total_consultations = 0

    for doc in doctors:
        pat_count_result = await session.execute(
            select(func.count(Patient.id)).where(Patient.doctor_id == doc.id)
        )
        patient_count = pat_count_result.scalar() or 0

        visits_result = await session.execute(
            select(func.sum(PatientVisit.visit_counter)).where(
                PatientVisit.doctor_id == doc.id,
                PatientVisit.cycle_start >= month_start,
            )
        )
        consultations_this_month = int(visits_result.scalar() or 0)
        total_consultations += consultations_this_month

        revenue = consultations_this_month * 1200
        royalty = round(revenue * 0.06, 2)

        per_doctor.append({
            "doctor_id": doc.id,
            "doctor_name": doc.name,
            "doctor_email": doc.email,
            "patient_count": patient_count,
            "consultations_this_month": consultations_this_month,
            "revenue_generated": revenue,
            "platform_royalty": royalty,
        })

    return {
        "month": month_start.strftime("%B %Y"),
        "total_consultations_this_month": total_consultations,
        "total_revenue": total_consultations * 1200,
        "total_royalty": round(total_consultations * 1200 * 0.06, 2),
        "per_doctor": per_doctor,
    }


# ─── GET /api/v1/admin/consultations/annual ──────────────────────────────

@router.get("/consultations/annual")
async def get_annual_consultations(
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Year-to-date totals and royalty split (2% × 3 team members)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await session.execute(
        select(func.sum(PatientVisit.visit_counter)).where(
            PatientVisit.cycle_start >= year_start
        )
    )
    ytd_consultations = int(result.scalar() or 0)
    ytd_revenue = ytd_consultations * 1200
    ytd_royalty_pool = round(ytd_revenue * 0.06, 2)

    return {
        "year": now.year,
        "ytd_consultations": ytd_consultations,
        "ytd_revenue": ytd_revenue,
        "royalty_pool_6pct": ytd_royalty_pool,
        "royalty_per_member_2pct": round(ytd_royalty_pool / 3, 2),
        "team_members": 3,
    }


# ─── GET /api/v1/admin/renewals ──────────────────────────────────────────

@router.get("/renewals")
async def get_pending_renewals(
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Platform-wide list of all patients with pending renewal requests."""
    result = await session.execute(
        select(Patient, Doctor.name.label("doctor_name")).join(
            Doctor, Patient.doctor_id == Doctor.id, isouter=True
        ).where(Patient.renewal_requested == True)
        .order_by(Patient.renewal_requested_at.asc())
    )
    rows = result.all()
    return [
        {
            "patient_id": p.Patient.id,
            "patient_name": p.Patient.name,
            "patient_email": p.Patient.email,
            "doctor_name": p.doctor_name,
            "token_1": p.Patient.token_1,
            "token_1_expiry": p.Patient.token_1_expiry.isoformat() if p.Patient.token_1_expiry else None,
            "renewal_requested_at": p.Patient.renewal_requested_at.isoformat() if p.Patient.renewal_requested_at else None,
        }
        for p in rows
    ]


# ─── POST /api/v1/admin/renewals/{patient_id}/override-approve ───────────

@router.post("/renewals/{patient_id}/override-approve")
async def admin_override_approve_renewal(
    patient_id: int,
    request: Request,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Admin manually approves a renewal if doctor is unresponsive."""
    from ..services.token_service import generate_token_2, token_1_expiry_from_now
    from datetime import datetime, timezone, timedelta
    from ..services.audit_service import log_action

    pat_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = pat_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    now = datetime.now(timezone.utc)
    new_expiry = token_1_expiry_from_now()

    await session.execute(
        update(Patient).where(Patient.id == patient_id).values(
            token_1_active=True,
            token_1_expiry=new_expiry,
            renewal_requested=False,
            renewal_requested_at=None,
            expiring_soon=False,
            subscription_status="active",
        )
    )

    if patient.doctor_id:
        pv = PatientVisit(
            patient_id=patient_id,
            doctor_id=patient.doctor_id,
            token_2=generate_token_2(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=30),
            visit_counter=0,
        )
        session.add(pv)

    await session.flush()
    await log_action(
        session, actor_id=admin.id, actor_role="admin",
        action="admin_override_renewal", entity_type="patient", entity_id=patient_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": f"Renewal approved by admin for patient {patient.name}."}


# ─── Extend GET /api/v1/admin/stats with token fields ────────────────────
# Note: stats endpoint already exists — we patch it at runtime via the
# existing route. The expiring_soon_count + pending_renewals_count are
# appended by the updated get_stats function below (replaces old one).
