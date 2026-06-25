"""add generation_version and approval_status to recommendations

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-16

R-1 (Schema Expansion), rebuild_spec.md §2 `recommendations`.
generation_version=1 marks the old single-combo JSONB model (existing rows
default here, no backfill needed). approval_status='approved' marks existing
rows as always patient-visible, matching current behavior. v2 plans will
write generation_version=2, approval_status='draft'.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'recommendations',
        sa.Column('generation_version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'recommendations',
        sa.Column('approval_status', sa.String(20), nullable=False, server_default='approved'),
    )
    op.create_check_constraint(
        'ck_rec_approval_status',
        'recommendations',
        "approval_status IN ('draft', 'approved')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_rec_approval_status', 'recommendations', type_='check')
    op.drop_column('recommendations', 'approval_status')
    op.drop_column('recommendations', 'generation_version')
