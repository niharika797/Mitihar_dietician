"""alter_ingredients_add_nutrition_source

Revision ID: d5e6f7a8b9c0
Revises: c2d3e4f5a6b7
Create Date: 2026-06-02

Changes (Session 14):
  - ingredients: add name_normalized (Text nullable), unit_weight_g (Numeric nullable)
  - ingredients: make 5 nutrition columns nullable (were NOT NULL, need nullable for seed-then-fill)
  - food_items: add nutrition_source (Text, default 'manual')
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ingredients: add 2 missing columns
    op.add_column('ingredients', sa.Column('name_normalized', sa.Text(), nullable=True))
    op.add_column('ingredients', sa.Column('unit_weight_g', sa.Numeric(), nullable=True))

    # ingredients: make 5 nutrition columns nullable
    op.alter_column('ingredients', 'calories_per_100g', existing_type=sa.Float(), nullable=True)
    op.alter_column('ingredients', 'protein_per_100g', existing_type=sa.Float(), nullable=True)
    op.alter_column('ingredients', 'carbs_per_100g', existing_type=sa.Float(), nullable=True)
    op.alter_column('ingredients', 'fat_per_100g', existing_type=sa.Float(), nullable=True)
    op.alter_column('ingredients', 'fiber_per_100g', existing_type=sa.Float(), nullable=True)

    # food_items: add nutrition_source with default 'manual'
    op.add_column('food_items', sa.Column(
        'nutrition_source',
        sa.Text(),
        nullable=False,
        server_default='manual'
    ))


def downgrade() -> None:
    op.drop_column('food_items', 'nutrition_source')
    op.drop_column('ingredients', 'unit_weight_g')
    op.drop_column('ingredients', 'name_normalized')
    op.alter_column('ingredients', 'calories_per_100g', existing_type=sa.Float(), nullable=False)
    op.alter_column('ingredients', 'protein_per_100g', existing_type=sa.Float(), nullable=False)
    op.alter_column('ingredients', 'carbs_per_100g', existing_type=sa.Float(), nullable=False)
    op.alter_column('ingredients', 'fat_per_100g', existing_type=sa.Float(), nullable=False)
    op.alter_column('ingredients', 'fiber_per_100g', existing_type=sa.Float(), nullable=False)
