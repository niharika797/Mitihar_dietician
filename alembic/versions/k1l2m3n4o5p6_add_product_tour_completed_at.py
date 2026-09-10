"""add_product_tour_completed_at

Revision ID: k1l2m3n4o5p6
Revises: f5a6b7c8d9e0
Create Date: 2026-09-10 00:00:00.000000

Phase 1 product tour (mobile app only): nullable timestamp on patients,
set identically whether the tour is finished or skipped. Distinct from
disclaimer_accepted_at, which gates the unrelated medical-onboarding wizard.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('product_tour_completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'product_tour_completed_at')
