"""normalize douyin detail column types

Revision ID: 029
Revises: 028
Create Date: 2026-05-27 13:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _fin_parse_douyin_detail_timestamp(raw_value TEXT)
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
        ALTER TABLE fin_douyin_dongzhang_details
        ALTER COLUMN shop_name TYPE VARCHAR(500),
        ALTER COLUMN period_source TYPE VARCHAR(100),
        ALTER COLUMN transaction_time DROP DEFAULT,
        ALTER COLUMN transaction_time DROP NOT NULL,
        ALTER COLUMN transaction_time TYPE TIMESTAMP USING _fin_parse_douyin_detail_timestamp(transaction_time::text),
        ALTER COLUMN transaction_flow_no TYPE VARCHAR(500),
        ALTER COLUMN transaction_direction TYPE VARCHAR(50),
        ALTER COLUMN transaction_account TYPE VARCHAR(500),
        ALTER COLUMN transaction_scene TYPE VARCHAR(500),
        ALTER COLUMN billing_type TYPE VARCHAR(500),
        ALTER COLUMN sub_order_no TYPE VARCHAR(500),
        ALTER COLUMN order_no TYPE VARCHAR(500),
        ALTER COLUMN after_sale_no TYPE VARCHAR(500),
        ALTER COLUMN order_time DROP DEFAULT,
        ALTER COLUMN order_time DROP NOT NULL,
        ALTER COLUMN order_time TYPE TIMESTAMP USING _fin_parse_douyin_detail_timestamp(order_time::text),
        ALTER COLUMN product_id TYPE VARCHAR(500),
        ALTER COLUMN product_name TYPE TEXT,
        ALTER COLUMN author_id TYPE VARCHAR(500),
        ALTER COLUMN author_name TYPE VARCHAR(500),
        ALTER COLUMN order_type TYPE VARCHAR(200),
        ALTER COLUMN is_commission_free TYPE VARCHAR(50),
        ALTER COLUMN merchant_name TYPE TEXT,
        ALTER COLUMN matched_compensation TYPE VARCHAR(500)
        """
    )
    op.execute("DROP FUNCTION IF EXISTS _fin_parse_douyin_detail_timestamp(TEXT)")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE fin_douyin_dongzhang_details
        ALTER COLUMN shop_name TYPE VARCHAR(200),
        ALTER COLUMN period_source TYPE VARCHAR(30),
        ALTER COLUMN transaction_time TYPE VARCHAR(100) USING COALESCE(to_char(transaction_time, 'YYYY-MM-DD HH24:MI:SS'), ''),
        ALTER COLUMN transaction_time SET DEFAULT '',
        ALTER COLUMN transaction_time SET NOT NULL,
        ALTER COLUMN transaction_flow_no TYPE VARCHAR(200),
        ALTER COLUMN transaction_direction TYPE VARCHAR(20),
        ALTER COLUMN transaction_account TYPE VARCHAR(100),
        ALTER COLUMN transaction_scene TYPE VARCHAR(200),
        ALTER COLUMN billing_type TYPE VARCHAR(100),
        ALTER COLUMN sub_order_no TYPE VARCHAR(100),
        ALTER COLUMN order_no TYPE VARCHAR(100),
        ALTER COLUMN after_sale_no TYPE VARCHAR(100),
        ALTER COLUMN order_time TYPE VARCHAR(100) USING COALESCE(to_char(order_time, 'YYYY-MM-DD HH24:MI:SS'), ''),
        ALTER COLUMN order_time SET DEFAULT '',
        ALTER COLUMN order_time SET NOT NULL,
        ALTER COLUMN product_id TYPE VARCHAR(100),
        ALTER COLUMN product_name TYPE VARCHAR(500),
        ALTER COLUMN author_id TYPE VARCHAR(100),
        ALTER COLUMN author_name TYPE VARCHAR(200),
        ALTER COLUMN order_type TYPE VARCHAR(100),
        ALTER COLUMN is_commission_free TYPE VARCHAR(20),
        ALTER COLUMN merchant_name TYPE VARCHAR(500),
        ALTER COLUMN matched_compensation TYPE VARCHAR(200)
        """
    )
