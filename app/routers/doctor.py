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
    MealLog, ProgressLog, ClinicalNote, FoodItem,
)
from ..schemas.doctor import (
    PatientSummary, PaginatedPatients, RecommendationDetail,
    PlanOverrideRequest, PatientRequestDetail, RejectRequest,
    GenerateCodesRequest, SubscriptionCodeDetail,
    MealLogEntry, PatientProgressEntry, PatientLogsResponse, PatientProgressResponse,
    ClinicalNoteCreate, ClinicalNoteResponse, MealPlanNoteRequest,
    FoodItemSummary, RecipeCreateRequest, RecipeAssignRequest,
    DoctorDashboardStats,
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
        if meal.get("Date") == body.meal_date and meal.get("Meal Type") == body.meal_type:
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


# ─── GET /api/v1/doctor/recipes ───────────────────────────────────────────

@router.get("/recipes", response_model=list[FoodItemSummary])
async def browse_recipes(
    request: Request,
    diet_type: Optional[str] = Query(default=None),
    meal_time: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Browse the food database. Supports optional filters and pagination."""
    stmt = select(FoodItem).where(FoodItem.is_verified == True)

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
    Doctor adds a new recipe to the food database.
    Saved with source='doctor', is_verified=False (pending admin approval).
    Once admin approves it (PATCH /admin/food/{id}/approve), it becomes available to all patients.
    """
    food = FoodItem(
        recipe_name=body.recipe_name,
        slot_type=body.slot_type,
        cal_per_serving=body.cal_per_serving,
        protein_per_serving=body.protein_per_serving,
        carbs_per_serving=body.carbs_per_serving,
        fat_per_serving=body.fat_per_serving,
        fiber_per_serving=body.fiber_per_serving,
        diet_type=body.diet_type,
        meal_time_tags=body.meal_time_tags,
        plan_type_tags=body.plan_type_tags,
        ingredients=body.ingredients,
        region_tags=body.region_tags,
        source="doctor",
        is_verified=False,
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

    # Verify food item exists
    food_result = await session.execute(select(FoodItem).where(FoodItem.id == recipe_id))
    food = food_result.scalars().first()
    if food is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Build the meal object to inject
    new_meal = {
        "Date": body.meal_date,
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


# ─── GET /api/v1/doctor/dashboard ─────────────────────────────────────────

@router.get("/dashboard", response_model=DoctorDashboardStats)
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
