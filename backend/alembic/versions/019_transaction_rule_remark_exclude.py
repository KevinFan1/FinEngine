"""add remark exclusion support to transaction rules

Revision ID: 019
Revises: 018
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_transaction_rules",
        sa.Column(
            "remark_exclude_pattern",
            sa.String(length=1000),
            nullable=False,
            server_default="",
            comment="备注排除内容；备注包含任一内容则不匹配",
        ),
    )
    op.drop_index("uq_fin_transaction_rule_business_key", table_name="fin_transaction_rules")
    op.create_index(
        "uq_fin_transaction_rule_business_key",
        "fin_transaction_rules",
        [
            "subject_id",
            "category_id",
            "platform_code",
            "transaction_direction",
            "transaction_scene",
            "match_type",
            "remark_pattern",
            "remark_exclude_pattern",
            "amount_field",
            "result_direction",
        ],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_fin_transaction_rule_business_key", table_name="fin_transaction_rules")
    op.create_index(
        "uq_fin_transaction_rule_business_key",
        "fin_transaction_rules",
        [
            "subject_id",
            "category_id",
            "platform_code",
            "transaction_direction",
            "transaction_scene",
            "match_type",
            "remark_pattern",
            "amount_field",
            "result_direction",
        ],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_column("fin_transaction_rules", "remark_exclude_pattern")
