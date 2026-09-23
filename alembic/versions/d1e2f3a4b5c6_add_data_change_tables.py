"""add data_change_requests + data_change_audit_log tables (Stage 6 governance)

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-07-31

Wires the DataChangeRequest model (already in db_models.py, table was never migrated)
and adds the append-only DataChangeAuditLog. App code only INSERTs into the audit log.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "d1e2f3a4b5c6"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_change_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_table", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("field_changed", sa.String(length=100), nullable=False),
        sa.Column("old_value", JSONB(), nullable=True),
        sa.Column("new_value", JSONB(), nullable=False),
        sa.Column("proposed_by", sa.String(length=50), nullable=False),
        sa.Column("proposal_reason", sa.Text(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["reviewed_by"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dcr_status_tier", "data_change_requests", ["status", "tier"])
    op.create_index("idx_dcr_proposed_by", "data_change_requests", ["proposed_by"])
    op.create_index("idx_dcr_target", "data_change_requests", ["target_table", "target_id"])

    op.create_table(
        "data_change_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("target_table", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("field_changed", sa.String(length=100), nullable=True),
        sa.Column("before_value", JSONB(), nullable=True),
        sa.Column("after_value", JSONB(), nullable=True),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["data_change_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dcal_target", "data_change_audit_log", ["target_table", "target_id"])
    op.create_index("idx_dcal_request", "data_change_audit_log", ["request_id"])
    op.create_index("idx_dcal_action", "data_change_audit_log", ["action"])


def downgrade() -> None:
    op.drop_index("idx_dcal_action", table_name="data_change_audit_log")
    op.drop_index("idx_dcal_request", table_name="data_change_audit_log")
    op.drop_index("idx_dcal_target", table_name="data_change_audit_log")
    op.drop_table("data_change_audit_log")
    op.drop_index("idx_dcr_target", table_name="data_change_requests")
    op.drop_index("idx_dcr_proposed_by", table_name="data_change_requests")
    op.drop_index("idx_dcr_status_tier", table_name="data_change_requests")
    op.drop_table("data_change_requests")
