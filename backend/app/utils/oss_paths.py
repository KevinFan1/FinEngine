from __future__ import annotations

from datetime import datetime
from pathlib import Path


UPLOAD_TYPE_DIR_MAP: dict[str, str] = {
    "动账": "dongzhang",
    "gmv": "gmv",
    "bic": "bic",
    "运费险": "shipping-insurance",
    "订单": "orders",
    "其他服务款": "other-service-fee",
    "红单": "red-sheet",
    "银行流水": "bank-flow",
    "对账清单": "reconciliation-checklist",
    "对账清单-原始数据": "reconciliation-checklist-source",
    "对账清单-发票更新": "reconciliation-checklist-invoice",
    "对账清单-商家更新": "reconciliation-checklist-merchant",
}

CHECKLIST_MANUAL_EDIT_DIR_MAP: dict[str, str] = {
    "invoice_edit": "reconciliation-checklist-invoice-edit",
    "merchant_edit": "reconciliation-checklist-merchant-edit",
}


def current_oss_period(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"{current.year}{current.month:02d}"


def sanitize_oss_filename(filename: str) -> str:
    safe_name = Path(filename).name.replace("\\", "_").replace("/", "_").strip()
    return safe_name or "unnamed.xlsx"


def upload_type_dir(type_name: str | None) -> str:
    normalized = (type_name or "").strip()
    return UPLOAD_TYPE_DIR_MAP.get(normalized, "misc")


def checklist_manual_edit_dir(task_type: str) -> str:
    return CHECKLIST_MANUAL_EDIT_DIR_MAP.get(task_type, "reconciliation-checklist-manual-edit")


def build_upload_oss_key(
    *,
    type_name: str | None,
    filename: str,
    unique_token: str,
    now: datetime | None = None,
) -> str:
    return (
        f"upload/{upload_type_dir(type_name)}/{current_oss_period(now)}/"
        f"{unique_token}_{sanitize_oss_filename(filename)}"
    )


def export_type_dir(export_type: str) -> str:
    return export_type.strip().replace("_", "-").replace(".", "-") or "export"


def build_export_oss_key(
    *,
    export_type: str,
    job_id: int,
    unique_token: str,
    now: datetime | None = None,
) -> str:
    return (
        f"export/{export_type_dir(export_type)}/{current_oss_period(now)}/"
        f"{job_id}_{unique_token}.xlsx"
    )
