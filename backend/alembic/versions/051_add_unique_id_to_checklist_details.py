"""add unique id fingerprint to checklist details

Revision ID: 051_checklist_unique_id
Revises: 050_add_org_type
Create Date: 2026-06-10

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "051_checklist_unique_id"
down_revision: Union[str, None] = "050_add_org_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_reconciliation_checklist_details",
        sa.Column("row_fingerprint", sa.String(length=32), nullable=False, server_default="", comment="系统唯一ID"),
    )
    op.execute(
        """
        UPDATE fin_reconciliation_checklist_details
        SET row_fingerprint = md5(
            concat_ws(
                '|',
                org_id::text,
                to_char(settlement_time, 'YYYY-MM-DD HH24:MI:SS'),
                coalesce(sub_order_no, ''),
                to_char(coalesce(platform_subsidy, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(talent_subsidy, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(douyin_pay_subsidy, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(douyin_monthly_pay_subsidy, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(bank_subsidy, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(user_paid_amount, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(platform_service_fee, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(talent_commission, 0)::numeric(14,2), 'FM9999999999990.00'),
                to_char(coalesce(investment_service_fee, 0)::numeric(14,2), 'FM9999999999990.00')
            )
        )
        """
    )
    op.alter_column("fin_reconciliation_checklist_details", "row_fingerprint", server_default=None)
    op.drop_index("uq_fin_reconciliation_checklist_detail_order", table_name="fin_reconciliation_checklist_details")
    op.create_index(
        "uq_fin_reconciliation_checklist_detail_row_fingerprint",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "row_fingerprint"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND row_fingerprint <> ''"),
    )


def downgrade() -> None:
    op.drop_index("uq_fin_reconciliation_checklist_detail_row_fingerprint", table_name="fin_reconciliation_checklist_details")
    op.create_index(
        "uq_fin_reconciliation_checklist_detail_order",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "sub_order_no"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND sub_order_no <> ''"),
    )
    op.drop_column("fin_reconciliation_checklist_details", "row_fingerprint")
