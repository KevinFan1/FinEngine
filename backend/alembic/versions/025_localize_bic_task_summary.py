"""localize bic task result summary

Revision ID: 025
Revises: 024
Create Date: 2026-05-26 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE fin_bic_tasks
        SET result_summary =
            (
                result_summary
                - 'type'
                - 'total_rows'
                - 'success_rows'
                - 'failed_rows'
                - 'groups'
                - 'report_groups'
                - 'errors'
                - 'detail_ids'
                - 'report_ids'
                - 'report_id'
            )
            || CASE
                WHEN result_summary ? 'type'
                THEN jsonb_build_object(
                    '文件类型',
                    CASE
                        WHEN lower(result_summary->>'type') = 'bic' THEN 'BIC'
                        ELSE result_summary->>'type'
                    END
                )
                ELSE '{}'::jsonb
            END
            || CASE WHEN result_summary ? 'total_rows' THEN jsonb_build_object('总行数', result_summary->'total_rows') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'success_rows' THEN jsonb_build_object('符合条件行数', result_summary->'success_rows') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'failed_rows' THEN jsonb_build_object('失败行数', result_summary->'failed_rows') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'groups' THEN jsonb_build_object('明细分组数', result_summary->'groups') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'report_groups' THEN jsonb_build_object('报表分组数', result_summary->'report_groups') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'errors' THEN jsonb_build_object('错误明细', result_summary->'errors') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'detail_ids' THEN jsonb_build_object('明细记录ID列表', result_summary->'detail_ids') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'report_ids' THEN jsonb_build_object('报表记录ID列表', result_summary->'report_ids') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? 'report_id' THEN jsonb_build_object('首个报表记录ID', result_summary->'report_id') ELSE '{}'::jsonb END
        WHERE result_summary IS NOT NULL
          AND result_summary ?| ARRAY[
            'type',
            'total_rows',
            'success_rows',
            'failed_rows',
            'groups',
            'report_groups',
            'errors',
            'detail_ids',
            'report_ids',
            'report_id'
          ]
        """
    )
    op.execute(
        """
        UPDATE fin_bic_tasks
        SET status = 'failed',
            failed_rows = 1,
            error_message = CASE
                WHEN jsonb_typeof(result_summary->'错误明细') = 'array' THEN (
                    SELECT string_agg(message, E'\n')
                    FROM jsonb_array_elements_text(result_summary->'错误明细') AS message
                )
                ELSE result_summary->>'错误明细'
            END,
            result_summary = result_summary || jsonb_build_object('文件解析失败', '是')
        WHERE result_summary ? '错误明细'
          AND COALESCE(success_rows, 0) = 0
          AND COALESCE(failed_rows, 0) = 0
          AND status IN ('success', 'partial_success')
        """
    )
    op.execute(
        """
        DELETE FROM fin_bic_details
        WHERE task_id IN (
            SELECT id
            FROM fin_bic_tasks
            WHERE result_summary->>'文件解析失败' = '是'
        )
        """
    )
    op.execute(
        """
        DELETE FROM fin_bic_report_rows
        WHERE task_id IN (
            SELECT id
            FROM fin_bic_tasks
            WHERE result_summary->>'文件解析失败' = '是'
        )
        """
    )
    op.execute(
        """
        UPDATE fin_bic_upload_files AS upload_file
        SET status = 'failed',
            error_message = task.error_message
        FROM fin_bic_tasks AS task
        WHERE task.file_id = upload_file.id
          AND task.result_summary->>'文件解析失败' = '是'
          AND task.error_message IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE fin_bic_tasks
        SET result_summary =
            (
                result_summary
                - '文件类型'
                - '总行数'
                - '符合条件行数'
                - '失败行数'
                - '明细分组数'
                - '报表分组数'
                - '错误明细'
                - '文件解析失败'
                - '明细记录ID列表'
                - '报表记录ID列表'
                - '首个报表记录ID'
            )
            || CASE WHEN result_summary ? '文件类型' THEN jsonb_build_object('type', result_summary->'文件类型') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '总行数' THEN jsonb_build_object('total_rows', result_summary->'总行数') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '符合条件行数' THEN jsonb_build_object('success_rows', result_summary->'符合条件行数') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '失败行数' THEN jsonb_build_object('failed_rows', result_summary->'失败行数') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '明细分组数' THEN jsonb_build_object('groups', result_summary->'明细分组数') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '报表分组数' THEN jsonb_build_object('report_groups', result_summary->'报表分组数') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '错误明细' THEN jsonb_build_object('errors', result_summary->'错误明细') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '明细记录ID列表' THEN jsonb_build_object('detail_ids', result_summary->'明细记录ID列表') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '报表记录ID列表' THEN jsonb_build_object('report_ids', result_summary->'报表记录ID列表') ELSE '{}'::jsonb END
            || CASE WHEN result_summary ? '首个报表记录ID' THEN jsonb_build_object('report_id', result_summary->'首个报表记录ID') ELSE '{}'::jsonb END
        WHERE result_summary IS NOT NULL
          AND result_summary ?| ARRAY[
            '文件类型',
            '总行数',
            '符合条件行数',
            '失败行数',
            '明细分组数',
            '报表分组数',
            '错误明细',
            '明细记录ID列表',
            '报表记录ID列表',
            '首个报表记录ID'
          ]
        """
    )
