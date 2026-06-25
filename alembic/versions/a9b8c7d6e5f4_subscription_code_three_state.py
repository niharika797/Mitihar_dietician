"""subscription_code_three_state

Revision ID: a9b8c7d6e5f4
Revises: 040ab0561e5a
Create Date: 2026-05-23

Adds reserved_by / reserved_at to subscription_codes to implement the
AVAILABLE → RESERVED → CONSUMED three-state lifecycle.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = '040ab0561e5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscription_codes',
        sa.Column('reserved_by', sa.Integer(), sa.ForeignKey('patients.id'), nullable=True),
    )
    op.add_column(
        'subscription_codes',
        sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'idx_sc_reserved_by',
        'subscription_codes',
        ['reserved_by'],
    )


def downgrade() -> None:
    op.drop_index('idx_sc_reserved_by', table_name='subscription_codes')
    op.drop_column('subscription_codes', 'reserved_at')
    op.drop_column('subscription_codes', 'reserved_by')
