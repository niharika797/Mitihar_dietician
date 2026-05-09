"""add token system: token_1 columns on patients, patient_visits table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-16

"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Token 1 columns on patients ───────────────────────────────────────
    op.add_column('patients', sa.Column('token_1', sa.String(20), nullable=True))
    op.add_column('patients', sa.Column('token_1_active', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('patients', sa.Column('token_1_expiry', sa.DateTime(timezone=True), nullable=True))
    op.add_column('patients', sa.Column('renewal_requested', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('patients', sa.Column('renewal_requested_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('patients', sa.Column('expiring_soon', sa.Boolean(), nullable=False, server_default='false'))
    op.create_unique_constraint('uq_patients_token_1', 'patients', ['token_1'])

    # ── patient_visits table (Token 2) ────────────────────────────────────
    op.create_table(
        'patient_visits',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('token_2', sa.String(24), nullable=False),
        sa.Column('cycle_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cycle_expiry', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_charged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('visit_counter', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_pv_patient', 'patient_visits', ['patient_id'])
    op.create_index('idx_pv_doctor', 'patient_visits', ['doctor_id'])


def downgrade() -> None:
    op.drop_index('idx_pv_doctor', table_name='patient_visits')
    op.drop_index('idx_pv_patient', table_name='patient_visits')
    op.drop_table('patient_visits')
    op.drop_constraint('uq_patients_token_1', 'patients', type_='unique')
    op.drop_column('patients', 'expiring_soon')
    op.drop_column('patients', 'renewal_requested_at')
    op.drop_column('patients', 'renewal_requested')
    op.drop_column('patients', 'token_1_expiry')
    op.drop_column('patients', 'token_1_active')
    op.drop_column('patients', 'token_1')
