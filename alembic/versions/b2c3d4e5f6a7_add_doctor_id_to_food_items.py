"""add_doctor_id_to_food_items

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'food_items',
        sa.Column('doctor_id', sa.Integer(), sa.ForeignKey('doctors.id'), nullable=True)
    )
    op.create_index('idx_fi_doctor', 'food_items', ['doctor_id'])


def downgrade() -> None:
    op.drop_index('idx_fi_doctor', table_name='food_items')
    op.drop_column('food_items', 'doctor_id')
