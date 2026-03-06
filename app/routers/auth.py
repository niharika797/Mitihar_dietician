from fastapi import APIRouter, HTTPException, Depends, Request
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from pydantic import BaseModel
from typing import Optional

from ..services.user_service import (
    create_patient, authenticate_patient, get_patient_by_email,
)
from ..core.security import create_access_token, verify_password, get_password_hash
from ..core.config import settings
from ..core.database import get_db
from ..core.limiter import limiter
from ..schemas.user import UserCreate
from ..models.db_models import Doctor, Patient

router = APIRouter()


# ---------------------------------------------------------------------------
# Patient auth
# ---------------------------------------------------------------------------

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a new patient.
    If doctor_code is provided: validates it, consumes it, and links patient to doctor immediately.
    If no doctor_code: standalone patient with inactive subscription.
    """
    from ..models.db_models import SubscriptionCode, Patient as PatientModel
    from datetime import datetime, timezone as _tz
    from sqlalchemy import update as sa_update

    data = user_data.model_dump()
    doctor_code = data.pop("doctor_code", None)

    try:
        patient_id = await create_patient(session, data=data)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If a doctor code was provided, validate and consume it immediately
    if doctor_code:
        now = datetime.now(_tz.utc)
        code_result = await session.execute(
            select(SubscriptionCode).where(
                SubscriptionCode.code == doctor_code,
                SubscriptionCode.is_used == False,
                SubscriptionCode.expires_at > now,
            )
        )
        code_row = code_result.scalars().first()

        if code_row is None:
            # Registration succeeded but code is invalid — do not roll back.
            # Return success with a warning. Patient can activate later via /activate.
            return {
                "message": "Registered successfully. Doctor code was invalid or expired — activate manually via /patients/activate.",
                "user_id": patient_id,
                "doctor_connected": False,
            }

        # Consume code and activate
        code_row.is_used = True
        code_row.used_by_patient_id = patient_id
        code_row.used_at = now

        await session.execute(
            sa_update(PatientModel)
            .where(PatientModel.id == patient_id)
            .values(
                doctor_id=code_row.doctor_id,
                user_type="doctor_assigned",
                subscription_status="active",
            )
        )
        await session.flush()
        return {
            "message": "Registered and connected to doctor successfully.",
            "user_id": patient_id,
            "doctor_connected": True,
        }

    return {
        "message": "User registered successfully",
        "user_id": patient_id,
        "doctor_connected": False,
    }


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


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

@router.post("/admin/login")
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin login — email + password. Returns JWT with role=admin.
    MFA verification is checked client-side for now (full TOTP in security sprint).
    """
    from ..models.db_models import Admin as AdminModel
    result = await session.execute(
        select(AdminModel).where(AdminModel.email == form_data.username)
    )
    admin = result.scalars().first()

    if admin is None or not verify_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token_data = {
        "sub": admin.email,
        "role": "admin",
        "user_type": "admin",
        "admin_id": admin.id,
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
# Google OAuth — client-side ID token flow (mobile / SPA)
# ---------------------------------------------------------------------------

class GoogleTokenRequest(BaseModel):
    id_token: str


@router.post("/google/verify")
@limiter.limit("20/minute")
async def google_verify(
    request: Request,
    body: GoogleTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Mobile / SPA Google Sign-In endpoint.

    The client uses the Google Sign-In SDK to obtain an ID token, then
    sends it here. We verify the token's signature against Google's public
    keys (via google-auth library), extract the stable `sub` identifier and
    profile fields, upsert the patient, and return the same JWT structure as
    the standard /token endpoint.

    Security guarantees:
      - Signature verified against Google's live public keys
      - `aud` claim checked against our GOOGLE_CLIENT_ID  → rejects tokens
        issued for other apps
      - `exp` enforced — expired tokens are rejected
      - Account lookup uses `google_id` (stable sub) first, email fallback
        for patients who already registered via password
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="Google Sign-In is not configured on this server",
        )

    # ── 1. Verify the ID token signature + claims ─────────────────────────
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError

    try:
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,   # tolerate minor clock drift
        )
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Google ID token: {exc}",
        )
    except ValueError as exc:
        # google-auth raises ValueError for malformed tokens
        raise HTTPException(
            status_code=401,
            detail=f"Malformed Google ID token: {exc}",
        )

    # ── 2. Extract verified claims ────────────────────────────────────────
    google_sub: str = id_info["sub"]           # stable, immutable user identifier
    email: Optional[str] = id_info.get("email")
    name: str = id_info.get("name") or (email.split("@")[0] if email else "Google User")
    email_verified: bool = id_info.get("email_verified", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=400,
            detail="Google account must have a verified email address",
        )

    # ── 3. Upsert patient ─────────────────────────────────────────────────
    # Lookup order:
    #   a) by google_id  → returning Google user, fastest path
    #   b) by email      → existing password-registered user; link their account
    #   c) neither       → new user, create row

    patient: Optional[Patient] = None

    # (a) google_id lookup
    result = await session.execute(
        select(Patient).where(Patient.google_id == google_sub)
    )
    patient = result.scalars().first()

    if patient is None:
        # (b) email lookup — existing password account
        result = await session.execute(
            select(Patient).where(Patient.email == email)
        )
        patient = result.scalars().first()

        if patient is not None:
            # Link Google identity to the existing account (one-time operation)
            patient.google_id = google_sub
            await session.flush()

    if patient is None:
        # (c) Brand-new user — create a minimal Patient row
        import secrets as _secrets
        random_pw = _secrets.token_hex(32)   # 64-char hex, not usable for login
        new_patient_id = await create_patient(
            session,
            data={
                "email": email,
                "password": random_pw,
                "name": name,
                "gender": "",
                "height": 0,
                "weight": 0,
                "activity_level": "S",
                "diet": "Vegetarian",
            },
        )
        result = await session.execute(
            select(Patient).where(Patient.id == new_patient_id)
        )
        patient = result.scalars().first()
        patient.google_id = google_sub
        await session.flush()

    # ── 4. Build JWT — identical structure to /token ──────────────────────
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
        "is_new_user": patient.height_cm == 0,  # hint for client: show onboarding
    }


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