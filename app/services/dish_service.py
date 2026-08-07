"""Canonical-dish helpers — one source of truth for name normalization + dedup.

The uq_fi_canonical partial-unique index guarantees at most one CANONICAL
(is_verified, deleted_at IS NULL) food_items row per (name_normalized, slot_type,
diet_type). Every insert path must set name_normalized via normalize_dish_name() so
the row is covered by that index once it is approved.
"""
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import FoodItem


def normalize_dish_name(name: str) -> str:
    """lower + strip + collapse internal whitespace. Matches the SQL backfill and
    scripts/audit_dish_duplicates.py norm()."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


async def find_reusable_dish(
    session: AsyncSession, *, name: str, slot_type: str, diet_type: str, doctor_id: int | None
) -> FoodItem | None:
    """Return a live row the doctor can reuse instead of inserting a duplicate:
    the shared verified canonical (any doctor), else this doctor's own live row for the
    same canonical key (keeps 'add recipe' idempotent per doctor). None if neither exists.
    """
    nn = normalize_dish_name(name)
    canonical = (await session.execute(
        select(FoodItem).where(
            FoodItem.name_normalized == nn,
            FoodItem.slot_type == slot_type,
            FoodItem.diet_type == diet_type,
            FoodItem.is_verified.is_(True),
            FoodItem.deleted_at.is_(None),
        ).limit(1)
    )).scalars().first()
    if canonical is not None:
        return canonical
    if doctor_id is not None:
        return (await session.execute(
            select(FoodItem).where(
                FoodItem.name_normalized == nn,
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == diet_type,
                FoodItem.doctor_id == doctor_id,
                FoodItem.deleted_at.is_(None),
            ).order_by(FoodItem.id.desc()).limit(1)
        )).scalars().first()
    return None


async def get_assignable_dish(
    session: AsyncSession, *, food_id: int, doctor_id: int | None
) -> FoodItem | None:
    """The dish this doctor is allowed to put in front of a patient, or None.

    Mirrors the pool the generator serves from (meal_generator.py: is_verified AND
    deleted_at IS NULL), with one deliberate widening: a doctor may also assign their
    OWN not-yet-approved dish, the same allowance find_reusable_dish() makes.

    Rejects:
      - soft-deleted / merged-away dishes (Stage 6 losers), which otherwise leave
        dangling food_id references in the weekly_combos JSONB snapshot
      - unverified dishes owned by nobody or by another doctor -- the 6k_dataset seed
        backlog awaiting review, and test artifacts, must not reach a patient
    """
    dish = (await session.execute(
        select(FoodItem).where(
            FoodItem.id == food_id,
            FoodItem.deleted_at.is_(None),
        ).limit(1)
    )).scalars().first()
    if dish is None:
        return None
    if dish.is_verified:
        return dish
    if doctor_id is not None and dish.doctor_id == doctor_id:
        return dish
    return None


async def canonical_collision(
    session: AsyncSession, *, name_normalized: str, slot_type: str, diet_type: str, exclude_id: int
) -> FoodItem | None:
    """The verified+live canonical that already owns this key (excluding exclude_id), or None.
    Used at admin-approval time to block creating a second canonical."""
    return (await session.execute(
        select(FoodItem).where(
            FoodItem.name_normalized == name_normalized,
            FoodItem.slot_type == slot_type,
            FoodItem.diet_type == diet_type,
            FoodItem.is_verified.is_(True),
            FoodItem.deleted_at.is_(None),
            FoodItem.id != exclude_id,
        ).limit(1)
    )).scalars().first()
