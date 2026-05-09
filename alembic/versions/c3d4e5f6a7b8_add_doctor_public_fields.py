"""add doctor public fields: state, experience_years, fee_per_month, rating, review_count, is_accepting

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-13

"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('state', sa.String(), nullable=True))
    op.add_column('doctors', sa.Column('experience_years', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('doctors', sa.Column('fee_per_month', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('doctors', sa.Column('rating', sa.Numeric(3, 2), nullable=True, server_default='0'))
    op.add_column('doctors', sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('doctors', sa.Column('is_accepting', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('doctors', 'is_accepting')
    op.drop_column('doctors', 'review_count')
    op.drop_column('doctors', 'rating')
    op.drop_column('doctors', 'fee_per_month')
    op.drop_column('doctors', 'experience_years')
    op.drop_column('doctors', 'state')
