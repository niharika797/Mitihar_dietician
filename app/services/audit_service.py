"""
Audit log service — write-only, fire-and-forget.
All writes are wrapped in try/except so audit failures never break the main request.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.db_models import AuditLog

_log = logging.getLogger(__name__)


async def log_action(
    session: AsyncSession,
    *,
    actor_id: int,
    actor_role: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Write an audit log entry. Never raises — failures are logged and swallowed.
    Call this AFTER the main operation has succeeded and session.flush() has run.
    """
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail or {},
            ip_address=ip_address,
        )
        session.add(entry)
        await session.flush()
    except Exception as exc:
        _log.error(f"Audit log failed: {exc}", exc_info=True)
