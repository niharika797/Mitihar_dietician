"""add_original_name_to_food_items

Revision ID: b5c6d7e8f9a0
Revises: 93ad56085772
Create Date: 2026-06-28

Safety column — stores original recipe_name before any cleanup pass.
Rollback: UPDATE food_items SET recipe_name = original_name WHERE original_name IS NOT NULL;
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = '93ad56085772'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('food_items',
        sa.Column('original_name', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('food_items', 'original_name')
