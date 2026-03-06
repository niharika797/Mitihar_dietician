from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.user_service import get_current_user, update_patient, get_patient_by_id
from ..models.db_models import Patient
from ..schemas.user import UserUpdate, UserResponse
from ..core.database import get_db

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: Patient = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.get("/bmi")
async def get_user_bmi(current_user: Patient = Depends(get_current_user)):
    """Get current user's BMI."""
    if not current_user.height_cm or not current_user.weight_kg:
        raise HTTPException(status_code=400, detail="User height or weight is not set")
    height_m = float(current_user.height_cm) / 100
    bmi = float(current_user.weight_kg) / (height_m ** 2)
    return {"bmi": round(bmi, 2)}


@router.put("/me", response_model=UserResponse)
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

    return updated