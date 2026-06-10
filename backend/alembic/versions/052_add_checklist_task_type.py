"""add checklist task type

Revision ID: 052_checklist_task_type
Revises: 051_checklist_unique_id
Create Date: 2026-06-10

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "052_checklist_task_type"
down_revision: Union[str, None] = "051_checklist_unique_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_reconciliation_checklist_tasks",
        sa.Column(
            "task_type",
            sa.String(length=30),
            nullable=False,
            server_default="source_import",
            comment="任务类型：source_import=底表导入 invoice_edit=发票修改 merchant_edit=商家修改",
        ),
    )
    op.alter_column("fin_reconciliation_checklist_tasks", "task_type", server_default=None)


def downgrade() -> None:
    op.drop_column("fin_reconciliation_checklist_tasks", "task_type")
