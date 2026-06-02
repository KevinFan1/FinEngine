"""fix merchant red sheet live_date columns to text

Revision ID: 037_fix_merchant_live_date_text
Revises: 036_douyin_detail_comments
Create Date: 2026-06-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "037_fix_merchant_live_date_text"
down_revision: Union[str, None] = "036_douyin_detail_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_type(table_name: str, column_name: str) -> str | None:
    bind = op.get_bind()
    return bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar_one_or_none()


def _quote_table_name(table_name: str) -> str:
    return op.get_bind().dialect.identifier_preparer.quote(table_name)


def _alter_live_date_to_text(table_name: str) -> None:
    quoted_table = _quote_table_name(table_name)
    data_type = _column_type(table_name, "live_date")
    if data_type in {"character varying", "text"}:
        op.execute(sa.text(f"UPDATE {quoted_table} SET live_date = '' WHERE live_date IS NULL"))
        op.alter_column(table_name, "live_date", existing_type=sa.String(length=100), nullable=False, server_default="")
        return
    if data_type != "date":
        raise RuntimeError(f"Unexpected live_date type for {table_name}: {data_type}")

    op.execute(sa.text(f"ALTER TABLE {quoted_table} ALTER COLUMN live_date DROP DEFAULT"))
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {quoted_table}
            ALTER COLUMN live_date TYPE VARCHAR(100)
            USING COALESCE(to_char(live_date, 'YYYY-MM-DD'), '')
            """
        )
    )
    op.alter_column(table_name, "live_date", existing_type=sa.String(length=100), nullable=False, server_default="")


def _ensure_live_date_date_compatible(table_name: str) -> None:
    bind = op.get_bind()
    quoted_table = _quote_table_name(table_name)
    invalid_count = bind.execute(
        sa.text(
            f"""
            SELECT count(*)
            FROM {quoted_table}
            WHERE live_date IS NOT NULL
              AND live_date <> ''
              AND live_date !~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
            """
        )
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(f"Cannot downgrade {table_name}.live_date: found non-ISO text values")


def _alter_live_date_to_date(table_name: str) -> None:
    quoted_table = _quote_table_name(table_name)
    data_type = _column_type(table_name, "live_date")
    if data_type == "date":
        return
    if data_type not in {"character varying", "text"}:
        raise RuntimeError(f"Unexpected live_date type for {table_name}: {data_type}")

    _ensure_live_date_date_compatible(table_name)
    op.execute(sa.text(f"ALTER TABLE {quoted_table} ALTER COLUMN live_date DROP DEFAULT"))
    op.alter_column(table_name, "live_date", existing_type=sa.String(length=100), nullable=True)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {quoted_table}
            ALTER COLUMN live_date TYPE DATE
            USING NULLIF(live_date, '')::date
            """
        )
    )


def upgrade() -> None:
    _alter_live_date_to_text("fin_merchant_red_sheet_purchases")
    _alter_live_date_to_text("fin_merchant_red_sheet_payments")


def downgrade() -> None:
    _alter_live_date_to_date("fin_merchant_red_sheet_payments")
    _alter_live_date_to_date("fin_merchant_red_sheet_purchases")
