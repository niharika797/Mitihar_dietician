"""add condition tags to food_items

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-06

Adds avoid_tags and prefer_tags JSONB arrays to food_items.
Values must match the valid tag list in docs/MEDICAL_TAGGING_KNOWLEDGE_BASE.md.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'food_items',
        sa.Column('avoid_tags', JSONB, nullable=False, server_default='[]'),
    )
    op.add_column(
        'food_items',
        sa.Column('prefer_tags', JSONB, nullable=False, server_default='[]'),
    )
    op.create_index(
        'idx_fi_avoid_tags',
        'food_items',
        ['avoid_tags'],
        postgresql_using='gin',
    )
    op.create_index(
        'idx_fi_prefer_tags',
        'food_items',
        ['prefer_tags'],
        postgresql_using='gin',
    )


def downgrade() -> None:
    op.drop_index('idx_fi_prefer_tags', table_name='food_items')
    op.drop_index('idx_fi_avoid_tags', table_name='food_items')
    op.drop_column('food_items', 'prefer_tags')
    op.drop_column('food_items', 'avoid_tags')
