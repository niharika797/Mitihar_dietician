"""
Unit tests for the doctor-flagged visit loop, both halves:
  * POST /doctor/patients/{patient_id}/flag-visit          (doctor flags)
  * POST /patients/pending-visits/{id}/respond             (patient answers)

The flow is the fraud-prevention path for a patient who cannot show Token 2
(phone forgotten or lost). Rather than charging the visit outright the doctor
creates a PendingVisitApproval that the patient must confirm from their own app
-- so a doctor cannot unilaterally record a visit that never happened.

Approval is a BILLING write: it increments PatientVisit.visit_counter, and
revenue is derived as SUM(visit_counter) * VISIT_CHARGE_INR with no invoice
table behind it. So the respond tests below are guarding money, not a status
field -- particularly the double-approve case.

DB-free by design: handlers are called directly with a mocked AsyncSession, so
this runs in CI alongside test_calculations.py / test_meal_generator.py without a
Postgres service container. Uses asyncio.run() rather than pytest-asyncio or the
anyio plugin -- neither is installed, and neither is worth adding for ten tests.

What is NOT covered here (needs the live-DB integration suite):
  * DoctorIsolationMiddleware actually injecting request.state.doctor_id
  * the real FK constraint on patient_visit_id
  * that the raise in the no-active-cycle path really rolls back the claimed
    row -- that is get_db's transaction behaviour, not visible to a mock
  * genuine DB-level concurrency; the double-approve test models the atomic
    UPDATE returning no row, it does not prove Postgres serialises the write
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# app.core.database raises at import time if DATABASE_URL is unset, and importing
# the router pulls it in. No connection is ever opened here -- the session is
# mocked -- so a placeholder is enough. Mirrors the env block in
# .github/workflows/ci.yml. setdefault so a real local .env value still wins.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "0" * 58)

from app.routers.doctor import flag_visit  # noqa: E402
from app.routers.patients import respond_to_pending_visit  # noqa: E402
from app.models.db_models import PendingVisitApproval  # noqa: E402
from app.services.token_service import VISIT_GRACE_DAYS  # noqa: E402


def _request(doctor_id=7):
    """Stand-in for the Request whose state DoctorIsolationMiddleware populates."""
    return SimpleNamespace(state=SimpleNamespace(doctor_id=doctor_id))


def _session(patient, visit):
    """AsyncSession mock returning `patient` then `visit` from successive execute()s.

    The handler runs two queries in order: the ownership-scoped Patient lookup,
    then the active PatientVisit lookup. Feeding results positionally keeps the
    mock honest about that sequence.
    """
    def _result(obj):
        scalars = MagicMock()
        scalars.first.return_value = obj
        wrapper = MagicMock()
        wrapper.scalars.return_value = scalars
        return wrapper

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_result(patient), _result(visit)])

    added: list = []

    def _add(obj):
        added.append(obj)

    async def _flush():
        # Real flush assigns the PK; downstream code reads pending.id.
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = 4242

    session.add = MagicMock(side_effect=_add)
    session.flush = AsyncMock(side_effect=_flush)
    session.added = added
    return session


def _patient(pid=1):
    return SimpleNamespace(id=pid, name="Test Patient", fcm_token=None)


def _doctor(name="Dr. Who"):
    return SimpleNamespace(id=7, name=name)


def test_flag_visit_rejects_patient_of_another_doctor():
    """Patient lookup is scoped by doctor_id, so a foreign patient reads as 404.

    This is the isolation guarantee -- a doctor must not be able to flag a visit
    against someone else's patient.
    """
    session = _session(patient=None, visit=None)

    with patch("app.routers.doctor.notify_visit_flagged") as notify:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(flag_visit(
                patient_id=999,
                body=SimpleNamespace(doctor_note=None),
                request=_request(),
                doctor=_doctor(),
                session=session,
            ))

    assert exc.value.status_code == 404
    assert session.add.call_count == 0, "must not create an approval row for a 404"
    assert notify.call_count == 0, "must not notify when the patient is not ours"


def test_flag_visit_creates_pending_approval_linked_to_active_cycle():
    """Happy path: creates a *pending* row linked to the open visit cycle."""
    now = datetime.now(timezone.utc)
    visit = SimpleNamespace(id=55, cycle_expiry=now + timedelta(days=10))
    session = _session(patient=_patient(), visit=visit)

    with patch("app.routers.doctor.notify_visit_flagged") as notify:
        result = asyncio.run(flag_visit(
            patient_id=1,
            body=SimpleNamespace(doctor_note="Patient forgot phone"),
            request=_request(doctor_id=7),
            doctor=_doctor(),
            session=session,
        ))

    assert len(session.added) == 1
    pending = session.added[0]
    assert isinstance(pending, PendingVisitApproval)
    assert pending.patient_id == 1
    assert pending.doctor_id == 7
    assert pending.patient_visit_id == 55, "should link to the active cycle"
    assert pending.doctor_note == "Patient forgot phone"

    # The whole point of the feature: nothing is charged or confirmed here.
    assert pending.status == "pending"

    assert result["pending_visit_id"] == 4242
    assert notify.call_count == 1, "patient must be told, or they can never approve"


def test_flag_visit_without_active_cycle_leaves_link_null():
    """No open PatientVisit -> patient_visit_id stays None rather than failing.

    patient_visit_id is nullable precisely so a flag can precede a cycle.
    """
    session = _session(patient=_patient(), visit=None)

    with patch("app.routers.doctor.notify_visit_flagged"):
        asyncio.run(flag_visit(
            patient_id=1,
            body=SimpleNamespace(doctor_note=None),
            request=_request(),
            doctor=_doctor(),
            session=session,
        ))

    pending = session.added[0]
    assert pending.patient_visit_id is None
    assert pending.status == "pending"


def test_flag_visit_survives_notification_failure():
    """A dead FCM path must not lose the approval row.

    notify_visit_flagged reaches Firebase. If a push failure propagated, the
    doctor's flag would be silently dropped and the visit never recordable.
    """
    session = _session(patient=_patient(), visit=None)

    with patch(
        "app.routers.doctor.notify_visit_flagged",
        side_effect=RuntimeError("FCM down"),
    ):
        try:
            asyncio.run(flag_visit(
                patient_id=1,
                body=SimpleNamespace(doctor_note=None),
                request=_request(),
                doctor=_doctor(),
                session=session,
            ))
        except RuntimeError:
            pytest.fail(
                "flag_visit propagated an FCM error; the approval row is created "
                "but the doctor sees a 500 and cannot tell the flag was saved"
            )

    assert len(session.added) == 1, "approval row must still be staged"


# ──────────────────────────────────────────────────────────────────────────
# POST /patients/pending-visits/{id}/respond — the approve/reject half
#
# Approving increments PatientVisit.visit_counter, and revenue is derived by
# summing that column, so these tests are guarding money rather than a status
# field. The double-approve case is the important one.
# ──────────────────────────────────────────────────────────────────────────


def _cycle(visit_counter=0, last_charged_at=None, days_ago=1):
    """An active visit cycle whose window has not expired."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=55,
        patient_id=1,
        doctor_id=7,
        cycle_start=now - timedelta(days=days_ago),
        cycle_expiry=now + timedelta(days=20),
        visit_counter=visit_counter,
        last_charged_at=last_charged_at,
    )


def _respond_session(claimed_row, cycle):
    """Mock for the respond handler: atomic UPDATE...RETURNING, then cycle SELECT.

    `claimed_row` is what the conditional UPDATE returns -- None models the row
    already having left 'pending' (or not being this patient's), which is
    exactly the double-approve case.
    """
    claim = MagicMock()
    claim.first.return_value = claimed_row

    cyc = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = cycle
    cyc.scalars.return_value = scalars

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[claim, cyc])
    session.flush = AsyncMock()
    return session


def _patient_obj(pid=1):
    return SimpleNamespace(id=pid, name="Test Patient", doctor_id=7)


def _claimed(visit_date=None):
    """Row shape returned by the RETURNING clause: (id, doctor_id, visit_date)."""
    return (99, 7, visit_date or datetime.now(timezone.utc))


def test_respond_approve_charges_and_increments_once():
    cycle = _cycle(visit_counter=2, last_charged_at=datetime.now(timezone.utc) - timedelta(days=40))
    session = _respond_session(_claimed(), cycle)

    with patch("app.services.audit_service.log_action", new=AsyncMock()):
        result = asyncio.run(respond_to_pending_visit(
            approval_id=99,
            body=SimpleNamespace(action="approve"),
            patient=_patient_obj(),
            session=session,
        ))

    assert result["status"] == "approved"
    assert result["charged"] is True
    assert cycle.visit_counter == 3, "counter must move exactly one step"
    assert cycle.last_charged_at is not None


def test_respond_approve_within_grace_does_not_charge():
    """Free-visit window: approving must not bill, and must not touch the counter."""
    cycle = _cycle(visit_counter=0, days_ago=VISIT_GRACE_DAYS - 1)
    session = _respond_session(_claimed(), cycle)

    with patch("app.services.audit_service.log_action", new=AsyncMock()):
        result = asyncio.run(respond_to_pending_visit(
            approval_id=99,
            body=SimpleNamespace(action="approve"),
            patient=_patient_obj(),
            session=session,
        ))

    assert result["charged"] is False
    assert cycle.visit_counter == 0, "a free visit must not increment the billing counter"


def test_respond_prices_by_visit_date_not_approval_time():
    """A visit flagged inside the grace window stays free however late it is approved.

    Cycle started 40 days ago; the visit happened on day 1 (free). Judging by
    wall-clock instead would make this chargeable purely because the patient
    took a while to tap approve.
    """
    cycle = _cycle(visit_counter=0, days_ago=40)
    visit_date = cycle.cycle_start + timedelta(days=1)
    session = _respond_session(_claimed(visit_date=visit_date), cycle)

    with patch("app.services.audit_service.log_action", new=AsyncMock()):
        result = asyncio.run(respond_to_pending_visit(
            approval_id=99,
            body=SimpleNamespace(action="approve"),
            patient=_patient_obj(),
            session=session,
        ))

    assert result["charged"] is False, "approval delay must not change the price"
    assert cycle.visit_counter == 0


def test_respond_double_approve_is_rejected_and_does_not_bill_twice():
    """The atomic claim returns nothing the second time, so no second charge.

    This is the revenue guard: without the conditional UPDATE, two taps both
    pass a read-then-write check and increment the counter twice.
    """
    cycle = _cycle(visit_counter=5)
    session = _respond_session(None, cycle)   # claim finds no 'pending' row

    with pytest.raises(HTTPException) as exc:
        asyncio.run(respond_to_pending_visit(
            approval_id=99,
            body=SimpleNamespace(action="approve"),
            patient=_patient_obj(),
            session=session,
        ))

    assert exc.value.status_code == 404
    assert cycle.visit_counter == 5, "a replayed approval must not bill again"


def test_respond_approve_without_active_cycle_is_blocked():
    """No live cycle -> 400, and the raise rolls back the claim so it stays pending."""
    session = _respond_session(_claimed(), None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(respond_to_pending_visit(
            approval_id=99,
            body=SimpleNamespace(action="approve"),
            patient=_patient_obj(),
            session=session,
        ))

    assert exc.value.status_code == 400
    assert "active visit cycle" in exc.value.detail


def test_respond_reject_never_charges():
    cycle = _cycle(visit_counter=2)
    session = _respond_session(_claimed(), cycle)

    result = asyncio.run(respond_to_pending_visit(
        approval_id=99,
        body=SimpleNamespace(action="reject"),
        patient=_patient_obj(),
        session=session,
    ))

    assert result["status"] == "rejected"
    assert result["charged"] is False
    assert cycle.visit_counter == 2, "rejection must never touch the billing counter"
