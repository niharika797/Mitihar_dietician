"""Security: email_verification_tokens, password_reset_tokens, is_email_verified on patients

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-17

"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── is_email_verified on patients ─────────────────────────────────────
    op.add_column(
        'patients',
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'),
    )

    # ── email_verification_tokens ─────────────────────────────────────────
    op.create_table(
        'email_verification_tokens',
        sa.Column('id',         sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.Integer(),     sa.ForeignKey('patients.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('token',      sa.String(64),    nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_evt_token',   'email_verification_tokens', ['token'])
    op.create_index('idx_evt_patient', 'email_verification_tokens', ['patient_id'])

    # ── password_reset_tokens ─────────────────────────────────────────────
    op.create_table(
        'password_reset_tokens',
        sa.Column('id',         sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('patient_id', sa.Integer(),     sa.ForeignKey('patients.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('token',      sa.String(64),    nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_prt_token',   'password_reset_tokens', ['token'])
    op.create_index('idx_prt_patient', 'password_reset_tokens', ['patient_id'])


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
    op.drop_table('email_verification_tokens')
    op.drop_column('patients', 'is_email_verified')
