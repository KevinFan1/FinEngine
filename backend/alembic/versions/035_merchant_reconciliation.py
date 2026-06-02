"""add merchant reconciliation red sheet tables

Revision ID: 035_merchant_reconciliation
Revises: 034_file_spec_upload_period_header
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "035_merchant_reconciliation"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_douyin_dongzhang_details",
        sa.Column("product_code", sa.String(length=500), nullable=False, server_default="", comment="商品编码"),
    )

    op.create_table(
        "fin_merchant_reconciliation_red_sheets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="上传用户ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=True, comment="店铺ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, server_default="douyin", comment="平台编码"),
        sa.Column("shop_name", sa.String(length=500), nullable=False, server_default="", comment="店铺名称"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="核算月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("original_name", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小字节数"),
        sa.Column("file_hash", sa.String(length=64), nullable=True, comment="文件 SHA-256 哈希值"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success", comment="状态"),
        sa.Column("purchase_rows", sa.Integer(), nullable=False, server_default="0", comment="采购明细行数"),
        sa.Column("payment_rows", sa.Integer(), nullable=False, server_default="0", comment="货款明细行数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="导入结果摘要"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账红单导入批次表",
    )
    op.create_index(
        "idx_fin_merchant_red_sheet_lookup",
        "fin_merchant_reconciliation_red_sheets",
        ["org_id", "platform_code", "shop_id", "accounting_period"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_merchant_red_sheet_created",
        "fin_merchant_reconciliation_red_sheets",
        ["org_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_merchant_red_sheet_purchases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("red_sheet_id", sa.BigInteger(), nullable=False, comment="红单批次ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=True, comment="店铺ID"),
        sa.Column("shop_name", sa.String(length=500), nullable=False, server_default="", comment="店铺名称快照"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("source_row_number", sa.Integer(), nullable=False, server_default="0", comment="源文件行号"),
        sa.Column("live_room", sa.String(length=500), nullable=False, server_default="", comment="直播间"),
        sa.Column("merchant", sa.String(length=500), nullable=False, server_default="", comment="商家"),
        sa.Column("live_date", sa.String(length=100), nullable=False, server_default="", comment="直播日期"),
        sa.Column("loan_return_order_no", sa.String(length=500), nullable=False, server_default="", comment="借/退货单号"),
        sa.Column("loan_return_date", sa.Date(), nullable=True, comment="借/退货日期"),
        sa.Column("live_code", sa.String(length=500), nullable=False, server_default="", comment="直播编号"),
        sa.Column("normalized_live_code", sa.String(length=500), nullable=False, server_default="", comment="新直播编码"),
        sa.Column("match_status", sa.String(length=500), nullable=False, server_default="", comment="匹配"),
        sa.Column("remark", sa.Text(), nullable=False, server_default="", comment="结算状态"),
        sa.Column("source_shop_name", sa.String(length=500), nullable=False, server_default="", comment="店铺"),
        sa.Column("subject", sa.String(length=500), nullable=False, server_default="", comment="主体"),
        sa.Column("summary", sa.String(length=500), nullable=False, server_default="", comment="摘要"),
        sa.Column("product_name", sa.Text(), nullable=False, server_default="", comment="货品名称"),
        sa.Column("piece_price", sa.Numeric(14, 2), nullable=False, server_default="0", comment="件/元"),
        sa.Column("gram_price", sa.Numeric(14, 2), nullable=False, server_default="0", comment="克/元"),
        sa.Column("sale_price", sa.Numeric(14, 2), nullable=False, server_default="0", comment="卖价"),
        sa.Column("borrow_quantity", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借货数量"),
        sa.Column("borrow_weight_g", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借货重量g"),
        sa.Column("borrow_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借货金额"),
        sa.Column("return_quantity", sa.Numeric(14, 2), nullable=False, server_default="0", comment="退货数量"),
        sa.Column("return_weight_g", sa.Numeric(14, 2), nullable=False, server_default="0", comment="退货重量g"),
        sa.Column("return_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="退货金额"),
        sa.Column("estimated_settlement_date", sa.Date(), nullable=True, comment="预计结款日期"),
        sa.Column("labor_fee_per_gram", sa.Numeric(14, 2), nullable=False, server_default="0", comment="工费/克"),
        sa.Column("labor_fee_per_piece", sa.Numeric(14, 2), nullable=False, server_default="0", comment="工费/件"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="原始行JSON"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["red_sheet_id"], ["fin_merchant_reconciliation_red_sheets.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账红单采购明细表",
    )
    op.create_index(
        "idx_fin_merchant_purchase_match",
        "fin_merchant_red_sheet_purchases",
        ["org_id", "shop_id", "accounting_period", "live_code"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_merchant_purchase_merchant",
        "fin_merchant_red_sheet_purchases",
        ["org_id", "shop_id", "accounting_period", "merchant", "live_date", "live_room"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_merchant_red_sheet_payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("red_sheet_id", sa.BigInteger(), nullable=False, comment="红单批次ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=True, comment="店铺ID"),
        sa.Column("shop_name", sa.String(length=500), nullable=False, server_default="", comment="店铺名称快照"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("source_row_number", sa.Integer(), nullable=False, server_default="0", comment="源文件行号"),
        sa.Column("sequence_no", sa.String(length=100), nullable=False, server_default="", comment="序号"),
        sa.Column("live_room", sa.String(length=500), nullable=False, server_default="", comment="直播间"),
        sa.Column("live_date", sa.String(length=100), nullable=False, server_default="", comment="直播日期"),
        sa.Column("merchant", sa.String(length=500), nullable=False, server_default="", comment="商家"),
        sa.Column("borrow_total_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借货总金额"),
        sa.Column("return_total_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="退货总金额"),
        sa.Column("business_fee_deduction", sa.Numeric(14, 2), nullable=False, server_default="0", comment="冲减业务费用"),
        sa.Column("deduction_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="冲减金额"),
        sa.Column("payable_goods_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付货款金额"),
        sa.Column("return_rate", sa.String(length=100), nullable=False, server_default="", comment="退货率"),
        sa.Column("settlement_subject", sa.String(length=500), nullable=False, server_default="", comment="结算主体"),
        sa.Column("receipt_subject", sa.String(length=500), nullable=False, server_default="", comment="收款主体"),
        sa.Column("cost_subject", sa.String(length=500), nullable=False, server_default="", comment="成本主体"),
        sa.Column("payable_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付款金额"),
        sa.Column("subject_collection_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="主体回款金额"),
        sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
        sa.Column("collection_merchant", sa.String(length=500), nullable=False, server_default="", comment="回款商家"),
        sa.Column("is_settled", sa.String(length=100), nullable=False, server_default="", comment="是否已结款"),
        sa.Column("is_collected", sa.String(length=100), nullable=False, server_default="", comment="是否已回款"),
        sa.Column("remark", sa.Text(), nullable=False, server_default="", comment="备注"),
        sa.Column("payment_screenshot", sa.String(length=1000), nullable=False, server_default="", comment="付款截图"),
        sa.Column("settlement_date", sa.Date(), nullable=True, comment="结算日期"),
        sa.Column("collection_date", sa.Date(), nullable=True, comment="回款日期"),
        sa.Column("deduction_remark", sa.Text(), nullable=False, server_default="", comment="冲减备注"),
        sa.Column("pending_issue", sa.Text(), nullable=False, server_default="", comment="待解决事项"),
        sa.Column("is_receipt_merchant_modified", sa.String(length=100), nullable=False, server_default="", comment="是否修改收款商家"),
        sa.Column("is_receipt_amount_modified", sa.String(length=100), nullable=False, server_default="", comment="是否修改收款金额"),
        sa.Column("modified_month", sa.String(length=100), nullable=False, server_default="", comment="修改月份"),
        sa.Column("application_date", sa.Date(), nullable=True, comment="申请日期"),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="已付"),
        sa.Column("borrow_minus_return", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借-退"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="原始行JSON"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["red_sheet_id"], ["fin_merchant_reconciliation_red_sheets.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账红单货款明细表",
    )
    op.create_index(
        "idx_fin_merchant_payment_match",
        "fin_merchant_red_sheet_payments",
        ["org_id", "shop_id", "accounting_period", "merchant", "live_date", "live_room"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_fin_merchant_payment_match", table_name="fin_merchant_red_sheet_payments")
    op.drop_table("fin_merchant_red_sheet_payments")
    op.drop_index("idx_fin_merchant_purchase_merchant", table_name="fin_merchant_red_sheet_purchases")
    op.drop_index("idx_fin_merchant_purchase_match", table_name="fin_merchant_red_sheet_purchases")
    op.drop_table("fin_merchant_red_sheet_purchases")
    op.drop_index("idx_fin_merchant_red_sheet_created", table_name="fin_merchant_reconciliation_red_sheets")
    op.drop_index("idx_fin_merchant_red_sheet_lookup", table_name="fin_merchant_reconciliation_red_sheets")
    op.drop_table("fin_merchant_reconciliation_red_sheets")
    op.drop_column("fin_douyin_dongzhang_details", "product_code")
