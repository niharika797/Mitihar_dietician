"""add reason_code to pending_visit_approvals

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-05

Why a coded reason rather than the free-text doctor_note that already exists:

doctor_note is rendered TO THE PATIENT alongside a request to confirm a
chargeable visit. Unrestricted text on that surface is a coercion channel -- a
doctor can write "confirm this or I'll stop seeing you" next to a bill. A fixed
vocabulary removes that for the common cases, and makes the data answerable:
"how often is the app itself the reason someone can't show Token 2" tells you
whether to fix the app rather than the process.

`other` remains available with free text, so genuine edge cases are not forced
into a wrong bucket -- but it is the exception rather than the default path.

Nullable, no backfill: rows written before this feature genuinely have no
reason, and inventing one for them would be fabricating a clinical record. The
UI renders NULL as "Not specified".

The CHECK constraint is the real guarantee. Pydantic validates the API, but the
column is what stops a stray script or a psql session writing a bucket the
clients cannot render.
"""
from alembic import op
import sqlalchemy as sa


revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

# Keep in sync with FLAG_VISIT_REASONS in app/schemas/doctor.py.
_ALLOWED = ("phone_not_present", "battery_dead", "app_issue", "signed_out", "other")


def upgrade() -> None:
    op.add_column(
        "pending_visit_approvals",
        sa.Column("reason_code", sa.String(32), nullable=True),
    )
    allowed = ", ".join(f"'{r}'" for r in _ALLOWED)
    op.create_check_constraint(
        "ck_pva_reason_code",
        "pending_visit_approvals",
        f"reason_code IS NULL OR reason_code IN ({allowed})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pva_reason_code", "pending_visit_approvals", type_="check")
    op.drop_column("pending_visit_approvals", "reason_code")
