import secrets
import string
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import get_db
from ..core.limiter import limiter
from ..core.security import get_current_doctor
from ..services.token_service import generate_token_2, token_1_expiry_from_now, is_chargeable_visit
from ..services.meal_generator.tag_utils import VALID_TAGS, get_avoid_tags, get_prefer_tags
from ..services.meal_generator.meal_generator import meal_generator
from ..models.db_models import (
    Doctor, Patient, Recommendation, PatientRequest, SubscriptionCode,
    MealLog, ProgressLog, ClinicalNote, FoodItem, PatientVisit,
    DoctorMealOverride, PendingVisitApproval,
    PatientMealConfig, PatientDishPreferences,
    WeeklyCombo, PatientMealChoice, WeeklyPatientSummary,
)
from ..services.weekly_summary_service import compute_weekly_summary
from ..schemas.doctor import (
    PatientSummary, PaginatedPatients, RecommendationDetail,
    PlanOverrideRequest, PatientRequestDetail, RejectRequest,
    GenerateCodesRequest, SubscriptionCodeDetail,
    MealLogEntry, PatientProgressEntry, PatientLogsResponse, PatientProgressResponse,
    ClinicalNoteCreate, ClinicalNoteResponse, MealPlanNoteRequest,
    FoodItemSummary, RecipeCreateRequest, RecipeAssignRequest, AddCustomDishRequest,
    DishAction, CustomDishBody, PatchDishRequest,
    DoctorDashboardStats,
    PatientVisitResponse, RecordVisitResponse, RenewalApproveResponse,
    BulkRenewalResponse, PendingRenewalItem,
    RecordVisitRequest, FlagVisitRequest, PendingVisitApprovalResponse,
    PatientSummaryWithVisit,
    MealConfigRequest, DishPrefRequest,
    RecipeTagsResponse, RecipeTagsPatchRequest,
    WeeklyPlanApproveRequest, ComboSwapRequest, WeeklyDishPatchRequest,
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


# ── Phase 8 Tier 0: override-logging helpers ──────────────────────────────────

def _bucket_age(dob) -> str:
    """Map date_of_birth → age bracket string for RL context bucketing."""
    if dob is None:
        return "unknown"
    from datetime import date as _date
    today = _date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 26:   return "18-25"
    if age < 36:   return "26-35"
    if age < 51:   return "36-50"
    return "50+"


def _bucket_bmi(bmi) -> str:
    """Map BMI float → category string for RL context bucketing."""
    if bmi is None:
        return "unknown"
    b = float(bmi)
    if b < 18.5:  return "underweight"
    if b < 25.0:  return "normal"
    if b < 30.0:  return "overweight"
    return "obese"


def _extract_food_id(meal: dict) -> Optional[int]:
    """
    Read food_item ID from a meal JSONB dict.
    Returns None if the meal was custom (no food_id key or value is None).
    """
    raw = meal.get("food_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _diff_meals(old_meals: list, new_meals: list) -> list[dict]:
    """
    Diff two meal arrays by (Date, Meal Type).
    Returns list of dicts with keys: meal_type, old_food_id, new_food_id.
    Only includes slots where the food_id actually changed.
    """
    old_map = {
        (m.get("Date"), m.get("Meal Type")): _extract_food_id(m)
        for m in old_meals
    }
    new_map = {
        (m.get("Date"), m.get("Meal Type")): (m, _extract_food_id(m))
        for m in new_meals
    }
    diffs = []
    for key, new_val in new_map.items():
        new_meal_dict, new_fid = new_val
        old_fid = old_map.get(key)
        if old_fid != new_fid:  # something changed in this slot
            diffs.append({
                "meal_type": key[1],
                "date": key[0],
                "old_food_id": old_fid,
                "new_food_id": new_fid,
                "slot_type": new_meal_dict.get("slot_type"),
            })
    return diffs


# ─── GET /api/v1/doctor/patients ──────────────────────────────────────────

@router.get("/patients", response_model=PaginatedPatients)
@limiter.limit("100/minute")
async def list_patients(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    offset = (page - 1) * page_size

    stmt = select(Patient).where(Patient.doctor_id == did)
    count_stmt = select(func.count(Patient.id)).where(Patient.doctor_id == did)

    if search:
        search_filter = (
            Patient.name.ilike(f"%{search}%") | 
            Patient.email.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar()

    result = await session.execute(
        stmt.order_by(Patient.created_at.desc())
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
        # ── Phase 8 Tier 0: record override events before applying change ──
        old_meals = list(rec.meals or [])
        diffs = _diff_meals(old_meals, body.meals)
        if diffs:
            # Fetch patient for context snapshot (ownership clause matches outer check)
            pat_result = await session.execute(
                select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
            )
            pat = pat_result.scalars().first()
            if pat:
                age_bucket = _bucket_age(pat.date_of_birth)
                bmi_bucket = _bucket_bmi(pat.bmi)
                for diff in diffs:
                    override = DoctorMealOverride(
                        doctor_id=did,
                        patient_id=patient_id,
                        override_date=date.today(),
                        slot_type=diff.get("slot_type"),
                        meal_type=diff["meal_type"] or "Unknown",
                        rejected_food_id=diff["old_food_id"],
                        chosen_food_id=diff["new_food_id"],
                        patient_health_condition=pat.health_condition,
                        patient_medical_conditions=list(pat.medical_conditions or []),
                        patient_region=pat.region,
                        patient_diet_type=pat.diet_type,
                        patient_age_bucket=age_bucket,
                        patient_bmi_bucket=bmi_bucket,
                    )
                    session.add(override)
        rec.meals = body.meals
    if body.doctor_notes is not None:
        rec.doctor_notes = body.doctor_notes
    rec.generated_by = "doctor"
    await session.flush()
    await session.refresh(rec)
    return rec


# ─── GET /api/v1/doctor/patients/{patient_id}/plan/overrides ─────────────

@router.get("/patients/{patient_id}/plan/overrides")
async def get_plan_overrides(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Return the history of AI meal replacements made by this doctor for the patient.
    Useful as an audit trail and for future RL inspection.
    """
    did = _doctor_id(request)
    pat_result = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(DoctorMealOverride)
        .where(
            DoctorMealOverride.doctor_id == did,
            DoctorMealOverride.patient_id == patient_id,
        )
        .order_by(DoctorMealOverride.override_date.desc(), DoctorMealOverride.id.desc())
        .limit(100)
    )
    overrides = result.scalars().all()
    return [
        {
            "id":                       o.id,
            "override_date":            str(o.override_date),
            "meal_type":                o.meal_type,
            "slot_type":                o.slot_type,
            "rejected_food_id":         o.rejected_food_id,
            "chosen_food_id":           o.chosen_food_id,
            "patient_health_condition": o.patient_health_condition,
            "patient_region":           o.patient_region,
            "patient_age_bucket":       o.patient_age_bucket,
            "patient_bmi_bucket":       o.patient_bmi_bucket,
        }
        for o in overrides
    ]


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

    # ── Activate patient subscription ──────────────────────────────────────
    from ..services.token_service import generate_token_1, token_1_expiry_from_now
    token_1 = generate_token_1(req.patient_id)
    now = datetime.now(timezone.utc)

    await session.execute(
        update(Patient)
        .where(Patient.id == req.patient_id)
        .values(
            doctor_id=did,
            user_type="doctor_assigned",
            subscription_status="active",
            # Token 1 — only set if not already assigned (idempotent)
            token_1=token_1,
            token_1_active=True,
            token_1_expiry=token_1_expiry_from_now(),
            renewal_requested=False,
        )
    )
    await session.flush()

    # ── Create initial PatientVisit row (Token 2) ─────────────────────────
    existing_pv = await session.execute(
        select(PatientVisit).where(
            PatientVisit.patient_id == req.patient_id,
            PatientVisit.doctor_id == did,
        )
    )
    if existing_pv.scalars().first() is None:
        pv = PatientVisit(
            patient_id=req.patient_id,
            doctor_id=did,
            token_2=generate_token_2(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=30),
            visit_counter=0,
        )
        session.add(pv)
        await session.flush()

    # ── Auto-generate diet plan if patient has onboarded ─────────────────
    # Fetch the patient to check if onboarding is done (height/weight set)
    pat_result = await session.execute(
        select(Patient).where(Patient.id == req.patient_id)
    )
    patient = pat_result.scalars().first()

    if patient and patient.height_cm and patient.weight_kg and float(patient.height_cm) > 0:
        import logging as _log
        _logger = _log.getLogger(__name__)
        try:
            from datetime import date as _date
            from ..services.diet_plan_service import DietPlanService
            diet_service = DietPlanService()

            dob = patient.date_of_birth
            if dob:
                today = _date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                age = 30

            user_data = {
                "id": str(patient.id),
                "email": patient.email,
                "name": patient.name,
                "gender": patient.gender or "Other",
                "height": float(patient.height_cm),
                "weight": float(patient.weight_kg),
                "activity_level": patient.activity_level or "LA",
                "diet": patient.diet_type or "Vegetarian",
                "health_condition": patient.health_condition or "Healthy",
                "region": patient.region or "North",
                "nonveg_meals_per_week": patient.nonveg_meals_per_week or 3,
                "health_goals": list(patient.health_goals or []),
                "medical_conditions": list(patient.medical_conditions or []),
                "food_allergies": list(patient.food_allergies or []),
                "age": age,
            }
            existing_plan = await diet_service.get_diet_plan(str(patient.id), session=session)
            if existing_plan is None:
                diet_plan = await diet_service.generate_diet_plan(user_data, session)
                await diet_service.store_diet_plan(diet_plan, session=session)
                _logger.info(f"Auto-generated diet plan for patient {patient.id} on doctor acceptance")
        except Exception as exc:
            _logger.error(f"Diet plan auto-gen failed on accept for patient {req.patient_id}: {exc}", exc_info=True)
            # Non-blocking — patient can generate from the app

    # ── FCM: notify patient that doctor accepted ──────────────────────────
    try:
        from ..services.notification_service import notify_doctor_accepted
        if patient:
            notify_doctor_accepted(patient, doctor.name)
    except Exception:
        pass  # fire-and-forget — never block accept flow

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


# ─── GET /api/v1/doctor/patients/{patient_id}/logs ────────────────────────

@router.get("/patients/{patient_id}/logs", response_model=PatientLogsResponse)
async def get_patient_logs(
    patient_id: int,
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor views a patient's meal logs for the last N days.
    Only returns logs for patients belonging to this doctor.
    """
    did = _doctor_id(request)

    # Ownership check
    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from datetime import timedelta
    start = date.today() - timedelta(days=days - 1)

    result = await session.execute(
        select(MealLog)
        .where(
            MealLog.patient_id == patient_id,
            MealLog.logged_date >= start,
        )
        .order_by(MealLog.logged_date.desc(), MealLog.created_at.desc())
    )
    logs = result.scalars().all()
    return PatientLogsResponse(patient_id=patient_id, period_days=days, meal_logs=logs)


# ─── GET /api/v1/doctor/patients/{patient_id}/progress ───────────────────

@router.get("/patients/{patient_id}/progress", response_model=PatientProgressResponse)
async def get_patient_progress(
    patient_id: int,
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor views a patient's weight/water/steps history for the last N days.
    """
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    from datetime import timedelta
    start = date.today() - timedelta(days=days - 1)

    result = await session.execute(
        select(ProgressLog)
        .where(
            ProgressLog.patient_id == patient_id,
            ProgressLog.log_date >= start,
        )
        .order_by(ProgressLog.log_date.asc())
    )
    progress = result.scalars().all()
    return PatientProgressResponse(patient_id=patient_id, period_days=days, progress_logs=progress)


# ─── DELETE /api/v1/doctor/patients/{patient_id} ─────────────────────────

@router.delete("/patients/{patient_id}")
async def remove_patient(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor removes a patient from their list.
    Patient's account is NOT deleted — they become standalone (doctor_id=None).
    Subscription is set to inactive since they no longer have a doctor.
    """
    did = _doctor_id(request)

    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    await session.execute(
        update(Patient)
        .where(Patient.id == patient_id)
        .values(
            doctor_id=None,
            user_type="standalone",
            subscription_status="inactive",
        )
    )
    await session.flush()
    return {"message": f"Patient {patient_id} removed from your list", "patient_id": patient_id}


# ─── POST /api/v1/doctor/patients/{patient_id}/notes ─────────────────────

@router.post("/patients/{patient_id}/notes", response_model=ClinicalNoteResponse, status_code=201)
async def add_clinical_note(
    patient_id: int,
    body: ClinicalNoteCreate,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Add a private clinical note for a patient."""
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    note = ClinicalNote(
        doctor_id=did,
        patient_id=patient_id,
        note_type=body.note_type,
        content=body.content,
        is_private=body.is_private,
    )
    session.add(note)
    await session.flush()
    return note


# ─── GET /api/v1/doctor/patients/{patient_id}/notes ──────────────────────

@router.get("/patients/{patient_id}/notes", response_model=list[ClinicalNoteResponse])
async def get_clinical_notes(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Get all clinical notes for a patient written by this doctor."""
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(ClinicalNote)
        .where(ClinicalNote.doctor_id == did, ClinicalNote.patient_id == patient_id)
        .order_by(ClinicalNote.created_at.desc())
    )
    return result.scalars().all()


# ─── POST /api/v1/doctor/patients/{patient_id}/plan/notes ────────────────

@router.post("/patients/{patient_id}/plan/notes")
async def add_meal_plan_note(
    patient_id: int,
    body: MealPlanNoteRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Add a doctor note to a specific meal in the patient's active plan.
    Finds the matching meal by date + meal_type and injects a 'doctor_note' field.
    Returns 404 if no active plan or if the specific meal is not found.
    """
    did = _doctor_id(request)

    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    meals = list(rec.meals or [])
    found = False
    updated_meals = []
    for meal in meals:
        meal = dict(meal)  # copy — JSONB dicts are immutable
        if meal.get("Date") == str(body.meal_date) and meal.get("Meal Type") == body.meal_type:
            meal["doctor_note"] = body.note
            found = True
        updated_meals.append(meal)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Meal '{body.meal_type}' on '{body.meal_date}' not found in plan",
        )

    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(meals=updated_meals)
    )
    await session.flush()
    return {"message": "Note added to meal", "meal_date": body.meal_date, "meal_type": body.meal_type}


# ─── POST /api/v1/doctor/patients/{patient_id}/plan/meals/{date}/{meal_type}/add ──

@router.post("/patients/{patient_id}/plan/meals/{meal_date}/{meal_type}/add")
async def add_custom_dish_to_plan(
    patient_id: int,
    meal_date: str,
    meal_type: str,
    body: AddCustomDishRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Add a custom dish directly to a patient's meal JSONB without creating a food_items record.

    Default path (add_to_library=False):
        Writes only to recommendations.meals JSONB. No food_items row created.

    Library path (add_to_library=True):
        Creates a food_items row (submitted_for_review=True, is_verified=False)
        then writes to JSONB with food_id set to the new row.
        Requires serving_weight_g.
    """
    did = _doctor_id(request)

    # Ownership check
    owner = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if owner.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Fetch active recommendation
    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    # v2 path: write to WeeklyCombo instead of JSONB
    if rec.generation_version == 2:
        from datetime import date as _date_type
        try:
            slot_date = _date_type.fromisoformat(meal_date)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid meal_date format: {meal_date}")
        combo_result_v2 = await session.execute(
            select(WeeklyCombo).where(
                WeeklyCombo.recommendation_id == rec.id,
                WeeklyCombo.slot_date == slot_date,
                WeeklyCombo.meal_type == meal_type,
                WeeklyCombo.combo_index == body.combo_index,
            )
        )
        combo_v2 = combo_result_v2.scalars().first()
        if combo_v2 is None:
            raise HTTPException(
                status_code=404,
                detail=f"No combo found for {meal_date} {meal_type} combo_index={body.combo_index}",
            )
        v2_dish: dict = {
            "food_id": None,
            "recipe_name": body.recipe_name,
            "slot_type": body.slot_type,
            "calories": body.calories,
            "scaled_calories": body.calories,
            "factor": 1.0,
            "protein": body.protein,
            "carbs": body.carbs,
            "fat": body.fat,
            "fiber": body.fiber,
            "is_custom_override": True,
        }
        if body.add_to_library:
            if not body.serving_weight_g:
                raise HTTPException(
                    status_code=422,
                    detail="serving_weight_g is required when add_to_library=True",
                )
            new_food_v2 = FoodItem(
                recipe_name=body.recipe_name,
                slot_type=body.slot_type,
                cal_per_serving=body.calories,
                protein_per_serving=body.protein,
                carbs_per_serving=body.carbs,
                fat_per_serving=body.fat,
                fiber_per_serving=body.fiber,
                serving_weight_g=body.serving_weight_g,
                diet_type=body.diet_type,
                meal_time_tags=[meal_type],
                plan_type_tags=["Healthy"],
                ingredients=[],
                region_tags=[],
                doctor_id=did,
                source="doctor",
                is_verified=False,
                submitted_for_review=True,
            )
            session.add(new_food_v2)
            await session.flush()
            v2_dish["food_id"] = new_food_v2.id
            v2_dish["is_custom_override"] = False
        v2_dishes = list(combo_v2.dishes or [])
        v2_dishes.append(v2_dish)
        combo_v2.dishes = v2_dishes
        combo_v2.total_calories = round(
            sum(d.get("scaled_calories", d.get("calories", 0)) for d in v2_dishes), 2
        )
        await session.flush()
        return {"message": "Dish added", "meal_type": meal_type, "dish": v2_dish}

    meals = [dict(m) for m in (rec.meals or [])]

    # Find the target meal slot
    slot_idx = next(
        (i for i, m in enumerate(meals)
         if str(m.get("Date")) == meal_date and m.get("Meal Type") == meal_type),
        None,
    )
    if slot_idx is None:
        raise HTTPException(
            status_code=404,
            detail=f"No meal slot found for {meal_date} {meal_type}",
        )

    # Build dish dict — default path: no food_id
    # Session 22E (decision b): doctor-entered macros are the intended portion —
    # factor 1.0, scaled_calories = calories.
    dish: dict = {
        "food_id": None,
        "recipe_name": body.recipe_name,
        "slot_type": body.slot_type,
        "calories": body.calories,
        "scaled_calories": body.calories,
        "factor": 1.0,
        "protein": body.protein,
        "carbs": body.carbs,
        "fat": body.fat,
        "fiber": body.fiber,
        "is_custom_override": True,
    }

    # Library path: create food_items record
    if body.add_to_library:
        if not body.serving_weight_g:
            raise HTTPException(
                status_code=422,
                detail="serving_weight_g is required when add_to_library=True",
            )
        new_food = FoodItem(
            recipe_name=body.recipe_name,
            slot_type=body.slot_type,
            cal_per_serving=body.calories,
            protein_per_serving=body.protein,
            carbs_per_serving=body.carbs,
            fat_per_serving=body.fat,
            fiber_per_serving=body.fiber,
            serving_weight_g=body.serving_weight_g,
            diet_type=body.diet_type,
            meal_time_tags=[meal_type],
            plan_type_tags=["Healthy"],
            ingredients=[],
            region_tags=[],
            doctor_id=did,
            source="doctor",
            is_verified=False,
            submitted_for_review=True,
        )
        session.add(new_food)
        await session.flush()  # get new_food.id
        dish["food_id"] = new_food.id
        dish["is_custom_override"] = False

    # Append dish to slot's dishes[] and recalculate totals
    slot = dict(meals[slot_idx])
    dishes = list(slot.get("dishes") or [])
    dishes.append(dish)
    slot["dishes"] = dishes

    # Session 22E (Bug 2): totals on the scaled basis; legacy dishes without the
    # new fields fall back to unscaled values (factor 1.0). "Target Calories"
    # is the generation-time budget and is never touched by doctor edits.
    slot["Total Calories"] = sum(d.get("scaled_calories", d.get("calories", 0)) for d in dishes)
    slot["Total Protein"]  = sum(d.get("protein",  0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Carbs"]    = sum(d.get("carbs",    0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Fat"]      = sum(d.get("fat",      0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Fiber"]    = sum(d.get("fiber",    0) * d.get("factor", 1.0) for d in dishes)
    slot["Menu Names"]     = " + ".join(d.get("recipe_name", "") for d in dishes)

    meals[slot_idx] = slot

    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(meals=meals)
    )
    await session.flush()
    return {"message": "Dish added", "meal_type": meal_type, "dish": dish}


# ─── PATCH /api/v1/doctor/patients/{patient_id}/plan/meals/{date}/{meal_type}/dishes/{dish_index} ──

@router.patch("/patients/{patient_id}/plan/meals/{meal_date}/{meal_type}/dishes/{dish_index}")
async def patch_dish(
    patient_id: int,
    meal_date: str,
    meal_type: str,
    dish_index: int,
    body: PatchDishRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Swap, remove, or add an individual dish within a meal slot's dishes[] array.

    swap:   replace dishes[dish_index] with a different dish
    remove: splice dishes[dish_index] out of the array
    add:    append a new dish (dish_index ignored)

    In all cases:
      - Slot totals (Total Calories/Protein/Carbs/Fat/Fiber) are recalculated
      - Menu Names is rebuilt from remaining dishes
      - recommendation_id is backfilled onto the slot if null
      - A DoctorMealOverride row is recorded with patient_id, date, meal_type, food_ids
    """
    from datetime import date as _date
    did = _doctor_id(request)

    # Ownership check
    pat_result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    pat = pat_result.scalars().first()
    if pat is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Fetch active recommendation
    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active plan found")

    meals = [dict(m) for m in (rec.meals or [])]

    # Find target meal slot
    slot_idx = next(
        (i for i, m in enumerate(meals)
         if str(m.get("Date")) == meal_date and m.get("Meal Type") == meal_type),
        None,
    )
    if slot_idx is None:
        raise HTTPException(
            status_code=404,
            detail=f"No meal slot found for {meal_date} {meal_type}",
        )

    slot = dict(meals[slot_idx])
    dishes = list(slot.get("dishes") or [])

    # Validate dish_index for swap/remove
    if body.action in (DishAction.swap, DishAction.remove):
        if dish_index < 0 or dish_index >= len(dishes):
            raise HTTPException(
                status_code=422,
                detail=f"dish_index {dish_index} out of range (0–{len(dishes) - 1})",
            )

    # ── Build new dish dict (for swap/add) ────────────────────────────────
    new_food_id: Optional[int] = None
    new_dish: Optional[dict] = None

    if body.action != DishAction.remove:
        effective_slot_type = body.slot_type or "main_dish"

        if body.replacement_food_id is not None:
            # Use existing food_items record
            fi_result = await session.execute(
                select(FoodItem).where(FoodItem.id == body.replacement_food_id)
            )
            fi = fi_result.scalars().first()
            if fi is None:
                raise HTTPException(status_code=404, detail="replacement_food_id not found")
            # Session 22E (decision b): doctor-swapped dishes are not rescaled.
            new_dish = {
                "food_id":    fi.id,
                "recipe_name": fi.recipe_name,
                "slot_type":  fi.slot_type,
                "calories":   float(fi.cal_per_serving),
                "scaled_calories": float(fi.cal_per_serving),
                "factor":     1.0,
                "protein":    float(fi.protein_per_serving),
                "carbs":      float(fi.carbs_per_serving),
                "fat":        float(fi.fat_per_serving),
                "fiber":      float(fi.fiber_per_serving),
                "is_custom_override": False,
            }
            new_food_id = fi.id

        elif body.custom_dish is not None:
            cd = body.custom_dish
            # Library path: create food_items record if flagged
            if body.flag_for_database:
                new_food = FoodItem(
                    recipe_name=cd.recipe_name,
                    slot_type=effective_slot_type,
                    cal_per_serving=cd.calories,
                    protein_per_serving=cd.protein,
                    carbs_per_serving=cd.carbs,
                    fat_per_serving=cd.fat,
                    fiber_per_serving=cd.fiber,
                    serving_weight_g=None,
                    diet_type="Vegetarian",
                    meal_time_tags=[meal_type],
                    plan_type_tags=["Healthy"],
                    ingredients=[],
                    region_tags=[],
                    doctor_id=did,
                    source="doctor",
                    is_verified=False,
                    submitted_for_review=True,
                )
                session.add(new_food)
                await session.flush()
                new_food_id = new_food.id
                is_custom = False
            else:
                new_food_id = None
                is_custom = True

            new_dish = {
                "food_id":    new_food_id,
                "recipe_name": cd.recipe_name,
                "slot_type":  effective_slot_type,
                "calories":   cd.calories,
                "scaled_calories": cd.calories,
                "factor":     1.0,
                "protein":    cd.protein,
                "carbs":      cd.carbs,
                "fat":        cd.fat,
                "fiber":      cd.fiber,
                "is_custom_override": is_custom,
            }
        else:
            raise HTTPException(
                status_code=422,
                detail="Either replacement_food_id or custom_dish must be provided for swap/add",
            )

    # ── Apply action to dishes[] ──────────────────────────────────────────
    old_food_id: Optional[int] = None

    if body.action == DishAction.swap:
        old_dish = dishes[dish_index]
        old_food_id = old_dish.get("food_id")
        dishes[dish_index] = new_dish

    elif body.action == DishAction.remove:
        old_dish = dishes[dish_index]
        old_food_id = old_dish.get("food_id")
        dishes.pop(dish_index)

    else:  # add
        dishes.append(new_dish)

    # ── Recalculate slot totals + rebuild Menu Names ──────────────────────
    # Session 22E (Bug 2): scaled basis with legacy fallback; Target Calories untouched.
    slot["dishes"]          = dishes
    slot["Total Calories"]  = sum(d.get("scaled_calories", d.get("calories", 0)) for d in dishes)
    slot["Total Protein"]   = sum(d.get("protein",  0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Carbs"]     = sum(d.get("carbs",    0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Fat"]       = sum(d.get("fat",      0) * d.get("factor", 1.0) for d in dishes)
    slot["Total Fiber"]     = sum(d.get("fiber",    0) * d.get("factor", 1.0) for d in dishes)
    slot["Menu Names"]      = " + ".join(d.get("recipe_name", "") for d in dishes)

    # ── Backfill recommendation_id onto slot if missing ───────────────────
    if not slot.get("recommendation_id"):
        slot["recommendation_id"] = rec.id

    meals[slot_idx] = slot

    # ── Write updated meals in single transaction ─────────────────────────
    from sqlalchemy import update as sa_update
    await session.execute(
        sa_update(Recommendation)
        .where(Recommendation.id == rec.id)
        .values(meals=meals)
    )

    # ── Record DoctorMealOverride ─────────────────────────────────────────
    try:
        override_date_obj = _date.fromisoformat(meal_date)
    except ValueError:
        override_date_obj = _date.today()

    override = DoctorMealOverride(
        doctor_id=did,
        patient_id=patient_id,
        override_date=override_date_obj,
        slot_type=slot.get("slot_type") or (new_dish.get("slot_type") if new_dish else None),
        meal_type=meal_type,
        rejected_food_id=old_food_id,
        chosen_food_id=new_food_id,
        patient_health_condition=pat.health_condition,
        patient_medical_conditions=list(pat.medical_conditions or []),
        patient_region=pat.region,
        patient_diet_type=pat.diet_type,
        patient_age_bucket=_bucket_age(pat.date_of_birth),
        patient_bmi_bucket=_bucket_bmi(pat.bmi),
    )
    session.add(override)
    await session.flush()

    _past = {"swap": "swapped", "remove": "removed", "add": "added"}
    return {
        "message":    f"Dish {_past[body.action.value]}",
        "meal_type":  meal_type,
        "dish_count": len(dishes),
        "total_calories": slot["Total Calories"],
        "override_id": override.id,
    }


# ─── R-3: Weekly plan (v2 multi-combo) doctor API ──────────────────────────
# rebuild_spec.md §3/§4 — generation_version=2 plans store 84 WeeklyCombo rows
# (7 days x 3 meal_types x 4 combo_index) instead of the v1 Recommendation.meals
# JSONB array. These 4 endpoints let the doctor view, approve, and edit them.

@router.get("/patients/{patient_id}/weekly-plan")
async def get_weekly_plan(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Active recommendation + all weekly_combos rows, grouped by
    slot_date -> meal_type -> combo_index (4 combos each).

    v1 plans (generation_version=1) have no weekly_combos rows — returns
    200 with plan={} and combos_available=False rather than 404, since the
    patient does have an active plan, just not in the v2 shape.
    """
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active recommendation found")

    if rec.generation_version == 1:
        return {
            "recommendation_id": rec.id,
            "generation_version": 1,
            "approval_status": rec.approval_status,
            "week_start": rec.week_start_date,
            "plan": {},
            "combos_available": False,
        }

    combos_result = await session.execute(
        select(WeeklyCombo)
        .where(WeeklyCombo.recommendation_id == rec.id)
        .order_by(WeeklyCombo.slot_date, WeeklyCombo.meal_type, WeeklyCombo.combo_index)
    )

    plan: dict = {}
    for c in combos_result.scalars().all():
        day = plan.setdefault(c.slot_date.isoformat(), {})
        day.setdefault(c.meal_type, []).append({
            "combo_id": c.id,
            "combo_index": c.combo_index,
            "total_calories": float(c.total_calories),
            "slot_composition": list(c.slot_composition),
            "dishes": c.dishes,
        })

    return {
        "recommendation_id": rec.id,
        "generation_version": rec.generation_version,
        "approval_status": rec.approval_status,
        "week_start": rec.week_start_date,
        "plan": plan,
    }


@router.post("/patients/{patient_id}/weekly-plan/approve")
async def approve_weekly_plan(
    patient_id: int,
    body: WeeklyPlanApproveRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Flip the active recommendation's approval_status draft -> approved, notify patient."""
    did = _doctor_id(request)
    pat = await _get_patient_for_doctor(patient_id, did, session)

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active recommendation found")

    if rec.approval_status == "approved":
        return {"status": "already_approved"}

    rec.approval_status = "approved"
    await session.flush()

    try:
        from ..services.notification_service import send_push
        send_push(
            fcm_token=getattr(pat, "fcm_token", None),
            title="Your meal plan is ready",
            body=f"Dr. {doctor.name} has approved your weekly plan.",
            data={"type": "weekly_plan_approved"},
        )
    except Exception:
        pass  # fire-and-forget — never block approval flow

    return {"status": "approved", "recommendation_id": rec.id}


@router.post("/patients/{patient_id}/weekly-plan/combos/{combo_id}/swap")
async def swap_weekly_combo(
    patient_id: int,
    combo_id: int,
    body: ComboSwapRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Regenerate one WeeklyCombo's dishes, excluding every dish already shown
    for this (slot_date, meal_type) across all 4 combos — including the one
    being swapped — so the new pick is guaranteed distinct. Records a
    doctor_meal_overrides row for the RL training corpus.

    Note: doctor_meal_overrides has no recommendation_id/slot_date/old_dishes/
    new_dishes columns (R-1 only added patient_condition_snapshot/edit_reason/
    doctor_note). Rather than a new migration (out of this session's scope),
    the full old/new dish payload is nested inside patient_condition_snapshot.
    """
    did = _doctor_id(request)
    pat = await _get_patient_for_doctor(patient_id, did, session)

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active recommendation found")

    combo_result = await session.execute(
        select(WeeklyCombo).where(WeeklyCombo.id == combo_id, WeeklyCombo.recommendation_id == rec.id)
    )
    combo = combo_result.scalars().first()
    if combo is None:
        raise HTTPException(status_code=404, detail="Combo not found for this patient's active plan")

    siblings_result = await session.execute(
        select(WeeklyCombo).where(
            WeeklyCombo.recommendation_id == rec.id,
            WeeklyCombo.slot_date == combo.slot_date,
            WeeklyCombo.meal_type == combo.meal_type,
        )
    )
    excluded_ids = {
        d["food_id"] for sib in siblings_result.scalars().all() for d in (sib.dishes or [])
    }

    old_dishes = list(combo.dishes or [])
    meal_target = float(combo.total_calories) if combo.total_calories else 0.0
    even_pct = 1.0 / max(len(old_dishes), 1)
    slots = [
        {
            "slot_type": d["slot_type"],
            "calorie_pct": (float(d.get("scaled_calories", 0)) / meal_target) if meal_target > 0 else even_pct,
            "required": True,
        }
        for d in old_dishes
    ]

    query_diet = meal_generator._derive_diet_label(old_dishes)
    user_diet = meal_generator._normalize_diet_label(pat.diet_type)

    conditions = list(pat.medical_conditions or [])
    patient_avoid_tags = frozenset(get_avoid_tags(conditions))
    patient_prefer_tags = frozenset(get_prefer_tags(conditions))

    raw_allergies = pat.food_allergies or []
    allergies = frozenset(
        a.strip().lower() for a in raw_allergies if a.strip().lower() not in ("", "none")
    )

    pref_result = await session.execute(
        select(PatientDishPreferences).where(PatientDishPreferences.patient_id == patient_id)
    )
    prefs = pref_result.scalars().all()
    pinned_food_ids = {p.food_item_id for p in prefs if p.preference_type == "pin"}
    blocked_food_ids = {p.food_item_id for p in prefs if p.preference_type == "block"}

    new_dishes, ok = await meal_generator._fill_slot_dishes(
        session, slots, query_diet, pat.region, combo.meal_type, pat.health_condition or "Healthy",
        meal_target,
        set(), set(), excluded_ids,
        user_diet=user_diet,
        allergies=allergies,
        blocked_food_ids=frozenset(blocked_food_ids),
        patient_avoid_tags=patient_avoid_tags,
        patient_prefer_tags=patient_prefer_tags,
        pinned_food_ids=pinned_food_ids,
    )

    if not ok or not new_dishes:
        raise HTTPException(
            status_code=409,
            detail={"error": "pool_exhausted", "message": "No distinct dishes available for swap"},
        )

    combo.dishes = new_dishes
    combo.slot_composition = [d["slot_type"] for d in new_dishes]
    combo.total_calories = round(sum(d["scaled_calories"] for d in new_dishes), 2)
    await session.flush()

    override = DoctorMealOverride(
        doctor_id=did,
        patient_id=patient_id,
        override_date=combo.slot_date,
        slot_type=",".join(d["slot_type"] for d in new_dishes) or None,
        meal_type=combo.meal_type,
        rejected_food_id=old_dishes[0]["food_id"] if old_dishes else None,
        chosen_food_id=new_dishes[0]["food_id"] if new_dishes else None,
        patient_health_condition=pat.health_condition,
        patient_medical_conditions=conditions,
        patient_region=pat.region,
        patient_diet_type=pat.diet_type,
        patient_age_bucket=_bucket_age(pat.date_of_birth),
        patient_bmi_bucket=_bucket_bmi(pat.bmi),
        patient_condition_snapshot={
            "conditions": conditions,
            "avoid_tags": list(patient_avoid_tags),
            "recommendation_id": rec.id,
            "slot_date": combo.slot_date.isoformat(),
            "old_dishes": old_dishes,
            "new_dishes": new_dishes,
        },
        edit_reason=body.edit_reason,
        doctor_note=body.doctor_note,
    )
    session.add(override)
    await session.flush()

    return {
        "status": "swapped",
        "combo": {
            "combo_id": combo.id,
            "combo_index": combo.combo_index,
            "total_calories": float(combo.total_calories),
            "slot_composition": list(combo.slot_composition),
            "dishes": combo.dishes,
        },
    }


@router.patch("/patients/{patient_id}/weekly-plan/combos/{combo_id}/dishes/{dish_index}")
async def patch_weekly_combo_dish(
    patient_id: int,
    combo_id: int,
    dish_index: int,
    body: WeeklyDishPatchRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    pat = await _get_patient_for_doctor(patient_id, did, session)

    rec_result = await session.execute(
        select(Recommendation)
        .where(Recommendation.patient_id == patient_id, Recommendation.is_active == True)
        .order_by(Recommendation.created_at.desc())
    )
    rec = rec_result.scalars().first()
    if rec is None:
        raise HTTPException(status_code=404, detail="No active recommendation found")

    combo_result = await session.execute(
        select(WeeklyCombo).where(
            WeeklyCombo.id == combo_id,
            WeeklyCombo.recommendation_id == rec.id,
        )
    )
    combo = combo_result.scalars().first()
    if combo is None:
        raise HTTPException(status_code=404, detail="Combo not found")

    dishes = list(combo.dishes or [])
    old_dishes = [dict(d) for d in dishes]

    slot_type_val = None
    rejected_food_id = None
    chosen_food_id = None

    # For remove: prefer food_item_id match over positional dish_index
    target_idx = dish_index
    if body.action == DishAction.remove and body.food_item_id is not None:
        found = next(
            (i for i, d in enumerate(dishes) if d.get("food_id") == body.food_item_id),
            None,
        )
        if found is not None:
            target_idx = found

    if body.action == DishAction.remove:
        if len(dishes) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove last dish from combo")
        if target_idx < 0 or target_idx >= len(dishes):
            raise HTTPException(status_code=422, detail=f"dish_index {target_idx} out of range")
        slot_type_val = old_dishes[target_idx].get("slot_type")
        rejected_food_id = old_dishes[target_idx].get("food_id")
        dishes.pop(target_idx)

    elif body.action in (DishAction.swap, DishAction.add):
        if body.food_item_id is None:
            raise HTTPException(status_code=422, detail="food_item_id required for swap/add")
        fi_result = await session.execute(
            select(FoodItem).where(FoodItem.id == body.food_item_id)
        )
        fi = fi_result.scalars().first()
        if fi is None:
            raise HTTPException(status_code=404, detail="food_item_id not found")
        new_dish = {
            "food_id": fi.id,
            "recipe_name": fi.recipe_name,
            "slot_type": fi.slot_type,
            "calories": float(fi.cal_per_serving),
            "scaled_calories": float(fi.cal_per_serving),
            "factor": 1.0,
            "protein": float(fi.protein_per_serving),
            "carbs": float(fi.carbs_per_serving),
            "fat": float(fi.fat_per_serving),
            "fiber": float(fi.fiber_per_serving),
            "is_custom_override": False,
        }
        if body.action == DishAction.swap:
            if dish_index < 0 or dish_index >= len(dishes):
                raise HTTPException(status_code=422, detail=f"dish_index {dish_index} out of range")
            slot_type_val = old_dishes[dish_index].get("slot_type")
            rejected_food_id = old_dishes[dish_index].get("food_id")
            chosen_food_id = fi.id
            dishes[dish_index] = new_dish
        else:
            slot_type_val = fi.slot_type
            chosen_food_id = fi.id
            dishes.append(new_dish)

    combo.dishes = dishes
    combo.slot_composition = [d["slot_type"] for d in dishes]
    combo.total_calories = round(
        sum(d.get("scaled_calories", d.get("calories", 0)) for d in dishes), 2
    )
    await session.flush()

    conditions = list(pat.medical_conditions or [])
    patient_avoid_tags = frozenset(get_avoid_tags(conditions))
    override = DoctorMealOverride(
        doctor_id=did,
        patient_id=patient_id,
        override_date=combo.slot_date,
        slot_type=slot_type_val,
        meal_type=combo.meal_type,
        rejected_food_id=rejected_food_id,
        chosen_food_id=chosen_food_id,
        patient_health_condition=pat.health_condition,
        patient_medical_conditions=conditions,
        patient_region=getattr(pat, "region", None),
        patient_diet_type=pat.diet_type,
        patient_age_bucket=_bucket_age(pat.date_of_birth),
        patient_bmi_bucket=_bucket_bmi(pat.bmi),
        patient_condition_snapshot={
            "conditions": conditions,
            "avoid_tags": list(patient_avoid_tags),
            "recommendation_id": rec.id,
            "slot_date": combo.slot_date.isoformat(),
            "action": body.action.value,
            "old_dishes": old_dishes,
            "new_dishes": dishes,
        },
        edit_reason=body.action.value,
        doctor_note=body.doctor_note,
    )
    session.add(override)
    await session.flush()

    return {
        "status": "updated",
        "combo": {
            "combo_id": combo.id,
            "combo_index": combo.combo_index,
            "total_calories": float(combo.total_calories),
            "slot_composition": list(combo.slot_composition),
            "dishes": combo.dishes,
        },
    }


@router.get("/patients/{patient_id}/weekly-summary")
async def get_weekly_summary(
    patient_id: int,
    request: Request,
    week_start_param: Optional[date] = Query(None, alias="week_start"),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Weekly adherence + dish-frequency summary. Computed on-demand, cached in weekly_patient_summary."""
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    target_week = week_start_param or (date.today() - timedelta(days=date.today().weekday()))
    summary_data = await compute_weekly_summary(session, patient_id, target_week)
    return summary_data


@router.get("/pending-approvals")
async def get_pending_approvals(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Lists all v2 draft plans from this doctor's patients that need approval."""
    did = _doctor_id(request)
    result = await session.execute(
        select(Recommendation.id, Recommendation.patient_id, Patient.name)
        .join(Patient, Patient.id == Recommendation.patient_id)
        .where(
            Recommendation.approval_status == "draft",
            Recommendation.generation_version == 2,
            Recommendation.is_active == True,
            Patient.doctor_id == did,
        )
    )
    rows = result.all()
    return {
        "pending": [
            {"patient_id": r.patient_id, "patient_name": r.name, "recommendation_id": r.id}
            for r in rows
        ]
    }


# ─── GET /api/v1/doctor/recipes ───────────────────────────────────────────

@router.get("/recipes", response_model=list[FoodItemSummary])
async def browse_recipes(
    request: Request,
    diet_type: Optional[str] = Query(default=None),
    meal_time: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    is_verified: Optional[bool] = Query(default=None, description="Filter by verification status"),
    my_library: bool = Query(default=False, description="True = show only this doctor's personal library items"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Browse food items.
    my_library=False (default): all items (verified + unverified), filterable by is_verified.
    my_library=True: this doctor's personal library (unverified, doctor_id=doctor.id).
    """
    did = _doctor_id(request)

    if my_library:
        # Doctor's personal library — their own unverified submissions
        stmt = select(FoodItem).where(
            FoodItem.doctor_id == did,
            FoodItem.source.in_(["doctor", "doctor_global"]),
        )
    else:
        stmt = select(FoodItem)

    if is_verified is not None:
        stmt = stmt.where(FoodItem.is_verified == is_verified)
    if diet_type:
        stmt = stmt.where(FoodItem.diet_type == diet_type)
    if meal_time:
        stmt = stmt.where(FoodItem.meal_time_tags.any(meal_time))
    if search:
        stmt = stmt.where(FoodItem.recipe_name.ilike(f"%{search}%"))

    offset = (page - 1) * page_size
    stmt = stmt.order_by(FoodItem.recipe_name).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    return result.scalars().all()


# ─── POST /api/v1/doctor/recipes ──────────────────────────────────────────

@router.post("/recipes", response_model=FoodItemSummary, status_code=201)
async def add_recipe(
    body: RecipeCreateRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor adds a recipe to their personal library.

    By default (submit_to_global=False): saved with source='doctor', is_verified=False,
    doctor_id=doctor.id — visible only in this doctor's library. Doctor can reuse it for
    any of their patients without repeating data entry.

    When submit_to_global=True: same item is also flagged for admin review. Once admin
    approves (PATCH /admin/food/{id}/approve), is_verified becomes True and the recipe
    joins the global dataset available to all doctors and the AI meal generator.
    """
    # Dedup: return existing record if name already matches (case-insensitive, trimmed)
    existing_result = await session.execute(
        select(FoodItem).where(
            func.lower(func.trim(FoodItem.recipe_name)) == body.recipe_name.strip().lower()
        ).limit(1)
    )
    existing = existing_result.scalars().first()
    if existing:
        return existing

    food = FoodItem(
        recipe_name=body.recipe_name,
        slot_type=body.slot_type,
        cal_per_serving=body.cal_per_serving,
        protein_per_serving=body.protein_per_serving,
        carbs_per_serving=body.carbs_per_serving,
        fat_per_serving=body.fat_per_serving,
        fiber_per_serving=body.fiber_per_serving,
        serving_weight_g=body.serving_weight_g,
        sodium_per_serving=body.sodium_per_serving,
        diet_type=body.diet_type,
        meal_time_tags=body.meal_time_tags,
        plan_type_tags=body.plan_type_tags,
        ingredients=[i.model_dump() for i in body.ingredients],  # IngredientItem → plain dict for JSONB
        region_tags=body.region_tags,
        doctor_id=doctor.id,
        # source differentiates library-only vs pending global approval
        source="doctor_global" if body.submit_to_global else "doctor",
        is_verified=False,  # admin must approve before entering global pool
    )
    session.add(food)
    await session.flush()
    return food


# ─── POST /api/v1/doctor/recipes/{recipe_id}/assign ──────────────────────

@router.post("/recipes/{recipe_id}/assign")
async def assign_recipe(
    recipe_id: int,
    body: RecipeAssignRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Inject a specific food item into specified patients' active meal plans.
    Adds the recipe as a new meal slot on the given date and meal_type.
    Only works for patients belonging to this doctor.
    Returns a summary of how many plans were updated.
    """
    did = _doctor_id(request)

    # Verify food item exists and is accessible to this doctor:
    # - Global verified items (is_verified=True) are accessible to all doctors
    # - Unverified items are only accessible to the doctor who created them
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == recipe_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if not food.is_verified and food.doctor_id != did:
        raise HTTPException(status_code=403, detail="Recipe not accessible")

    # Build the meal object to inject
    # Session 22E (W6): write a 1-dish dishes[] so this path produces the same
    # slot shape as the generator and PATCH endpoints (was dishes[]-less legacy).
    new_meal = {
        "Date": str(body.meal_date),  # date → str for JSONB compatibility
        "Meal Type": body.meal_type,
        "Menu Names": food.recipe_name,
        "Diet Type": food.diet_type,
        "Total Calories": float(food.cal_per_serving),
        "Total Protein": float(food.protein_per_serving),
        "Total Carbs": float(food.carbs_per_serving),
        "Total Fat": float(food.fat_per_serving),
        "Total Fiber": float(food.fiber_per_serving),
        "doctor_note": body.note or "",
        "food_id": recipe_id,
        "dishes": [{
            "food_id":    food.id,
            "recipe_name": food.recipe_name,
            "slot_type":  food.slot_type,
            "diet_type":  food.diet_type,
            "calories":   float(food.cal_per_serving),
            "scaled_calories": float(food.cal_per_serving),
            "factor":     1.0,
            "protein":    float(food.protein_per_serving),
            "carbs":      float(food.carbs_per_serving),
            "fat":        float(food.fat_per_serving),
            "fiber":      float(food.fiber_per_serving),
            "is_custom_override": False,
        }],
    }

    updated_count = 0
    failed_ids = []

    for pid in body.patient_ids:
        # Ownership check per patient
        owner = await session.execute(
            select(Patient.id).where(Patient.id == pid, Patient.doctor_id == did)
        )
        if owner.scalars().first() is None:
            failed_ids.append(pid)
            continue

        rec_result = await session.execute(
            select(Recommendation)
            .where(Recommendation.patient_id == pid, Recommendation.is_active == True)
            .order_by(Recommendation.created_at.desc())
        )
        rec = rec_result.scalars().first()
        if rec is None:
            failed_ids.append(pid)
            continue

        updated_meals = list(rec.meals or []) + [new_meal]
        from sqlalchemy import update as sa_update
        await session.execute(
            sa_update(Recommendation)
            .where(Recommendation.id == rec.id)
            .values(meals=updated_meals)
        )
        updated_count += 1

    await session.flush()
    return {
        "message": f"Recipe assigned to {updated_count} patient(s)",
        "updated_count": updated_count,
        "failed_patient_ids": failed_ids,
    }


# ─── GET /api/v1/doctor/recipes/{food_item_id}/tags ──────────────────────────

@router.get("/recipes/{food_item_id}/tags", response_model=RecipeTagsResponse)
async def get_recipe_tags(
    food_item_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(FoodItem).where(FoodItem.id == food_item_id))
    food = result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeTagsResponse(
        food_item_id=food.id,
        recipe_name=food.recipe_name,
        avoid_tags=list(food.avoid_tags or []),
        prefer_tags=list(food.prefer_tags or []),
        is_verified=food.is_verified,
    )


# ─── PATCH /api/v1/doctor/recipes/{food_item_id}/tags ────────────────────────

@router.patch("/recipes/{food_item_id}/tags", response_model=RecipeTagsResponse)
async def patch_recipe_tags(
    food_item_id: int,
    body: RecipeTagsPatchRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    unknown = (set(body.avoid_tags) | set(body.prefer_tags)) - VALID_TAGS
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown tags: {sorted(unknown)}. Valid tags: {sorted(VALID_TAGS)}",
        )
    result = await session.execute(select(FoodItem).where(FoodItem.id == food_item_id))
    food = result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await session.execute(
        update(FoodItem)
        .where(FoodItem.id == food_item_id)
        .values(avoid_tags=body.avoid_tags, prefer_tags=body.prefer_tags, is_verified=True)
    )
    await session.commit()
    return RecipeTagsResponse(
        food_item_id=food_item_id,
        recipe_name=food.recipe_name,
        avoid_tags=body.avoid_tags,
        prefer_tags=body.prefer_tags,
        is_verified=True,
    )


# ─── POST /api/v1/doctor/recipes/estimate ────────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel

class RecipeEstimateRequest(PydanticBaseModel):
    dish_name: str

# ── Local nutrition lookup — 60 common Indian dishes ─────────────────────────
# Values are per standard single serving. Source: ICMR / NIN food composition tables.
_INDIAN_NUTRITION_DB: list[dict] = [
    # Breakfast
    {"dish_name": "Idli", "aliases": ["idli", "idly"], "calories": 39, "protein": 2, "carbs": 8, "fat": 0, "cuisine": "South Indian", "serving_description": "1 piece (40g)"},
    {"dish_name": "Dosa", "aliases": ["dosa", "dosai", "plain dosa"], "calories": 168, "protein": 4, "carbs": 30, "fat": 4, "cuisine": "South Indian", "serving_description": "1 piece"},
    {"dish_name": "Masala Dosa", "aliases": ["masala dosa"], "calories": 230, "protein": 5, "carbs": 38, "fat": 7, "cuisine": "South Indian", "serving_description": "1 piece"},
    {"dish_name": "Ragi Dosa", "aliases": ["ragi dosa", "finger millet dosa"], "calories": 210, "protein": 9, "carbs": 38, "fat": 4, "cuisine": "South Indian", "serving_description": "2 pieces"},
    {"dish_name": "Uttapam", "aliases": ["uttapam", "uttappa"], "calories": 175, "protein": 5, "carbs": 28, "fat": 5, "cuisine": "South Indian", "serving_description": "1 piece"},
    {"dish_name": "Poha", "aliases": ["poha", "aval", "beaten rice", "pohe"], "calories": 195, "protein": 4, "carbs": 36, "fat": 4, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Upma", "aliases": ["upma", "uppuma", "rava upma", "vegetable upma"], "calories": 200, "protein": 6, "carbs": 34, "fat": 5, "cuisine": "South Indian", "serving_description": "1 cup"},
    {"dish_name": "Oats Upma", "aliases": ["oats upma", "oat upma"], "calories": 210, "protein": 8, "carbs": 35, "fat": 5, "cuisine": "Fusion", "serving_description": "1 cup"},
    {"dish_name": "Moong Dal Cheela", "aliases": ["moong dal cheela", "moong cheela", "green gram pancake"], "calories": 185, "protein": 12, "carbs": 24, "fat": 5, "cuisine": "North Indian", "serving_description": "2 pieces"},
    {"dish_name": "Besan Cheela", "aliases": ["besan cheela", "gram flour pancake", "chickpea pancake"], "calories": 170, "protein": 9, "carbs": 22, "fat": 5, "cuisine": "North Indian", "serving_description": "2 pieces"},
    {"dish_name": "Stuffed Paratha", "aliases": ["stuffed paratha", "aloo paratha", "gobi paratha", "paneer paratha"], "calories": 280, "protein": 8, "carbs": 40, "fat": 10, "cuisine": "North Indian", "serving_description": "1 paratha"},
    {"dish_name": "Plain Paratha", "aliases": ["paratha", "plain paratha", "wheat paratha"], "calories": 200, "protein": 5, "carbs": 30, "fat": 7, "cuisine": "North Indian", "serving_description": "1 paratha"},
    {"dish_name": "Methi Paratha", "aliases": ["methi paratha", "fenugreek paratha"], "calories": 210, "protein": 6, "carbs": 30, "fat": 7, "cuisine": "North Indian", "serving_description": "1 paratha"},
    {"dish_name": "Methi Thepla", "aliases": ["methi thepla", "thepla"], "calories": 145, "protein": 5, "carbs": 22, "fat": 4, "cuisine": "Gujarati", "serving_description": "2 pieces"},
    {"dish_name": "Dhokla", "aliases": ["dhokla", "khaman dhokla", "khaman"], "calories": 160, "protein": 7, "carbs": 25, "fat": 4, "cuisine": "Gujarati", "serving_description": "4 pieces"},
    {"dish_name": "Rava Idli", "aliases": ["rava idli", "semolina idli"], "calories": 170, "protein": 5, "carbs": 28, "fat": 5, "cuisine": "South Indian", "serving_description": "2 pieces"},
    # Rice dishes
    {"dish_name": "Steamed Rice", "aliases": ["rice", "plain rice", "white rice", "steamed rice"], "calories": 130, "protein": 3, "carbs": 28, "fat": 0, "cuisine": "Generic", "serving_description": "1 cup cooked (150g)"},
    {"dish_name": "Brown Rice", "aliases": ["brown rice"], "calories": 120, "protein": 3, "carbs": 25, "fat": 1, "cuisine": "Generic", "serving_description": "1 cup cooked (150g)"},
    {"dish_name": "Jeera Rice", "aliases": ["jeera rice", "cumin rice"], "calories": 200, "protein": 4, "carbs": 36, "fat": 5, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Biryani", "aliases": ["biryani", "chicken biryani", "veg biryani", "hyderabadi biryani"], "calories": 350, "protein": 14, "carbs": 55, "fat": 10, "cuisine": "Hyderabadi", "serving_description": "1 plate (250g)"},
    {"dish_name": "Pulao", "aliases": ["pulao", "pilaf", "veg pulao"], "calories": 250, "protein": 6, "carbs": 42, "fat": 6, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Khichdi", "aliases": ["khichdi", "khichri", "dal khichdi"], "calories": 185, "protein": 7, "carbs": 32, "fat": 4, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Curd Rice", "aliases": ["curd rice", "thayir sadam", "dahi rice"], "calories": 180, "protein": 6, "carbs": 28, "fat": 5, "cuisine": "South Indian", "serving_description": "1 cup"},
    # Dal / Lentils
    {"dish_name": "Dal Tadka", "aliases": ["dal tadka", "tarka dal", "yellow dal"], "calories": 180, "protein": 10, "carbs": 28, "fat": 5, "cuisine": "North Indian", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Dal Makhani", "aliases": ["dal makhani", "makhani dal", "black dal"], "calories": 230, "protein": 11, "carbs": 25, "fat": 10, "cuisine": "Punjabi", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Rajma", "aliases": ["rajma", "kidney bean curry", "rajma masala"], "calories": 210, "protein": 13, "carbs": 32, "fat": 4, "cuisine": "Punjabi", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Chana Masala", "aliases": ["chana masala", "chole", "chickpea curry"], "calories": 220, "protein": 11, "carbs": 32, "fat": 6, "cuisine": "North Indian", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Sambar", "aliases": ["sambar", "sambhar"], "calories": 95, "protein": 5, "carbs": 14, "fat": 3, "cuisine": "South Indian", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Rasam", "aliases": ["rasam", "pepper rasam", "tomato rasam"], "calories": 45, "protein": 2, "carbs": 8, "fat": 1, "cuisine": "South Indian", "serving_description": "1 bowl (200ml)"},
    # Sabzi / Vegetables
    {"dish_name": "Palak Paneer", "aliases": ["palak paneer", "spinach paneer"], "calories": 220, "protein": 16, "carbs": 12, "fat": 12, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Paneer Butter Masala", "aliases": ["paneer butter masala", "paneer makhani"], "calories": 290, "protein": 14, "carbs": 16, "fat": 18, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Aloo Gobi", "aliases": ["aloo gobi", "potato cauliflower"], "calories": 150, "protein": 4, "carbs": 22, "fat": 5, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Baingan Bharta", "aliases": ["baingan bharta", "eggplant bharta", "brinjal bharta"], "calories": 120, "protein": 3, "carbs": 15, "fat": 6, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Bhindi Masala", "aliases": ["bhindi", "okra masala", "bhindi masala", "ladies finger"], "calories": 100, "protein": 3, "carbs": 12, "fat": 5, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Lauki Sabzi", "aliases": ["lauki", "bottle gourd", "lauki sabzi", "dudhi"], "calories": 75, "protein": 2, "carbs": 10, "fat": 3, "cuisine": "North Indian", "serving_description": "1 cup"},
    {"dish_name": "Paneer Bhurji", "aliases": ["paneer bhurji", "scrambled paneer"], "calories": 250, "protein": 18, "carbs": 8, "fat": 17, "cuisine": "North Indian", "serving_description": "1 cup"},
    # Breads
    {"dish_name": "Roti", "aliases": ["roti", "chapati", "phulka", "wheat roti"], "calories": 80, "protein": 3, "carbs": 15, "fat": 1, "cuisine": "Generic", "serving_description": "1 roti"},
    {"dish_name": "Multigrain Roti", "aliases": ["multigrain roti", "multigrain chapati"], "calories": 85, "protein": 4, "carbs": 14, "fat": 2, "cuisine": "Generic", "serving_description": "1 roti"},
    {"dish_name": "Naan", "aliases": ["naan", "plain naan", "butter naan"], "calories": 262, "protein": 9, "carbs": 45, "fat": 5, "cuisine": "North Indian", "serving_description": "1 piece"},
    {"dish_name": "Puri", "aliases": ["puri", "poori"], "calories": 150, "protein": 3, "carbs": 18, "fat": 8, "cuisine": "North Indian", "serving_description": "2 pieces"},
    {"dish_name": "Bhature", "aliases": ["bhatura", "bhature"], "calories": 230, "protein": 6, "carbs": 34, "fat": 8, "cuisine": "Punjabi", "serving_description": "1 piece"},
    # Snacks
    {"dish_name": "Makhana", "aliases": ["makhana", "fox nuts", "roasted makhana", "lotus seeds"], "calories": 120, "protein": 4, "carbs": 20, "fat": 1, "cuisine": "Generic", "serving_description": "1 cup"},
    {"dish_name": "Roasted Chana", "aliases": ["roasted chana", "chana", "roasted chickpeas", "bhuna chana"], "calories": 115, "protein": 7, "carbs": 18, "fat": 2, "cuisine": "Generic", "serving_description": "30g"},
    {"dish_name": "Sprout Chaat", "aliases": ["sprout chaat", "sprouted moong", "sprouts salad"], "calories": 130, "protein": 9, "carbs": 20, "fat": 2, "cuisine": "Generic", "serving_description": "1 bowl"},
    {"dish_name": "Samosa", "aliases": ["samosa"], "calories": 250, "protein": 5, "carbs": 30, "fat": 13, "cuisine": "North Indian", "serving_description": "2 pieces"},
    {"dish_name": "Vada", "aliases": ["vada", "medu vada", "urad vada"], "calories": 175, "protein": 6, "carbs": 22, "fat": 8, "cuisine": "South Indian", "serving_description": "2 pieces"},
    # Non-veg
    {"dish_name": "Chicken Curry", "aliases": ["chicken curry", "murgh curry"], "calories": 250, "protein": 28, "carbs": 8, "fat": 13, "cuisine": "North Indian", "serving_description": "1 bowl (200ml)"},
    {"dish_name": "Chicken Tikka", "aliases": ["chicken tikka", "tandoori chicken"], "calories": 190, "protein": 30, "carbs": 5, "fat": 6, "cuisine": "Punjabi", "serving_description": "4 pieces"},
    {"dish_name": "Egg Bhurji", "aliases": ["egg bhurji", "scrambled eggs", "anda bhurji"], "calories": 180, "protein": 13, "carbs": 4, "fat": 13, "cuisine": "Generic", "serving_description": "2 eggs"},
    {"dish_name": "Fish Curry", "aliases": ["fish curry", "meen curry"], "calories": 200, "protein": 25, "carbs": 6, "fat": 9, "cuisine": "South Indian", "serving_description": "1 bowl"},
    # Sweets / Desserts
    {"dish_name": "Kheer", "aliases": ["kheer", "rice pudding", "payasam"], "calories": 180, "protein": 5, "carbs": 30, "fat": 5, "cuisine": "Generic", "serving_description": "1 small bowl"},
    {"dish_name": "Halwa", "aliases": ["halwa", "sooji halwa", "gajar halwa", "carrot halwa"], "calories": 280, "protein": 4, "carbs": 40, "fat": 12, "cuisine": "North Indian", "serving_description": "1 small bowl"},
    {"dish_name": "Raita", "aliases": ["raita", "dahi raita", "cucumber raita", "boondi raita"], "calories": 80, "protein": 4, "carbs": 9, "fat": 3, "cuisine": "Generic", "serving_description": "1 bowl (150ml)"},
    {"dish_name": "Lassi", "aliases": ["lassi", "sweet lassi", "plain lassi"], "calories": 150, "protein": 5, "carbs": 20, "fat": 5, "cuisine": "Punjabi", "serving_description": "1 glass (250ml)"},
    {"dish_name": "Buttermilk", "aliases": ["buttermilk", "chaas", "chaach", "mattha"], "calories": 50, "protein": 3, "carbs": 6, "fat": 1, "cuisine": "Generic", "serving_description": "1 glass (250ml)"},
]


def _find_dish(dish_name: str) -> dict | None:
    """Fuzzy-match dish_name against the local DB. Returns best match or None."""
    query = dish_name.strip().lower()
    best: dict | None = None
    best_score = 0

    for entry in _INDIAN_NUTRITION_DB:
        for alias in entry["aliases"]:
            # Exact match wins immediately
            if query == alias:
                return entry
            # Partial match scoring
            if alias in query or query in alias:
                score = len(set(alias.split()) & set(query.split()))  # word overlap
                if score > best_score:
                    best_score = score
                    best = entry

    return best if best_score > 0 else None


@router.post("/recipes/estimate")
@limiter.limit("10/hour")
async def estimate_recipe_nutrition(
    request: Request,
    body: RecipeEstimateRequest,
    doctor: Doctor = Depends(get_current_doctor),
):
    """
    Estimate nutrition for a dish name.
    Strategy: local Indian dish lookup table first (instant, offline).
    Falls back to Gemini API if a key is configured and dish not found locally.
    The doctor reviews and edits before saving.
    """
    # ── Step 1: Try local lookup first (fast, free, reliable) ──────────────
    match = _find_dish(body.dish_name)
    if match:
        return {
            "ai_estimated": True,
            "source": "local_db",
            "dish_name": match["dish_name"],
            "calories": match["calories"],
            "protein": match["protein"],
            "carbs": match["carbs"],
            "fat": match["fat"],
            "cuisine": match["cuisine"],
            "serving_description": match["serving_description"],
        }

    # ── Step 2: Fall back to Gemini if key is available ─────────────────────
    import httpx
    from ..core.config import settings

    api_key = settings.GEMINI_API_KEY_1
    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=f"Dish '{body.dish_name}' not found in local database. Add a Gemini API key to enable AI estimation.",
        )

    prompt = f"""You are a nutritionist AI specializing in Indian cuisine.

For the dish \"{body.dish_name}\", provide nutritional estimates per standard single serving.

Respond ONLY with a valid JSON object — no markdown, no explanation, no backticks.

Required format:
{{
  "dish_name": "<canonical dish name>",
  "calories": <integer kcal>,
  "protein": <integer grams>,
  "carbs": <integer grams>,
  "fat": <integer grams>,
  "cuisine": "<cuisine type e.g. South Indian, North Indian, Gujarati>",
  "serving_description": "<e.g. 2 pieces, 1 bowl 200ml, 1 cup>"
}}"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Gemini API error: {e.response.status_code}")
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Could not reach Gemini API")

    import json as _json
    try:
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        clean = raw_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        nutrition = _json.loads(clean)
    except (KeyError, _json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse AI response: {e}")

    return {"ai_estimated": True, "source": "gemini", **nutrition}


# ─── GET /api/v1/doctor/dashboard ─────────────────────────────────────────

@router.get("/dashboard", response_model=DoctorDashboardStats)
@limiter.limit("100/minute")
async def get_dashboard(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Aggregated stats for the doctor's home dashboard.
    Includes: patient counts, pending requests, plans this week,
    inactive patients (no logs 7+ days), expiring subscriptions (next 7 days).
    """
    from datetime import timedelta
    did = _doctor_id(request)
    today = date.today()
    seven_days_ago = today - timedelta(days=7)
    seven_days_ahead = today + timedelta(days=7)

    # Total patients
    total = (await session.execute(
        select(func.count(Patient.id)).where(Patient.doctor_id == did)
    )).scalar() or 0

    # Active patients
    active = (await session.execute(
        select(func.count(Patient.id)).where(
            Patient.doctor_id == did,
            Patient.subscription_status == "active",
        )
    )).scalar() or 0

    # Pending requests
    pending = (await session.execute(
        select(func.count(PatientRequest.id)).where(
            PatientRequest.doctor_id == did,
            PatientRequest.status == "pending",
        )
    )).scalar() or 0

    # Plans generated this week
    week_start = today - timedelta(days=today.weekday())
    plans_this_week = (await session.execute(
        select(func.count(Recommendation.id))
        .join(Patient, Recommendation.patient_id == Patient.id)
        .where(
            Patient.doctor_id == did,
            Recommendation.week_start_date >= week_start,
        )
    )).scalar() or 0

    # Inactive patients — no meal log in the last 7 days
    # Get all patient IDs for this doctor who logged at least once in 7 days
    active_patients_result = await session.execute(
        select(MealLog.patient_id)
        .join(Patient, MealLog.patient_id == Patient.id)
        .where(
            Patient.doctor_id == did,
            MealLog.logged_date >= seven_days_ago,
        )
        .distinct()
    )
    active_patient_ids = {row[0] for row in active_patients_result.all()}

    # All patients for this doctor
    all_patients_result = await session.execute(
        select(Patient).where(Patient.doctor_id == did)
    )
    all_patients = all_patients_result.scalars().all()

    inactive_patients = [
        {"patient_id": p.id, "name": p.name, "email": p.email}
        for p in all_patients
        if p.id not in active_patient_ids
    ]

    # Expiring soon — subscription_end_date within next 7 days
    expiring_result = await session.execute(
        select(Patient).where(
            Patient.doctor_id == did,
            Patient.subscription_status == "active",
            Patient.subscription_end_date.isnot(None),
            Patient.subscription_end_date <= seven_days_ahead,
        )
    )
    expiring_patients = expiring_result.scalars().all()
    expiring_soon = [
        {
            "patient_id": p.id,
            "name": p.name,
            "subscription_end_date": p.subscription_end_date.isoformat() if p.subscription_end_date else None,
        }
        for p in expiring_patients
    ]

    return DoctorDashboardStats(
        total_patients=total,
        active_patients=active,
        pending_requests=pending,
        plans_generated_this_week=plans_this_week,
        inactive_patients=inactive_patients,
        expiring_soon=expiring_soon,
    )


# ─── POST /api/v1/doctor/patients/{patient_id}/record-visit ───────────────

@router.post("/patients/{patient_id}/record-visit", response_model=RecordVisitResponse)
async def record_patient_visit(
    patient_id: int,
    body: RecordVisitRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Record a physical clinic visit for a patient using their Token 2.

    FRAUD PREVENTION: The patient must show their Token 2 from the patient app.
    The doctor enters this token here. If it doesn't match the patient's current
    cycle token, the visit is rejected with HTTP 400.

    Charging rules (see token_service.is_chargeable_visit):
      - First visit within 15 days of Token 1 activation → FREE (included in ₹800/mo)
      - First visit after 15-day grace period → ₹1,500
      - Subsequent visits > 15 days since last charge → ₹1,500
      - Subsequent visits ≤ 15 days since last charge → FREE (follow-up grace)
    """
    from ..services.audit_service import log_action
    did = _doctor_id(request)

    # Verify patient belongs to this doctor
    pat_result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = pat_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    now = datetime.now(timezone.utc)

    # Get current active PatientVisit row
    pv_result = await session.execute(
        select(PatientVisit).where(
            PatientVisit.patient_id == patient_id,
            PatientVisit.doctor_id == did,
            PatientVisit.cycle_expiry > now,
        ).order_by(PatientVisit.cycle_start.desc())
    )
    pv = pv_result.scalars().first()

    if pv is None:
        raise HTTPException(
            status_code=400,
            detail="No active visit cycle found for this patient. "
                   "Please ensure the patient's subscription is active.",
        )

    # ── TOKEN 2 VERIFICATION — fraud prevention ────────────────────────────
    # Normalise both sides: strip whitespace, uppercase
    submitted = body.token_2.strip().upper()
    expected  = pv.token_2.strip().upper()
    if submitted != expected:
        raise HTTPException(
            status_code=400,
            detail="Token 2 does not match. Ask the patient to show their Token 2 "
                   "from the Mityahar app and enter it exactly.",
        )

    # ── Apply charging rules ───────────────────────────────────────────────
    charged = is_chargeable_visit(
        last_charged_at=pv.last_charged_at,
        visit_counter=pv.visit_counter,
        cycle_start=pv.cycle_start,
    )
    if charged:
        pv.visit_counter += 1
        pv.last_charged_at = now

    await session.flush()
    await log_action(
        session,
        actor_id=did,
        actor_role="doctor",
        action="record_visit",
        entity_type="patient",
        entity_id=patient_id,
        detail={"charged": charged, "visit_counter": pv.visit_counter, "token_2_verified": True},
    )

    if charged:
        msg = f"Visit verified and charged (₹1,500). Total visits this cycle: {pv.visit_counter}"
    elif pv.visit_counter == 0:
        msg = "Visit verified — free initial consultation (within 15-day grace period after subscription)."
    else:
        msg = "Visit verified — within 15-day follow-up window, no charge."

    return RecordVisitResponse(
        charged=charged,
        visit_counter=pv.visit_counter,
        last_charged_at=pv.last_charged_at,
        message=msg,
    )


# ─── POST /api/v1/doctor/patients/{patient_id}/flag-visit ─────────────────

@router.post("/patients/{patient_id}/flag-visit", status_code=201)
async def flag_visit(
    patient_id: int,
    body: FlagVisitRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Flag a visit when the patient forgot their phone and can't show Token 2.

    Creates a PendingVisitApproval record. The patient sees a notification in
    their app and must approve it before the visit is recorded and charged.
    This maintains fraud prevention even when the patient is phoneless.
    """
    did = _doctor_id(request)

    pat_result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = pat_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    now = datetime.now(timezone.utc)

    # Get active PatientVisit to link to
    pv_result = await session.execute(
        select(PatientVisit).where(
            PatientVisit.patient_id == patient_id,
            PatientVisit.doctor_id == did,
            PatientVisit.cycle_expiry > now,
        ).order_by(PatientVisit.cycle_start.desc())
    )
    pv = pv_result.scalars().first()

    pending = PendingVisitApproval(
        patient_id=patient_id,
        doctor_id=did,
        patient_visit_id=pv.id if pv else None,
        status="pending",
        visit_date=now,
        doctor_note=body.doctor_note,
    )
    session.add(pending)
    await session.flush()

    return {
        "message": "Visit flagged. The patient will receive a notification to confirm.",
        "pending_visit_id": pending.id,
    }


# ─── GET /api/v1/doctor/patients/{patient_id}/visits ─────────────────────

@router.get("/patients/{patient_id}/visits", response_model=list[PatientVisitResponse])
async def get_patient_visits(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Return all visit cycles for a patient, newest first."""
    did = _doctor_id(request)
    pat_result = await session.execute(
        select(Patient.id).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    if pat_result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(PatientVisit)
        .where(PatientVisit.patient_id == patient_id, PatientVisit.doctor_id == did)
        .order_by(PatientVisit.cycle_start.desc())
    )
    return result.scalars().all()


# ─── POST /api/v1/doctor/patients/{patient_id}/request-renewal ───────────

@router.post("/patients/{patient_id}/request-renewal", status_code=200)
async def request_renewal(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Patient-triggered renewal request. Sets renewal_requested flag."""
    did = _doctor_id(request)
    pat_result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = pat_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    await session.execute(
        update(Patient).where(Patient.id == patient_id).values(
            renewal_requested=True,
            renewal_requested_at=datetime.now(timezone.utc),
        )
    )
    await session.flush()
    return {"message": "Renewal request submitted. Your doctor will be notified."}


# ─── POST /api/v1/doctor/patients/{patient_id}/approve-renewal ───────────

@router.post("/patients/{patient_id}/approve-renewal", response_model=RenewalApproveResponse)
async def approve_renewal(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor approves a single patient's renewal.
    Reactivates Token 1 (same value), generates new Token 2, resets 30-day cycle.
    """
    from ..services.audit_service import log_action
    did = _doctor_id(request)
    pat_result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == did)
    )
    patient = pat_result.scalars().first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    now = datetime.now(timezone.utc)
    new_expiry = token_1_expiry_from_now()
    new_token_2 = generate_token_2()

    # Reactivate Token 1
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

    # Create fresh PatientVisit (Token 2) for new cycle
    pv = PatientVisit(
        patient_id=patient_id,
        doctor_id=did,
        token_2=new_token_2,
        cycle_start=now,
        cycle_expiry=now + timedelta(days=30),
        visit_counter=0,
    )
    session.add(pv)
    await session.flush()

    await log_action(
        session, actor_id=did, actor_role="doctor",
        action="approve_renewal", entity_type="patient", entity_id=patient_id,
    )

    # ── FCM: notify patient that renewal was approved ─────────────────────
    try:
        from ..services.notification_service import notify_renewal_approved
        notify_renewal_approved(patient, doctor.name)
    except Exception:
        pass  # fire-and-forget

    return RenewalApproveResponse(
        message=f"Renewal approved for patient {patient.name}.",
        token_1=patient.token_1,
        token_2=new_token_2,
        token_1_expiry=new_expiry,
    )


# ─── POST /api/v1/doctor/patients/approve-all-renewals ───────────────────

@router.post("/patients/approve-all-renewals", response_model=BulkRenewalResponse)
async def approve_all_renewals(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Bulk approve all pending renewal requests for this doctor's patients."""
    from ..services.audit_service import log_action
    did = _doctor_id(request)

    result = await session.execute(
        select(Patient).where(
            Patient.doctor_id == did,
            Patient.renewal_requested == True,
        )
    )
    patients = result.scalars().all()
    if not patients:
        return BulkRenewalResponse(approved_count=0, patient_ids=[])

    now = datetime.now(timezone.utc)
    approved_ids = []

    for patient in patients:
        new_expiry = token_1_expiry_from_now()
        await session.execute(
            update(Patient).where(Patient.id == patient.id).values(
                token_1_active=True,
                token_1_expiry=new_expiry,
                renewal_requested=False,
                renewal_requested_at=None,
                expiring_soon=False,
                subscription_status="active",
            )
        )
        pv = PatientVisit(
            patient_id=patient.id,
            doctor_id=did,
            token_2=generate_token_2(),
            cycle_start=now,
            cycle_expiry=now + timedelta(days=30),
            visit_counter=0,
        )
        session.add(pv)
        approved_ids.append(patient.id)

    await session.flush()
    await log_action(
        session, actor_id=did, actor_role="doctor",
        action="approve_all_renewals", entity_type="patient", entity_id=None,
        detail={"approved_count": len(approved_ids), "patient_ids": approved_ids},
    )
    return BulkRenewalResponse(approved_count=len(approved_ids), patient_ids=approved_ids)


# ─── GET /api/v1/doctor/pending-renewals ─────────────────────────────────
# NOTE: This route is at /doctor/pending-renewals (NOT under /patients/{id})
# to avoid FastAPI matching "pending-renewals" as a patient_id int parameter.

@router.get("/pending-renewals", response_model=list[PendingRenewalItem])
async def get_pending_renewals(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Return all patients with a pending renewal request for this doctor."""
    did = _doctor_id(request)
    result = await session.execute(
        select(Patient).where(
            Patient.doctor_id == did,
            Patient.renewal_requested == True,
        ).order_by(Patient.renewal_requested_at.asc())
    )
    patients = result.scalars().all()
    return [
        PendingRenewalItem(
            patient_id=p.id,
            patient_name=p.name,
            patient_email=p.email,
            token_1=p.token_1,
            renewal_requested_at=p.renewal_requested_at,
            token_1_expiry=p.token_1_expiry,
        )
        for p in patients
    ]


# ─── POST /api/v1/doctor/recipes/lookup ───────────────────────────────────────
# Task 4 — Gemini nutrition fallback
# When a doctor types a dish name not in the DB, this endpoint asks Gemini
# to estimate the macros. Keys rotate round-robin across 4 API keys.

import os, json, itertools, httpx
from pydantic import BaseModel as _BM

class RecipeLookupRequest(_BM):
    food_name: str

class RecipeLookupResponse(_BM):
    food_name: str
    calories: str
    protein: str
    carbs: str
    fat: str
    fiber: str
    source: str = "gemini_estimate"

# Build round-robin key cycle from env
_gemini_keys = [
    v for k, v in sorted(os.environ.items())
    if k.startswith("GEMINI_API_KEY") and v.strip()
]
_key_cycle = itertools.cycle(_gemini_keys) if _gemini_keys else None

_GEMINI_PROMPT = """You are a nutrition expert specializing in Indian food.
Given the dish name below, estimate the nutritional values per standard single serving.
Return ONLY a JSON object with these exact keys (all values as strings, numbers only):
{{"calories": "...", "protein": "...", "carbs": "...", "fat": "...", "fiber": "..."}}
No explanation, no markdown, no units in values — just the JSON object.

Dish: {food_name}"""

@router.post("/recipes/lookup", response_model=RecipeLookupResponse)
async def gemini_recipe_lookup(
    body: RecipeLookupRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
):
    """
    Estimate nutritional values for an unrecognised dish via Gemini.
    Rotates across up to 4 API keys to stay within free tier rate limits.
    Returns editable estimates — doctor should verify before saving.
    """
    if not _key_cycle:
        raise HTTPException(status_code=503, detail="Gemini API keys not configured")

    api_key = next(_key_cycle)
    prompt  = _GEMINI_PROMPT.format(food_name=body.food_name.strip())

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-lite:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Gemini API error — try again")

    try:
        raw_text = (
            resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        ).strip()
        # Strip markdown fences if Gemini wraps in ```json ... ```
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        data = json.loads(raw_text.strip())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not parse Gemini response")

    return RecipeLookupResponse(
        food_name=body.food_name,
        calories=str(data.get("calories", "0")),
        protein=str(data.get("protein",  "0")),
        carbs=str(data.get("carbs",    "0")),
        fat=str(data.get("fat",      "0")),
        fiber=str(data.get("fiber",   "0")),
    )


# ═══════════════════════════════════════════════════════════════════════════
# MEAL CONFIG — per-patient TDEE split + dish pin/block
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_MEAL_SPLIT = {"Breakfast": 25, "Lunch": 35, "Dinner": 25}
_BUFFER_PCT = 15


def _build_meal_config_user_data(patient: Patient) -> dict:
    dob = patient.date_of_birth
    if dob:
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    else:
        age = 30
    return {
        "id": str(patient.id),
        "email": patient.email,
        "name": patient.name,
        "gender": patient.gender or "Other",
        "height": float(patient.height_cm),
        "weight": float(patient.weight_kg),
        "activity_level": patient.activity_level or "LA",
        "diet": patient.diet_type or "Vegetarian",
        "health_condition": patient.health_condition or "Healthy",
        "region": patient.region or "North",
        "nonveg_meals_per_week": patient.nonveg_meals_per_week or 3,
        "health_goals": list(patient.health_goals or []),
        "medical_conditions": list(patient.medical_conditions or []),
        "food_allergies": list(patient.food_allergies or []),
        "age": age,
    }


async def _regen_plan(patient: Patient, session: AsyncSession) -> tuple[bool, str]:
    """Generate + store a new plan. Rolls back partial writes on failure. Never raises."""
    try:
        from ..services.diet_plan_service import DietPlanService
        svc = DietPlanService()
        plan = await svc.generate_diet_plan(_build_meal_config_user_data(patient), session)
        await svc.store_diet_plan(plan, session=session)
        return True, ""
    except Exception as exc:
        await session.rollback()
        return False, str(exc)


async def _get_prefs_for_patient(patient_id: int, session: AsyncSession) -> tuple[list, list]:
    """Returns (pinned_dishes, blocked_dishes) lists joined with food_items."""
    result = await session.execute(
        select(PatientDishPreferences, FoodItem)
        .join(FoodItem, FoodItem.id == PatientDishPreferences.food_item_id)
        .where(PatientDishPreferences.patient_id == patient_id)
    )
    pinned, blocked = [], []
    for pref, fi in result.all():
        entry = {
            "food_id": fi.id,
            "recipe_name": fi.recipe_name,
            "calories_per_serving": float(fi.cal_per_serving),
        }
        if pref.preference_type == "pin":
            pinned.append(entry)
        else:
            blocked.append(entry)
    return pinned, blocked


async def _get_patient_for_doctor(patient_id: int, doctor_id: int, session: AsyncSession) -> Patient:
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == doctor_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ─── GET /api/v1/doctor/patients/{patient_id}/meal-config ─────────────────

@router.get("/patients/{patient_id}/meal-config")
async def get_meal_config(
    patient_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    config_result = await session.execute(
        select(PatientMealConfig).where(PatientMealConfig.patient_id == patient_id)
    )
    config = config_result.scalar_one_or_none()

    if config and config.meal_split_override:
        split = config.meal_split_override
    else:
        split = _DEFAULT_MEAL_SPLIT

    pinned, blocked = await _get_prefs_for_patient(patient_id, session)
    return {
        "meal_split": split,
        "buffer_pct": _BUFFER_PCT,
        "pinned_dishes": pinned,
        "blocked_dishes": blocked,
    }


# ─── PATCH /api/v1/doctor/patients/{patient_id}/meal-config ───────────────

@router.patch("/patients/{patient_id}/meal-config")
async def patch_meal_config(
    patient_id: int,
    body: MealConfigRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    patient = await _get_patient_for_doctor(patient_id, did, session)

    if body.meal_split is not None:
        required = {"Breakfast", "Lunch", "Dinner"}
        if set(body.meal_split.keys()) != required or \
                any(v <= 0 for v in body.meal_split.values()) or \
                sum(body.meal_split.values()) != 85:
            raise HTTPException(
                status_code=422,
                detail="Meal split must sum to 85. The remaining 15% is the passive buffer.",
            )

    if body.meal_split is None:
        existing = (await session.execute(
            select(PatientMealConfig).where(PatientMealConfig.patient_id == patient_id)
        )).scalar_one_or_none()
        if existing:
            await session.delete(existing)
        effective_split = _DEFAULT_MEAL_SPLIT
    else:
        stmt = pg_insert(PatientMealConfig).values(
            patient_id=patient_id,
            meal_split_override=body.meal_split,
        ).on_conflict_do_update(
            index_elements=["patient_id"],
            set_={
                "meal_split_override": body.meal_split,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)
        effective_split = body.meal_split

    # Commit config before attempting regen so config is safe even if regen fails
    await session.commit()

    plan_regenerated = False
    regen_error = ""
    if body.regenerate_plan:
        plan_regenerated, regen_error = await _regen_plan(patient, session)

    pinned, blocked = await _get_prefs_for_patient(patient_id, session)
    response = {
        "config_saved": True,
        "plan_regenerated": plan_regenerated,
        "meal_split": effective_split,
        "buffer_pct": _BUFFER_PCT,
        "pinned_dishes": pinned,
        "blocked_dishes": blocked,
    }
    if regen_error:
        response["error"] = regen_error
    return response


# ─── POST /api/v1/doctor/patients/{patient_id}/meal-config/pin ────────────

@router.post("/patients/{patient_id}/meal-config/pin")
async def pin_dish(
    patient_id: int,
    body: DishPrefRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    food = (await session.execute(
        select(FoodItem).where(FoodItem.id == body.food_id)
    )).scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    stmt = pg_insert(PatientDishPreferences).values(
        patient_id=patient_id,
        food_item_id=body.food_id,
        preference_type="pin",
        added_by_doctor_id=doctor.id,
    ).on_conflict_do_update(
        constraint="uq_patient_dish_preference",
        set_={"preference_type": "pin", "added_by_doctor_id": doctor.id},
    )
    await session.execute(stmt)

    pinned, _ = await _get_prefs_for_patient(patient_id, session)
    return {"pinned_dishes": pinned}


# ─── POST /api/v1/doctor/patients/{patient_id}/meal-config/block ──────────

@router.post("/patients/{patient_id}/meal-config/block")
async def block_dish(
    patient_id: int,
    body: DishPrefRequest,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    food = (await session.execute(
        select(FoodItem).where(FoodItem.id == body.food_id)
    )).scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    stmt = pg_insert(PatientDishPreferences).values(
        patient_id=patient_id,
        food_item_id=body.food_id,
        preference_type="block",
        added_by_doctor_id=doctor.id,
    ).on_conflict_do_update(
        constraint="uq_patient_dish_preference",
        set_={"preference_type": "block", "added_by_doctor_id": doctor.id},
    )
    await session.execute(stmt)

    _, blocked = await _get_prefs_for_patient(patient_id, session)
    return {"blocked_dishes": blocked}


# ─── DELETE /api/v1/doctor/patients/{patient_id}/meal-config/pin/{food_id} ─

@router.delete("/patients/{patient_id}/meal-config/pin/{food_id}")
async def unpin_dish(
    patient_id: int,
    food_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    pref = (await session.execute(
        select(PatientDishPreferences).where(
            PatientDishPreferences.patient_id == patient_id,
            PatientDishPreferences.food_item_id == food_id,
            PatientDishPreferences.preference_type == "pin",
        )
    )).scalar_one_or_none()
    if pref:
        await session.delete(pref)

    pinned, _ = await _get_prefs_for_patient(patient_id, session)
    return {"pinned_dishes": pinned}


# ─── DELETE /api/v1/doctor/patients/{patient_id}/meal-config/block/{food_id}

@router.delete("/patients/{patient_id}/meal-config/block/{food_id}")
async def unblock_dish(
    patient_id: int,
    food_id: int,
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    did = _doctor_id(request)
    await _get_patient_for_doctor(patient_id, did, session)

    pref = (await session.execute(
        select(PatientDishPreferences).where(
            PatientDishPreferences.patient_id == patient_id,
            PatientDishPreferences.food_item_id == food_id,
            PatientDishPreferences.preference_type == "block",
        )
    )).scalar_one_or_none()
    if pref:
        await session.delete(pref)

    _, blocked = await _get_prefs_for_patient(patient_id, session)
    return {"blocked_dishes": blocked}
