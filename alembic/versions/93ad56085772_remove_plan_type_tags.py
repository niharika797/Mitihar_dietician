"""remove_plan_type_tags

Revision ID: 93ad56085772
Revises: b4c5d6e7f8a9
Create Date: 2026-06-28 17:13:44.767062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '93ad56085772'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('idx_fi_plan_types', table_name='food_items', postgresql_using='gin')
    op.drop_column('food_items', 'plan_type_tags')


def downgrade() -> None:
    # server_default='{}' fills existing rows so NOT NULL constraint is satisfied.
    # The original column stored tag arrays; empty array is the correct empty value.
    op.add_column('food_items', sa.Column(
        'plan_type_tags', postgresql.ARRAY(sa.TEXT()),
        server_default='{}', nullable=False,
    ))
    op.create_index('idx_fi_plan_types', 'food_items', ['plan_type_tags'], unique=False, postgresql_using='gin')
    # Remove server_default after backfill — original column had none.
    op.alter_column('food_items', 'plan_type_tags', server_default=None)
