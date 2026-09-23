"""add quantity_g to patient_pantry

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-04

Turns the presence-only pantry into a quantity-aware one, so coverage ranking
can ask "enough onions?" rather than only "any onions?", and so confirming a
meal can draw stock down.

Three-state semantics, deliberately:
  NULL  -- "I have this, amount unknown". Every pre-existing row, so no backfill
           is needed and current behaviour is preserved exactly.
  0     -- out of stock. Treated as NOT having the ingredient.
  > 0   -- grams on hand.

Nullable with no default is what makes NULL mean "unknown" rather than "zero" --
defaulting to 0 would silently mark every existing pantry row as empty.
"""
from alembic import op
import sqlalchemy as sa


revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_pantry",
        sa.Column("quantity_g", sa.Numeric(8, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_pantry_quantity_nonneg",
        "patient_pantry",
        "quantity_g IS NULL OR quantity_g >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pantry_quantity_nonneg", "patient_pantry", type_="check")
    op.drop_column("patient_pantry", "quantity_g")
