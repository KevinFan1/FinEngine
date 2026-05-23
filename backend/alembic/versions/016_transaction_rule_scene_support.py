"""add transaction scene support to transaction rules

Revision ID: 016
Revises: 015
Create Date: 2026-05-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_transaction_rules",
        sa.Column("transaction_scene", sa.String(length=200), nullable=True, comment="动账场景，空字符串表示空场景，空值表示不限制"),
    )
    op.alter_column(
        "fin_transaction_rules",
        "match_type",
        existing_type=sa.String(length=20),
        server_default="none",
    )
    op.alter_column(
        "fin_transaction_rules",
        "remark_pattern",
        existing_type=sa.String(length=1000),
        server_default="",
        existing_nullable=False,
    )
    op.execute("UPDATE fin_transaction_details SET rule_id = NULL WHERE rule_id IS NOT NULL")
    op.execute("DELETE FROM fin_transaction_rules")
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
            "remark_pattern",
            "amount_field",
            "result_direction",
        ],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.alter_column(
        "fin_transaction_rules",
        "remark_pattern",
        existing_type=sa.String(length=1000),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "fin_transaction_rules",
        "match_type",
        existing_type=sa.String(length=20),
        server_default="contains",
    )
    op.drop_column("fin_transaction_rules", "transaction_scene")
