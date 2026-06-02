"""backfill chinese comments for database tables and columns

Revision ID: 038_backfill_chinese_comments
Revises: 037_fix_merchant_live_date_text
Create Date: 2026-06-02

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "038_backfill_chinese_comments"
down_revision: Union[str, None] = "037_fix_merchant_live_date_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_COMMENTS: dict[str, str] = {
    "fin_bic_upload_files": "BIC 独立上传文件表",
    "fin_bic_tasks": "BIC 独立任务表",
    "fin_bic_details": "BIC 核算明细汇总表",
    "fin_bic_source_rows": "BIC 源数据明细表",
    "fin_douyin_dongzhang_details": "抖音动账核算源明细表",
}


COLUMN_COMMENTS: dict[str, dict[str, str]] = {
    "fin_transaction_upload_files": {
        "source_upload_file_id": "统一上传来源文件ID",
        "shop_id": "店铺ID",
    },
    "fin_transaction_details": {
        "shop_id": "店铺ID",
    },
    "fin_transaction_summary_rows": {
        "shop_id": "店铺ID",
    },
    "fin_users": {
        "must_change_password": "首次登录后是否需要修改密码",
    },
    "fin_shops": {
        "store_long_id": "店铺长ID",
        "store_short_id": "店铺短ID",
        "settlement_period": "结算周期",
        "primary_account": "主账号",
        "purpose": "用途",
        "former_name": "历史名称",
    },
    "fin_bic_upload_files": {
        "id": "主键ID",
        "org_id": "所属组织ID",
        "user_id": "上传用户ID",
        "shop_id": "店铺ID",
        "source_upload_file_id": "统一上传来源文件ID",
        "original_name": "原始文件名",
        "oss_key": "OSS存储路径",
        "file_size": "文件大小字节数",
        "file_hash": "文件 SHA-256 哈希值",
        "platform_code": "平台编码",
        "shop_name": "店铺名称",
        "accounting_year": "核算年份",
        "accounting_month": "核算月份",
        "status": "文件状态",
        "error_message": "错误信息",
        "created_at": "创建时间",
        "updated_at": "更新时间",
        "is_deleted": "是否已软删除",
        "deleted_at": "软删除时间",
    },
    "fin_bic_tasks": {
        "id": "主键ID",
        "file_id": "BIC上传文件ID",
        "org_id": "所属组织ID",
        "user_id": "触发用户ID",
        "celery_task_id": "异步任务 ID（Celery）",
        "status": "任务状态",
        "progress": "进度百分比",
        "processed_rows": "已处理行数",
        "success_rows": "成功行数",
        "failed_rows": "失败行数",
        "error_message": "错误信息",
        "result_summary": "处理结果摘要",
        "started_at": "开始时间",
        "finished_at": "结束时间",
        "created_at": "创建时间",
        "updated_at": "更新时间",
        "is_deleted": "是否已软删除",
        "deleted_at": "软删除时间",
    },
    "fin_bic_details": {
        "id": "主键ID",
        "task_id": "处理任务ID",
        "file_id": "上传文件ID",
        "org_id": "所属组织ID",
        "shop_id": "店铺ID",
        "platform_code": "平台编码",
        "shop_name": "店铺名称",
        "accounting_year": "文件名核算年份",
        "accounting_month": "文件名核算月份",
        "service_provider": "服务商",
        "qic_warehouse": "QIC仓",
        "row_count": "汇总行数",
        "total_amount": "结算金额合计",
        "created_at": "创建时间",
        "is_deleted": "是否已软删除",
        "deleted_at": "软删除时间",
    },
    "fin_bic_source_rows": {
        "id": "主键ID",
        "task_id": "处理任务ID",
        "file_id": "上传文件ID",
        "detail_id": "BIC明细汇总ID",
        "org_id": "所属组织ID",
        "shop_id": "店铺ID",
        "platform_code": "平台编码",
        "shop_name": "店铺名称",
        "accounting_year": "文件名核算年份",
        "accounting_month": "文件名核算月份",
        "accounting_period": "文件名核算年月 YYYYMM",
        "service_provider": "服务商",
        "qic_warehouse": "QIC仓",
        "source_row_number": "源文件行号",
        "settlement_no": "结算单号",
        "order_code": "订单码",
        "related_order_no": "关联订单号",
        "related_waybill_no": "关联运单号",
        "fee_item": "费用项",
        "settlement_amount": "结算金额",
        "billing_params": "计费参数",
        "billing_completed_time": "计费完成时间",
        "business_node": "业务节点",
        "business_occurred_time": "业务发生时间",
        "settled_at": "结算时间",
        "status": "状态",
        "transaction_account": "动账账户",
        "transaction_flow_no": "动账流水号",
        "remark": "备注",
        "is_mudaibao": "是否木带宝",
        "is_child_order": "是否子单",
        "created_at": "创建时间",
        "is_deleted": "是否已软删除",
        "deleted_at": "软删除时间",
    },
    "fin_douyin_dongzhang_details": {
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
    },
}


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _comment_pairs(comments: dict[str, str]) -> str:
    return ",\n                    ".join(
        f"({_sql_literal(column_name)}, {_sql_literal(comment)})"
        for column_name, comment in comments.items()
    )


def _column_names(comments: dict[str, str]) -> str:
    return ",\n                    ".join(
        f"({_sql_literal(column_name)})"
        for column_name in comments
    )


def _apply_comments(table_name: str, table_comment: str | None, column_comments: dict[str, str], *, include_partitions: bool = False) -> None:
    if not table_comment and not column_comments:
        return

    targets_sql = (
        f"""
                SELECT {_sql_literal(table_name)}::regclass
                UNION
                SELECT inhrelid::regclass
                FROM pg_inherits
                WHERE inhparent = {_sql_literal(table_name)}::regclass
        """
        if include_partitions
        else f"SELECT {_sql_literal(table_name)}::regclass"
    )
    comment_values = _comment_pairs(column_comments)

    comment_body = ""
    if table_comment:
        comment_body += (
            f"""
                EXECUTE format('COMMENT ON TABLE %s IS %L', target_rel, {_sql_literal(table_comment)});
            """
        )
    if column_comments:
        comment_body += (
            f"""
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
            """
        )

    op.execute(
        f"""
        DO $$
        DECLARE
            target_rel regclass;
            comment_row record;
        BEGIN
            IF to_regclass({_sql_literal(table_name)}) IS NULL THEN
                RETURN;
            END IF;

            FOR target_rel IN
                {targets_sql}
            LOOP
                {comment_body}
            END LOOP;
        END $$;
        """
    )


def _clear_comments(table_name: str, column_comments: dict[str, str], *, include_partitions: bool = False) -> None:
    if not column_comments:
        return

    targets_sql = (
        f"""
                SELECT {_sql_literal(table_name)}::regclass
                UNION
                SELECT inhrelid::regclass
                FROM pg_inherits
                WHERE inhparent = {_sql_literal(table_name)}::regclass
        """
        if include_partitions
        else f"SELECT {_sql_literal(table_name)}::regclass"
    )
    column_values = _column_names(column_comments)

    op.execute(
        f"""
        DO $$
        DECLARE
            target_rel regclass;
            column_row record;
        BEGIN
            IF to_regclass({_sql_literal(table_name)}) IS NULL THEN
                RETURN;
            END IF;

            FOR target_rel IN
                {targets_sql}
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
                        EXECUTE format('COMMENT ON COLUMN %s.%I IS NULL', target_rel, column_row.column_name);
                    END IF;
                END LOOP;
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    partitioned_tables = {"fin_bic_source_rows", "fin_douyin_dongzhang_details"}
    for table_name, table_comment in TABLE_COMMENTS.items():
        _apply_comments(
            table_name,
            table_comment,
            COLUMN_COMMENTS.get(table_name, {}),
            include_partitions=table_name in partitioned_tables,
        )

    for table_name, column_comments in COLUMN_COMMENTS.items():
        if table_name in TABLE_COMMENTS:
            continue
        _apply_comments(table_name, None, column_comments, include_partitions=False)


def downgrade() -> None:
    partitioned_tables = {"fin_bic_source_rows", "fin_douyin_dongzhang_details"}
    for table_name, column_comments in COLUMN_COMMENTS.items():
        _clear_comments(
            table_name,
            column_comments,
            include_partitions=table_name in partitioned_tables,
        )
