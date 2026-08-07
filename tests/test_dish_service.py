"""get_assignable_dish() — the gate on doctor-driven dish assignment.

The meal generator only ever serves dishes that are is_verified AND not soft-deleted
(meal_generator.py). Two doctor endpoints — plan dish swap and pin-dish — previously
did a bare `select(FoodItem).where(FoodItem.id == ...)`, so a doctor could put a
merged-away dish, an unreviewed seed dish, or a zero-ingredient test artifact
straight into a patient's plan. This pins the gate that closed that hole.

No DB required: get_assignable_dish() is exercised against a fake session so the
allow/deny decision is tested in isolation from query mechanics.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.services.dish_service import get_assignable_dish, normalize_dish_name


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def scalars(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    """Returns `row` for any query — get_assignable_dish filters deleted_at in SQL,
    so we hand back None to represent 'the soft-delete predicate matched nothing'."""

    def __init__(self, row):
        self._row = row

    async def execute(self, _stmt):
        return _FakeResult(self._row)


def _dish(**kw):
    return SimpleNamespace(**{
        "id": 1, "is_verified": True, "doctor_id": None, "deleted_at": None, **kw
    })


def _call(row, doctor_id):
    return asyncio.run(
        get_assignable_dish(_FakeSession(row), food_id=1, doctor_id=doctor_id)
    )


def test_verified_dish_is_assignable():
    dish = _dish(is_verified=True)
    assert _call(dish, doctor_id=7) is dish


def test_soft_deleted_dish_is_rejected():
    """The SQL filters deleted_at IS NULL, so a merged-away dish never comes back.
    This is what left dangling food_id refs in the weekly_combos snapshot."""
    assert _call(None, doctor_id=7) is None


def test_unverified_dish_owned_by_nobody_is_rejected():
    """The 6k_dataset seed backlog awaiting doctor review, and test artifacts."""
    assert _call(_dish(is_verified=False, doctor_id=None), doctor_id=7) is None


def test_unverified_dish_owned_by_another_doctor_is_rejected():
    assert _call(_dish(is_verified=False, doctor_id=99), doctor_id=7) is None


def test_doctor_may_assign_their_own_unverified_dish():
    """Matches the allowance find_reusable_dish() already makes, so doctors keep
    working with their own not-yet-approved recipes."""
    dish = _dish(is_verified=False, doctor_id=7)
    assert _call(dish, doctor_id=7) is dish


def test_no_doctor_context_still_rejects_unverified():
    assert _call(_dish(is_verified=False, doctor_id=7), doctor_id=None) is None


@pytest.mark.parametrize("raw,expected", [
    ("  Palak   Paneer ", "palak paneer"),
    ("PALAK PANEER", "palak paneer"),
    ("", ""),
])
def test_normalize_dish_name(raw, expected):
    assert normalize_dish_name(raw) == expected
