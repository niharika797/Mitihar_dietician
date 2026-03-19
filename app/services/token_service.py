"""
Token service — generates and manages Token 1 (permanent patient ID)
and Token 2 (monthly visit tracker).
"""
import random
import string
from datetime import datetime, timezone, timedelta


def _random_suffix(length: int = 5) -> str:
    """Uppercase alphanumeric random suffix."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_token_1(patient_id: int) -> str:
    """
    Generate a permanent Token 1 for a patient.
    Format: TKN1-PAT-XXXXX  (e.g. TKN1-PAT-00142)
    The patient_id is zero-padded to 5 digits.
    """
    return f"TKN1-PAT-{patient_id:05d}"


def generate_token_2() -> str:
    """
    Generate a fresh Token 2 for a new 30-day visit cycle.
    Format: TKN2-XXXXX  (e.g. TKN2-AB3K7)
    """
    return f"TKN2-{_random_suffix(5)}"


def token_1_expiry_from_now() -> datetime:
    """Return UTC datetime 30 days from now."""
    return datetime.now(timezone.utc) + timedelta(days=30)


def is_chargeable_visit(
    last_charged_at: datetime | None,
    visit_counter: int = 0,
    cycle_start: datetime | None = None,
) -> bool:
    """
    Determine whether a clinic visit should incur the ₹1,200 consultation charge.

    Rules:
    1. First visit (visit_counter == 0) within 15 days of cycle_start (Token 1
       activation) → FREE.  This is the initial consultation included in the
       ₹800/month subscription fee.  The patient has 15 days to use this free slot.

    2. First visit after 15 days from cycle_start → CHARGED ₹1,200.
       The patient delayed their initial consultation past the grace period.

    3. Subsequent visits (visit_counter > 0):
       - If > 15 days since last_charged_at → CHARGED ₹1,200.
       - If ≤ 15 days since last_charged_at → FREE (follow-up within grace window).

    The 15-day gap between charges prevents a doctor from billing a quick
    follow-up appointment at the same rate as a full consultation.
    """
    now = datetime.now(timezone.utc)

    def _to_utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    # ── Rule 1 & 2: First visit ever in this cycle ────────────────────────
    if visit_counter == 0:
        if cycle_start is None:
            return True  # No cycle info → charge (safe default)
        days_since_activation = (now - _to_utc(cycle_start)).days
        return days_since_activation > 15  # Free within first 15 days

    # ── Rule 3: Subsequent visits ─────────────────────────────────────────
    if last_charged_at is None:
        return True  # Should not happen for counter > 0, but charge if so
    return (now - _to_utc(last_charged_at)).days > 15
