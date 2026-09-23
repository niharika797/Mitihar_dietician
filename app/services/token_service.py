"""
Token service — generates and manages Token 1 (permanent patient ID)
and Token 2 (monthly visit tracker).
"""
import random
import string
from datetime import datetime, timezone, timedelta

# ── Billing / cycle constants ─────────────────────────────────────────────
# These were literals scattered across patients.py, doctor.py and admin.py.
# Named here because they are the knobs a future multi-month plan turns.

VISIT_CHARGE_INR = 1500
"""Consultation charge per chargeable visit.

There is no invoice table — revenue is derived as
`SUM(patient_visits.visit_counter) * VISIT_CHARGE_INR` (admin.py). So
incrementing visit_counter IS the billing event, and this constant is the
only place the rate is defined. Docstrings here previously said ₹1,200
while admin.py computed ₹1,500; the ₹1,500 the money math used wins.
"""

CYCLE_DAYS = 30
"""Length of one visit cycle (one PatientVisit row).

A future 3/6-month plan is modelled as N *sequential* monthly cycles, not one
long cycle — that keeps is_chargeable_visit, the grace window, and admin.py's
revenue-by-cycle_start-month attribution all working unchanged. Do not stretch
this to 90/180; mint more cycles instead. See token_1_expiry_from_now, which
takes the subscription length separately.
"""

VISIT_GRACE_DAYS = 15
"""Free-visit window: the initial consultation is free within this many days of
cycle_start, and follow-ups within this many days of the last charge are free."""


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


def token_1_expiry_from_now(days: int = CYCLE_DAYS) -> datetime:
    """Return the UTC subscription expiry, `days` from now.

    `days` is the SUBSCRIPTION length, which is deliberately a separate number
    from CYCLE_DAYS (the visit-cycle length) even though both are 30 today. A
    future 6-month plan passes 180 here while visit cycles stay monthly.
    """
    return datetime.now(timezone.utc) + timedelta(days=days)


def is_chargeable_visit(
    last_charged_at: datetime | None,
    visit_counter: int = 0,
    cycle_start: datetime | None = None,
    now: datetime | None = None,
) -> bool:
    """
    Determine whether a clinic visit should incur the ₹1,500 consultation charge.

    Rules:
    1. First visit (visit_counter == 0) within VISIT_GRACE_DAYS of cycle_start
       (Token 1 activation) → FREE.  This is the initial consultation included
       in the monthly subscription fee.

    2. First visit after the grace window → CHARGED.
       The patient delayed their initial consultation past the grace period.

    3. Subsequent visits (visit_counter > 0):
       - If > VISIT_GRACE_DAYS since last_charged_at → CHARGED.
       - If ≤ VISIT_GRACE_DAYS since last_charged_at → FREE (follow-up).

    The grace gap between charges prevents a doctor from billing a quick
    follow-up appointment at the same rate as a full consultation.

    `now` is the instant the visit is judged against, defaulting to wall-clock.
    Pass it explicitly when the visit happened at a different time than the
    decision — e.g. a doctor-flagged visit approved by the patient days later
    must be priced as of the visit date, or the approval delay itself changes
    the price.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    def _to_utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    now = _to_utc(now)

    # ── Rule 1 & 2: First visit ever in this cycle ────────────────────────
    if visit_counter == 0:
        if cycle_start is None:
            return True  # No cycle info → charge (safe default)
        days_since_activation = (now - _to_utc(cycle_start)).days
        return days_since_activation > VISIT_GRACE_DAYS

    # ── Rule 3: Subsequent visits ─────────────────────────────────────────
    if last_charged_at is None:
        return True  # Should not happen for counter > 0, but charge if so
    return (now - _to_utc(last_charged_at)).days > VISIT_GRACE_DAYS
