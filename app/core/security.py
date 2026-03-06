"""
Core security module — JWT creation + three role-based FastAPI dependencies.

Exports:
    create_access_token, verify_password, get_password_hash,
    get_current_patient, get_current_doctor, get_current_admin
"""

from datetime import datetime, timedelta
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
    Create a JWT.  Always embeds: sub, role, user_type, exp, iat, nbf.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Guarantee required claims are present
    to_encode.setdefault("role", "patient")
    to_encode.setdefault("user_type", "standalone")

    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


# ---------------------------------------------------------------------------
# Internal JWT decoder (shared by all role deps)
# ---------------------------------------------------------------------------

def _decode_jwt(token: str) -> dict:
    """Decode a JWT and return its payload. Raises HTTPException on failure."""
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
    Decode JWT → verify role==patient → check is_active.
    Subscription enforcement is handled by SubscriptionCheckMiddleware, not here.
    """
    from ..models.db_models import Patient  # avoid circular import

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