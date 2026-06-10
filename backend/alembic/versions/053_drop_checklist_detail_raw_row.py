"""drop checklist detail raw_row

Revision ID: 053_drop_raw_row
Revises: 052_checklist_task_type
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "053_drop_raw_row"
down_revision = "052_checklist_task_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("fin_reconciliation_checklist_details", "raw_row")


def downgrade() -> None:
    op.add_column(
        "fin_reconciliation_checklist_details",
        sa.Column(
            "raw_row",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="原始行JSON",
        ),
    )
    op.alter_column("fin_reconciliation_checklist_details", "raw_row", server_default=None)
