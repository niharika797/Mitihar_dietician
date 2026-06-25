"""add ingredient tags and condiment slot_type

Revision ID: b8c9d0e1f2a3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-06

Adds avoid_tags and prefer_tags JSONB columns to ingredients (Layer 1 schema).
Adds CHECK constraint to food_items.slot_type that includes 'condiment' (Layer 2 schema).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b8c9d0e1f2a3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None

VALID_SLOT_TYPES = (
    'grain', 'main_dish', 'dal_protein', 'sabzi', 'snack_item',
    'accompaniment', 'beverage', 'one_pot', 'condiment',
)


def upgrade() -> None:
    # ── ingredients: add tag columns ─────────────────────────────────────────
    op.add_column(
        'ingredients',
        sa.Column('avoid_tags', JSONB, nullable=False, server_default='[]'),
    )
    op.add_column(
        'ingredients',
        sa.Column('prefer_tags', JSONB, nullable=False, server_default='[]'),
    )
    op.create_index(
        'idx_ing_avoid_tags',
        'ingredients',
        ['avoid_tags'],
        postgresql_using='gin',
    )
    op.create_index(
        'idx_ing_prefer_tags',
        'ingredients',
        ['prefer_tags'],
        postgresql_using='gin',
    )

    # ── food_items: add slot_type check constraint ────────────────────────────
    slot_list = ", ".join(f"'{v}'" for v in VALID_SLOT_TYPES)
    op.create_check_constraint(
        'ck_fi_slot_type',
        'food_items',
        f"slot_type IN ({slot_list})",
    )


def downgrade() -> None:
    op.drop_constraint('ck_fi_slot_type', 'food_items', type_='check')
    op.drop_index('idx_ing_prefer_tags', table_name='ingredients')
    op.drop_index('idx_ing_avoid_tags', table_name='ingredients')
    op.drop_column('ingredients', 'prefer_tags')
    op.drop_column('ingredients', 'avoid_tags')
