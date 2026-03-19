"""
Auth router — patient, doctor, admin login + MFA TOTP flow.

MFA Flow (doctor & admin):
  1. POST /doctor/login   →  if mfa_enabled=False  →  full JWT (existing behaviour)
                             if mfa_enabled=True   →  partial token (role=mfa_pending_doctor, exp=5min)
  2. POST /doctor/mfa-login  →  { partial_token, totp_code }  →  verifies TOTP → full JWT

Same pattern for /admin/mfa-login.

Backward-compatible: accounts with mfa_enabled=False go through exactly the same
code path as before — no change to the token structure they receive.
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.limiter import limiter
from ..core.security import create_access_token, create_refresh_token, get_current_doctor, get_current_admin, verify_password, get_password_hash
from ..models.db_models import Doctor, Patient
from ..schemas.user import UserCreate
from ..services.audit_service import log_action
from ..services.mfa_service import generate_mfa_secret, get_totp_uri, verify_totp
from ..services.user_service import authenticate_patient, create_patient, get_patient_by_email

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _patient_token_data(patient: Patient) -> dict:
    return {
        "sub": patient.email,
        "role": "patient",
        "user_type": patient.user_type or "standalone",
        "sub_status": patient.subscription_status or "inactive",
        "patient_id": patient.id,
    }


def _doctor_token_data(doctor: Doctor) -> dict:
    return {
        "sub": doctor.email,
        "role": "doctor",
        "user_type": "doctor",
        "doctor_id": doctor.id,
    }


def _admin_token_data(admin) -> dict:
    return {
        "sub": admin.email,
        "role": "admin",
        "user_type": "admin",
        "admin_id": admin.id,
    }


def _issue_tokens(data: dict) -> dict:
    """
    Issue access + refresh token pair.
    Access token: short-lived (15 min), token_type='access'.
    Refresh token: long-lived (7 days), token_type='refresh', minimal claims only.
    The two token types are structurally distinct — a refresh token is rejected
    by _decode_jwt() so it cannot be used to access protected endpoints.
    """
    access = create_access_token(
        data=data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Refresh token carries only the minimum needed to re-issue: sub + role + ids
    refresh_data = {
        "sub":  data["sub"],
        "role": data["role"],
    }
    for key in ("patient_id", "doctor_id", "admin_id"):
        if key in data:
            refresh_data[key] = data[key]
    refresh = create_refresh_token(
        data=refresh_data,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def _issue_partial_token(role_pending: str, user_id: int, email: str) -> str:
    """
    Issue a short-lived (5-minute) partial token for MFA step-2.
    Uses create_access_token with a non-standard role so middleware/deps reject
    it for all normal endpoints — it can only be used for /mfa-login.
    token_type stays 'access' so it isn't treated as a refresh token.
    """
    return create_access_token(
        data={"sub": email, "role": role_pending, "pending_id": user_id},
        expires_delta=timedelta(minutes=5),
    )


def _decode_partial_token(token: str, expected_role: str) -> dict:
    """Decode & validate a partial MFA token. Raises HTTPException on any failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA session token")
    if payload.get("role") != expected_role:
        raise HTTPException(status_code=401, detail="Invalid MFA session token role")
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Patient auth
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=dict)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Register a new patient.
    Rate-limited to 10/minute per IP — prevents account-creation floods.
    If doctor_code is provided: validates, consumes it, links patient to doctor immediately.
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

    # Issue email verification token immediately after registration
    verification_token = await _create_email_verification_token(session, patient_id)
    # TODO (Phase 7): send real email — for now log the link for dev testing
    import logging as _logging
    _logging.getLogger(__name__).info(
        f"[DEV] Email verification link for new patient: "
        f"/api/v1/auth/verify-email?token={verification_token}"
    )

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
            return {
                "message": "Registered successfully. Doctor code was invalid or expired — activate manually via /patients/activate.",
                "doctor_connected": False,
            }

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
            "doctor_connected": True,
        }

    return {
        "message": "User registered successfully",
        "doctor_connected": False,
    }


@router.post("/token")
@limiter.limit("20/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """Patient login — returns JWT tokens."""
    patient = await authenticate_patient(session, form_data.username, form_data.password)
    if not patient:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_tokens(_patient_token_data(patient))


# ─────────────────────────────────────────────────────────────────────────────
# Admin auth
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin login — email + password.
    If mfa_enabled=False → full JWT immediately.
    If mfa_enabled=True  → partial token (5 min); client must call /admin/mfa-login.
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

    if admin.mfa_enabled:
        partial = _issue_partial_token("mfa_pending_admin", admin.id, admin.email)
        return {"mfa_required": True, "partial_token": partial}

    tokens = _issue_tokens(_admin_token_data(admin))
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/api/v1/auth",
    )
    return tokens


class MFALoginRequest(BaseModel):
    partial_token: str
    totp_code: str = Field(..., min_length=6, max_length=6)


@router.post("/admin/mfa-login")
@limiter.limit("10/minute")
async def admin_mfa_login(
    request: Request,
    body: MFALoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Step-2 of admin MFA login.
    Validates the partial token from /admin/login + a 6-digit TOTP code.
    Returns full JWT on success.
    """
    from ..models.db_models import Admin as AdminModel

    payload = _decode_partial_token(body.partial_token, "mfa_pending_admin")
    admin_id: int = payload.get("pending_id")

    result = await session.execute(select(AdminModel).where(AdminModel.id == admin_id))
    admin = result.scalars().first()

    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account not found or deactivated")

    if not verify_totp(admin.mfa_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid or expired TOTP code")

    return _issue_tokens(_admin_token_data(admin))


# ─────────────────────────────────────────────────────────────────────────────
# Admin MFA setup endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/mfa-setup")
async def admin_mfa_setup(
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Generate and store a new TOTP secret for the admin.
    Returns an otpauth:// URI — client renders it as a QR code.
    MFA is NOT enabled yet; call /admin/mfa-confirm after scanning.
    """
    from ..models.db_models import Admin as AdminModel

    secret = generate_mfa_secret()
    uri = get_totp_uri(secret, admin.email)

    result = await session.execute(select(AdminModel).where(AdminModel.id == admin.id))
    admin_row = result.scalars().first()
    admin_row.mfa_secret = secret
    await session.flush()

    return {
        "message": "Scan this URI with Google Authenticator or Authy, then call /admin/mfa-confirm.",
        "totp_uri": uri,
    }


class MFAConfirmRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)


@router.post("/admin/mfa-confirm")
async def admin_mfa_confirm(
    body: MFAConfirmRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """
    Confirm MFA setup by verifying a live TOTP code.
    Sets mfa_enabled=True on the admin account.
    """
    from ..models.db_models import Admin as AdminModel

    result = await session.execute(select(AdminModel).where(AdminModel.id == admin.id))
    admin_row = result.scalars().first()

    if not admin_row.mfa_secret:
        raise HTTPException(status_code=400, detail="Run /admin/mfa-setup first")

    if not verify_totp(admin_row.mfa_secret, body.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code — try again")

    admin_row.mfa_enabled = True
    await session.flush()
    return {"message": "MFA enabled successfully for admin account"}


@router.post("/admin/mfa-disable")
async def admin_mfa_disable(
    body: MFAConfirmRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Disable MFA on admin account. Requires a valid TOTP code to confirm identity."""
    from ..models.db_models import Admin as AdminModel

    result = await session.execute(select(AdminModel).where(AdminModel.id == admin.id))
    admin_row = result.scalars().first()

    if not admin_row.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if not verify_totp(admin_row.mfa_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    admin_row.mfa_enabled = False
    admin_row.mfa_secret = None
    await session.flush()
    return {"message": "MFA disabled"}


# ─────────────────────────────────────────────────────────────────────────────
# Token refresh — cookie-based for doctor/admin, body-based fallback for patient
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """
    Refresh access token for doctor, admin, or patient.

    Doctor / Admin: reads refresh_token from the HttpOnly cookie set at login.
    Patient (legacy): reads refresh_token from JSON request body.
    Returns a new access_token. Re-issues the HttpOnly cookie for doctor/admin.
    """
    # 1. Try HttpOnly cookie first (doctor / admin path)
    refresh_tok: Optional[str] = request.cookies.get("refresh_token")

    # 2. Fallback to JSON body (patient path)
    if not refresh_tok:
        try:
            body = await request.json()
            refresh_tok = body.get("refresh_token")
        except Exception:
            pass

    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    # Decode and validate the refresh token
    try:
        payload = jwt.decode(refresh_tok, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        role: str = payload.get("role", "patient")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        # Reject access tokens being used as refresh tokens
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Token is not a refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Issue new tokens based on role
    if role == "doctor":
        result = await session.execute(select(Doctor).where(Doctor.email == email))
        doctor = result.scalars().first()
        if not doctor or not doctor.is_active:
            raise HTTPException(status_code=401, detail="Doctor account not found")
        tokens = _issue_tokens(_doctor_token_data(doctor))
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            path="/api/v1/auth",
        )
        return {"access_token": tokens["access_token"], "token_type": "bearer"}

    elif role == "admin":
        from ..models.db_models import Admin as AdminModel
        result = await session.execute(select(AdminModel).where(AdminModel.email == email))
        admin = result.scalars().first()
        if not admin or not admin.is_active:
            raise HTTPException(status_code=401, detail="Admin account not found")
        tokens = _issue_tokens(_admin_token_data(admin))
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            path="/api/v1/auth",
        )
        return {"access_token": tokens["access_token"], "token_type": "bearer"}

    else:
        # Patient path — legacy body-based refresh
        patient = await get_patient_by_email(session, email)
        if not patient:
            raise HTTPException(status_code=401, detail="Patient not found")
        access_token = create_access_token(
            data=_patient_token_data(patient),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access_token, "token_type": "bearer"}


# ─────────────────────────────────────────────────────────────────────────────
# Google OAuth — client-side ID token flow (mobile / SPA)
# ─────────────────────────────────────────────────────────────────────────────

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
    Client obtains ID token via Google SDK, sends it here.
    We verify signature + claims, upsert the patient, and return JWT.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="Google Sign-In is not configured on this server",
        )

    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError

    try:
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Malformed Google ID token: {exc}")

    google_sub: str = id_info["sub"]
    email: Optional[str] = id_info.get("email")
    name: str = id_info.get("name") or (email.split("@")[0] if email else "Google User")
    email_verified: bool = id_info.get("email_verified", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=400,
            detail="Google account must have a verified email address",
        )

    patient: Optional[Patient] = None

    result = await session.execute(select(Patient).where(Patient.google_id == google_sub))
    patient = result.scalars().first()

    if patient is None:
        result = await session.execute(select(Patient).where(Patient.email == email))
        patient = result.scalars().first()
        if patient is not None:
            # Existing email-password account being linked to Google for the first time
            patient.google_id = google_sub
            patient.is_email_verified = True  # Google already verified this email
            await session.flush()

    if patient is None:
        import secrets as _secrets
        new_patient_id = await create_patient(
            session,
            data={
                "email": email,
                "password": _secrets.token_hex(32),
                "name": name,
                "gender": "",
                "height": 0,
                "weight": 0,
                "activity_level": "S",
                "diet": "Vegetarian",
            },
        )
        result = await session.execute(select(Patient).where(Patient.id == new_patient_id))
        patient = result.scalars().first()
        patient.google_id = google_sub
        patient.is_email_verified = True  # Google already verified this email
        await session.flush()

    tokens = _issue_tokens(_patient_token_data(patient))
    tokens["is_new_user"] = patient.height_cm == 0
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# Doctor auth
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/doctor/login")
@limiter.limit("10/minute")
async def doctor_login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """
    Doctor login — email + password.
    If mfa_enabled=False → full JWT immediately.
    If mfa_enabled=True  → partial token (5 min); client must call /doctor/mfa-login.
    """
    result = await session.execute(select(Doctor).where(Doctor.email == form_data.username))
    doctor = result.scalars().first()

    if doctor is None or not verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not doctor.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    if doctor.mfa_enabled:
        partial = _issue_partial_token("mfa_pending_doctor", doctor.id, doctor.email)
        return {"mfa_required": True, "partial_token": partial}

    tokens = _issue_tokens(_doctor_token_data(doctor))
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/api/v1/auth",
    )
    return tokens


@router.post("/doctor/mfa-login")
@limiter.limit("10/minute")
async def doctor_mfa_login(
    request: Request,
    body: MFALoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Step-2 of doctor MFA login.
    Validates the partial token from /doctor/login + a 6-digit TOTP code.
    Returns full JWT on success.
    """
    payload = _decode_partial_token(body.partial_token, "mfa_pending_doctor")
    doctor_id: int = payload.get("pending_id")

    result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalars().first()

    if doctor is None or not doctor.is_active:
        raise HTTPException(status_code=401, detail="Doctor account not found or deactivated")

    if not verify_totp(doctor.mfa_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid or expired TOTP code")

    return _issue_tokens(_doctor_token_data(doctor))


# ─────────────────────────────────────────────────────────────────────────────
# Doctor MFA setup endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/doctor/mfa-setup")
async def doctor_mfa_setup(
    doctor=Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Generate and store a new TOTP secret for the doctor.
    Returns an otpauth:// URI — client renders it as a QR code.
    MFA is NOT enabled yet; call /doctor/mfa-confirm after scanning.
    """
    secret = generate_mfa_secret()
    uri = get_totp_uri(secret, doctor.email)

    result = await session.execute(select(Doctor).where(Doctor.id == doctor.id))
    doctor_row = result.scalars().first()
    doctor_row.mfa_secret = secret
    await session.flush()

    return {
        "message": "Scan this URI with Google Authenticator or Authy, then call /doctor/mfa-confirm.",
        "totp_uri": uri,
    }


@router.post("/doctor/mfa-confirm")
async def doctor_mfa_confirm(
    body: MFAConfirmRequest,
    doctor=Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """
    Confirm MFA setup by verifying a live TOTP code.
    Sets mfa_enabled=True on the doctor account.
    """
    result = await session.execute(select(Doctor).where(Doctor.id == doctor.id))
    doctor_row = result.scalars().first()

    if not doctor_row.mfa_secret:
        raise HTTPException(status_code=400, detail="Run /doctor/mfa-setup first")

    if not verify_totp(doctor_row.mfa_secret, body.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code — try again")

    doctor_row.mfa_enabled = True
    await session.flush()
    return {"message": "MFA enabled successfully for doctor account"}


@router.post("/doctor/mfa-disable")
async def doctor_mfa_disable(
    body: MFAConfirmRequest,
    doctor=Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db),
):
    """Disable MFA on doctor account. Requires a valid TOTP code to confirm identity."""
    result = await session.execute(select(Doctor).where(Doctor.id == doctor.id))
    doctor_row = result.scalars().first()

    if not doctor_row.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if not verify_totp(doctor_row.mfa_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    doctor_row.mfa_enabled = False
    doctor_row.mfa_secret = None
    await session.flush()
    return {"message": "MFA disabled"}


# ─────────────────────────────────────────────────────────────────────────────
# Logout — server-side cookie deletion
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/logout")
@limiter.limit("30/minute")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """
    Server-side logout for doctor and admin.

    What this does:
      1. Reads the actor identity from the Authorization Bearer token (access token).
         Falls back to the refresh_token cookie if the access token is absent/expired.
      2. Deletes the HttpOnly refresh_token cookie by expiring it server-side.
         The browser will drop the cookie immediately regardless of what JS does.
      3. Writes an audit log entry so the logout event is traceable.

    Why cookie deletion must happen server-side:
      HttpOnly cookies cannot be deleted by JavaScript — that’s the whole point.
      Only the server can expire them via Set-Cookie with Max-Age=0.
    """
    client_ip: str = request.client.host if request.client else "unknown"

    # ── 1. Identify the actor ────────────────────────────────────────────────
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None

    # Try access token first (sent as Authorization: Bearer)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
        try:
            payload = jwt.decode(
                raw_token, settings.SECRET_KEY, algorithms=["HS256"],
                options={"verify_exp": False},  # allow expired access tokens at logout
            )
            role = payload.get("role")
            if role == "doctor":
                actor_id = payload.get("doctor_id")
                actor_role = "doctor"
            elif role == "admin":
                actor_id = payload.get("admin_id")
                actor_role = "admin"
        except JWTError:
            pass  # token is malformed — still proceed with cookie deletion

    # Fall back to refresh token cookie if access token gave us nothing
    if actor_id is None:
        refresh_tok = request.cookies.get("refresh_token")
        if refresh_tok:
            try:
                payload = jwt.decode(
                    refresh_tok, settings.SECRET_KEY, algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                role = payload.get("role")
                if role == "doctor":
                    actor_id = payload.get("doctor_id")
                    actor_role = "doctor"
                elif role == "admin":
                    actor_id = payload.get("admin_id")
                    actor_role = "admin"
            except JWTError:
                pass

    # ── 2. Delete the HttpOnly cookie server-side ────────────────────────────
    # Path MUST match the path used in set_cookie() exactly — otherwise
    # the browser treats them as different cookies and ignores the deletion.
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
    )

    # ── 3. Audit log ────────────────────────────────────────────────────
    if actor_id and actor_role:
        await log_action(
            session,
            actor_id=actor_id,
            actor_role=actor_role,
            action="logout",
            detail={"ip": client_ip},
            ip_address=client_ip,
        )

    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# Email verification
# ─────────────────────────────────────────────────────────────────────────────

def _make_secure_token() -> str:
    """Generate a 64-character cryptographically secure URL-safe token."""
    import secrets
    return secrets.token_urlsafe(48)  # 48 bytes → 64-char base64url string


async def _create_email_verification_token(session: AsyncSession, patient_id: int) -> str:
    """
    Create (or replace) an email verification token for a patient.
    Returns the raw token string to be embedded in the verification link.
    Expires in 24 hours.
    """
    from ..models.db_models import EmailVerificationToken
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete

    token = _make_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Delete any existing token for this patient (only one active at a time)
    await session.execute(
        delete(EmailVerificationToken).where(
            EmailVerificationToken.patient_id == patient_id
        )
    )
    row = EmailVerificationToken(
        patient_id=patient_id,
        token=token,
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()
    return token


@router.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    token: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Confirm a patient's email address via the link emailed on registration.
    The link contains a one-time token: GET /api/v1/auth/verify-email?token=<token>

    On success: sets is_email_verified=True on the patient, deletes the token.
    On failure: returns 400 — token not found, already used, or expired.
    Always responds with a generic message to avoid oracle attacks.
    """
    from ..models.db_models import EmailVerificationToken, Patient as PatientModel
    from datetime import datetime, timezone
    from sqlalchemy import update as sa_update, delete

    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token,
            EmailVerificationToken.expires_at > now,
        )
    )
    evt = result.scalars().first()

    if evt is None:
        raise HTTPException(
            status_code=400,
            detail="Verification link is invalid or has expired. Request a new one.",
        )

    # Mark patient as verified and consume (delete) the token
    await session.execute(
        sa_update(PatientModel)
        .where(PatientModel.id == evt.patient_id)
        .values(is_email_verified=True)
    )
    await session.execute(
        delete(EmailVerificationToken).where(EmailVerificationToken.id == evt.id)
    )
    await session.flush()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification_email(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """
    Re-send the email verification link for the currently authenticated patient.
    Rate-limited to 3/minute — prevents verification-email flooding.
    The patient must be logged in (holds a valid access token).
    """
    from ..core.security import get_current_patient
    from ..models.db_models import Patient as PatientModel

    patient = await get_current_patient(
        token=request.headers.get("authorization", "").replace("Bearer ", "").strip(),
        session=session,
    )

    if patient.is_email_verified:
        return {"message": "Email is already verified."}

    token = await _create_email_verification_token(session, patient.id)

    # TODO (Phase 7): send real email via SendGrid / SES
    # For now: log the link so devs can test manually
    import logging
    logging.getLogger(__name__).info(
        f"[DEV] Email verification link for {patient.email}: "
        f"/api/v1/auth/verify-email?token={token}"
    )

    return {"message": "Verification email sent. Check your inbox."}


# ─────────────────────────────────────────────────────────────────────────────
# Password reset (forgot-password / reset-password)
# ─────────────────────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)

    @staticmethod
    def validate_password(v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Initiate the password-reset flow for a patient.

    Always returns HTTP 200 with the same message regardless of whether the
    email exists — this prevents user-enumeration attacks where an attacker
    can discover which emails are registered by checking responses.

    If the email IS registered: generates a 30-min expiring token, logs the
    reset link (real email sending wired in Phase 7).
    If the email is NOT registered: silently does nothing.
    """
    from ..models.db_models import PasswordResetToken
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete

    SAFE_RESPONSE = {"message": "If that email is registered, a reset link has been sent."}

    result = await session.execute(
        select(Patient).where(Patient.email == body.email)
    )
    patient = result.scalars().first()

    if patient is None:
        # No patient with this email — return safe response, do nothing
        return SAFE_RESPONSE

    token = _make_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )

    # Replace any existing reset token (only one active per patient)
    await session.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.patient_id == patient.id
        )
    )
    row = PasswordResetToken(
        patient_id=patient.id,
        token=token,
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()

    # TODO (Phase 7): send real email via SendGrid / SES
    import logging
    logging.getLogger(__name__).info(
        f"[DEV] Password reset link for {patient.email}: "
        f"/api/v1/auth/reset-password?token={token}  "
        f"(expires in {settings.RESET_TOKEN_EXPIRE_MINUTES} min)"
    )

    return SAFE_RESPONSE


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Complete the password-reset flow using the token from the reset email.

    Security properties:
    - Token is single-use: deleted immediately after a successful reset
    - Token expires in RESET_TOKEN_EXPIRE_MINUTES (30 min by default)
    - New password is validated against the same strength policy as registration
    - Returns a generic error for invalid/expired tokens (no oracle attacks)
    """
    from ..models.db_models import PasswordResetToken, Patient as PatientModel
    from datetime import datetime, timezone
    from sqlalchemy import update as sa_update, delete

    # Validate new password strength before hitting DB
    try:
        ResetPasswordRequest.validate_password(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == body.token,
            PasswordResetToken.expires_at > now,
        )
    )
    prt = result.scalars().first()

    if prt is None:
        raise HTTPException(
            status_code=400,
            detail="Reset link is invalid or has expired. Request a new one.",
        )

    # Update password and consume (delete) the token atomically
    new_hash = get_password_hash(body.new_password)
    await session.execute(
        sa_update(PatientModel)
        .where(PatientModel.id == prt.patient_id)
        .values(hashed_password=new_hash)
    )
    await session.execute(
        delete(PasswordResetToken).where(PasswordResetToken.id == prt.id)
    )
    await session.flush()

    return {"message": "Password reset successfully. You can now log in with your new password."}
