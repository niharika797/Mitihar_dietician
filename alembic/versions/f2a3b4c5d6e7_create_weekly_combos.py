"""create weekly_combos table

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-16

R-1 (Schema Expansion), rebuild_spec.md §2 `weekly_combos`.
Pre-generated combos for the v2 multi-combo model: one row per combo,
4 combo_index values (0-3) per (recommendation_id, slot_date, meal_type).
Additive — no existing rows affected; generation engine (R-2) will write here.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'weekly_combos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('recommendation_id', sa.Integer(),
                  sa.ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(20), nullable=False),
        sa.Column('combo_index', sa.SmallInteger(), nullable=False),
        sa.Column('slot_composition', ARRAY(sa.Text()), nullable=False),
        sa.Column('total_calories', sa.Numeric(7, 2), nullable=False),
        sa.Column('dishes', JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.UniqueConstraint('recommendation_id', 'slot_date', 'meal_type', 'combo_index',
                             name='uq_weekly_combo'),
        sa.CheckConstraint('combo_index BETWEEN 0 AND 3', name='ck_combo_index'),
        sa.CheckConstraint("meal_type IN ('Breakfast', 'Lunch', 'Dinner')", name='ck_meal_type'),
    )
    op.create_index('idx_wc_rec_date_meal', 'weekly_combos',
                     ['recommendation_id', 'slot_date', 'meal_type'])
    op.create_index('idx_wc_rec_id', 'weekly_combos', ['recommendation_id'])


def downgrade() -> None:
    op.drop_index('idx_wc_rec_id', table_name='weekly_combos')
    op.drop_index('idx_wc_rec_date_meal', table_name='weekly_combos')
    op.drop_table('weekly_combos')
