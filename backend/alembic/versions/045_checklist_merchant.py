"""add merchant name to reconciliation checklist

Revision ID: 045_checklist_merchant
Revises: 044_reconciliation_checklist
Create Date: 2026-06-04

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "045_checklist_merchant"
down_revision: Union[str, None] = "044_reconciliation_checklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE fin_reconciliation_checklist_details "
        "ADD COLUMN IF NOT EXISTS merchant_name VARCHAR(500) NOT NULL DEFAULT ''"
    )
    op.execute("COMMENT ON COLUMN fin_reconciliation_checklist_details.merchant_name IS '商家'")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_summary")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_export")
    op.create_index(
        "idx_fin_reconciliation_checklist_summary",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "merchant_name", "receipt_merchant", "live_promoter"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_export",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "merchant_name", "receipt_merchant", "live_promoter", "product_name"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_export")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_summary")
    op.create_index(
        "idx_fin_reconciliation_checklist_export",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "receipt_merchant", "live_promoter", "product_name"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_summary",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "live_promoter", "receipt_merchant"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_column("fin_reconciliation_checklist_details", "merchant_name")
