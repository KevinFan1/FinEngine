"""add transaction major categories and subject bindings

Revision ID: 021
Revises: 020
Create Date: 2026-05-25 00:00:00.000000

"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_transaction_major_categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="大分类名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100", comment="排序"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1", comment="状态：1=启用 0=停用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算大分类表",
    )
    op.create_index(
        "uq_fin_transaction_major_category_name",
        "fin_transaction_major_categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.add_column(
        "fin_transaction_subjects",
        sa.Column("major_category_id", sa.BigInteger(), nullable=True, comment="大分类ID"),
    )
    op.add_column(
        "fin_transaction_subjects",
        sa.Column("cash_flow_item_id", sa.BigInteger(), nullable=True, comment="现金流项目ID"),
    )
    op.create_foreign_key(
        "fk_fin_transaction_subjects_major_category_id",
        "fin_transaction_subjects",
        "fin_transaction_major_categories",
        ["major_category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_fin_transaction_subjects_cash_flow_item_id",
        "fin_transaction_subjects",
        "fin_cash_flow_items",
        ["cash_flow_item_id"],
        ["id"],
    )
    op.create_index(
        "idx_fin_transaction_subjects_major_category",
        "fin_transaction_subjects",
        ["major_category_id", "sort_order"],
    )
    op.create_index(
        "idx_fin_transaction_subjects_cash_flow_item",
        "fin_transaction_subjects",
        ["cash_flow_item_id"],
    )

    op.add_column(
        "fin_transaction_details",
        sa.Column("major_category_id", sa.BigInteger(), nullable=True, comment="大分类ID快照"),
    )
    op.add_column(
        "fin_transaction_details",
        sa.Column("major_category_name", sa.String(length=100), nullable=True, comment="大分类名称快照"),
    )
    op.create_foreign_key(
        "fk_fin_transaction_details_major_category_id",
        "fin_transaction_details",
        "fin_transaction_major_categories",
        ["major_category_id"],
        ["id"],
    )
    op.create_index(
        "idx_fin_transaction_details_major_category",
        "fin_transaction_details",
        ["major_category_id", "accounting_year", "accounting_month"],
    )

    op.add_column(
        "fin_transaction_summary_rows",
        sa.Column("major_category_id", sa.BigInteger(), nullable=True, comment="大分类ID快照"),
    )
    op.add_column(
        "fin_transaction_summary_rows",
        sa.Column("major_category_name", sa.String(length=100), nullable=True, comment="大分类名称快照"),
    )
    op.add_column(
        "fin_transaction_summary_rows",
        sa.Column("cash_flow_item_id", sa.BigInteger(), nullable=True, comment="现金流项目ID快照"),
    )
    op.create_foreign_key(
        "fk_fin_transaction_summary_rows_major_category_id",
        "fin_transaction_summary_rows",
        "fin_transaction_major_categories",
        ["major_category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_fin_transaction_summary_rows_cash_flow_item_id",
        "fin_transaction_summary_rows",
        "fin_cash_flow_items",
        ["cash_flow_item_id"],
        ["id"],
    )
    op.create_index(
        "idx_fin_transaction_summary_major_category",
        "fin_transaction_summary_rows",
        ["major_category_id", "accounting_year", "accounting_month"],
    )
    op.create_index(
        "idx_fin_transaction_summary_cash_flow_item",
        "fin_transaction_summary_rows",
        ["cash_flow_item_id", "accounting_year", "accounting_month"],
    )

    _backfill_transaction_major_categories()


def downgrade() -> None:
    op.drop_index("idx_fin_transaction_summary_cash_flow_item", table_name="fin_transaction_summary_rows")
    op.drop_index("idx_fin_transaction_summary_major_category", table_name="fin_transaction_summary_rows")
    op.drop_constraint("fk_fin_transaction_summary_rows_cash_flow_item_id", "fin_transaction_summary_rows", type_="foreignkey")
    op.drop_constraint("fk_fin_transaction_summary_rows_major_category_id", "fin_transaction_summary_rows", type_="foreignkey")
    op.drop_column("fin_transaction_summary_rows", "cash_flow_item_id")
    op.drop_column("fin_transaction_summary_rows", "major_category_name")
    op.drop_column("fin_transaction_summary_rows", "major_category_id")

    op.drop_index("idx_fin_transaction_details_major_category", table_name="fin_transaction_details")
    op.drop_constraint("fk_fin_transaction_details_major_category_id", "fin_transaction_details", type_="foreignkey")
    op.drop_column("fin_transaction_details", "major_category_name")
    op.drop_column("fin_transaction_details", "major_category_id")

    op.drop_index("idx_fin_transaction_subjects_cash_flow_item", table_name="fin_transaction_subjects")
    op.drop_index("idx_fin_transaction_subjects_major_category", table_name="fin_transaction_subjects")
    op.drop_constraint("fk_fin_transaction_subjects_cash_flow_item_id", "fin_transaction_subjects", type_="foreignkey")
    op.drop_constraint("fk_fin_transaction_subjects_major_category_id", "fin_transaction_subjects", type_="foreignkey")
    op.drop_column("fin_transaction_subjects", "cash_flow_item_id")
    op.drop_column("fin_transaction_subjects", "major_category_id")

    op.drop_index("uq_fin_transaction_major_category_name", table_name="fin_transaction_major_categories")
    op.drop_table("fin_transaction_major_categories")


def _backfill_transaction_major_categories() -> None:
    bind = op.get_bind()
    context = op.get_context()

    level1_rows = list(
        bind.execute(
            sa.text(
                """
                SELECT id, name, sort_order
                FROM fin_cash_flow_items
                WHERE is_deleted = false
                  AND status = 1
                  AND level = 1
                ORDER BY sort_order, id
                """
            )
        )
        .mappings()
    )
    if level1_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO fin_transaction_major_categories (name, sort_order, status)
                VALUES (:name, :sort_order, 1)
                """
            ),
            [
                {
                    "name": row["name"],
                    "sort_order": row["sort_order"],
                }
                for row in level1_rows
            ],
        )

    major_category_rows = bind.execute(
        sa.text(
            """
            SELECT id, name
            FROM fin_transaction_major_categories
            WHERE is_deleted = false
            """
        )
    ).mappings()
    major_category_by_name = {
        row["name"]: int(row["id"])
        for row in major_category_rows
    }

    cash_flow_rows = bind.execute(
        sa.text(
            """
            SELECT child.id AS cash_flow_item_id, child.name AS subject_name, parent.name AS parent_name
            FROM fin_cash_flow_items AS child
            JOIN fin_cash_flow_items AS parent ON parent.id = child.parent_id
            WHERE child.is_deleted = false
              AND parent.is_deleted = false
              AND child.status = 1
              AND parent.status = 1
              AND child.level = 2
              AND parent.level = 1
            ORDER BY child.id
            """
        )
    ).mappings()

    matches_by_subject_name: dict[str, list[dict[str, int | str]]] = defaultdict(list)
    for row in cash_flow_rows:
        matches_by_subject_name[str(row["subject_name"])].append(
            {
                "cash_flow_item_id": int(row["cash_flow_item_id"]),
                "parent_name": str(row["parent_name"]),
            }
        )

    subject_rows = bind.execute(
        sa.text(
            """
            SELECT id, name
            FROM fin_transaction_subjects
            WHERE is_deleted = false
            ORDER BY id
            """
        )
    ).mappings()

    updates: list[dict[str, int]] = []
    unresolved: list[str] = []
    conflicts: list[str] = []
    for row in subject_rows:
        subject_name = str(row["name"])
        matches = matches_by_subject_name.get(subject_name, [])
        if len(matches) != 1:
            if not matches:
                unresolved.append(subject_name)
            else:
                match_desc = ", ".join(
                    f"{item['cash_flow_item_id']}->{item['parent_name']}"
                    for item in matches
                )
                conflicts.append(f"{subject_name}: {match_desc}")
            continue
        match = matches[0]
        major_category_id = major_category_by_name.get(str(match["parent_name"]))
        if major_category_id is None:
            unresolved.append(subject_name)
            continue
        updates.append(
            {
                "id": int(row["id"]),
                "major_category_id": int(major_category_id),
                "cash_flow_item_id": int(match["cash_flow_item_id"]),
            }
        )

    if updates:
        bind.execute(
            sa.text(
                """
                UPDATE fin_transaction_subjects
                SET major_category_id = :major_category_id,
                    cash_flow_item_id = :cash_flow_item_id
                WHERE id = :id
                """
            ),
            updates,
        )

    bind.execute(
        sa.text(
            """
            UPDATE fin_transaction_details AS detail
            SET major_category_id = subject.major_category_id,
                major_category_name = category.name
            FROM fin_transaction_subjects AS subject
            LEFT JOIN fin_transaction_major_categories AS category
                ON category.id = subject.major_category_id
               AND category.is_deleted = false
            WHERE detail.subject_id = subject.id
              AND detail.is_deleted = false
              AND subject.is_deleted = false
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE fin_transaction_summary_rows AS summary
            SET major_category_id = subject.major_category_id,
                major_category_name = category.name,
                cash_flow_item_id = subject.cash_flow_item_id
            FROM fin_transaction_subjects AS subject
            LEFT JOIN fin_transaction_major_categories AS category
                ON category.id = subject.major_category_id
               AND category.is_deleted = false
            WHERE summary.subject_id = subject.id
              AND summary.is_deleted = false
              AND subject.is_deleted = false
            """
        )
    )

    if unresolved:
        context.config.print_stdout(
            "transaction major category backfill unresolved subjects: "
            + ", ".join(sorted(set(unresolved)))
        )
    if conflicts:
        context.config.print_stdout(
            "transaction major category backfill conflicting subjects: "
            + " | ".join(sorted(set(conflicts)))
        )
