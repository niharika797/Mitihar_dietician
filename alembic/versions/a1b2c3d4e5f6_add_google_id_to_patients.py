"""add_google_id_to_patients

Revision ID: a1b2c3d4e5f6
Revises: 370efc812ae5
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'eb8dbef8dd19'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'patients',
        sa.Column('google_id', sa.String(128), nullable=True)
    )
    op.create_index(
        'idx_patients_google_id',
        'patients',
        ['google_id'],
        unique=True,
        postgresql_where=sa.text('google_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_patients_google_id', table_name='patients')
    op.drop_column('patients', 'google_id')
