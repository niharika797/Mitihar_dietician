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
    await session.refresh(rec)
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
async def estimate_recipe_nutrition(
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
