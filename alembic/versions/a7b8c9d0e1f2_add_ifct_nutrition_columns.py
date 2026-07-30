"""add_ifct_nutrition_columns

Revision ID: a7b8c9d0e1f2
Revises: j9k0l1m2n3o4
Create Date: 2026-07-29 00:00:00.000000

IFCT2017 integration (plan: wire IFCT nutrition into medical filtering).
Adds per-100g nutrient columns to `ingredients` (populated from IFCT Tables 5/6/7
for name-matched foods) and the matching per-serving columns to `food_items`
(computed from the ingredient chain by recalculate_recipe_nutrition.py).

All nutrient columns are nullable — NULL means "not known" (ingredient unmatched or
below coverage), never 0. Minerals + fatty acids stored in mg; sugars in g.

`food_items.tags_locked` guards doctor tag edits: derive_medical_tags.py only
rewrites tags on rows where tags_locked = false.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'j9k0l1m2n3o4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INGREDIENT_COLS = [
    "potassium_per_100g", "phosphorus_per_100g", "zinc_per_100g",
    "total_sugars_per_100g", "free_sugars_per_100g",
    "saturated_fat_per_100g", "mufa_per_100g", "pufa_per_100g",
]
FOOD_ITEM_COLS = [
    "iron_per_serving", "calcium_per_serving", "potassium_per_serving",
    "phosphorus_per_serving", "zinc_per_serving", "free_sugars_per_serving",
    "saturated_fat_per_serving",
]


def upgrade() -> None:
    for col in INGREDIENT_COLS:
        op.add_column("ingredients", sa.Column(col, sa.Float(), nullable=True))
    for col in FOOD_ITEM_COLS:
        op.add_column("food_items", sa.Column(col, sa.Numeric(8, 2), nullable=True))
    op.add_column(
        "food_items",
        sa.Column("tags_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("food_items", "tags_locked")
    for col in FOOD_ITEM_COLS:
        op.drop_column("food_items", col)
    for col in INGREDIENT_COLS:
        op.drop_column("ingredients", col)
