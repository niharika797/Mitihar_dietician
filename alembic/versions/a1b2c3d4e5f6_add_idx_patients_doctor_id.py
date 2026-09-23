"""add_idx_patients_doctor_id

Revision ID: 1a2b3c4d5e6f
Revises: b5c6d7e8f9a0
Create Date: 2026-07-01

Eliminates sequential scans on the patients table when filtering by doctor_id.
Every doctor dashboard query that fetches patient counts or lists does
WHERE doctor_id = $1 — without this index that's a full table scan.
"""
from alembic import op

revision = '1a2b3c4d5e6f'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('idx_patients_doctor_id', 'patients', ['doctor_id'], unique=False)


def downgrade():
    op.drop_index('idx_patients_doctor_id', table_name='patients')
