from __future__ import annotations

from datetime import datetime

from app.utils.oss_paths import (
    build_export_oss_key,
    build_upload_oss_key,
    checklist_manual_edit_dir,
    current_oss_period,
    export_type_dir,
    upload_type_dir,
)


def test_current_oss_period_uses_current_month_format() -> None:
    assert current_oss_period(datetime(2026, 6, 11, 13, 45, 59)) == "202606"


def test_upload_type_dir_maps_common_business_types() -> None:
    assert upload_type_dir("动账") == "dongzhang"
    assert upload_type_dir("gmv") == "gmv"
    assert upload_type_dir("bic") == "bic"
    assert upload_type_dir("运费险") == "shipping-insurance"
    assert upload_type_dir("订单") == "orders"
    assert upload_type_dir("其他服务款") == "other-service-fee"
    assert upload_type_dir("红单") == "red-sheet"
    assert upload_type_dir("银行流水") == "bank-flow"
    assert upload_type_dir("对账清单-原始数据") == "reconciliation-checklist-source"


def test_checklist_manual_edit_dir_maps_task_types() -> None:
    assert checklist_manual_edit_dir("invoice_edit") == "reconciliation-checklist-invoice-edit"
    assert checklist_manual_edit_dir("merchant_edit") == "reconciliation-checklist-merchant-edit"


def test_build_upload_oss_key_uses_type_and_current_period_directory() -> None:
    oss_key = build_upload_oss_key(
        type_name="动账",
        filename="26年06月_动账_云上叙珍珠臻品店.xlsx",
        unique_token="1718088888000",
        now=datetime(2026, 6, 11, 9, 8, 7),
    )

    assert oss_key == "upload/dongzhang/202606/1718088888000_26年06月_动账_云上叙珍珠臻品店.xlsx"


def test_export_type_dir_normalizes_export_type() -> None:
    assert export_type_dir("summary.detail") == "summary-detail"
    assert export_type_dir("merchant_reconciliation.summary") == "merchant-reconciliation-summary"
    assert export_type_dir("bic.source_rows") == "bic-source-rows"


def test_build_export_oss_key_uses_type_and_current_period_directory() -> None:
    oss_key = build_export_oss_key(
        export_type="summary.detail",
        job_id=321,
        unique_token="abc123def456",
        now=datetime(2026, 6, 11, 9, 8, 7),
    )

    assert oss_key == "export/summary-detail/202606/321_abc123def456.xlsx"
