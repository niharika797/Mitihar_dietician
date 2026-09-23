"""drop_unused_beverages_and_food_items_instructions

Revision ID: 651cd3d46fa9
Revises: 2b3c4d5e6f7a
Create Date: 2026-07-13 14:02:56.044218

Both confirmed dead on local dev AND staging (verified via direct query,
2026-07-13): `beverages` has 0 rows, `food_items.instructions` has 0
non-null rows out of 2137 total.

`beverages` — standalone catalog from Session 11 (migration c2d3e4f5a6b7),
superseded by Session 22E's decision to serve beverages via
food_items(slot_type='beverage') instead (see app/routers/meal_plan.py
list_beverages() docstring). No model class, no code path reads/writes it.

`food_items.instructions` — original schema column (migration
92084b0bc541), never populated, never read anywhere in app/ or scripts/.
Replaces the ad-hoc scripts/drop_instructions.py, which dropped this same
column via a raw engine connection outside Alembic — that script should
no longer be run; this migration is the tracked equivalent.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '651cd3d46fa9'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('food_items', 'instructions')

    op.drop_index('idx_bev_name', table_name='beverages')
    op.drop_index('idx_bev_category', table_name='beverages')
    op.drop_index('idx_bev_active', table_name='beverages')
    op.drop_table('beverages')


def downgrade() -> None:
    op.add_column('food_items', sa.Column('instructions', sa.Text(), nullable=True))

    op.create_table(
        'beverages',
        sa.Column('id',                      sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name',                    sa.Text(),    nullable=False),
        sa.Column('category',                sa.Text(),    nullable=False),
        sa.Column('calories_per_serving',    sa.Float(),   nullable=False),
        sa.Column('protein_per_serving',     sa.Float(),   nullable=True),
        sa.Column('carbs_per_serving',       sa.Float(),   nullable=True),
        sa.Column('fat_per_serving',         sa.Float(),   nullable=True),
        sa.Column('serving_size_ml',         sa.Integer(), nullable=True),
        sa.Column('is_caffeinated',          sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('suitable_for_conditions', JSONB(),      nullable=True),
        sa.Column('is_active',               sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_bev_name',     'beverages', ['name'])
    op.create_index('idx_bev_category', 'beverages', ['category'])
    op.create_index('idx_bev_active',   'beverages', ['is_active'])
