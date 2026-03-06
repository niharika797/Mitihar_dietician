from fastapi import APIRouter, Depends
from datetime import date
from ..services.user_service import get_current_user
from ..models.db_models import Patient
from ..services.meal_generator.calculations import calculate_bmr, calculate_tdee, calculate_bmi

router = APIRouter()


def _get_age(patient: Patient) -> int:
    """Derive age from date_of_birth; fallback 30 if not set."""
    if patient.date_of_birth:
        today = date.today()
        dob = patient.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return 30


@router.get("/bmr")
async def get_bmr(current_user: Patient = Depends(get_current_user)):
    bmr = calculate_bmr(
        current_user.gender,
        float(current_user.weight_kg),
        float(current_user.height_cm),
        _get_age(current_user),
    )
    return {"bmr": round(bmr, 2)}


@router.get("/tdee")
async def get_tdee(current_user: Patient = Depends(get_current_user)):
    bmr = calculate_bmr(
        current_user.gender,
        float(current_user.weight_kg),
        float(current_user.height_cm),
        _get_age(current_user),
    )
    tdee = calculate_tdee(bmr, current_user.activity_level)
    return {"tdee": round(tdee, 2)}


@router.get("/bmi")
async def get_bmi(current_user: Patient = Depends(get_current_user)):
    bmi = calculate_bmi(float(current_user.height_cm), float(current_user.weight_kg))
    return {"bmi": round(bmi, 2)}
