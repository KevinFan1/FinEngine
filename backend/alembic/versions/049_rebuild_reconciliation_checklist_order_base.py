"""rebuild reconciliation checklist order base

Revision ID: 049_checklist_order_base
Revises: 048_checklist_summary_partition
Create Date: 2026-06-09

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "049_checklist_order_base"
down_revision: Union[str, None] = "048_checklist_summary_partition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_old_tables() -> None:
    for table_name in (
        "fin_reconciliation_checklist_product_summary_rows",
        "fin_reconciliation_checklist_receipt_summary_rows",
        "fin_reconciliation_checklist_payable_balance_summary_rows",
        "fin_reconciliation_checklist_summary_product_rows",
        "fin_reconciliation_checklist_summary_rows",
        "fin_reconciliation_checklist_details",
        "fin_reconciliation_checklist_order_keys",
        "fin_reconciliation_checklist_entities",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
    for sequence_name in (
        "fin_reconciliation_checklist_details_id_seq",
        "fin_reconciliation_checklist_product_summary_rows_id_seq",
        "fin_reconciliation_checklist_receipt_summary_rows_id_seq",
        "fin_reconciliation_checklist_payable_balance_summary_rows_id_seq",
        "fin_reconciliation_checklist_summary_rows_id_seq",
        "fin_reconciliation_checklist_summary_product_rows_id_seq",
    ):
        op.execute(f"DROP SEQUENCE IF EXISTS {sequence_name} CASCADE")


def upgrade() -> None:
    # Product decision: old checklist data is cleared/replaced because the old
    # flow did not have子订单号 and cannot be migrated into the new base table.
    op.execute("TRUNCATE TABLE fin_reconciliation_checklist_tasks RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE fin_reconciliation_checklist_upload_files RESTART IDENTITY CASCADE")
    _drop_old_tables()

    op.create_table(
        "fin_reconciliation_checklist_order_keys",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("sub_order_no", sa.String(length=200), nullable=False, comment="子订单号"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="结算年月 YYYYMM"),
        sa.Column("detail_id", sa.BigInteger(), nullable=True, comment="明细ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="对账清单子订单全局定位表",
    )
    op.create_index("uq_fin_reconciliation_checklist_order_key", "fin_reconciliation_checklist_order_keys", ["org_id", "sub_order_no"], unique=True)
    op.create_index("idx_fin_reconciliation_checklist_order_key_period", "fin_reconciliation_checklist_order_keys", ["org_id", "accounting_period"])

    op.create_table(
        "fin_reconciliation_checklist_details",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("task_id", sa.BigInteger(), nullable=False, comment="处理任务ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="上传文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="结算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="结算月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="结算年月 YYYYMM"),
        sa.Column("source_row_number", sa.Integer(), nullable=False, server_default="0", comment="源文件行号"),
        sa.Column("live_platform", sa.String(length=100), nullable=False, server_default="", comment="进驻的直播平台"),
        sa.Column("settlement_time", sa.DateTime(timezone=False), nullable=False, comment="结算时间"),
        sa.Column("sub_order_no", sa.String(length=200), nullable=False, server_default="", comment="子订单号"),
        sa.Column("order_time", sa.DateTime(timezone=False), nullable=True, comment="下单时间"),
        sa.Column("product_id", sa.String(length=200), nullable=False, server_default="", comment="商品ID"),
        sa.Column("product_name", sa.String(length=500), nullable=False, server_default="", comment="商品名称"),
        sa.Column("product_quantity", sa.Integer(), nullable=False, server_default="0", comment="商品数量"),
        sa.Column("talent_name", sa.String(length=500), nullable=False, server_default="", comment="达人名称"),
        sa.Column("platform_subsidy", sa.Numeric(14, 2), nullable=False, server_default="0", comment="平台补贴"),
        sa.Column("talent_subsidy", sa.Numeric(14, 2), nullable=False, server_default="0", comment="达人补贴"),
        sa.Column("douyin_pay_subsidy", sa.Numeric(14, 2), nullable=False, server_default="0", comment="抖音支付补贴"),
        sa.Column("douyin_monthly_pay_subsidy", sa.Numeric(14, 2), nullable=False, server_default="0", comment="抖音月付营销补贴"),
        sa.Column("bank_subsidy", sa.Numeric(14, 2), nullable=False, server_default="0", comment="银行补贴"),
        sa.Column("user_paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="用户实付（订单金额）"),
        sa.Column("platform_service_fee", sa.Numeric(14, 2), nullable=False, server_default="0", comment="平台服务费"),
        sa.Column("talent_commission", sa.Numeric(14, 2), nullable=False, server_default="0", comment="达人佣金"),
        sa.Column("investment_service_fee", sa.Numeric(14, 2), nullable=False, server_default="0", comment="招商服务费"),
        sa.Column("merchant_subject_name", sa.String(length=500), nullable=False, server_default="", comment="商户主体名称"),
        sa.Column("customer_service_code", sa.String(length=200), nullable=False, server_default="", comment="客服代码"),
        sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
        sa.Column("live_commission", sa.Numeric(14, 2), nullable=False, server_default="0", comment="直播推广佣金"),
        sa.Column("commission_rate", sa.Numeric(10, 6), nullable=True, comment="佣金率"),
        sa.Column("merchant_net_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额"),
        sa.Column("payment_amount", sa.Numeric(14, 2), nullable=True, comment="付款金额"),
        sa.Column("merchant_net_balance", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额余额"),
        sa.Column("merchant_payment_time", sa.DateTime(timezone=False), nullable=True, comment="付款时间（商家）"),
        sa.Column("invoice_time", sa.DateTime(timezone=False), nullable=True, comment="开票时间"),
        sa.Column("invoice_number", sa.String(length=200), nullable=False, server_default="", comment="发票号码"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="原始行JSON"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["task_id"], ["fin_reconciliation_checklist_tasks.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["fin_reconciliation_checklist_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.PrimaryKeyConstraint("id", "org_id", "accounting_period"),
        comment="对账清单订单明细底表",
        postgresql_partition_by="RANGE (accounting_period)",
    )
    op.create_index("uq_fin_reconciliation_checklist_detail_order", "fin_reconciliation_checklist_details", ["org_id", "accounting_period", "sub_order_no"], unique=True, postgresql_where=sa.text("is_deleted = false AND sub_order_no <> ''"))
    op.create_index("idx_fin_reconciliation_checklist_period_org", "fin_reconciliation_checklist_details", ["accounting_period", "org_id"], postgresql_where=sa.text("is_deleted = false"))
    op.create_index("idx_fin_reconciliation_checklist_sub_order", "fin_reconciliation_checklist_details", ["org_id", "sub_order_no"], postgresql_where=sa.text("is_deleted = false"))
    op.create_index("idx_fin_reconciliation_checklist_product_summary", "fin_reconciliation_checklist_details", ["org_id", "accounting_period", "receipt_merchant", "merchant_subject_name", "product_name"], postgresql_where=sa.text("is_deleted = false"))
    op.create_index("idx_fin_reconciliation_checklist_receipt_summary", "fin_reconciliation_checklist_details", ["org_id", "accounting_period", "merchant_subject_name", "live_platform", "receipt_merchant"], postgresql_where=sa.text("is_deleted = false"))
    op.create_index("idx_fin_reconciliation_checklist_balance_summary", "fin_reconciliation_checklist_details", ["org_id", "accounting_period", "merchant_subject_name", "receipt_merchant"], postgresql_where=sa.text("is_deleted = false"))

    def common_summary_metrics() -> list[sa.Column]:
        return [
            sa.Column("total_user_paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="用户实付合计"),
            sa.Column("total_live_commission", sa.Numeric(14, 2), nullable=False, server_default="0", comment="直播推广佣金合计"),
            sa.Column("total_merchant_net_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额合计"),
        ]

    def payable_balance_metrics() -> list[sa.Column]:
        return [
            sa.Column("total_user_paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="用户实付合计"),
            sa.Column("total_merchant_net_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额合计"),
            sa.Column("total_payment_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="付款金额合计"),
            sa.Column("total_merchant_net_balance", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额余额合计"),
        ]

    for table_name, extra_columns, metric_columns, unique_columns, unique_index_name, comment in (
        (
            "fin_reconciliation_checklist_product_summary_rows",
            [
                sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
                sa.Column("merchant_subject_name", sa.String(length=500), nullable=False, server_default="", comment="商户主体名称"),
                sa.Column("product_name", sa.String(length=500), nullable=False, server_default="", comment="商品名称"),
                sa.Column("product_quantity", sa.Integer(), nullable=False, server_default="0", comment="商品数量合计"),
            ],
            common_summary_metrics(),
            ["org_id", "accounting_period", "receipt_merchant", "merchant_subject_name", "product_name"],
            "uq_fin_reconciliation_checklist_product_summary",
            "对账清单商品维度预聚合汇总表",
        ),
        (
            "fin_reconciliation_checklist_receipt_summary_rows",
            [
                sa.Column("merchant_subject_name", sa.String(length=500), nullable=False, server_default="", comment="商户主体名称"),
                sa.Column("live_platform", sa.String(length=100), nullable=False, server_default="", comment="进驻的直播平台"),
                sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
                sa.Column("order_count", sa.Integer(), nullable=False, server_default="0", comment="订单数量"),
            ],
            common_summary_metrics(),
            ["org_id", "accounting_period", "merchant_subject_name", "live_platform", "receipt_merchant"],
            "uq_fin_reconciliation_checklist_receipt_summary",
            "对账清单收款商家维度预聚合汇总表",
        ),
        (
            "fin_reconciliation_checklist_payable_balance_summary_rows",
            [
                sa.Column("merchant_subject_name", sa.String(length=500), nullable=False, server_default="", comment="商户主体名称"),
                sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
            ],
            payable_balance_metrics(),
            ["org_id", "accounting_period", "merchant_subject_name", "receipt_merchant"],
            "uq_fin_reconciliation_checklist_payable_balance_summary",
            "对账清单商家应付余额预聚合汇总表",
        ),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
            sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="结算年份"),
            sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="结算月份"),
            sa.Column("accounting_period", sa.Integer(), nullable=False, comment="结算年月 YYYYMM"),
            *extra_columns,
            *metric_columns,
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
            sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
            sa.PrimaryKeyConstraint("id", "org_id", "accounting_period"),
            comment=comment,
            postgresql_partition_by="RANGE (accounting_period)",
        )
        op.create_index(unique_index_name, table_name, unique_columns, unique=True)


def downgrade() -> None:
    _drop_old_tables()
