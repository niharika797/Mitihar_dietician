"""add profile_picture_url to patients

Revision ID: b1c91b42450c
Revises: f5a6b7c8d9e0
Create Date: 2026-09-11

Captures Google's OIDC 'picture' claim, set/refreshed on every Google
Sign-In (see auth.py:google_verify). NULL for password-only accounts —
no backfill possible since we never had this data before.
"""
from alembic import op
import sqlalchemy as sa


revision = "b1c91b42450c"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("profile_picture_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patients", "profile_picture_url")
