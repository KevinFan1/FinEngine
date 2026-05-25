"""add transaction subject account type

Revision ID: 023
Revises: 022
Create Date: 2026-05-25 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_transaction_subjects",
        sa.Column(
            "account_type",
            sa.String(length=20),
            nullable=False,
            server_default="动账账户",
            comment="账户类型：银行账户/动账账户",
        ),
    )
    op.execute("UPDATE fin_transaction_subjects SET account_type = '动账账户' WHERE account_type IS NULL")
    op.execute("DROP INDEX IF EXISTS uq_fin_transaction_subject_name")
    op.execute("DROP INDEX IF EXISTS uq_fin_transaction_subject_scope_name")
    op.create_index(
        "uq_fin_transaction_subject_scope_name",
        "fin_transaction_subjects",
        ["major_category_id", "account_type", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_fin_transaction_subject_scope_name", table_name="fin_transaction_subjects")
    op.execute("DROP INDEX IF EXISTS uq_fin_transaction_subject_name")
    op.create_index(
        "uq_fin_transaction_subject_name",
        "fin_transaction_subjects",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_column("fin_transaction_subjects", "account_type")
