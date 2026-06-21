"""create weekly_patient_summary table, add columns to patient_meal_choices

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-16

R-1 (Schema Expansion), rebuild_spec.md §2 `weekly_patient_summary` and
`patient_meal_choices`. weekly_patient_summary is a new cache table for the
doctor weekly-summary view (computed on-demand, R-3+). patient_meal_choices
gains weekly_combo_id (links a confirmed choice to one of the 4 stored
combos, nullable — NULL for v1 legacy choices) and bowl_size/actual_calories
for the Bowl Size feature (§3.8, PD-9).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'weekly_patient_summary',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.Integer(),
                  sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_id', sa.Integer(),
                  sa.ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('summary_data', JSONB, nullable=False, server_default='{}'),

        sa.UniqueConstraint('patient_id', 'week_start_date', name='uq_wps_patient_week'),
    )
    op.create_index('idx_wps_patient_id', 'weekly_patient_summary', ['patient_id'])

    op.add_column(
        'patient_meal_choices',
        sa.Column('weekly_combo_id', sa.Integer(),
                  sa.ForeignKey('weekly_combos.id', ondelete='SET NULL'), nullable=True),
    )
    op.add_column(
        'patient_meal_choices',
        sa.Column('bowl_size', sa.String(6), nullable=True),
    )
    op.add_column(
        'patient_meal_choices',
        sa.Column('actual_calories', sa.Numeric(7, 2), nullable=True),
    )
    op.create_check_constraint(
        'ck_pmc_bowl_size',
        'patient_meal_choices',
        "bowl_size IN ('small', 'medium', 'large')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_pmc_bowl_size', 'patient_meal_choices', type_='check')
    op.drop_column('patient_meal_choices', 'actual_calories')
    op.drop_column('patient_meal_choices', 'bowl_size')
    op.drop_column('patient_meal_choices', 'weekly_combo_id')

    op.drop_index('idx_wps_patient_id', table_name='weekly_patient_summary')
    op.drop_table('weekly_patient_summary')
