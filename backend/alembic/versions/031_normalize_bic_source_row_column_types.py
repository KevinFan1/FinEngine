"""normalize bic source row column types

Revision ID: 031
Revises: 030
Create Date: 2026-05-27 15:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _fin_parse_bic_source_timestamp(raw_value TEXT)
        RETURNS TIMESTAMP AS $$
        DECLARE
            cleaned TEXT := btrim(COALESCE(raw_value, ''));
        BEGIN
            IF cleaned = '' THEN
                RETURN NULL;
            END IF;

            BEGIN
                RETURN cleaned::timestamp;
            EXCEPTION WHEN others THEN
                BEGIN
                    RETURN to_timestamp(cleaned, 'YYYY"年"MM"月"DD"日" HH24:MI:SS')::timestamp;
                EXCEPTION WHEN others THEN
                    BEGIN
                        RETURN to_timestamp(cleaned, 'YYYY"年"MM"月"DD"日" HH24:MI')::timestamp;
                    EXCEPTION WHEN others THEN
                        BEGIN
                            RETURN to_timestamp(cleaned, 'YYYY"年"MM"月"DD"日"')::timestamp;
                        EXCEPTION WHEN others THEN
                            RETURN NULL;
                        END;
                    END;
                END;
            END;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ALTER COLUMN shop_name TYPE VARCHAR(500),
        ALTER COLUMN service_provider TYPE VARCHAR(500),
        ALTER COLUMN qic_warehouse TYPE VARCHAR(500)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_source_rows
        ALTER COLUMN shop_name TYPE VARCHAR(500),
        ALTER COLUMN service_provider TYPE VARCHAR(500),
        ALTER COLUMN qic_warehouse TYPE VARCHAR(500),
        ALTER COLUMN settlement_no TYPE VARCHAR(500),
        ALTER COLUMN order_code TYPE VARCHAR(500),
        ALTER COLUMN related_order_no TYPE VARCHAR(500),
        ALTER COLUMN related_waybill_no TYPE VARCHAR(500),
        ALTER COLUMN fee_item TYPE VARCHAR(500),
        ALTER COLUMN billing_completed_time DROP DEFAULT,
        ALTER COLUMN billing_completed_time DROP NOT NULL,
        ALTER COLUMN billing_completed_time TYPE TIMESTAMP USING _fin_parse_bic_source_timestamp(billing_completed_time::text),
        ALTER COLUMN business_node TYPE VARCHAR(500),
        ALTER COLUMN business_occurred_time DROP DEFAULT,
        ALTER COLUMN business_occurred_time DROP NOT NULL,
        ALTER COLUMN business_occurred_time TYPE TIMESTAMP USING _fin_parse_bic_source_timestamp(business_occurred_time::text),
        ALTER COLUMN settled_at DROP DEFAULT,
        ALTER COLUMN settled_at DROP NOT NULL,
        ALTER COLUMN settled_at TYPE TIMESTAMP USING _fin_parse_bic_source_timestamp(settled_at::text),
        ALTER COLUMN status TYPE VARCHAR(500),
        ALTER COLUMN transaction_account TYPE VARCHAR(500),
        ALTER COLUMN transaction_flow_no TYPE VARCHAR(500),
        ALTER COLUMN is_mudaibao TYPE VARCHAR(50),
        ALTER COLUMN is_child_order TYPE VARCHAR(50)
        """
    )
    op.execute("DROP FUNCTION IF EXISTS _fin_parse_bic_source_timestamp(TEXT)")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ALTER COLUMN shop_name TYPE VARCHAR(200),
        ALTER COLUMN service_provider TYPE VARCHAR(200),
        ALTER COLUMN qic_warehouse TYPE VARCHAR(200)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_source_rows
        ALTER COLUMN shop_name TYPE VARCHAR(200),
        ALTER COLUMN service_provider TYPE VARCHAR(200),
        ALTER COLUMN qic_warehouse TYPE VARCHAR(200),
        ALTER COLUMN settlement_no TYPE VARCHAR(300),
        ALTER COLUMN order_code TYPE VARCHAR(100),
        ALTER COLUMN related_order_no TYPE VARCHAR(100),
        ALTER COLUMN related_waybill_no TYPE VARCHAR(100),
        ALTER COLUMN fee_item TYPE VARCHAR(100),
        ALTER COLUMN billing_completed_time TYPE VARCHAR(100) USING COALESCE(to_char(billing_completed_time, 'YYYY-MM-DD HH24:MI:SS'), ''),
        ALTER COLUMN billing_completed_time SET DEFAULT '',
        ALTER COLUMN billing_completed_time SET NOT NULL,
        ALTER COLUMN business_node TYPE VARCHAR(100),
        ALTER COLUMN business_occurred_time TYPE VARCHAR(100) USING COALESCE(to_char(business_occurred_time, 'YYYY-MM-DD HH24:MI:SS'), ''),
        ALTER COLUMN business_occurred_time SET DEFAULT '',
        ALTER COLUMN business_occurred_time SET NOT NULL,
        ALTER COLUMN settled_at TYPE VARCHAR(100) USING COALESCE(to_char(settled_at, 'YYYY-MM-DD HH24:MI:SS'), ''),
        ALTER COLUMN settled_at SET DEFAULT '',
        ALTER COLUMN settled_at SET NOT NULL,
        ALTER COLUMN status TYPE VARCHAR(100),
        ALTER COLUMN transaction_account TYPE VARCHAR(100),
        ALTER COLUMN transaction_flow_no TYPE VARCHAR(200),
        ALTER COLUMN is_mudaibao TYPE VARCHAR(20),
        ALTER COLUMN is_child_order TYPE VARCHAR(20)
        """
    )
