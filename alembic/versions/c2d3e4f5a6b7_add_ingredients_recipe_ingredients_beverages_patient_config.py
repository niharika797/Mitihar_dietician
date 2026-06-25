"""add_ingredients_recipe_ingredients_beverages_patient_config

Revision ID: c2d3e4f5a6b7
Revises: a9b8c7d6e5f4
Create Date: 2026-06-01

Adds five schema additions for the new data architecture (Sessions 11-17):
  - ingredients       — master nutritional source of truth (per 100g, INDB-compatible)
  - recipe_ingredients — links food_items to verified ingredients with quantity
  - beverages         — standalone beverage catalog, separate from meal slots
  - patient_meal_config — doctor TDEE split override per patient (one row per patient)
  - patient_dish_preferences — doctor pin/block per patient per dish

Approved and run: Session 11 (2026-06-01).
"""
from typing import Union, Sequence
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredients ──────────────────────────────────────────────────────
    # Master ingredient table. All nutrition values per 100g.
    # Source = "INDB_ICMR" for verified imports, "doctor_added" for doctor entries,
    # "manual" for legacy data.
    op.create_table(
        'ingredients',
        sa.Column('id',                 sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('name',               sa.Text(),     nullable=False),
        sa.Column('name_hindi',         sa.Text(),     nullable=True),
        sa.Column('calories_per_100g',  sa.Float(),    nullable=False),
        sa.Column('protein_per_100g',   sa.Float(),    nullable=False),
        sa.Column('carbs_per_100g',     sa.Float(),    nullable=False),
        sa.Column('fat_per_100g',       sa.Float(),    nullable=False),
        sa.Column('fiber_per_100g',     sa.Float(),    nullable=True),
        sa.Column('sodium_per_100g',    sa.Float(),    nullable=True),
        sa.Column('iron_per_100g',      sa.Float(),    nullable=True),
        sa.Column('calcium_per_100g',   sa.Float(),    nullable=True),
        sa.Column('source',             sa.Text(),     nullable=False),
        sa.Column('is_verified',        sa.Boolean(),  nullable=False, server_default='false'),
        sa.Column('added_by_doctor_id', sa.Integer(),
                  sa.ForeignKey('doctors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('name', 'source', name='uq_ingredient_name_source'),
    )
    op.create_index('idx_ing_name',     'ingredients', ['name'])
    op.create_index('idx_ing_source',   'ingredients', ['source'])
    op.create_index('idx_ing_verified', 'ingredients', ['is_verified'])

    # ── recipe_ingredients ────────────────────────────────────────────────
    # Links food_items to ingredients with per-serving quantity in grams.
    # ON DELETE CASCADE on food_item_id: deleting a recipe removes its ingredient links.
    # ON DELETE RESTRICT on ingredient_id: prevents deleting an ingredient used in a recipe.
    op.create_table(
        'recipe_ingredients',
        sa.Column('id',            sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('food_item_id',  sa.Integer(),
                  sa.ForeignKey('food_items.id',  ondelete='CASCADE'),  nullable=False),
        sa.Column('ingredient_id', sa.Integer(),
                  sa.ForeignKey('ingredients.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity_g',    sa.Float(),   nullable=False),
        sa.Column('notes',         sa.Text(),    nullable=True),
        sa.UniqueConstraint('food_item_id', 'ingredient_id', name='uq_recipe_ingredient'),
        sa.CheckConstraint("quantity_g > 0", name='ck_ri_quantity_positive'),
    )
    op.create_index('idx_ri_food_item',  'recipe_ingredients', ['food_item_id'])
    op.create_index('idx_ri_ingredient', 'recipe_ingredients', ['ingredient_id'])

    # ── beverages ─────────────────────────────────────────────────────────
    # Standalone beverage catalog. Not linked to meal slots.
    # category: "daily_staple" (chai/coffee/milk) | "occasional" (juices/lassi) |
    #           "therapeutic" (kadha/herbal drinks)
    # suitable_for_conditions: JSONB array of condition tags e.g. ["diabetes_friendly"]
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

    # ── patient_meal_config ───────────────────────────────────────────────
    # One row per patient. Created when a doctor first sets a TDEE override.
    # meal_split_override NULL = use system defaults (Breakfast 25% / Lunch 35% / Dinner 25%).
    # When set: {"breakfast_pct": 10, "lunch_pct": 45, "dinner_pct": 30}.
    # Application layer enforces: breakfast_pct + lunch_pct + dinner_pct == 85.
    # The remaining 15% is always the buffer — not configurable.
    op.create_table(
        'patient_meal_config',
        sa.Column('id',                  sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id',          sa.Integer(),
                  sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('meal_split_override', JSONB(),      nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_pmc_patient', 'patient_meal_config', ['patient_id'])

    # ── patient_dish_preferences ──────────────────────────────────────────
    # Doctor pins (always show first) or blocks (never show) specific dishes
    # for a specific patient. One preference per (patient, food_item) pair —
    # a dish cannot be both pinned and blocked.
    # ON DELETE CASCADE on patient_id: patient deleted → preferences deleted.
    # ON DELETE CASCADE on food_item_id: recipe deleted → preferences deleted.
    # ON DELETE RESTRICT on added_by_doctor_id: doctor cannot be deleted while
    # they have active preferences (prevents accidental data loss).
    op.create_table(
        'patient_dish_preferences',
        sa.Column('id',                 sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('patient_id',         sa.Integer(),
                  sa.ForeignKey('patients.id',   ondelete='CASCADE'),  nullable=False),
        sa.Column('food_item_id',       sa.Integer(),
                  sa.ForeignKey('food_items.id', ondelete='CASCADE'),  nullable=False),
        sa.Column('preference_type',    sa.Text(),    nullable=False),
        sa.Column('added_by_doctor_id', sa.Integer(),
                  sa.ForeignKey('doctors.id',    ondelete='RESTRICT'), nullable=False),
        sa.Column('note',               sa.Text(),    nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('patient_id', 'food_item_id', name='uq_patient_dish_preference'),
        sa.CheckConstraint("preference_type IN ('pin', 'block')", name='ck_pdp_preference_type'),
    )
    op.create_index('idx_pdp_patient',   'patient_dish_preferences', ['patient_id'])
    op.create_index('idx_pdp_food_item', 'patient_dish_preferences', ['food_item_id'])
    op.create_index('idx_pdp_doctor',    'patient_dish_preferences', ['added_by_doctor_id'])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('patient_dish_preferences')
    op.drop_table('patient_meal_config')
    op.drop_table('beverages')
    op.drop_table('recipe_ingredients')
    op.drop_table('ingredients')
