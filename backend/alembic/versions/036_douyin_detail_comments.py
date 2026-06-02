"""backfill douyin detail column comments

Revision ID: 036_douyin_detail_comments
Revises: 035_merchant_reconciliation
Create Date: 2026-06-01

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "036_douyin_detail_comments"
down_revision: Union[str, None] = "035_merchant_reconciliation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "fin_douyin_dongzhang_details"
TABLE_COMMENT = "Douyin 动账核算源明细表"

DOUYIN_DETAIL_COLUMN_COMMENTS = {
    "id": "主键ID",
    "task_id": "处理任务ID",
    "file_id": "上传文件ID",
    "summary_id": "汇总表ID",
    "org_id": "所属组织ID",
    "shop_id": "店铺ID",
    "source_platform_code": "来源平台编码",
    "report_platform_code": "报表归集平台编码",
    "shop_name": "店铺名称",
    "source_year": "上传年月-年份",
    "source_month": "上传年月-月份",
    "source_period": "上传年月 YYYYMM",
    "summary_year": "汇总年月-年份",
    "summary_month": "汇总年月-月份",
    "period_source": "汇总年月来源",
    "source_row_number": "源文件行号",
    "transaction_time": "动账时间",
    "transaction_flow_no": "动账流水号",
    "transaction_direction": "动账方向",
    "transaction_amount": "动账金额",
    "transaction_account": "动账账户",
    "transaction_scene": "动账场景",
    "billing_type": "计费类型",
    "sub_order_no": "子订单号",
    "order_no": "订单号",
    "after_sale_no": "售后编号",
    "order_time": "下单时间",
    "product_id": "商品ID",
    "product_code": "商品编码",
    "product_name": "商品名称",
    "author_id": "达人ID",
    "author_name": "达人名称",
    "order_type": "订单类型",
    "order_paid_amount_raw": "订单实付应结",
    "shipping_fee": "运费实付",
    "platform_subsidy_shipping": "实际平台补贴_运费",
    "platform_subsidy": "实际平台补贴",
    "other_platform_subsidy": "其他平台补贴",
    "trade_in_deduction": "以旧换新抵扣",
    "gov_subsidy_platform": "政府补贴平台垫资",
    "author_subsidy": "实际达人补贴",
    "douyin_pay_subsidy": "实际抖音支付补贴",
    "douyin_monthly_subsidy": "实际抖音月付营销补贴",
    "bank_subsidy": "银行补贴",
    "order_refund_raw": "订单退款",
    "platform_fee_raw": "平台服务费",
    "commission_raw": "佣金",
    "provider_commission_raw": "服务商佣金",
    "channel_share": "渠道分成",
    "merchant_fee_raw": "招商服务费",
    "promotion_fee_raw": "站外推广费",
    "other_share": "其他分成",
    "is_commission_free": "是否免佣",
    "commission_free_amount": "免佣金额",
    "merchant_name": "商户主体名称",
    "remark": "备注",
    "matched_compensation": "匹配赔付",
    "refund_to_compensation": "退款转赔付",
    "cashback": "返现",
    "order_paid": "收",
    "refund_amount": "退",
    "gmv": "实收GMV",
    "platform_income": "平台其他收入",
    "platform_fee_positive": "平台服务费（正数）",
    "return_cost": "退货及其他费用",
    "commission_derived": "达人佣金",
    "bic": "BIC",
    "insurance_fee": "运费险",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "is_deleted": "是否已软删除",
    "deleted_at": "软删除时间",
}


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _comment_values() -> str:
    return ",\n            ".join(
        f"({_sql_literal(column_name)}, {_sql_literal(comment)})"
        for column_name, comment in DOUYIN_DETAIL_COLUMN_COMMENTS.items()
    )


def _column_values() -> str:
    return ",\n            ".join(
        f"({_sql_literal(column_name)})"
        for column_name in DOUYIN_DETAIL_COLUMN_COMMENTS
    )


def upgrade() -> None:
    comment_values = _comment_values()
    op.execute(
        f"""
        DO $$
        DECLARE
            target_rel regclass;
            comment_row record;
        BEGIN
            FOR target_rel IN
                SELECT {_sql_literal(TABLE_NAME)}::regclass
                UNION
                SELECT inhrelid::regclass
                FROM pg_inherits
                WHERE inhparent = {_sql_literal(TABLE_NAME)}::regclass
            LOOP
                EXECUTE format('COMMENT ON TABLE %s IS %L', target_rel, {_sql_literal(TABLE_COMMENT)});

                FOR comment_row IN
                    SELECT column_name, comment_text
                    FROM (VALUES
            {comment_values}
                    ) AS comments(column_name, comment_text)
                LOOP
                    IF EXISTS (
                        SELECT 1
                        FROM pg_attribute
                        WHERE attrelid = target_rel
                          AND attname = comment_row.column_name
                          AND NOT attisdropped
                    ) THEN
                        EXECUTE format(
                            'COMMENT ON COLUMN %s.%I IS %L',
                            target_rel,
                            comment_row.column_name,
                            comment_row.comment_text
                        );
                    END IF;
                END LOOP;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    column_values = _column_values()
    op.execute(
        f"""
        DO $$
        DECLARE
            target_rel regclass;
            column_row record;
        BEGIN
            FOR target_rel IN
                SELECT {_sql_literal(TABLE_NAME)}::regclass
                UNION
                SELECT inhrelid::regclass
                FROM pg_inherits
                WHERE inhparent = {_sql_literal(TABLE_NAME)}::regclass
            LOOP
                FOR column_row IN
                    SELECT column_name
                    FROM (VALUES
            {column_values}
                    ) AS columns(column_name)
                LOOP
                    IF EXISTS (
                        SELECT 1
                        FROM pg_attribute
                        WHERE attrelid = target_rel
                          AND attname = column_row.column_name
                          AND NOT attisdropped
                    ) THEN
                        EXECUTE format(
                            'COMMENT ON COLUMN %s.%I IS NULL',
                            target_rel,
                            column_row.column_name
                        );
                    END IF;
                END LOOP;
            END LOOP;
        END $$;
        """
    )
