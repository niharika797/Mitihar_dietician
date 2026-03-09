from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_patient
from ..models.db_models import Patient, SubscriptionCode, Doctor, PatientRequest
from ..schemas.patients import (
    OnboardingRequest, ActivationRequest,
    DoctorRequestBody, PatientProfileResponse,
)
from ..services.meal_generator.calculations import (
    calculate_bmr, calculate_tdee, calculate_bmi,
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
        patient.gender,
        float(patient.weight_kg),
        float(patient.height_cm),
        age,
    )
    tdee = calculate_tdee(bmr, patient.activity_level)
    bmi = calculate_bmi(float(patient.height_cm), float(patient.weight_kg))

    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(
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
        )
    )
    await session.flush()

    # Return the refreshed row
    result = await session.execute(select(Patient).where(Patient.id == patient.id))
    updated = result.scalars().first()
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
                "height": float(updated.height_cm),
                "weight": float(updated.weight_kg),
                "activity_level": updated.activity_level,
                "diet": updated.diet_type,
                "health_condition": updated.health_condition or "Healthy",
                "region": updated.region or "North",
                "nonveg_meals_per_week": updated.nonveg_meals_per_week or 3,
                "food_allergies": updated.food_allergies or [],
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

@router.post("/activate", response_model=PatientProfileResponse)
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
    return updated


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
