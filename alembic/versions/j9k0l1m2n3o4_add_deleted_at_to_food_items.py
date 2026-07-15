"""add_deleted_at_to_food_items

Revision ID: j9k0l1m2n3o4
Revises: 651cd3d46fa9
Create Date: 2026-07-15 00:00:00.000000

Stage 6 Section 1 (product owner decision 3, docs/DISH_DUPLICATE_AUDIT.md
"Open items needing sign-off" #3): real soft-delete column for food_items,
replacing the is_verified=False proxy. is_verified=False means "not yet
reviewed / not in the generator pool" — it does NOT mean "deleted", and the
Data Review tab (Stage 6 Section 4) needs to distinguish "still reviewable"
from "merged away by Tier 1 auto-merge". Tier 1 merges set deleted_at
instead of hard-deleting so the canonical row's merge history stays
inspectable.

NULL = active (default, all 2,137 existing rows). Non-NULL = soft-deleted.
Partial index on deleted_at IS NULL for the (expected-common) "exclude
soft-deleted" filter.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j9k0l1m2n3o4'
down_revision: Union[str, Sequence[str], None] = '651cd3d46fa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('food_items', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        'idx_fi_deleted_at', 'food_items', ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_fi_deleted_at', table_name='food_items')
    op.drop_column('food_items', 'deleted_at')
