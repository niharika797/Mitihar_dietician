"""add refresh_tokens (rotation + reuse detection)

Revision ID: e9a1c4b7d302
Revises: b5e2fa9b0b8c
Create Date: 2026-10-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9a1c4b7d302'
down_revision: Union[str, Sequence[str], None] = 'b5e2fa9b0b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('family_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('idx_refresh_tokens_family', 'refresh_tokens', ['family_id'])
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['role', 'user_id'])
    op.create_index('idx_refresh_tokens_expires', 'refresh_tokens', ['expires_at'])


def downgrade() -> None:
    op.drop_index('idx_refresh_tokens_expires', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_user', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_family', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
