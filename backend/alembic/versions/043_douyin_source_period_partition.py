"""ensure douyin details partition by upload period rule month

Revision ID: 043_douyin_source_partition
Revises: 042_purchase_product_code
Create Date: 2026-06-03

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "043_douyin_source_partition"
down_revision: Union[str, None] = "042_purchase_product_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "fin_douyin_dongzhang_details"
LEGACY_TABLE = "fin_douyin_dongzhang_details_legacy_043"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _table_exists(table_name: str) -> bool:
    return bool(
        op.get_bind().execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name}).scalar()
    )


def _partition_key_def(table_name: str) -> str | None:
    return op.get_bind().execute(
        text("SELECT pg_get_partkeydef(to_regclass(:table_name))"),
        {"table_name": table_name},
    ).scalar()


def _partition_key_uses(table_name: str, column_name: str) -> bool:
    partition_key = (_partition_key_def(table_name) or "").lower()
    return column_name.lower() in partition_key


def upgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    if not _partition_key_uses(TABLE_NAME, "source_period"):
        _repartition_to_source_period()

    op.execute(f"ALTER TABLE {TABLE_NAME} DROP COLUMN IF EXISTS summary_period")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_year IS '核算汇总年月-年份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_month IS '核算汇总年月-月份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_period IS '核算汇总年月 YYYYMM'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.summary_year IS '业务年月-年份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.summary_month IS '业务年月-月份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.period_source IS '业务年月来源'")
    _copy_parent_comments_to_partitions(TABLE_NAME)


def downgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_year IS '上传年月-年份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_month IS '上传年月-月份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.source_period IS '上传年月 YYYYMM'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.summary_year IS '汇总年月-年份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.summary_month IS '汇总年月-月份'")
    op.execute(f"COMMENT ON COLUMN {TABLE_NAME}.period_source IS '汇总年月来源'")
    _copy_parent_comments_to_partitions(TABLE_NAME)


def _repartition_to_source_period() -> None:
    if _table_exists(LEGACY_TABLE):
        raise RuntimeError(f"legacy table {LEGACY_TABLE} already exists")

    op.execute(f"ALTER TABLE {TABLE_NAME} RENAME TO {LEGACY_TABLE}")
    _rename_attached_partitions(LEGACY_TABLE, "_legacy_043")
    _drop_detail_indexes_and_constraints(LEGACY_TABLE)

    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_douyin_dongzhang_details_id_seq")
    op.execute(
        f"""
        CREATE TABLE {TABLE_NAME} (
            LIKE {LEGACY_TABLE}
            INCLUDING DEFAULTS
            INCLUDING CONSTRAINTS
            INCLUDING COMMENTS
            INCLUDING STORAGE
        ) PARTITION BY RANGE (source_period)
        """
    )
    op.execute(f"ALTER TABLE {TABLE_NAME} DROP COLUMN IF EXISTS summary_period")
    op.execute(f"ALTER SEQUENCE fin_douyin_dongzhang_details_id_seq OWNED BY {TABLE_NAME}.id")
    op.execute(f"COMMENT ON TABLE {TABLE_NAME} IS '抖音动账核算源明细表'")
    _add_detail_foreign_keys()
    _create_partitions_from_column(LEGACY_TABLE, partition_column="source_period")
    _copy_common_columns(LEGACY_TABLE, TABLE_NAME)
    op.execute(f"ALTER TABLE {TABLE_NAME} ADD CONSTRAINT pk_douyin_dongzhang_details PRIMARY KEY (id, source_period)")
    _set_sequence_value()
    _create_source_partition_indexes()
    _copy_parent_comments_to_partitions(TABLE_NAME)
    op.execute(f"DROP TABLE IF EXISTS {LEGACY_TABLE} CASCADE")


def _rename_attached_partitions(parent_table: str, suffix: str) -> None:
    parent_literal = _sql_literal(parent_table)
    suffix_literal = _sql_literal(suffix)
    max_prefix_length = 63 - len(suffix)
    op.execute(
        f"""
        DO $$
        DECLARE
            child_row record;
            renamed_child TEXT;
        BEGIN
            FOR child_row IN
                SELECT n.nspname, c.relname
                FROM pg_inherits i
                JOIN pg_class c ON c.oid = i.inhrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE i.inhparent = {parent_literal}::regclass
            LOOP
                IF right(child_row.relname, length({suffix_literal})) = {suffix_literal} THEN
                    CONTINUE;
                END IF;
                renamed_child := left(child_row.relname, {max_prefix_length}) || {suffix_literal};
                IF to_regclass(format('%I.%I', child_row.nspname, renamed_child)) IS NOT NULL THEN
                    RAISE EXCEPTION 'partition rename target already exists: %.%', child_row.nspname, renamed_child;
                END IF;
                EXECUTE format('ALTER TABLE %I.%I RENAME TO %I', child_row.nspname, child_row.relname, renamed_child);
            END LOOP;
        END $$;
        """
    )


def _drop_detail_indexes_and_constraints(table_name: str) -> None:
    op.execute(f"ALTER TABLE IF EXISTS {table_name} DROP CONSTRAINT IF EXISTS pk_douyin_dongzhang_details CASCADE")
    op.execute(f"ALTER TABLE IF EXISTS {table_name} DROP CONSTRAINT IF EXISTS fin_douyin_dongzhang_details_pkey CASCADE")
    for index_name in (
        "uq_douyin_dongzhang_detail_flow",
        "idx_douyin_dongzhang_detail_id",
        "idx_douyin_dongzhang_detail_summary",
        "idx_douyin_dongzhang_detail_task",
        "idx_douyin_dongzhang_detail_file",
        "idx_douyin_dongzhang_detail_source_period",
        "idx_douyin_dongzhang_detail_summary_period",
    ):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")


def _add_detail_foreign_keys() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = {_sql_literal(TABLE_NAME)}::regclass
                  AND conname = 'fk_douyin_dongzhang_details_task'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT fk_douyin_dongzhang_details_task
                FOREIGN KEY (task_id) REFERENCES fin_processing_tasks(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = {_sql_literal(TABLE_NAME)}::regclass
                  AND conname = 'fk_douyin_dongzhang_details_file'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT fk_douyin_dongzhang_details_file
                FOREIGN KEY (file_id) REFERENCES fin_upload_files(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = {_sql_literal(TABLE_NAME)}::regclass
                  AND conname = 'fk_douyin_dongzhang_details_summary'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT fk_douyin_dongzhang_details_summary
                FOREIGN KEY (summary_id) REFERENCES fin_financial_summaries(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = {_sql_literal(TABLE_NAME)}::regclass
                  AND conname = 'fk_douyin_dongzhang_details_org'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT fk_douyin_dongzhang_details_org
                FOREIGN KEY (org_id) REFERENCES fin_organizations(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = {_sql_literal(TABLE_NAME)}::regclass
                  AND conname = 'fk_douyin_dongzhang_details_shop'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT fk_douyin_dongzhang_details_shop
                FOREIGN KEY (shop_id) REFERENCES fin_shops(id);
            END IF;
        END $$;
        """
    )


def _create_partitions_from_column(source_table: str, *, partition_column: str) -> None:
    source_literal = _sql_literal(source_table)
    column_literal = _sql_literal(partition_column)
    op.execute(
        f"""
        DO $$
        DECLARE
            period_value INTEGER;
            next_period INTEGER;
            partition_name TEXT;
        BEGIN
            FOR period_value IN
                EXECUTE format(
                    'SELECT DISTINCT %1$I::INTEGER FROM %2$s WHERE %1$I IS NOT NULL AND %1$I > 0'
                    || ' UNION SELECT to_char(month_value, ''YYYYMM'')::INTEGER'
                    || ' FROM generate_series(date_trunc(''month'', CURRENT_DATE),'
                    || ' date_trunc(''month'', CURRENT_DATE) + interval ''12 months'','
                    || ' interval ''1 month'') AS month_value'
                    || ' ORDER BY 1',
                    {column_literal},
                    {source_literal}
                )
            LOOP
                next_period := CASE
                    WHEN period_value % 100 = 12 THEN ((period_value / 100)::INTEGER + 1) * 100 + 1
                    ELSE period_value + 1
                END;
                partition_name := format('fin_douyin_dongzhang_details_%s', period_value);
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF {TABLE_NAME} FOR VALUES FROM (%s) TO (%s)',
                    partition_name,
                    period_value,
                    next_period
                );
            END LOOP;

            CREATE TABLE IF NOT EXISTS fin_douyin_dongzhang_details_default
            PARTITION OF {TABLE_NAME} DEFAULT;
        END $$;
        """
    )


def _copy_common_columns(source_table: str, target_table: str) -> None:
    source_literal = _sql_literal(source_table)
    target_literal = _sql_literal(target_table)
    op.execute(
        f"""
        DO $$
        DECLARE
            column_names TEXT;
        BEGIN
            SELECT string_agg(format('%I', target_column.attname), ', ' ORDER BY target_column.attnum)
            INTO column_names
            FROM pg_attribute target_column
            WHERE target_column.attrelid = {target_literal}::regclass
              AND target_column.attnum > 0
              AND NOT target_column.attisdropped
              AND EXISTS (
                  SELECT 1
                  FROM pg_attribute source_column
                  WHERE source_column.attrelid = {source_literal}::regclass
                    AND source_column.attname = target_column.attname
                    AND source_column.attnum > 0
                    AND NOT source_column.attisdropped
              );

            IF column_names IS NULL THEN
                RAISE EXCEPTION 'no common columns to copy from % to %', {source_literal}, {target_literal};
            END IF;

            EXECUTE format(
                'INSERT INTO %s (%s) SELECT %s FROM %s',
                {target_literal},
                column_names,
                column_names,
                {source_literal}
            );
        END $$;
        """
    )


def _set_sequence_value() -> None:
    op.execute(
        f"""
        SELECT setval(
            'fin_douyin_dongzhang_details_id_seq',
            GREATEST(
                COALESCE((SELECT max(id) FROM {TABLE_NAME}), 0),
                COALESCE((SELECT last_value FROM fin_douyin_dongzhang_details_id_seq), 0)
            ),
            true
        )
        """
    )


def _create_source_partition_indexes() -> None:
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_douyin_dongzhang_detail_flow
        ON {TABLE_NAME} (
            org_id,
            source_platform_code,
            shop_id,
            source_period,
            transaction_flow_no
        )
        WHERE is_deleted = false AND transaction_flow_no <> ''
        """
    )
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_id ON {TABLE_NAME}(id)")
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary
        ON {TABLE_NAME} (summary_id)
        WHERE is_deleted = false
        """
    )
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_task ON {TABLE_NAME}(task_id)")
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_file ON {TABLE_NAME}(file_id)")
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_source_period
        ON {TABLE_NAME} (
            org_id,
            source_platform_code,
            shop_id,
            source_period
        )
        WHERE is_deleted = false
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary_period
        ON {TABLE_NAME} (
            org_id,
            source_platform_code,
            shop_id,
            summary_year,
            summary_month
        )
        WHERE is_deleted = false
        """
    )


def _copy_parent_comments_to_partitions(parent_table: str) -> None:
    if not _table_exists(parent_table):
        return
    parent_literal = _sql_literal(parent_table)
    op.execute(
        f"""
        DO $$
        DECLARE
            target_rel regclass;
            table_comment TEXT;
            comment_row record;
        BEGIN
            table_comment := obj_description({parent_literal}::regclass, 'pg_class');
            FOR target_rel IN
                SELECT inhrelid::regclass
                FROM pg_inherits
                WHERE inhparent = {parent_literal}::regclass
            LOOP
                IF table_comment IS NOT NULL THEN
                    EXECUTE format('COMMENT ON TABLE %s IS %L', target_rel, table_comment);
                END IF;

                FOR comment_row IN
                    SELECT a.attname, d.description
                    FROM pg_attribute a
                    JOIN pg_description d
                      ON d.objoid = a.attrelid
                     AND d.objsubid = a.attnum
                    WHERE a.attrelid = {parent_literal}::regclass
                      AND a.attnum > 0
                      AND NOT a.attisdropped
                LOOP
                    EXECUTE format(
                        'COMMENT ON COLUMN %s.%I IS %L',
                        target_rel,
                        comment_row.attname,
                        comment_row.description
                    );
                END LOOP;
            END LOOP;
        END $$;
        """
    )
