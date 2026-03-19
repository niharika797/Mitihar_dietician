"""pending_visit_approvals table + visit fraud prevention

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-18
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, Sequence[str], None] = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pending_visit_approvals',
        sa.Column('id',               sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('patient_id',       sa.Integer(),     sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id',        sa.Integer(),     sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('patient_visit_id', sa.Integer(),     sa.ForeignKey('patient_visits.id'), nullable=True),
        sa.Column('status',           sa.String(10),    nullable=False, server_default='pending'),
        sa.Column('visit_date',       sa.DateTime(timezone=True), nullable=False),
        sa.Column('doctor_note',      sa.Text(),        nullable=True),
        sa.Column('responded_at',     sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',       sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_pva_patient', 'pending_visit_approvals', ['patient_id'])
    op.create_index('idx_pva_status',  'pending_visit_approvals', ['status'])


def downgrade() -> None:
    op.drop_table('pending_visit_approvals')
