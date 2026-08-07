from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.limiter import limiter
from ..core.security import get_current_patient
from ..models.db_models import (
    Patient, SubscriptionCode, Doctor, PatientRequest, PatientVisit,
    PendingVisitApproval,
)
from ..schemas.patients import (
    OnboardingRequest, ActivationRequest,
    DoctorRequestBody, PatientProfileResponse, PublicDoctorResponse,
    ActivationResponse, RespondVisitRequest
)
from ..schemas.doctor import FLAG_VISIT_REASONS
from ..services.meal_generator.calculations import (
    calculate_bmr, calculate_tdee, calculate_bmi,
)
from ..services.token_service import (
    generate_token_1, generate_token_2, token_1_expiry_from_now, CYCLE_DAYS,
    is_chargeable_visit, VISIT_CHARGE_INR,
)

router = APIRouter()


def _derive_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


# ─── POST /api/v1/patients/onboarding ─────────────────────────────────────

async def _generate_plan_background(patient_id: int, user_data: dict, age: int) -> None:
    import logging
    _log = logging.getLogger(__name__)
    from ..core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as bg_session:
        try:
            from ..services.diet_plan_service import DietPlanService
            diet_service = DietPlanService()
            existing = await diet_service.get_diet_plan(str(patient_id), session=bg_session)
            if existing is None:
                diet_plan = await diet_service.generate_diet_plan(user_data, bg_session)
                await diet_service.store_diet_plan(diet_plan, session=bg_session)
                await bg_session.commit()
                _log.info(f"Background: diet plan generated for patient {patient_id}")
                try:
                    from ..services.notification_service import notify_plan_ready
                    from sqlalchemy import select as _select
                    from ..models.db_models import Patient as _Patient
                    result = await bg_session.execute(_select(_Patient).where(_Patient.id == patient_id))
                    pt = result.scalars().first()
                    if pt:
                        notify_plan_ready(pt)
                except Exception as notif_exc:
                    _log.debug(f"notify_plan_ready failed silently: {notif_exc}")
        except Exception as exc:
            _log.error(f"Background plan generation failed for patient {patient_id}: {exc}", exc_info=True)


async def _launch_plan_background(patient_id: int, user_data: dict, age: int) -> None:
    import asyncio as _asyncio
    _asyncio.create_task(_generate_plan_background(patient_id, user_data, age))


@router.post("/onboarding", response_model=PatientProfileResponse)
@limiter.limit("100/minute")
async def onboard_patient(
    request: Request,
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
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
            renewal_requested=False,
            expiring_soon=False,
        )
    )
    await session.flush()

    # Return the refreshed row
    result = await session.execute(select(Patient).where(Patient.id == patient.id))
    updated = result.scalars().first()

    # ── Create initial PatientVisit row (Token 2) if doctor is assigned ──
    # Guard: only insert when no row exists for this (patient, doctor) pair.
    # Without this check every re-call of the idempotent onboarding endpoint
    # would mint a fresh token_2, reset cycle_expiry +30 days, and orphan the
    # prior billing cycle — effectively letting patients extend for free.
    if updated.doctor_id:
        existing_pv = await session.execute(
            select(PatientVisit).where(
                PatientVisit.patient_id == updated.id,
                PatientVisit.doctor_id == updated.doctor_id,
            )
        )
        if existing_pv.scalars().first() is None:
            from datetime import timezone as _tz
            now = datetime.now(_tz.utc)
            pv = PatientVisit(
                patient_id=updated.id,
                doctor_id=updated.doctor_id,
                token_2=generate_token_2(),
                cycle_start=now,
                cycle_expiry=now + timedelta(days=CYCLE_DAYS),
                visit_counter=0,
            )
            session.add(pv)
            await session.flush()
    # ── Schedule plan generation as a background task ────────────────────
    # Runs AFTER the 200 response is sent — the client never waits for it.
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
        "age": age,
    }
    background_tasks.add_task(_launch_plan_background, updated.id, user_data, age)  # async task, returns immediately

    return updated


# ─── POST /api/v1/patients/activate ───────────────────────────────────────

@router.post("/activate", response_model=ActivationResponse)
async def activate_subscription(
    body: ActivationRequest,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Activate subscription. Two paths:
    - Sub-case A: Patient registered with a code (reserved) — no code needed in body.
    - Sub-case B: Free user activating later — must supply code in body.
    Generates token_1 and sets 30-day expiry. Issues fresh JWT.
    """
    now = datetime.now(timezone.utc)

    # Sub-case A: look for a code already reserved for this patient at registration
    reserved_result = await session.execute(
        select(SubscriptionCode).where(
            SubscriptionCode.reserved_by == patient.id,
            SubscriptionCode.is_used == False,
        ).with_for_update()
    )
    code_row = reserved_result.scalars().first()

    if code_row is not None:
        # RESERVED → CONSUMED
        code_row.is_used = True
        code_row.used_by_patient_id = patient.id
        code_row.used_at = now
    else:
        # Sub-case B: free user supplying a code manually
        if not body.code:
            raise HTTPException(
                status_code=400,
                detail="No subscription code provided. Enter the code from your doctor.",
            )

        b_result = await session.execute(
            select(SubscriptionCode).where(
                SubscriptionCode.code == body.code,
                SubscriptionCode.expires_at > now,
            ).with_for_update()
        )
        code_row = b_result.scalars().first()

        if code_row is None:
            raise HTTPException(
                status_code=400,
                detail="This code does not exist or has expired. Check with your doctor.",
            )
        if code_row.is_used:
            raise HTTPException(
                status_code=400,
                detail="This code has already been used by another account.",
            )
        if code_row.reserved_by is not None and code_row.reserved_by != patient.id:
            raise HTTPException(
                status_code=400,
                detail="This code has already been reserved by another account.",
            )

        # AVAILABLE (or reserved by same patient) → CONSUMED
        code_row.reserved_by = patient.id
        code_row.reserved_at = now
        code_row.is_used = True
        code_row.used_by_patient_id = patient.id
        code_row.used_at = now

    # Generate token_1 — idempotent, never overwrite if already set
    token_1_val = patient.token_1 or generate_token_1(patient.id)

    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(
            subscription_status="active",
            doctor_id=code_row.doctor_id,
            user_type="doctor_assigned",
            token_1=token_1_val,
            token_1_active=True,
            token_1_expiry=token_1_expiry_from_now(),
        )
    )

    # Create PatientVisit (Token 2) if none exists for this patient+doctor pair
    existing_pv = await session.execute(
        select(PatientVisit).where(
            PatientVisit.patient_id == patient.id,
            PatientVisit.doctor_id == code_row.doctor_id,
        )
    )
    if existing_pv.scalars().first() is None:
        pv = PatientVisit(
            patient_id=patient.id,
            doctor_id=code_row.doctor_id,
            token_2=generate_token_2(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=CYCLE_DAYS),
            visit_counter=0,
        )
        session.add(pv)

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
@limiter.limit("100/minute")
async def list_doctors(
    request: Request,
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


# ─── POST /api/v1/patients/request-renewal ────────────────────────────────
# Audit C-5: patient-facing renewal endpoint that sits outside /doctor/* so
# DoctorIsolationMiddleware does NOT intercept it.  The doctor-facing
# /doctor/patients/{id}/request-renewal remains for doctor-initiated flows.

@router.post("/request-renewal", status_code=200)
async def patient_request_renewal(
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Patient requests subscription renewal from their assigned doctor.
    Sets renewal_requested=True on the patient row so the doctor's
    pending-renewals list picks it up automatically.
    Returns 409 if the patient has no linked doctor yet.
    """
    if not patient.doctor_id:
        raise HTTPException(
            status_code=409,
            detail="No doctor linked to this account — cannot request renewal",
        )
    await session.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(renewal_requested=True)
    )
    await session.flush()
    return {"message": "Renewal request submitted successfully"}


# ─── GET /api/v1/patients/pending-visits ──────────────────────────────────

@router.get("/pending-visits")
async def list_pending_visits(
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Visits the doctor flagged that this patient has not yet responded to.

    Flagging happens when the patient cannot show Token 2 (phone forgotten or
    lost). Nothing is charged until the patient approves here — that is the
    fraud control, so this list is the patient's only view of a pending charge.

    Joined to Doctor for the name; PendingVisitApprovalResponse carries no
    doctor field and a bare id is meaningless in the app.
    """
    result = await session.execute(
        select(PendingVisitApproval, Doctor.name)
        .join(Doctor, Doctor.id == PendingVisitApproval.doctor_id)
        .where(
            PendingVisitApproval.patient_id == patient.id,
            PendingVisitApproval.status == "pending",
        )
        .order_by(PendingVisitApproval.visit_date.desc())
    )
    return [
        {
            "id": pv.id,
            "doctor_id": pv.doctor_id,
            "doctor_name": doctor_name,
            "visit_date": pv.visit_date.isoformat(),
            "reason_code": pv.reason_code,
            "reason_label": FLAG_VISIT_REASONS.get(pv.reason_code or "", "Not specified"),
            # Only ever populated when the doctor picked "other" — the schema
            # strips it on preset reasons so this surface stays a fixed
            # vocabulary next to a charge the patient is asked to confirm.
            "doctor_note": pv.doctor_note,
            "status": pv.status,
            "created_at": pv.created_at.isoformat() if pv.created_at else None,
        }
        for pv, doctor_name in result.all()
    ]


# ─── POST /api/v1/patients/pending-visits/{approval_id}/respond ───────────

@router.post("/pending-visits/{approval_id}/respond", status_code=200)
async def respond_to_pending_visit(
    approval_id: int,
    body: RespondVisitRequest,
    patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_db),
):
    """
    Approve or reject a doctor-flagged visit.

    Approving may increment PatientVisit.visit_counter, and since revenue is
    derived by summing that column (there is no invoice table), this endpoint
    is a billing write. Two consequences shape the implementation:

    1. The status transition is an atomic UPDATE ... WHERE status='pending'
       RETURNING, not a read-then-write. A double-tap on a slow connection
       would otherwise pass the read check twice and bill twice; there is no
       DB constraint that would catch it.
    2. Chargeability is judged as of the VISIT date, not now. The doctor flags
       on the day of the visit but the patient may approve days later, and the
       approval delay must not be what turns a free visit into a charged one.
    """
    from ..services.audit_service import log_action

    now = datetime.now(timezone.utc)
    new_status = "approved" if body.action == "approve" else "rejected"

    # Atomic claim — only one caller can move a row out of 'pending'.
    claim = await session.execute(
        update(PendingVisitApproval)
        .where(
            PendingVisitApproval.id == approval_id,
            PendingVisitApproval.patient_id == patient.id,
            PendingVisitApproval.status == "pending",
        )
        .values(status=new_status, responded_at=now)
        .returning(
            PendingVisitApproval.id,
            PendingVisitApproval.doctor_id,
            PendingVisitApproval.visit_date,
        )
    )
    row = claim.first()
    if row is None:
        # Either it does not exist, is not this patient's, or was already
        # answered. Deliberately one message: distinguishing them would leak
        # whether another patient's approval id exists.
        raise HTTPException(
            status_code=404,
            detail="No pending visit approval found for this id",
        )

    _, doctor_id, visit_date = row

    if body.action == "reject":
        await session.flush()
        return {
            "status": "rejected",
            "charged": False,
            "message": "Visit rejected. Your doctor has been notified that this visit did not happen.",
        }

    # ── Approve: find the live cycle to charge against ────────────────────
    pv_result = await session.execute(
        select(PatientVisit).where(
            PatientVisit.patient_id == patient.id,
            PatientVisit.doctor_id == doctor_id,
            PatientVisit.cycle_expiry > now,
        ).order_by(PatientVisit.cycle_start.desc())
    )
    pv = pv_result.scalars().first()
    if pv is None:
        # Mirrors record_patient_visit (doctor.py). Raising rolls back the
        # claim above, so the row stays 'pending' and can be approved once the
        # subscription is renewed rather than being silently consumed.
        raise HTTPException(
            status_code=400,
            detail="No active visit cycle — ask your doctor to renew your subscription "
                   "before confirming this visit.",
        )

    charged = is_chargeable_visit(
        last_charged_at=pv.last_charged_at,
        visit_counter=pv.visit_counter,
        cycle_start=pv.cycle_start,
        now=visit_date,          # price as of the visit, not the approval
    )
    if charged:
        pv.visit_counter += 1
        pv.last_charged_at = now

    await session.flush()
    await log_action(
        session,
        actor_id=patient.id,
        actor_role="patient",
        action="approve_flagged_visit",
        entity_type="patient",
        entity_id=patient.id,
        detail={
            "approval_id": approval_id,
            "doctor_id": doctor_id,
            "charged": charged,
            "visit_counter": pv.visit_counter,
            "visit_date": visit_date.isoformat(),
        },
    )

    msg = (
        f"Visit confirmed and charged (₹{VISIT_CHARGE_INR:,}). "
        f"Total visits this cycle: {pv.visit_counter}"
        if charged
        else "Visit confirmed — no charge (within your free-visit window)."
    )
    return {
        "status": "approved",
        "charged": charged,
        "visit_counter": pv.visit_counter,
        "message": msg,
    }
