"""add food_items.name_normalized + backfill + lookup index

Revision ID: d2e3f4a5b6c7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-31

Canonical name form (lower/trim/collapse-whitespace) for dedup and the
uq_fi_canonical partial-unique index (created later, after dedup cleanup).
This migration is safe on populated data — the index here is NON-unique.
"""
from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("food_items", sa.Column("name_normalized", sa.String(length=255), nullable=True))
    # Backfill: lower + trim + collapse internal whitespace — matches scripts/audit_dish_duplicates.py norm().
    op.execute(
        r"UPDATE food_items "
        r"SET name_normalized = regexp_replace(btrim(lower(recipe_name)), '\s+', ' ', 'g')"
    )
    op.create_index("idx_fi_name_norm", "food_items", ["name_normalized"])


def downgrade() -> None:
    op.drop_index("idx_fi_name_norm", table_name="food_items")
    op.drop_column("food_items", "name_normalized")
