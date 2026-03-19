"""add used_food_ids to recommendations for cross-week meal variety

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-16

"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'recommendations',
        sa.Column('used_food_ids', JSONB(), nullable=True, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('recommendations', 'used_food_ids')
