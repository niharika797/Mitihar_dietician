"""
Refresh-token records: issue, rotate on use, detect reuse, revoke.

Every refresh token carries a unique `jti` and a `fam` (family) claim and has one row in
`refresh_tokens`. /auth/refresh calls claim(): the first use marks the row used and the caller
issues a child in the same family. Using the same token again after REFRESH_REUSE_GRACE_SECONDS
means someone else holds a copy, so every token of that user is revoked ("sign out everywhere").
Tokens issued before this existed have no jti; they are tracked from their first use by a hash
of the token (LEGACY_PREFIX) and can be used once, then replaced.
"""
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..core.security import create_access_token, create_refresh_token
from ..models.db_models import RefreshToken

_log = logging.getLogger(__name__)

LEGACY_PREFIX = "legacy:"


class RefreshRejected(Exception):
    """Refresh token cannot be used. reason: invalid | revoked | reuse (for logs only, never sent to the client)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _user_id(data: dict) -> int:
    return data[f"{data['role']}_id"]


async def issue_tokens(data: dict, session: Optional[AsyncSession] = None, family_id: Optional[str] = None) -> dict:
    """
    Issue an access + refresh pair and record the refresh token. Commits (on `session` when given,
    otherwise on a short session of its own) so the record exists before the client can use the token.
    """
    jti = uuid.uuid4().hex
    family = family_id or uuid.uuid4().hex
    access = create_access_token(
        data=data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_data = {"sub": data["sub"], "role": data["role"], "jti": jti, "fam": family}
    for key in ("patient_id", "doctor_id", "admin_id"):
        if key in data:
            refresh_data[key] = data[key]
    ttl = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh = create_refresh_token(data=refresh_data, expires_delta=ttl)

    row = RefreshToken(
        jti=jti,
        family_id=family,
        role=data["role"],
        user_id=_user_id(data),
        expires_at=datetime.now(timezone.utc) + ttl,
    )
    if session is None:
        async with AsyncSessionLocal() as own:
            own.add(row)
            await own.commit()
    else:
        session.add(row)
        await session.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def revoke_user(session: AsyncSession, role: str, user_id: int) -> None:
    """Revoke every live refresh token of one user. Caller commits."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.role == role, RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )


async def revoke_family_of(session: AsyncSession, jti: str) -> None:
    """Logout: revoke the family the given token belongs to. Unknown (legacy) tokens: nothing to do. Caller commits."""
    family = await session.scalar(select(RefreshToken.family_id).where(RefreshToken.jti == jti))
    if family:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )


async def delete_expired(session: AsyncSession) -> int:
    """Delete records that expired more than a day ago. Caller commits."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    result = await session.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff))
    return result.rowcount or 0


async def claim(session: AsyncSession, token: str, payload: dict) -> tuple[str, str]:
    """
    Use up a refresh token. `payload` is the already-verified JWT payload.
    Returns ("new", family) on first use: caller issues a child token in that family.
    Returns ("grace", family) on a repeat within the grace window: caller issues an access token only.
    Raises RefreshRejected otherwise. On reuse it revokes every token of the user and commits first.
    """
    now = datetime.now(timezone.utc)
    role = payload.get("role", "patient")
    jti = payload.get("jti")
    legacy = jti is None
    if legacy:
        jti = LEGACY_PREFIX + hashlib.sha256(token.encode("utf-8")).hexdigest()[:48]

    # Row lock: two simultaneous calls with one token are handled one after the other.
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.jti == jti).with_for_update())
    ).scalars().first()

    if row is None:
        user_id = payload.get(f"{role}_id")
        if not legacy or user_id is None:
            raise RefreshRejected("invalid")  # a jti we never issued (or already purged)
        row = RefreshToken(
            jti=jti,
            family_id=uuid.uuid4().hex,
            role=role,
            user_id=user_id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            used_at=now,
        )
        session.add(row)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()  # another request recorded this legacy token first: re-evaluate
            return await claim(session, token, payload)
        return "new", row.family_id

    if row.revoked_at is not None:
        raise RefreshRejected("revoked")

    if row.used_at is None:
        row.used_at = now
        await session.flush()
        return "new", row.family_id

    if (now - row.used_at).total_seconds() <= settings.REFRESH_REUSE_GRACE_SECONDS:
        return "grace", row.family_id

    await revoke_user(session, row.role, row.user_id)
    await session.commit()
    _log.warning(
        "refresh_token_reuse_detected role=%s user_id=%s family=%s: all sessions revoked",
        row.role, row.user_id, row.family_id,
    )
    raise RefreshRejected("reuse")
