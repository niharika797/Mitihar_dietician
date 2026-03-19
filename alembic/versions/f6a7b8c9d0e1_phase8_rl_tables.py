"""Phase 8 Tier 0: add doctor_meal_overrides and meal_ratings tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-17

"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── doctor_meal_overrides ─────────────────────────────────────────────
    op.create_table(
        'doctor_meal_overrides',
        sa.Column('id',                         sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('doctor_id',                  sa.Integer(),    sa.ForeignKey('doctors.id'),    nullable=False),
        sa.Column('patient_id',                 sa.Integer(),    sa.ForeignKey('patients.id'),   nullable=False),
        sa.Column('override_date',              sa.Date(),       nullable=False),
        sa.Column('slot_type',                  sa.String(50),   nullable=True),
        sa.Column('meal_type',                  sa.String(30),   nullable=False),
        sa.Column('rejected_food_id',           sa.Integer(),    sa.ForeignKey('food_items.id'), nullable=True),
        sa.Column('chosen_food_id',             sa.Integer(),    sa.ForeignKey('food_items.id'), nullable=True),
        sa.Column('patient_health_condition',   sa.String(30),   nullable=True),
        sa.Column('patient_medical_conditions', JSONB(),         nullable=True,  server_default='[]'),
        sa.Column('patient_region',             sa.String(10),   nullable=True),
        sa.Column('patient_diet_type',          sa.String(30),   nullable=True),
        sa.Column('patient_age_bucket',         sa.String(10),   nullable=True),
        sa.Column('patient_bmi_bucket',         sa.String(15),   nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_dmo_doctor',  'doctor_meal_overrides', ['doctor_id'])
    op.create_index('idx_dmo_patient', 'doctor_meal_overrides', ['patient_id'])
    op.create_index('idx_dmo_date',    'doctor_meal_overrides', ['override_date'])

    # ── meal_ratings ─────────────────────────────────────────────────────
    op.create_table(
        'meal_ratings',
        sa.Column('id',                sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('patient_id',        sa.Integer(),  sa.ForeignKey('patients.id'),       nullable=False),
        sa.Column('food_item_id',      sa.Integer(),  sa.ForeignKey('food_items.id'),     nullable=False),
        sa.Column('recommendation_id', sa.Integer(),  sa.ForeignKey('recommendations.id'), nullable=True),
        sa.Column('rating',            sa.Integer(),  nullable=False),   # +1 or -1
        sa.Column('rated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('patient_id', 'food_item_id', 'recommendation_id',
                            name='uq_meal_rating'),
    )
    op.create_index('idx_mr_patient', 'meal_ratings', ['patient_id'])
    op.create_index('idx_mr_food',    'meal_ratings', ['food_item_id'])


def downgrade() -> None:
    op.drop_table('meal_ratings')
    op.drop_table('doctor_meal_overrides')
