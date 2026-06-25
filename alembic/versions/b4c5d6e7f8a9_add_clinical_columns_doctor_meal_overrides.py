"""add clinical edit-trail columns to doctor_meal_overrides

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-06-16

R-1 (Schema Expansion), rebuild_spec.md §2 `doctor_meal_overrides`. Enriches
the append-only RL training corpus with clinical context so the
recommendation engine can learn from doctor edits over time.
edit_reason defaults to 'swap' for existing rows (backward compatible);
patient_condition_snapshot and doctor_note default to NULL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'doctor_meal_overrides',
        sa.Column('patient_condition_snapshot', JSONB, nullable=True),
    )
    op.add_column(
        'doctor_meal_overrides',
        sa.Column('edit_reason', sa.String(20), nullable=False, server_default='swap'),
    )
    op.add_column(
        'doctor_meal_overrides',
        sa.Column('doctor_note', sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        'ck_dmo_edit_reason',
        'doctor_meal_overrides',
        "edit_reason IN ('swap', 'add', 'remove', 'custom_add')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_dmo_edit_reason', 'doctor_meal_overrides', type_='check')
    op.drop_column('doctor_meal_overrides', 'doctor_note')
    op.drop_column('doctor_meal_overrides', 'edit_reason')
    op.drop_column('doctor_meal_overrides', 'patient_condition_snapshot')
