"""make transaction accounting rules global

Revision ID: 009
Revises: 008
Create Date: 2026-05-20 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM fin_transaction_summary_rows")
    op.execute("DELETE FROM fin_transaction_details")
    op.execute("DELETE FROM fin_transaction_tasks")
    op.execute("DELETE FROM fin_transaction_upload_files")
    op.execute("DELETE FROM fin_transaction_rules")
    op.execute("DELETE FROM fin_transaction_categories")
    op.execute("DELETE FROM fin_transaction_subjects")

    op.drop_index("idx_fin_transaction_rules_lookup", table_name="fin_transaction_rules")
    op.drop_index("uq_fin_transaction_subject_org_name", table_name="fin_transaction_subjects")

    op.drop_constraint("fin_transaction_rules_org_id_fkey", "fin_transaction_rules", type_="foreignkey")
    op.drop_constraint("fin_transaction_categories_org_id_fkey", "fin_transaction_categories", type_="foreignkey")
    op.drop_constraint("fin_transaction_subjects_org_id_fkey", "fin_transaction_subjects", type_="foreignkey")
    op.drop_column("fin_transaction_rules", "org_id")
    op.drop_column("fin_transaction_categories", "org_id")
    op.drop_column("fin_transaction_subjects", "org_id")

    op.create_index(
        "uq_fin_transaction_subject_name",
        "fin_transaction_subjects",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
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
    op.create_index(
        "idx_fin_transaction_rules_lookup",
        "fin_transaction_rules",
        ["platform_code", "transaction_direction", "status"],
    )


def downgrade() -> None:
    op.add_column("fin_transaction_subjects", sa.Column("org_id", sa.BigInteger(), nullable=True, comment="所属组织ID"))
    op.add_column("fin_transaction_categories", sa.Column("org_id", sa.BigInteger(), nullable=True, comment="所属组织ID"))
    op.add_column("fin_transaction_rules", sa.Column("org_id", sa.BigInteger(), nullable=True, comment="所属组织ID"))

    op.drop_index("idx_fin_transaction_rules_lookup", table_name="fin_transaction_rules")
    op.drop_index("uq_fin_transaction_rule_business_key", table_name="fin_transaction_rules")
    op.drop_index("uq_fin_transaction_subject_name", table_name="fin_transaction_subjects")

    op.create_foreign_key(
        "fin_transaction_subjects_org_id_fkey",
        "fin_transaction_subjects",
        "fin_organizations",
        ["org_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fin_transaction_categories_org_id_fkey",
        "fin_transaction_categories",
        "fin_organizations",
        ["org_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fin_transaction_rules_org_id_fkey",
        "fin_transaction_rules",
        "fin_organizations",
        ["org_id"],
        ["id"],
    )
    op.create_index(
        "uq_fin_transaction_subject_org_name",
        "fin_transaction_subjects",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_transaction_rules_lookup",
        "fin_transaction_rules",
        ["org_id", "platform_code", "transaction_direction", "status"],
    )
