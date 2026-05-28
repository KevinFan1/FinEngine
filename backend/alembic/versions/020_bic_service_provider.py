"""add service provider to bic accounting rows

Revision ID: 020
Revises: 019
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_bic_details",
        sa.Column(
            "service_provider",
            sa.String(length=500),
            nullable=False,
            server_default="-",
            comment="服务商",
        ),
    )
    op.create_index("idx_fin_bic_details_provider", "fin_bic_details", ["service_provider"])

    op.add_column(
        "fin_bic_report_rows",
        sa.Column(
            "service_provider",
            sa.String(length=200),
            nullable=False,
            server_default="-",
            comment="服务商",
        ),
    )
    op.create_index("idx_fin_bic_report_provider", "fin_bic_report_rows", ["service_provider"])


def downgrade() -> None:
    op.drop_index("idx_fin_bic_report_provider", table_name="fin_bic_report_rows")
    op.drop_column("fin_bic_report_rows", "service_provider")
    op.drop_index("idx_fin_bic_details_provider", table_name="fin_bic_details")
    op.drop_column("fin_bic_details", "service_provider")
