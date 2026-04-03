"""
Core security module — JWT creation + three role-based FastAPI dependencies.

Exports:
    create_access_token, verify_password, get_password_hash,
    get_current_patient, get_current_doctor, get_current_admin
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

# Monkeypatch bcrypt for passlib compatibility
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": bcrypt.__version__})

from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a short-lived access JWT (token_type='access').
    Always embeds: sub, role, user_type, token_type, exp, iat, nbf.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.setdefault("role", "patient")
    to_encode.setdefault("user_type", "standalone")
    to_encode.setdefault("token_type", "access")  # distinguishes from refresh tokens

    to_encode.update({"exp": expire, "iat": now, "nbf": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a long-lived refresh JWT (token_type='refresh').
    Structurally separate from access tokens — cannot be used as an access token.
    Carries minimal claims: only sub, role, and identifiers needed for re-issuance.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))

    to_encode.setdefault("role", "patient")
    to_encode["token_type"] = "refresh"  # always override — never allow access payload as refresh

    to_encode.update({"exp": expire, "iat": now, "nbf": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


# ---------------------------------------------------------------------------
# Internal JWT decoder (shared by all role deps)
# ---------------------------------------------------------------------------

def _decode_jwt(token: str) -> dict:
    """
    Decode a JWT and return its payload. Raises HTTPException on failure.
    Explicitly rejects refresh tokens — they must never be used as access tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_iat": True, "verify_nbf": True},
        )
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
            )
        # Prevent refresh tokens from being used as access tokens
        if payload.get("token_type") == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used for API access",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Role-based dependencies
# ---------------------------------------------------------------------------

async def get_current_patient(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
):
    """
    Decode JWT → verify role==patient → check is_active → optional email-verification gate
    → reject tokens issued before the last password reset (stateless session invalidation).
    Subscription enforcement is handled by SubscriptionCheckMiddleware, not here.
    """
    from ..models.db_models import Patient  # avoid circular import
    from datetime import timezone

    payload = _decode_jwt(token)

    if payload.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient role required",
        )

    email: str = payload["sub"]
    result = await session.execute(select(Patient).where(Patient.email == email))
    patient = result.scalars().first()

    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if not patient.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    # T1-5: Email verification gate (only enforced when flag is True)
    if settings.REQUIRE_EMAIL_VERIFICATION and not patient.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Check your inbox or request a new verification link.",
        )

    # T1-7: Stateless session invalidation — reject tokens issued before last password reset.
    # Protects against a session thief continuing to use a stolen token after a password change.
    if patient.password_changed_at is not None:
        token_iat = payload.get("iat", 0)
        changed_at_ts = patient.password_changed_at.replace(tzinfo=timezone.utc).timestamp() \
            if patient.password_changed_at.tzinfo is None \
            else patient.password_changed_at.timestamp()
        if token_iat < changed_at_ts:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated by password change. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return patient


async def get_current_doctor(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
):
    """Decode JWT → verify role==doctor → check is_active."""
    from ..models.db_models import Doctor

    payload = _decode_jwt(token)

    if payload.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor role required",
        )

    email: str = payload["sub"]
    result = await session.execute(select(Doctor).where(Doctor.email == email))
    doctor = result.scalars().first()

    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    if not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    return doctor


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
):
    """Decode JWT → verify role==admin → check is_active."""
    from ..models.db_models import Admin

    payload = _decode_jwt(token)

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    email: str = payload["sub"]
    result = await session.execute(select(Admin).where(Admin.email == email))
    admin = result.scalars().first()

    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    return admin