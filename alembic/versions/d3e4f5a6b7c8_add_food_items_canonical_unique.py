"""add uq_fi_canonical partial-unique index on food_items

Revision ID: d3e4f5a6b7c8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-31

At most one CANONICAL dish per (name_normalized, slot_type, diet_type) in the served
pool. Private/unverified dishes and soft-deleted history are exempt via the predicate;
diet-variants differ on diet_type so both diet pools keep their copy.

ORDER-SENSITIVE: this UNIQUE index can only build after the served pool is dedup-clean
(Phase 1 merge + Phase 2 conflict-resolve). On a fresh clone the schema is built on an
empty table first, then the already-deduped content dump is restored — so no collision.
On the live dev/staging DB, run the cleanup scripts BEFORE `alembic upgrade` reaches here.
"""
from alembic import op
import sqlalchemy as sa


revision = "d3e4f5a6b7c8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_fi_canonical",
        "food_items",
        ["name_normalized", "slot_type", "diet_type"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND is_verified = true AND name_normalized IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_fi_canonical", table_name="food_items")
