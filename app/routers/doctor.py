import secrets
import string
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import get_db
from ..core.security import get_current_doctor
from ..models.db_models import (
    Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
)
from ..schemas.doctor import (
    PatientSummary, PaginatedPatients, RecommendationDetail,
    PlanOverrideRequest, PatientRequestDetail, RejectRequest,
    GenerateCodesRequest, SubscriptionCodeDetail,
)

router = APIRouter()


def _doctor_id(request: Request) -> int:
    """Extract doctor_id injected by DoctorIsolationMiddleware."""
    doctor_id = getattr(request.state, "doctor_id", None)
    if doctor_id is None:
        raise HTTPException(status_code=403, detail="Doctor identity not established")
    return int(doctor_id)


def _generate_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ─── GET /api/v1/doctor/patients ──────────────────────────────────────────

@router.get("/patients", response_model=PaginatedPatients)
async def list_patients(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    offset = (page - 1) * page_size

    total_result = await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == did)
    )
    total = total_result.scalar()

    result = await session.execute(
        select(Patient)
        .where(Patient.doctor_id == did)
        .order_by(Patient.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    patients = result.scalars().all()
    return PaginatedPatients(patients=patients, total=total, page=page, page_size=page_size)


# ─── GET /api/v1/doctor/patients/{patient_id} ─────────────────────────────

@router.get("/patients/{patient_id}", response_model=PatientSummary)
async def get_patient(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.doctor_id == did,
        )
    )
    patient = result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ─── GET /api/v1/doctor/patients/{patient_id}/plan ────────────────────────

@router.get("/patients/{patient_id}/plan", response_model=RecommendationDetail)
async def get_patient_plan(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    # First verify patient belongs to this doctor
    pat_result = await session.execute(
        select(Patient.id).where(
            Patient.id == patient_id,
            Patient.doctor_id == did,
        )
    )
    if pat_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rec_result = await session.execute(
        select(Recommendation).where(
            Recommendation.patient_id == patient_id,
            Recommendation.is_active == True,
        ).order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found for this patient")
    return rec


# ─── PUT /api/v1/doctor/patients/{patient_id}/plan ────────────────────────

@router.put("/patients/{patient_id}/plan", response_model=RecommendationDetail)
async def override_patient_plan(
    patient_id: int,
    body: PlanOverrideRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    pat_result = await session.execute(
        select(Patient.id).where(
            Patient.id == patient_id,
            Patient.doctor_id == did,
        )
    )
    if pat_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rec_result = await session.execute(
        select(Recommendation).where(
            Recommendation.patient_id == patient_id,
            Recommendation.is_active == True,
        ).order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan to update")

    if body.meals is not None:
        rec.meals = body.meals
    if body.doctor_notes is not None:
        rec.doctor_notes = body.doctor_notes
    rec.generated_by = "doctor"
    await session.flush()
    return rec


# ─── GET /api/v1/doctor/requests ──────────────────────────────────────────

@router.get("/requests", response_model=list[PatientRequestDetail])
async def list_requests(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    result = await session.execute(
        select(PatientRequest)
        .where(
            PatientRequest.doctor_id == did,
            PatientRequest.status == "pending",
        )
        .options(selectinload(PatientRequest.patient))
        .order_by(PatientRequest.requested_at.desc())
    )
    return result.scalars().all()


# ─── POST /api/v1/doctor/requests/{id}/accept ─────────────────────────────

@router.post("/requests/{request_id}/accept")
async def accept_request(
    request_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    result = await session.execute(
        select(PatientRequest).where(
            PatientRequest.id == request_id,
            PatientRequest.doctor_id == did,
            PatientRequest.status == "pending",
        )
    )
    req = result.scalars().first()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "accepted"
    req.responded_at = datetime.now(timezone.utc)

    await session.execute(
        update(Patient)
        .where(Patient.id == req.patient_id)
        .values(
            doctor_id=did,
            user_type="doctor_assigned",
            subscription_status="active",
        )
    )
    await session.flush()
    return {"message": "Request accepted", "patient_id": req.patient_id}


# ─── POST /api/v1/doctor/requests/{id}/reject ─────────────────────────────

@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    body: RejectRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    result = await session.execute(
        select(PatientRequest).where(
            PatientRequest.id == request_id,
            PatientRequest.doctor_id == did,
            PatientRequest.status == "pending",
        )
    )
    req = result.scalars().first()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "rejected"
    req.rejection_note = body.rejection_note
    req.responded_at = datetime.now(timezone.utc)
    await session.flush()
    return {"message": "Request rejected"}


# ─── POST /api/v1/doctor/subscription-codes ───────────────────────────────

@router.post("/subscription-codes", response_model=list[SubscriptionCodeDetail], status_code=201)
async def generate_codes(
    body: GenerateCodesRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=body.expires_in_days)
    created = []

    for _ in range(body.count):
        # Collision-safe: retry on duplicate
        for attempt in range(10):
            candidate = _generate_code()
            exists = await session.execute(
                select(SubscriptionCode.id).where(SubscriptionCode.code == candidate)
            )
            if exists.scalars().first() is None:
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique code")

        code = SubscriptionCode(
            doctor_id=did,
            code=candidate,
            is_used=False,
            expires_at=expiry,
        )
        session.add(code)
        created.append(code)

    await session.flush()
    return created


# ─── GET /api/v1/doctor/subscription-codes ────────────────────────────────

@router.get("/subscription-codes", response_model=list[SubscriptionCodeDetail])
async def list_codes(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    result = await session.execute(
        select(SubscriptionCode)
        .where(SubscriptionCode.doctor_id == did)
        .order_by(SubscriptionCode.created_at.desc())
    )
    return result.scalars().all()
