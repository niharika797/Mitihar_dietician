from fastapi import APIRouter, HTTPException, Depends, Request
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from pydantic import BaseModel

from ..services.user_service import (
    create_patient, authenticate_patient, get_patient_by_email,
)
from ..core.security import create_access_token, verify_password
from ..core.config import settings
from ..core.database import get_db
from ..core.limiter import limiter
from ..schemas.user import UserCreate
from ..models.db_models import Doctor

router = APIRouter()


# ---------------------------------------------------------------------------
# Patient auth
# ---------------------------------------------------------------------------

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
):
    """Register a new patient."""
    try:
        patient_id = await create_patient(session, data=user_data.model_dump())
        return {
            "message": "User registered successfully",
            "user_id": patient_id,
        }
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
@limiter.limit("20/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """Patient login — return JWT tokens."""
    patient = await authenticate_patient(
        session, form_data.username, form_data.password
    )
    if not patient:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": patient.email,
        "role": "patient",
        "user_type": patient.user_type or "standalone",
        "sub_status": patient.subscription_status or "inactive",
        "patient_id": patient.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Refresh JWT token."""
    try:
        payload = jwt.decode(
            token_request.refresh_token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    patient = await get_patient_by_email(session, email)
    if not patient:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(
        data={
            "sub": patient.email,
            "role": "patient",
            "user_type": patient.user_type or "standalone",
            "sub_status": patient.subscription_status or "inactive",
            "patient_id": patient.id,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Doctor auth
# ---------------------------------------------------------------------------

@router.post("/doctor/login")
@limiter.limit("20/minute")
async def doctor_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """Doctor login — authenticate against doctors table, return JWT with role=doctor."""
    result = await session.execute(
        select(Doctor).where(Doctor.email == form_data.username)
    )
    doctor = result.scalars().first()

    if doctor is None or not verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not doctor.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token_data = {
        "sub": doctor.email,
        "role": "doctor",
        "user_type": "doctor",
        "doctor_id": doctor.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }