"""merge heads: product tour and profile picture migrations

Revision ID: b5e2fa9b0b8c
Revises: b1c91b42450c, c6d7e8f9a0b1, k1l2m3n4o5p6
Create Date: 2026-09-18 21:24:28.665292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e2fa9b0b8c'
down_revision: Union[str, Sequence[str], None] = ('b1c91b42450c', 'c6d7e8f9a0b1', 'k1l2m3n4o5p6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
