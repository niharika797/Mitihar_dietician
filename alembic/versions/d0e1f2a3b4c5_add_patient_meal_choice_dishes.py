"""add patient_meal_choice_dishes child table

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-13

Session 22E (Part 3, Option B). Per-dish breakdown of a confirmed meal choice,
additive child of patient_meal_choices for future doctor weekly-summary analytics.

Schema notes:
- `calories` is UNSCALED per-serving (= food_items.cal_per_serving, same value as
  recommendations.meals[].dishes[].calories). This is intentionally a different
  basis from meal_logs.calories_consumed (which logs Σ scaled_calories) — the same
  meal recorded on two calorie bases. Documented so it isn't a future "why don't
  these numbers match" mystery.
- The parent patient_meal_choices.calories column REMAINS the denormalized summed
  total and stays the budget-math source of truth. These child rows are additive
  and never read by the plan-time budget path.
- food_item_id FK has no ON DELETE CASCADE: a child snapshot should not vanish if
  the food_item is later removed (consistent with treating choices as a history log).
"""
from alembic import op
import sqlalchemy as sa

revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'patient_meal_choice_dishes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('choice_id', sa.Integer(),
                  sa.ForeignKey('patient_meal_choices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('food_item_id', sa.Integer(),
                  sa.ForeignKey('food_items.id'), nullable=False),
        sa.Column('slot_type', sa.String(30), nullable=True),
        sa.Column('calories', sa.Float(), nullable=True),
    )
    op.create_index('idx_pmcd_choice', 'patient_meal_choice_dishes', ['choice_id'])


def downgrade() -> None:
    op.drop_index('idx_pmcd_choice', table_name='patient_meal_choice_dishes')
    op.drop_table('patient_meal_choice_dishes')
