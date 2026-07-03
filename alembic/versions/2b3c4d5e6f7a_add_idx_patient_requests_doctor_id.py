"""add_idx_patient_requests_doctor_id

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-03

Eliminates sequential scans on the patient_requests table when filtering
by doctor_id. Doctor dashboard fetches pending requests with
WHERE doctor_id = $1 — without this index that's a full table scan.
"""
from alembic import op

revision = '2b3c4d5e6f7a'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('idx_patient_requests_doctor_id', 'patient_requests', ['doctor_id'], unique=False)


def downgrade():
    op.drop_index('idx_patient_requests_doctor_id', table_name='patient_requests')
