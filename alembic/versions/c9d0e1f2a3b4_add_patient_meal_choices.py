"""add patient_meal_choices table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-07

One confirmed dish choice per meal slot per day per patient.
Tracks planned choices (not consumption logs — those live in meal_logs).
calories column stores the dish's cal_per_serving at time of confirmation
for budget computation: remaining_today = tdee - SUM(calories WHERE date=today).
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'patient_meal_choices',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.Integer(),
                  sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('food_item_id', sa.Integer(),
                  sa.ForeignKey('food_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(20), nullable=False),
        sa.Column('calories', sa.Float(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )
    op.create_unique_constraint(
        'uq_pmc_patient_date_meal',
        'patient_meal_choices',
        ['patient_id', 'date', 'meal_type'],
    )
    op.create_index('idx_pmc_patient_date', 'patient_meal_choices',
                    ['patient_id', 'date'])


def downgrade() -> None:
    op.drop_index('idx_pmc_patient_date', table_name='patient_meal_choices')
    op.drop_constraint('uq_pmc_patient_date_meal', 'patient_meal_choices')
    op.drop_table('patient_meal_choices')
