""""fix_nullable_streak_requestedat"

Revision ID: cf7a21f007f0
Revises: 4e5124b3e103
Create Date: 2026-03-05 12:26:34.967064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cf7a21f007f0'
down_revision: Union[str, Sequence[str], None] = '4e5124b3e103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # GIN index drops intentionally removed — idx_fi_meal_times/plan_types/regions
    # exist in DB by design and must not be dropped.
    op.alter_column('patient_requests', 'requested_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('progress_logs', 'streak_days',
               existing_type=sa.INTEGER(),
               nullable=False,
               server_default=sa.text('0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('progress_logs', 'streak_days',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('patient_requests', 'requested_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    # GIN index recreation intentionally removed
