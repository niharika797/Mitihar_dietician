from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.user_service import get_current_user, update_patient, get_patient_by_id
from ..models.db_models import Patient
from ..schemas.user import UserUpdate
from ..schemas.patients import PatientProfileResponse
from ..core.database import get_db
from ..core.limiter import limiter
from ..core.security import verify_password

router = APIRouter()


@router.get("/me", response_model=PatientProfileResponse)
@limiter.limit("100/minute")
async def get_user_profile(request: Request, current_user: Patient = Depends(get_current_user)):
    """Get current user full profile — includes subscription, token, disclaimer status."""
    return current_user


@router.get("/bmi")
async def get_user_bmi(current_user: Patient = Depends(get_current_user)):
    """Get current user's BMI."""
    if not current_user.height_cm or not current_user.weight_kg:
        raise HTTPException(status_code=400, detail="User height or weight is not set")
    height_m = float(current_user.height_cm) / 100
    bmi = float(current_user.weight_kg) / (height_m ** 2)
    return {"bmi": round(bmi, 2)}


@router.put("/me", response_model=PatientProfileResponse)
async def update_user_profile(
    update_data: UserUpdate,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update current user profile. Auto-recalculates BMI/BMR/TDEE if weight or height changes."""
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        return current_user

    # Map schema field names to ORM column names
    field_map = {
        "height": "height_cm",
        "weight": "weight_kg",
        "diet": "diet_type",
    }
    mapped = {field_map.get(k, k): v for k, v in data.items()}

    success = await update_patient(session, current_user.id, mapped)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    updated = await get_patient_by_id(session, current_user.id)

    # Auto-recalculate BMI/BMR/TDEE if any body metric changed
    recalc_triggers = {"height_cm", "weight_kg", "activity_level"}
    diet_triggers = {"height_cm", "weight_kg", "activity_level", "diet_type", "health_condition", "region", "target_weight_kg", "diabetes_status", "gym_goal"}
    
    if recalc_triggers.intersection(mapped.keys()):
        if updated.date_of_birth:
            from datetime import date as _date
            dob = updated.date_of_birth
            today = _date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            age = 30  # fallback until date_of_birth is set via onboarding

        from ..services.meal_generator.calculations import (
            calculate_bmr, calculate_tdee, calculate_bmi,
        )
        from sqlalchemy import update as sa_update
        from ..models.db_models import Patient as PatientModel

        new_bmr = calculate_bmr(
            updated.gender,
            float(updated.weight_kg),
            float(updated.height_cm),
            age,
        )
        new_tdee = calculate_tdee(new_bmr, updated.activity_level)
        new_bmi = calculate_bmi(float(updated.height_cm), float(updated.weight_kg))

        await session.execute(
            sa_update(PatientModel)
            .where(PatientModel.id == updated.id)
            .values(
                bmi=round(new_bmi, 2),
                bmr=round(new_bmr, 2),
                tdee=round(new_tdee, 2),
            )
        )
        await session.flush()
        updated = await get_patient_by_id(session, updated.id)

    if diet_triggers.intersection(mapped.keys()):
        from ..services.diet_plan_service import DietPlanService
        
        diet_service = DietPlanService()
        
        if updated.date_of_birth:
            from datetime import date as _date
            dob = updated.date_of_birth
            today = _date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            age = 30
            
        user_data = {
            "id": updated.id,
            "age": age,
            "gender": updated.gender,
            "weight": float(updated.weight_kg) if updated.weight_kg else 70.0,
            "height": float(updated.height_cm) if updated.height_cm else 170.0,
            "diet": updated.diet_type or "Anything",
            "health_state": updated.health_condition or "Healthy",
            "region": updated.region or "none",
            "target_weight": float(updated.target_weight_kg) if getattr(updated, "target_weight_kg", None) else None,
            "activity_level": getattr(updated, "activity_level", "Lightly Active"),
            "tdee": float(updated.tdee) if getattr(updated, "tdee", None) else 2000.0,
        }
        
        try:
            new_plan = await diet_service.generate_diet_plan(user_data, session)
            await diet_service.store_diet_plan(new_plan, session)
            print("Auto-regenerated diet plan upon profile update")
        except Exception as e:
            print(f"Failed to auto-generate diet plan: {e}")

    return updated

# ─── DELETE /api/v1/users/me ──────────────────────────────────────────────────
#
# Patient self-delete — right to erasure, initiated by the patient themselves.
# Requires password confirmation to prevent accidental or unauthorised deletion.
#
# What happens:
#   1. Password is verified against the stored bcrypt hash.
#   2. PII is anonymised (name, email, phone, health arrays).
#   3. All associated data is hard-deleted: MealLog, ProgressLog,
#      ClinicalNote, Recommendation.
#   4. The patient row itself is kept for aggregate stats but is fully anonymised.
#      The original email is freed so the same address can be re-registered.
#
# Google OAuth patients cannot use this endpoint — they have no real password.
# They should contact support for manual erasure.

class NotificationPreferencesBody(BaseModel):
    preferences: dict


@router.get("/me/notification-preferences")
async def get_notification_preferences(
    current_user: Patient = Depends(get_current_user),
):
    """Return the patient's saved notification preference flags."""
    return current_user.notification_preferences or {}


@router.post("/me/notification-preferences")
async def update_notification_preferences(
    body: NotificationPreferencesBody,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Merge incoming preference flags into the patient's notification_preferences JSONB."""
    from sqlalchemy import update as sa_update

    merged = {**(current_user.notification_preferences or {}), **body.preferences}
    await session.execute(
        sa_update(Patient)
        .where(Patient.id == current_user.id)
        .values(notification_preferences=merged)
    )
    await session.flush()
    return merged


class DeleteAccountRequest(BaseModel):
    password: str


@router.delete("/me")
async def delete_my_account(
    body: DeleteAccountRequest,
    current_user: Patient = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update as sa_update, delete as sa_delete
    from ..models.db_models import MealLog, ProgressLog, ClinicalNote, Recommendation

    patient_id = current_user.id

    # ── Step 1: Reject Google OAuth accounts ─────────────────────────────
    # Google patients have a random 64-char hex as their password — there is
    # no real password to verify. Direct them to contact support instead.
    if getattr(current_user, "google_id", None):
        raise HTTPException(
            status_code=400,
            detail="This account uses Google Sign-In. Please contact support to delete it.",
        )

    # ── Step 2: Verify the password ───────────────────────────────────────
    if not current_user.hashed_password or not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password. Please try again.",
        )

    # ── Step 3: Anonymise PII ─────────────────────────────────────────────
    await session.execute(
        sa_update(Patient)
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

    # ── Step 4: Cascade delete all associated data ────────────────────────
    await session.execute(sa_delete(MealLog).where(MealLog.patient_id == patient_id))
    await session.execute(sa_delete(ProgressLog).where(ProgressLog.patient_id == patient_id))
    await session.execute(sa_delete(ClinicalNote).where(ClinicalNote.patient_id == patient_id))
    await session.execute(sa_delete(Recommendation).where(Recommendation.patient_id == patient_id))

    await session.flush()
    return {"message": "Account deleted successfully."}
