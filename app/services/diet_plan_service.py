"""
Diet-plan service — PostgreSQL via AsyncSession + Recommendation ORM.
"""

from typing import Dict, Optional
from datetime import datetime, date

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from ..schemas.diet_plan import DietPlanResponse as DietPlan
from ..models.db_models import Recommendation
from ..core.config import settings
from .meal_generator.meal_generator import meal_generator


class ActivityLevel(str, Enum):
    SEDENTARY = "S"
    LIGHTLY_ACTIVE = "LA"
    MODERATELY_ACTIVE = "MA"
    VERY_ACTIVE = "VA"
    SUPER_ACTIVE = "SA"

class DietType(str, Enum):
    VEGETARIAN = "Vegetarian"
    NON_VEGETARIAN = "Non-Vegetarian"

class HealthCondition(str, Enum):
    HEALTHY = "Healthy"
    DIABETIC = "Diabetic-Friendly"
    GYM = "Gym-Friendly"

class region(str, Enum):
    East = "East"
    South = "South"
    West = "West"
    North = "North"
    none = "none"


class DietPlanService:

    # ------------------------------------------------------------------
    # Generation (unchanged — delegates to meal_generator)
    # ------------------------------------------------------------------

    async def generate_diet_plan(self, user_data: Dict, session: AsyncSession) -> DietPlan:
        """Generate personalised diet plan using nutritional science principles."""
        # ── Cross-week variety: load food IDs from last 2 plans ─────────────
        try:
            past_result = await session.execute(
                select(Recommendation.used_food_ids)
                .where(
                    Recommendation.patient_id == int(user_data["id"]),
                    Recommendation.used_food_ids.isnot(None),
                )
                .order_by(Recommendation.created_at.desc())
                .limit(2)
            )
            prior_ids: set[int] = set()
            for row in past_result.all():
                if row[0]:
                    prior_ids.update(int(x) for x in row[0])
            if prior_ids:
                user_data = {**user_data, "prior_used_food_ids": list(prior_ids)}
        except Exception:
            pass  # Non-fatal — generation proceeds without cross-week memory

        meal_plan = await meal_generator.generate_meal_plan(user_data, session)
        return DietPlan(
            user_id=str(user_data["id"]),
            created_at=datetime.now(),
            meals=meal_plan.get("meals", []),
            ingredient_checklist=meal_plan.get("ingredient_checklist", []),
            used_food_ids=meal_plan.get("used_food_ids", []),
            version=1,
        )

    # ------------------------------------------------------------------
    # CRUD — PostgreSQL recommendations table
    # ------------------------------------------------------------------

    async def store_diet_plan(self, diet_plan: DietPlan, *, session: AsyncSession) -> int:
        """
        Soft-delete any existing active plan, then insert a new one.
        New plan version = previous version + 1 (so version history is trackable).
        Returns the new recommendation id.
        """
        # Find current active plan to read its version before soft-deleting
        existing_result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == int(diet_plan.user_id),
                Recommendation.is_active == True,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        existing = existing_result.scalars().first()

        next_version = 1
        if existing is not None:
            next_version = (existing.version or 1) + 1
            existing.is_active = False  # soft-delete previous plan
            await session.flush()

        rec = Recommendation(
            patient_id=int(diet_plan.user_id),
            week_start_date=date.today(),
            meals=diet_plan.meals,
            ingredient_checklist=diet_plan.ingredient_checklist,
            used_food_ids=diet_plan.used_food_ids,
            is_active=True,
            version=next_version,
        )
        session.add(rec)
        await session.flush()
        return rec.id

    async def get_diet_plan(self, patient_id_str: str, *, session: AsyncSession) -> Optional[DietPlan]:
        """Return the active recommendation for a patient as a DietPlan."""
        result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == int(patient_id_str),
                Recommendation.is_active == True,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        rec = result.scalars().first()
        if rec is None:
            return None
        return DietPlan(
            user_id=str(rec.patient_id),
            created_at=rec.created_at,
            meals=rec.meals or [],
            ingredient_checklist=rec.ingredient_checklist or [],
            version=rec.version or 1,
        )

    async def update_diet_plan(self, patient_id_str: str, updated_plan: DietPlan, *, session: AsyncSession) -> bool:
        """Update the active recommendation's meals and checklist."""
        result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == int(patient_id_str),
                Recommendation.is_active == True,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        rec = result.scalars().first()
        if rec is None:
            return False
        rec.meals = updated_plan.meals
        rec.ingredient_checklist = updated_plan.ingredient_checklist
        await session.flush()
        return True

    async def delete_diet_plan(self, patient_id_str: str, *, session: AsyncSession) -> bool:
        """Soft-delete: set is_active = false on the current recommendation."""
        result = await session.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == int(patient_id_str),
                Recommendation.is_active == True,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        rec = result.scalars().first()
        if rec is None:
            return False
        rec.is_active = False
        await session.flush()
        return True

    async def get_plan_history(
        self,
        patient_id_str: str,
        *,
        session: AsyncSession,
        limit: int = 10,
    ) -> list[dict]:
        """
        Return all past (inactive) recommendations for a patient, newest first.
        Each entry includes week_start_date, created_at, generated_by, version.
        Meals/checklist are excluded from history list for performance.
        """
        result = await session.execute(
            select(
                Recommendation.id,
                Recommendation.week_start_date,
                Recommendation.created_at,
                Recommendation.generated_by,
                Recommendation.version,
                Recommendation.is_active,
            )
            .where(Recommendation.patient_id == int(patient_id_str))
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "id": r.id,
                "week_start_date": str(r.week_start_date) if r.week_start_date else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "generated_by": r.generated_by,
                "version": r.version,
                "is_active": r.is_active,
            }
            for r in rows
        ]