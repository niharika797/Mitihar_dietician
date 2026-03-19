from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_patient
from ..models.db_models import Patient, SubscriptionCode, Doctor, PatientRequest, PatientVisit, PendingVisitApproval
from ..schemas.patients import (
    OnboardingRequest, ActivationRequest,
    DoctorRequestBody, PatientProfileResponse, PublicDoctorResponse,
    ActivationResponse
)
from ..services.meal_generator.calculations import (
    calculate_bmr, calculate_tdee, calculate_bmi,
)
from ..services.token_service import (
    generate_token_1, generate_token_2, token_1_expiry_from_now,
)

router = APIRouter()


def _derive_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


# ─── POST /api/v1/patients/onboarding ─────────────────────────────────────

@router.post("/onboarding", response_model=PatientProfileResponse)
async def onboard_patient(
    body: OnboardingRequest,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Complete patient profile. Calculates and STORES bmi, bmr, tdee on the row.
    Idempotent — re-calling this overwrites previous onboarding data.
    """
    age = _derive_age(body.date_of_birth)

    bmr = calculate_bmr(
        body.gender,
        body.weight_kg,
        body.height_cm,
        age,
    )
    tdee = calculate_tdee(bmr, body.activity_level)
    bmi = calculate_bmi(body.height_cm, body.weight_kg)

    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(
            gender=body.gender,
            height_cm=body.height_cm,
            weight_kg=body.weight_kg,
            activity_level=body.activity_level,
            diet_type=body.diet_type,
            region=body.region,
            health_condition=body.health_condition,
            date_of_birth=body.date_of_birth,
            health_goals=body.health_goals,
            medical_conditions=body.medical_conditions,
            food_allergies=body.food_allergies,
            target_weight_kg=body.target_weight_kg,
            meals_per_day=body.meals_per_day,
            sleep_hours=body.sleep_hours,
            water_glasses=body.water_glasses,
            occupation=body.occupation,
            nonveg_meals_per_week=body.nonveg_meals_per_week,
            dietary_preferences=body.dietary_preferences,
            fasting_days=body.fasting_days,
            smoking=body.smoking,
            alcohol=body.alcohol,
            pace_preference=body.pace_preference,
            eating_habits=body.eating_habits,
            bmi=round(bmi, 2),
            bmr=round(bmr, 2),
            tdee=round(tdee, 2),
            # Token 1 — only set if not already assigned (idempotent re-onboarding)
            token_1=generate_token_1(patient.id) if not patient.token_1 else patient.token_1,
            token_1_active=True,
            token_1_expiry=token_1_expiry_from_now(),
            renewal_requested=False,
            expiring_soon=False,
        )
    )
    await session.flush()

    # Return the refreshed row
    result = await session.execute(select(Patient).where(Patient.id == patient.id))
    updated = result.scalars().first()

    # ── Create initial PatientVisit row (Token 2) if doctor is assigned ──
    if updated.doctor_id:
        from datetime import timezone as _tz
        now = datetime.now(_tz.utc)
        pv = PatientVisit(
            patient_id=updated.id,
            doctor_id=updated.doctor_id,
            token_2=generate_token_2(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=30),
            visit_counter=0,
        )
        session.add(pv)
        await session.flush()
    # ── Auto-generate first diet plan (fire-and-soft-fail) ──────────────
    # Only generates if no active plan exists. Never fails the onboarding response.
    import logging
    _log = logging.getLogger(__name__)
    try:
        from ..services.diet_plan_service import DietPlanService
        from ..services.meal_generator.meal_generator import meal_generator
        diet_service = DietPlanService()
        existing = await diet_service.get_diet_plan(str(updated.id), session=session)
        if existing is None:
            user_data = {
                "id": str(updated.id),
                "email": updated.email,
                "name": updated.name,
                "gender": updated.gender,
                "height": float(updated.height_cm or 0),
                "weight": float(updated.weight_kg or 0),
                "activity_level": updated.activity_level,
                "diet": updated.diet_type,
                "health_condition": updated.health_condition or "Healthy",
                "region": updated.region or "North",
                "nonveg_meals_per_week": updated.nonveg_meals_per_week or 3,
                "food_allergies": updated.food_allergies or [],
                "health_goals": list(updated.health_goals or []),
                "medical_conditions": list(updated.medical_conditions or []),
                # medical_conditions drives PCOS/Thyroid macro overrides
                "age": age,
            }
            diet_plan = await diet_service.generate_diet_plan(user_data, session)
            await diet_service.store_diet_plan(diet_plan, session=session)
            _log.info(f"Auto-generated diet plan for patient {updated.id} after onboarding")
    except Exception as exc:
        _log.error(f"Auto plan generation failed for patient {updated.id}: {exc}", exc_info=True)
        # Do NOT re-raise — onboarding must succeed even if plan gen fails

    return updated


# ─── POST /api/v1/patients/activate ───────────────────────────────────────

@router.post("/activate", response_model=ActivationResponse)
async def activate_subscription(
    body: ActivationRequest,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient enters a subscription code given by their doctor.
    Validates code → activates patient → links to doctor.
    JWT sub_status is stale until next login — that is expected behaviour.
    """
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(SubscriptionCode).where(
            SubscriptionCode.code == body.code,
            SubscriptionCode.is_used == False,
            SubscriptionCode.expires_at > now,
        )
    )
    code_row = result.scalars().first()

    if code_row is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already-used subscription code",
        )

    # Mark code consumed
    code_row.is_used = True
    code_row.used_by_patient_id = patient.id
    code_row.used_at = now

    # Activate patient
    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(
            subscription_status="active",
            doctor_id=code_row.doctor_id,
            user_type="doctor_assigned",
        )
    )
    await session.flush()

    result2 = await session.execute(select(Patient).where(Patient.id == patient.id))
    updated = result2.scalars().first()

    from ..routers.auth import _patient_token_data, _issue_tokens
    token_data = _patient_token_data(updated)
    tokens = _issue_tokens(token_data)

    return ActivationResponse(
        patient=PatientProfileResponse.model_validate(updated),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"]
    )


# ─── POST /api/v1/patients/request-doctor ─────────────────────────────────

@router.post("/request-doctor", status_code=201)
async def request_doctor(
    body: DoctorRequestBody,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient requests to connect with a doctor (alternative to subscription code).
    Doctor accepts/rejects via /api/v1/doctor/requests endpoints.
    """
    # Verify doctor exists
    doc_result = await session.execute(
        select(Doctor).where(Doctor.id == body.doctor_id, Doctor.is_active == True)
    )
    if doc_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if patient.doctor_id == body.doctor_id:
        raise HTTPException(status_code=409, detail="Already connected to this doctor")

    # Prevent duplicate pending request
    existing = await session.execute(
        select(PatientRequest).where(
            PatientRequest.patient_id == patient.id,
            PatientRequest.doctor_id == body.doctor_id,
            PatientRequest.status == "pending",
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="A pending request to this doctor already exists",
        )

    req = PatientRequest(
        patient_id=patient.id,
        doctor_id=body.doctor_id,
        status="pending",
        requested_at=datetime.now(timezone.utc)
    )
    session.add(req)
    await session.flush()
    await session.refresh(req)
    return {"message": "Request submitted successfully", "request_id": req.id}


# ─── GET /api/v1/patients/request-status ──────────────────────────────────

@router.get("/request-status")
async def get_request_status(
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient polls this to check if their doctor connection request was accepted.
    Returns the most recent request for this patient, regardless of status.
    Returns 404 if the patient has never sent a request.
    """
    result = await session.execute(
        select(PatientRequest)
        .where(PatientRequest.patient_id == patient.id)
        .order_by(PatientRequest.requested_at.desc())
    )
    req = result.scalars().first()
    if req is None:
        raise HTTPException(status_code=404, detail="No doctor request found")

    return {
        "request_id": req.id,
        "doctor_id": req.doctor_id,
        "status": req.status,
        "rejection_note": req.rejection_note,
        "requested_at": req.requested_at.isoformat(),
        "responded_at": req.responded_at.isoformat() if req.responded_at else None,
    }


# ─── GET /api/v1/patients/doctors ─────────────────────────────────────────

@router.get("/doctors", response_model=list[PublicDoctorResponse])
async def list_doctors(
    search: str | None = None,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Public doctor directory for patients. Returns all active doctors.
    Supports optional `search` query param (name / specialization / city).
    Sorted by rating descending (highest first), then by id.
    """
    stmt = select(Doctor).where(Doctor.is_active == True)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            Doctor.name.ilike(term) |
            Doctor.specialization.ilike(term) |
            Doctor.city.ilike(term)
        )
    stmt = stmt.order_by(
        Doctor.rating.desc().nulls_last(),
        Doctor.id.asc(),
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# ─── GET /api/v1/patients/my-visit ────────────────────────────────────────

@router.get("/my-visit")
async def get_my_visit(
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Return the patient's most recent active PatientVisit row (Token 2 details).
    Used by the patient app to show subscription / visit cycle info.
    Returns null fields if no visit cycle exists yet.
    """
    if not patient.doctor_id:
        return {
            "has_visit": False,
            "token_2": None,
            "visit_counter": 0,
            "cycle_start": None,
            "cycle_expiry": None,
            "last_charged_at": None,
        }

    result = await session.execute(
        select(PatientVisit)
        .where(
            PatientVisit.patient_id == patient.id,
            PatientVisit.doctor_id == patient.doctor_id,
        )
        .order_by(PatientVisit.cycle_start.desc())
        .limit(1)
    )
    pv = result.scalars().first()

    if pv is None:
        return {
            "has_visit": False,
            "token_2": None,
            "visit_counter": 0,
            "cycle_start": None,
            "cycle_expiry": None,
            "last_charged_at": None,
        }

    return {
        "has_visit": True,
        "token_2": pv.token_2,
        "visit_counter": pv.visit_counter,
        "cycle_start": pv.cycle_start.isoformat() if pv.cycle_start else None,
        "cycle_expiry": pv.cycle_expiry.isoformat() if pv.cycle_expiry else None,
        "last_charged_at": pv.last_charged_at.isoformat() if pv.last_charged_at else None,
    }


# ─── POST /api/v1/patients/disclaimer ─────────────────────────────────────

@router.post("/disclaimer", status_code=200)
async def accept_disclaimer(
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient taps 'I Understand' on the disclaimer screen.
    Stores the UTC timestamp. Idempotent — safe to call multiple times.
    """
    accepted_at = datetime.now(timezone.utc)
    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(disclaimer_accepted_at=accepted_at)
    )
    await session.flush()
    return {"message": "Disclaimer accepted", "accepted_at": accepted_at.isoformat()}
