"""Service layer for reconciliation checklist imports and reports."""

from __future__ import annotations

import hashlib
import logging
import tempfile
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from time import perf_counter
from typing import AsyncIterator, Iterable

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, Side
from sqlalchemy import and_, func, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.models.organization import Organization
from app.models.reconciliation_checklist import (
    ReconciliationChecklistDetail,
    ReconciliationChecklistEntity,
    ReconciliationChecklistSummaryProductRow,
    ReconciliationChecklistSummaryRow,
    ReconciliationChecklistTask,
    ReconciliationChecklistUploadFile,
)
from app.models.shop import Shop
from app.models.upload import UploadFile
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.oss_service import SOURCE_FILE_UNAVAILABLE_MESSAGE, is_oss_object_unavailable_error, oss_service
from app.services.partition_maintenance_service import ensure_reconciliation_checklist_partitions_for_year
from app.services.partition_service import (
    RECONCILIATION_CHECKLIST_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
    ensure_month_partition,
)
from app.services.shop_service import ShopService
from app.services.shop_visibility import active_shop_filter
from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, open_tabular_rows, parse_datetime, safe_str
from app.utils.money import safe_decimal
from app.utils.query_filters import resolve_org_ids, split_int_filter_values

CHECKLIST_HEADERS = [
    "平台",
    "店铺",
    "动账时间",
    "动账流水号",
    "商品名称",
    "直播推广方",
    "商家",
    "收款商家",
    "订单金额",
    "直播推广佣金",
    "应付商家净额",
]
CHECKLIST_FILE_TYPE = "对账清单"
CHECKLIST_ERROR_SAMPLE_LIMIT = 20
CHECKLIST_RESULT_TASK_STATUSES = ("success", "partial_success", "failed", "expired")
CHECKLIST_PROCESSED_TASK_STATUSES = ("success", "partial_success")
CHECKLIST_EXPORT_BATCH_SIZE = 5000
CHECKLIST_SUMMARY_HEADERS = ["直播编号", "货品名称", "订单金额", "直播推广佣金", "应付商家净额"]
CHECKLIST_ENTITY_TYPES = {"live_promoter", "merchant", "receipt_merchant"}
CHECKLIST_HEADER_ALIASES = {
    "动帐流水号": "动账流水号",
    "GMV": "订单金额",
    "gmv": "订单金额",
}
CHECKLIST_EXPORT_WIDTHS = {
    "A": 10,
    "B": 36,
    "C": 18,
    "D": 18,
    "E": 18,
}
CHECKLIST_EXPORT_SIDE = Side(style="thin", color="000000")
CHECKLIST_EXPORT_BORDER = Border(
    left=CHECKLIST_EXPORT_SIDE,
    right=CHECKLIST_EXPORT_SIDE,
    top=CHECKLIST_EXPORT_SIDE,
    bottom=CHECKLIST_EXPORT_SIDE,
)
CHECKLIST_EXPORT_ALIGNMENT = Alignment(horizontal="center", vertical="center")
CHECKLIST_EXPORT_HEADER_FONT = Font(bold=True)
ChecklistScope = tuple[int, int, str, int]
logger = logging.getLogger("finengine.reconciliation_checklist")
DETAIL_INSERT_FIELDS = (
    "task_id",
    "file_id",
    "org_id",
    "shop_id",
    "platform_code",
    "shop_name",
    "accounting_year",
    "accounting_month",
    "accounting_period",
    "source_row_number",
    "transaction_time",
    "transaction_flow_no",
    "product_name",
    "live_promoter_id",
    "merchant_id",
    "receipt_merchant_id",
    "live_promoter",
    "merchant_name",
    "receipt_merchant",
    "order_amount",
    "live_commission",
    "merchant_net_amount",
)


def _canonical_header(value: object) -> str:
    text = safe_str(value).replace("帐", "账")
    text = text.strip()
    return CHECKLIST_HEADER_ALIASES.get(text, text)


def _accounting_period(year: int, month: int) -> int:
    if month < 1 or month > 12:
        raise ValueError("月份必须在 1-12 之间")
    return int(year) * 100 + int(month)


def _money(value: object) -> Decimal:
    return safe_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _capture_result_state(task: ReconciliationChecklistTask) -> dict[str, object]:
    return {
        "total_rows": task.total_rows,
        "success_rows": task.success_rows,
        "failed_rows": task.failed_rows,
        "inserted_rows": task.inserted_rows,
        "updated_rows": task.updated_rows,
        "result_summary": task.result_summary,
    }


def _restore_result_state(task: ReconciliationChecklistTask, state: dict[str, object]) -> None:
    task.total_rows = int(state.get("total_rows") or 0)
    task.success_rows = int(state.get("success_rows") or 0)
    task.failed_rows = int(state.get("failed_rows") or 0)
    task.inserted_rows = int(state.get("inserted_rows") or 0)
    task.updated_rows = int(state.get("updated_rows") or 0)
    task.result_summary = state.get("result_summary")  # type: ignore[assignment]


def _split_filter_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def _summary_key(
    *,
    org_id: int,
    period: int,
    merchant_id: int | None,
    receipt_merchant_id: int | None,
    live_promoter_id: int | None,
    merchant_name: str,
    receipt_merchant: str,
    live_promoter: str,
) -> str:
    return f"{org_id}:{period}:{merchant_id or 0}:{receipt_merchant_id or 0}:{live_promoter_id or 0}:{merchant_name}:{receipt_merchant}:{live_promoter}"


def _parse_summary_key(value: str) -> tuple[int, int, int | None, int | None, int | None, str, str, str] | None:
    parts = value.split(":", 7)
    if len(parts) == 8:
        try:
            merchant_id = int(parts[2]) or None
            receipt_merchant_id = int(parts[3]) or None
            live_promoter_id = int(parts[4]) or None
            return int(parts[0]), int(parts[1]), merchant_id, receipt_merchant_id, live_promoter_id, parts[5], parts[6], parts[7]
        except ValueError:
            return None
    if len(parts) == 5:
        try:
            return int(parts[0]), int(parts[1]), None, None, None, parts[2], parts[3], parts[4]
        except ValueError:
            return None
    return None


def _split_id_values(value: str | int | None) -> list[int]:
    return split_int_filter_values(value)


def _chunked[T](items: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _scope_condition(source_model, scopes: Sequence[ChecklistScope]):
    return tuple_(
        source_model.org_id,
        source_model.accounting_period,
        source_model.platform_code,
        source_model.shop_id,
    ).in_(scopes)


def _scope_lock_key(scope: ChecklistScope) -> int:
    raw_key = f"reconciliation_checklist:{scope[0]}:{scope[1]}:{scope[2]}:{scope[3]}"
    digest = hashlib.blake2b(raw_key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


async def _lock_scopes(db: AsyncSession, scopes: Sequence[ChecklistScope]) -> None:
    for scope in scopes:
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _scope_lock_key(scope)},
        )


def _period_filters(
    column,
    *,
    accounting_year: int | None = None,
    accounting_month: int | None = None,
    accounting_start_year: int | None = None,
    accounting_start_month: int | None = None,
    accounting_end_year: int | None = None,
    accounting_end_month: int | None = None,
) -> list:
    filters = []
    if accounting_year is not None:
        filters.append(column >= accounting_year * 100 + 1)
        filters.append(column <= accounting_year * 100 + 12)
    if accounting_year is not None and accounting_month is not None:
        filters = [column == _accounting_period(accounting_year, accounting_month)]
    if accounting_start_year is not None and accounting_start_month is not None:
        filters.append(column >= _accounting_period(accounting_start_year, accounting_start_month))
    if accounting_end_year is not None and accounting_end_month is not None:
        filters.append(column <= _accounting_period(accounting_end_year, accounting_end_month))
    return filters


def _month_label(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _sheet_title(year: int, month: int, merchant_name: str) -> str:
    raw = f"{year}年{month}月_{merchant_name}"
    for char in r"[]:*?/\\":
        raw = raw.replace(char, "_")
    return (raw or "对账清单")[:31]


def _apply_export_sheet_style(sheet) -> None:
    thin_side = Side(style="thin", color="000000")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.row <= sheet.max_row and cell.column <= 5:
                cell.border = border
    for cell in sheet[1]:
        cell.font = Font(bold=True, size=16)
    for cell in sheet[2]:
        cell.font = Font(bold=True)
    for cell in sheet[3]:
        cell.font = Font(bold=True)
    for cell in sheet[4]:
        cell.font = Font(bold=True)
    widths = {
        "A": 10,
        "B": 36,
        "C": 18,
        "D": 18,
        "E": 18,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width


def _export_cell(sheet, value: object, *, bold: bool = False, font_size: int | None = None) -> WriteOnlyCell:
    cell = WriteOnlyCell(sheet, value=value)
    cell.alignment = CHECKLIST_EXPORT_ALIGNMENT
    cell.border = CHECKLIST_EXPORT_BORDER
    if font_size:
        cell.font = Font(bold=bold, size=font_size)
    elif bold:
        cell.font = CHECKLIST_EXPORT_HEADER_FONT
    return cell


def _export_row(sheet, values: Iterable[object], *, bold: bool = False, font_size: int | None = None) -> list[WriteOnlyCell]:
    return [_export_cell(sheet, value, bold=bold, font_size=font_size) for value in values]


def _prepare_write_only_export_sheet(sheet) -> None:
    for column, width in CHECKLIST_EXPORT_WIDTHS.items():
        sheet.column_dimensions[column].width = width


def _summary_row_key(row: dict[str, object]) -> str:
    key = row.get("key")
    if key:
        return safe_str(key)
    return _summary_key(
        org_id=int(row["org_id"]),
        period=int(row["accounting_period"]),
        merchant_id=row.get("merchant_id"),
        receipt_merchant_id=row.get("receipt_merchant_id"),
        live_promoter_id=row.get("live_promoter_id"),
        merchant_name=safe_str(row["merchant_name"]),
        receipt_merchant=safe_str(row["receipt_merchant"]),
        live_promoter=safe_str(row["live_promoter"]),
    )


class ReconciliationChecklistService:
    @staticmethod
    def resolve_org_id(*, user: User, requested_org_id: int | str | None = None) -> int | str | None:
        if user.role == "superadmin":
            return requested_org_id
        return user.org_id

    @staticmethod
    def validate_org_scope(*, org_id: int, user: User) -> None:
        if user.role != "superadmin" and org_id != user.org_id:
            raise ValueError("数据不存在或无权访问")

    @staticmethod
    async def create_from_shared_upload(
        db: AsyncSession,
        *,
        upload_file: UploadFile,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ReconciliationChecklistTask:
        if (upload_file.parsed_type or "").strip() != CHECKLIST_FILE_TYPE:
            raise ValueError("仅对账清单文件可创建对账清单任务")

        existing_stmt = select(ReconciliationChecklistUploadFile).where(
            ReconciliationChecklistUploadFile.source_upload_file_id == upload_file.id,
            ReconciliationChecklistUploadFile.is_deleted.is_(False),
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        checklist_upload_file = existing
        if existing is not None:
            task_stmt = (
                select(ReconciliationChecklistTask)
                .where(
                    ReconciliationChecklistTask.file_id == existing.id,
                    ReconciliationChecklistTask.is_deleted.is_(False),
                )
                .order_by(ReconciliationChecklistTask.id.desc())
            )
            current_task = (await db.execute(task_stmt)).scalars().first()
            if current_task is not None:
                return current_task

        if checklist_upload_file is None:
            checklist_upload_file = ReconciliationChecklistUploadFile(
                org_id=upload_file.org_id,
                user_id=user.id,
                source_upload_file_id=upload_file.id,
                original_name=upload_file.original_name,
                oss_key=upload_file.oss_key,
                file_size=upload_file.file_size,
                file_hash=upload_file.file_hash,
                status="uploaded",
            )
            db.add(checklist_upload_file)
            await db.flush()

        task = ReconciliationChecklistTask(
            file_id=checklist_upload_file.id,
            org_id=checklist_upload_file.org_id,
            user_id=user.id,
            status="queued",
            progress=0,
        )
        db.add(task)
        await db.flush()

        await AuditService.log(
            db,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            org_id=checklist_upload_file.org_id,
            module="reconciliation_checklist",
            action="upload_file",
            description=f"上传对账清单文件 [{checklist_upload_file.original_name}]",
            target_type="reconciliation_checklist_upload_file",
            target_id=checklist_upload_file.id,
            target_name=checklist_upload_file.original_name,
            ip=ip,
            user_agent=user_agent,
            extra_data={
                "task_id": task.id,
                "file_size": checklist_upload_file.file_size,
                "source_upload_file_id": upload_file.id,
            },
        )

        ReconciliationChecklistService.dispatch_task_after_commit(
            db,
            task=task,
            upload_file=checklist_upload_file,
        )
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    def dispatch_task_after_commit(
        db: AsyncSession,
        *,
        task: ReconciliationChecklistTask,
        upload_file: ReconciliationChecklistUploadFile,
    ) -> None:
        async def dispatch() -> None:
            try:
                from app.tasks.reconciliation_checklist import run_reconciliation_checklist_task

                async_result = run_reconciliation_checklist_task.delay(task.id)
                task.celery_task_id = async_result.id
            except Exception as exc:
                task.status = "failed"
                task.progress = 100
                task.error_message = f"对账清单任务投递失败: {exc}"
                upload_file.status = "failed"
                upload_file.error_message = task.error_message
            await db.flush()

        register_after_commit(db, dispatch)

    @staticmethod
    async def rerun_task(
        db: AsyncSession,
        *,
        task_id: int,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ReconciliationChecklistTask | None:
        task = await db.get(ReconciliationChecklistTask, task_id)
        if task is None or task.is_deleted:
            return None
        ReconciliationChecklistService.validate_org_scope(org_id=task.org_id, user=user)
        if task.status == "expired":
            raise ValueError("源文件已过期或不存在，不能重新导入，请重新上传文件")
        upload_file = await db.get(ReconciliationChecklistUploadFile, task.file_id)
        if upload_file is None or upload_file.is_deleted:
            raise ValueError("对账清单上传文件不存在")

        task.status = "queued"
        task.progress = 0
        task.celery_task_id = None
        task.error_message = None
        task.started_at = None
        task.finished_at = None
        upload_file.status = "uploaded"
        upload_file.error_message = None

        await AuditService.log(
            db,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            org_id=task.org_id,
            module="reconciliation_checklist",
            action="task_rerun",
            description=f"重跑对账清单任务 [{task.id}]",
            target_type="reconciliation_checklist_task",
            target_id=task.id,
            ip=ip,
            user_agent=user_agent,
        )

        ReconciliationChecklistService.dispatch_task_after_commit(db, task=task, upload_file=upload_file)
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def execute_task(db: AsyncSession, *, task_id: int) -> ReconciliationChecklistTask:
        task_started = perf_counter()
        partition_seconds = 0.0
        download_seconds = 0.0
        persist_seconds = 0.0
        task = await db.get(ReconciliationChecklistTask, task_id)
        if task is None or task.is_deleted:
            raise ValueError("对账清单任务不存在")
        upload_file = await db.get(ReconciliationChecklistUploadFile, task.file_id)
        if upload_file is None or upload_file.is_deleted:
            raise ValueError("对账清单上传文件不存在")

        previous_state = _capture_result_state(task)
        task.status = "running"
        task.progress = 5
        task.started_at = datetime.now(timezone.utc)
        task.finished_at = None
        task.error_message = None
        await db.flush()
        await db.commit()

        try:
            partition_started = perf_counter()
            await ensure_reconciliation_checklist_partitions_for_year(
                db,
                year=datetime.now().year,
            )
            partition_seconds = perf_counter() - partition_started
            suffix = Path(upload_file.original_name).suffix or ".xlsx"
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
                download_started = perf_counter()
                oss_service.download_to_temp(upload_file.oss_key, tmp.name)
                download_seconds = perf_counter() - download_started
                persist_started = perf_counter()
                summary = await ReconciliationChecklistService.persist_task_result(
                    db,
                    task=task,
                    upload_file=upload_file,
                    file_path=tmp.name,
                )
                persist_seconds = perf_counter() - persist_started

            task.total_rows = int(summary.get("总行数", 0))
            task.success_rows = int(summary.get("成功行数", 0))
            task.failed_rows = int(summary.get("失败行数", 0))
            task.inserted_rows = int(summary.get("新增行数", 0))
            task.updated_rows = int(summary.get("更新行数", 0))
            task.result_summary = summary
            task.progress = 100
            task.status = "failed" if summary.get("文件解析失败") else ("partial_success" if task.failed_rows > 0 else "success")
            error_messages = summary.get("错误明细")
            task.error_message = "\n".join(map(str, error_messages)) if isinstance(error_messages, list) and error_messages else None
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "failed" if task.status == "failed" else "processed"
            upload_file.error_message = task.error_message
        except Exception as exc:
            await db.rollback()
            task = await db.get(ReconciliationChecklistTask, task_id)
            if task is None or task.is_deleted:
                raise ValueError("对账清单任务不存在") from exc
            upload_file = await db.get(ReconciliationChecklistUploadFile, task.file_id)
            if upload_file is None or upload_file.is_deleted:
                raise ValueError("对账清单上传文件不存在") from exc
            is_expired = is_oss_object_unavailable_error(exc)
            _restore_result_state(task, previous_state)
            task.status = "expired" if is_expired else "failed"
            task.progress = 100
            task.error_message = SOURCE_FILE_UNAVAILABLE_MESSAGE if is_expired else str(exc)
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "expired" if is_expired else "failed"
            upload_file.error_message = task.error_message

        total_seconds = perf_counter() - task_started
        logger.info(
            "reconciliation_checklist.task_perf task_id=%s file_id=%s status=%s total_rows=%s inserted_rows=%s deleted_rows=%s partition_seconds=%.3f download_seconds=%.3f persist_seconds=%.3f total_seconds=%.3f",
            task.id,
            task.file_id,
            task.status,
            task.total_rows,
            task.inserted_rows,
            int((task.result_summary or {}).get("覆盖删除行数", 0) or 0),
            partition_seconds,
            download_seconds,
            persist_seconds,
            total_seconds,
        )
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def persist_task_result(
        db: AsyncSession,
        *,
        task: ReconciliationChecklistTask,
        upload_file: ReconciliationChecklistUploadFile,
        file_path: str,
    ) -> dict:
        persist_started = perf_counter()
        parse_result = ReconciliationChecklistService.parse_file(file_path)
        parse_seconds = perf_counter() - persist_started
        inserted_rows = 0
        deleted_rows = 0
        partition_seconds = 0.0
        build_seconds = 0.0
        replace_seconds = 0.0
        summary_seconds = 0.0
        deduped_rows = 0
        periods: list[int] = []
        scopes: list[ChecklistScope] = []
        if not parse_result.get("fatal_error"):
            parsed_rows = ReconciliationChecklistService._dedupe_rows(parse_result.get("rows", []))
            deduped_rows = len(parsed_rows)
            periods = sorted({int(row["accounting_period"]) for row in parsed_rows})
            partition_started = perf_counter()
            for period in periods:
                for partition_spec in (
                    RECONCILIATION_CHECKLIST_PARTITION,
                    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
                    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
                ):
                    await ensure_month_partition(db, spec=partition_spec, period=period)
            partition_seconds = perf_counter() - partition_started
            build_started = perf_counter()
            details = await ReconciliationChecklistService._build_detail_rows(
                db,
                task=task,
                upload_file=upload_file,
                rows=parsed_rows,
            )
            build_seconds = perf_counter() - build_started
            replace_started = perf_counter()
            inserted_rows, deleted_rows, scopes = await ReconciliationChecklistService._replace_detail_rows(db, details)
            replace_seconds = perf_counter() - replace_started
            summary_started = perf_counter()
            await ReconciliationChecklistService._rebuild_summary_rows(db, scopes)
            summary_seconds = perf_counter() - summary_started
            await db.flush()

        summary = {
            "文件类型": CHECKLIST_FILE_TYPE,
            "总行数": parse_result.get("total_rows", 0),
            "成功行数": parse_result.get("success_rows", 0),
            "失败行数": parse_result.get("failed_rows", 0),
            "新增行数": inserted_rows,
            "更新行数": 0,
            "覆盖删除行数": deleted_rows,
        }
        errors = parse_result.get("errors", [])[:CHECKLIST_ERROR_SAMPLE_LIMIT]
        if errors:
            summary["错误明细"] = errors
        if parse_result.get("fatal_error"):
            summary["文件解析失败"] = "是"
        warnings = parse_result.get("warnings", [])
        if warnings:
            summary["处理提示"] = warnings
        total_seconds = perf_counter() - persist_started
        logger.info(
            "reconciliation_checklist.persist_task_result_perf task_id=%s file_id=%s raw_rows=%s deduped_rows=%s fatal_error=%s periods=%s scopes=%s parse_seconds=%.3f ensure_partition_seconds=%.3f build_details_seconds=%.3f replace_details_seconds=%.3f rebuild_summary_seconds=%.3f total_seconds=%.3f",
            task.id,
            upload_file.id,
            len(parse_result.get("rows", [])),
            deduped_rows,
            bool(parse_result.get("fatal_error")),
            len(periods),
            len(scopes),
            parse_seconds,
            partition_seconds,
            build_seconds,
            replace_seconds,
            summary_seconds,
            total_seconds,
        )
        return summary

    @staticmethod
    def _dedupe_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
        deduped: list[dict[str, object]] = []
        positions: dict[tuple[int, str, str, str], int] = {}
        for row in rows:
            flow_no = safe_str(row.get("transaction_flow_no"))
            if not flow_no:
                deduped.append(row)
                continue
            key = (
                int(row.get("accounting_period") or 0),
                safe_str(row.get("platform_code")),
                safe_str(row.get("shop_name")),
                flow_no,
            )
            if key in positions:
                deduped[positions[key]] = row
            else:
                positions[key] = len(deduped)
                deduped.append(row)
        return deduped

    @staticmethod
    async def _build_detail_rows(
        db: AsyncSession,
        *,
        task: ReconciliationChecklistTask,
        upload_file: ReconciliationChecklistUploadFile,
        rows: Iterable[dict[str, object]],
    ) -> list[ReconciliationChecklistDetail]:
        row_list = list(rows)
        entity_map = await ReconciliationChecklistService._ensure_entities(
            db,
            org_id=task.org_id,
            rows=row_list,
        )
        shop_cache: dict[tuple[str, str], Shop] = {}
        details: list[ReconciliationChecklistDetail] = []
        for row in row_list:
            platform_code = safe_str(row.get("platform_code"))
            shop_name = safe_str(row.get("shop_name"))
            cache_key = (platform_code, shop_name)
            shop = shop_cache.get(cache_key)
            if shop is None:
                shop = await ShopService.get_or_create_shop(
                    db,
                    org_id=task.org_id,
                    platform_name=platform_code,
                    shop_name=shop_name,
                )
                shop_cache[cache_key] = shop
            details.append(
                ReconciliationChecklistDetail(
                    task_id=task.id,
                    file_id=upload_file.id,
                    org_id=task.org_id,
                    shop_id=shop.id,
                    platform_code=platform_code,
                    shop_name=shop.shop_name,
                    accounting_year=int(row["accounting_year"]),
                    accounting_month=int(row["accounting_month"]),
                    accounting_period=int(row["accounting_period"]),
                    source_row_number=int(row.get("source_row_number") or 0),
                    transaction_time=row["transaction_time"],
                    transaction_flow_no=safe_str(row.get("transaction_flow_no")),
                    product_name=safe_str(row.get("product_name")),
                    live_promoter_id=entity_map.get((platform_code, "live_promoter", safe_str(row.get("live_promoter")))),
                    merchant_id=entity_map.get((platform_code, "merchant", safe_str(row.get("merchant_name")))),
                    receipt_merchant_id=entity_map.get((platform_code, "receipt_merchant", safe_str(row.get("receipt_merchant")))),
                    live_promoter=safe_str(row.get("live_promoter")),
                    merchant_name=safe_str(row.get("merchant_name")),
                    receipt_merchant=safe_str(row.get("receipt_merchant")),
                    order_amount=safe_decimal(row.get("order_amount")),
                    live_commission=safe_decimal(row.get("live_commission")),
                    merchant_net_amount=safe_decimal(row.get("merchant_net_amount")),
                )
            )
        return details

    @staticmethod
    async def _ensure_entities(
        db: AsyncSession,
        *,
        org_id: int,
        rows: Iterable[dict[str, object]],
    ) -> dict[tuple[str, str, str], int]:
        candidates: dict[tuple[str, str, str], int | None] = {}
        receipt_parent_keys: dict[tuple[str, str], tuple[str, str, str]] = {}
        for row in rows:
            platform_code = safe_str(row.get("platform_code"))
            period = int(row.get("accounting_period") or 0) or None
            merchant_name = safe_str(row.get("merchant_name"))
            receipt_merchant = safe_str(row.get("receipt_merchant"))
            values = (
                ("live_promoter", safe_str(row.get("live_promoter"))),
                ("merchant", merchant_name),
                ("receipt_merchant", receipt_merchant),
            )
            for entity_type, name in values:
                if name:
                    key = (platform_code, entity_type, name)
                    candidates[key] = max(candidates.get(key) or 0, period or 0) or None
            if merchant_name and receipt_merchant:
                receipt_parent_keys[(platform_code, receipt_merchant)] = (platform_code, "merchant", merchant_name)

        if not candidates:
            return {}

        values = [
            {
                "org_id": org_id,
                "platform_code": platform_code,
                "entity_type": entity_type,
                "name": name,
                "status": "active",
                "source": "auto",
                "last_seen_period": period,
            }
            for (platform_code, entity_type, name), period in candidates.items()
        ]
        stmt = insert(ReconciliationChecklistEntity).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["org_id", "platform_code", "entity_type", "name"],
            index_where=text("is_deleted = false"),
            set_={
                "last_seen_period": func.greatest(
                    func.coalesce(ReconciliationChecklistEntity.last_seen_period, 0),
                    func.coalesce(stmt.excluded.last_seen_period, 0),
                ),
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)

        keys = list(candidates.keys())
        result = await db.execute(
            select(ReconciliationChecklistEntity).where(
                ReconciliationChecklistEntity.is_deleted.is_(False),
                ReconciliationChecklistEntity.org_id == org_id,
                tuple_(
                    ReconciliationChecklistEntity.platform_code,
                    ReconciliationChecklistEntity.entity_type,
                    ReconciliationChecklistEntity.name,
                ).in_(keys),
            )
        )
        entity_map = {(entity.platform_code, entity.entity_type, entity.name): entity.id for entity in result.scalars().all()}
        parent_updates: list[tuple[int, int]] = []
        for (platform_code, receipt_name), parent_key in receipt_parent_keys.items():
            receipt_id = entity_map.get((platform_code, "receipt_merchant", receipt_name))
            parent_id = entity_map.get(parent_key)
            if receipt_id and parent_id:
                parent_updates.append((receipt_id, parent_id))
        for receipt_id, parent_id in parent_updates:
            await db.execute(select(ReconciliationChecklistEntity).where(ReconciliationChecklistEntity.id == receipt_id).with_for_update())
            entity = await db.get(ReconciliationChecklistEntity, receipt_id)
            if entity is not None and entity.parent_id != parent_id:
                entity.parent_id = parent_id
        return entity_map

    @staticmethod
    async def _replace_detail_rows(
        db: AsyncSession,
        rows: Iterable[ReconciliationChecklistDetail],
    ) -> tuple[int, int, list[ChecklistScope]]:
        replace_started = perf_counter()
        delete_seconds = 0.0
        insert_seconds = 0.0
        detail_rows = list(rows)
        if not detail_rows:
            return 0, 0, []

        scopes = sorted({(row.org_id, row.accounting_period, row.platform_code, row.shop_id) for row in detail_rows})
        await _lock_scopes(db, scopes)

        deleted_rows = 0
        delete_started = perf_counter()
        for scope_chunk in _chunked(scopes, 200):
            delete_result = await db.execute(
                ReconciliationChecklistDetail.__table__.delete().where(
                    tuple_(
                        ReconciliationChecklistDetail.org_id,
                        ReconciliationChecklistDetail.accounting_period,
                        ReconciliationChecklistDetail.platform_code,
                        ReconciliationChecklistDetail.shop_id,
                    ).in_(scope_chunk)
                )
            )
            deleted_rows += int(getattr(delete_result, "rowcount", 0) or 0)
        delete_seconds = perf_counter() - delete_started

        values = [{field: getattr(row, field) for field in DETAIL_INSERT_FIELDS} for row in detail_rows]
        insert_batch_size = 1000
        insert_started = perf_counter()
        for value_chunk in _chunked(values, insert_batch_size):
            await db.execute(ReconciliationChecklistDetail.__table__.insert(), value_chunk)
        insert_seconds = perf_counter() - insert_started
        total_seconds = perf_counter() - replace_started
        logger.info(
            "reconciliation_checklist.replace_detail_rows_perf rows=%s scopes=%s deleted_rows=%s insert_batches=%s delete_seconds=%.3f insert_seconds=%.3f total_seconds=%.3f",
            len(detail_rows),
            len(scopes),
            deleted_rows,
            (len(values) + insert_batch_size - 1) // insert_batch_size,
            delete_seconds,
            insert_seconds,
            total_seconds,
        )
        return len(detail_rows), deleted_rows, scopes

    @staticmethod
    async def _rebuild_summary_rows(db: AsyncSession, scopes: Sequence[ChecklistScope]) -> None:
        if not scopes:
            return
        for scope_chunk in _chunked(scopes, 200):
            await db.execute(ReconciliationChecklistSummaryProductRow.__table__.delete().where(_scope_condition(ReconciliationChecklistSummaryProductRow, scope_chunk)))
            await db.execute(ReconciliationChecklistSummaryRow.__table__.delete().where(_scope_condition(ReconciliationChecklistSummaryRow, scope_chunk)))

            detail_filter = _scope_condition(ReconciliationChecklistDetail, scope_chunk)
            summary_columns = (
                "org_id",
                "shop_id",
                "platform_code",
                "shop_name",
                "accounting_year",
                "accounting_month",
                "accounting_period",
                "live_promoter_id",
                "merchant_id",
                "receipt_merchant_id",
                "live_promoter",
                "merchant_name",
                "receipt_merchant",
                "product_quantity",
                "total_order_amount",
                "total_live_commission",
                "total_merchant_net_amount",
            )
            summary_group_columns = (
                ReconciliationChecklistDetail.org_id,
                ReconciliationChecklistDetail.shop_id,
                ReconciliationChecklistDetail.platform_code,
                ReconciliationChecklistDetail.shop_name,
                ReconciliationChecklistDetail.accounting_year,
                ReconciliationChecklistDetail.accounting_month,
                ReconciliationChecklistDetail.accounting_period,
                ReconciliationChecklistDetail.live_promoter_id,
                ReconciliationChecklistDetail.merchant_id,
                ReconciliationChecklistDetail.receipt_merchant_id,
                ReconciliationChecklistDetail.live_promoter,
                ReconciliationChecklistDetail.merchant_name,
                ReconciliationChecklistDetail.receipt_merchant,
            )
            summary_select = (
                select(
                    *summary_group_columns,
                    func.count(ReconciliationChecklistDetail.id),
                    func.sum(ReconciliationChecklistDetail.order_amount),
                    func.sum(ReconciliationChecklistDetail.live_commission),
                    func.sum(ReconciliationChecklistDetail.merchant_net_amount),
                )
                .where(detail_filter)
                .group_by(*summary_group_columns)
            )
            await db.execute(insert(ReconciliationChecklistSummaryRow).from_select(summary_columns, summary_select))

            product_columns = (
                "org_id",
                "shop_id",
                "platform_code",
                "shop_name",
                "accounting_year",
                "accounting_month",
                "accounting_period",
                "live_promoter_id",
                "merchant_id",
                "receipt_merchant_id",
                "live_promoter",
                "merchant_name",
                "receipt_merchant",
                "product_name",
                "product_quantity",
                "total_order_amount",
                "total_live_commission",
                "total_merchant_net_amount",
            )
            product_group_columns = (
                *summary_group_columns,
                ReconciliationChecklistDetail.product_name,
            )
            product_select = (
                select(
                    *product_group_columns,
                    func.count(ReconciliationChecklistDetail.id),
                    func.sum(ReconciliationChecklistDetail.order_amount),
                    func.sum(ReconciliationChecklistDetail.live_commission),
                    func.sum(ReconciliationChecklistDetail.merchant_net_amount),
                )
                .where(detail_filter)
                .group_by(*product_group_columns)
            )
            await db.execute(insert(ReconciliationChecklistSummaryProductRow).from_select(product_columns, product_select))

    @staticmethod
    def _summary_filters(
        *,
        user: User,
        source_model=ReconciliationChecklistDetail,
        org_id: str | int | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        shop_ids: str | int | None = None,
        merchant_name: str | None = None,
        live_promoter: str | None = None,
        receipt_merchant: str | None = None,
        merchant_ids: str | int | None = None,
        live_promoter_ids: str | int | None = None,
        receipt_merchant_ids: str | int | None = None,
        keyword: str | None = None,
        ids: list[str] | None = None,
    ) -> list:
        filters = [active_shop_filter(source_model.shop_id)]
        is_deleted_column = getattr(source_model, "is_deleted", None)
        if is_deleted_column is not None:
            filters.append(is_deleted_column.is_(False))
        org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=org_id)
        if org_ids is not None:
            filters.append(source_model.org_id.in_(org_ids))
        filters.extend(
            _period_filters(
                source_model.accounting_period,
                accounting_year=accounting_year,
                accounting_month=accounting_month,
                accounting_start_year=accounting_start_year,
                accounting_start_month=accounting_start_month,
                accounting_end_year=accounting_end_year,
                accounting_end_month=accounting_end_month,
            )
        )
        shop_id_list = split_int_filter_values(shop_ids)
        if shop_id_list:
            filters.append(source_model.shop_id.in_(shop_id_list))
        merchant_id_values = _split_id_values(merchant_ids)
        if merchant_id_values:
            filters.append(source_model.merchant_id.in_(merchant_id_values))
        promoter_id_values = _split_id_values(live_promoter_ids)
        if promoter_id_values:
            filters.append(source_model.live_promoter_id.in_(promoter_id_values))
        receipt_id_values = _split_id_values(receipt_merchant_ids)
        if receipt_id_values:
            filters.append(source_model.receipt_merchant_id.in_(receipt_id_values))
        merchant_name_values = _split_filter_values(merchant_name)
        if merchant_name_values:
            filters.append(source_model.merchant_name.in_(merchant_name_values))
        promoter_values = _split_filter_values(live_promoter)
        if promoter_values:
            filters.append(source_model.live_promoter.in_(promoter_values))
        merchant_values = _split_filter_values(receipt_merchant)
        if merchant_values:
            filters.append(source_model.receipt_merchant.in_(merchant_values))
        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            keyword_columns = [
                getattr(source_model, "product_name", None),
                source_model.merchant_name,
                source_model.live_promoter,
                source_model.receipt_merchant,
                source_model.shop_name,
            ]
            filters.append(or_(*(column.ilike(like_pattern) for column in keyword_columns if column is not None)))
        if ids is not None:
            parsed_conditions = []
            for raw_id in ids:
                parsed = _parse_summary_key(raw_id)
                if parsed is None:
                    continue
                (
                    key_org_id,
                    period,
                    merchant_id,
                    receipt_merchant_id,
                    live_promoter_id,
                    merchant_name_value,
                    receipt_merchant_value,
                    promoter,
                ) = parsed
                condition_parts = [
                    source_model.org_id == key_org_id,
                    source_model.accounting_period == period,
                    source_model.merchant_name == merchant_name_value,
                    source_model.receipt_merchant == receipt_merchant_value,
                    source_model.live_promoter == promoter,
                ]
                if merchant_id is not None:
                    condition_parts.append(source_model.merchant_id == merchant_id)
                if receipt_merchant_id is not None:
                    condition_parts.append(source_model.receipt_merchant_id == receipt_merchant_id)
                if live_promoter_id is not None:
                    condition_parts.append(source_model.live_promoter_id == live_promoter_id)
                parsed_conditions.append(and_(*condition_parts))
            if not parsed_conditions:
                filters.append(source_model.id.in_([]))
            else:
                filters.append(or_(*parsed_conditions))
        return filters

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        *,
        user: User,
        org_id: str | int | None = None,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[ReconciliationChecklistTask, ReconciliationChecklistUploadFile, str | None]], int]:
        filters = [ReconciliationChecklistTask.is_deleted.is_(False), ReconciliationChecklistUploadFile.is_deleted.is_(False)]
        org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=org_id)
        if org_ids is not None:
            filters.append(ReconciliationChecklistTask.org_id.in_(org_ids))
        status_values = _split_filter_values(status)
        if status_values:
            filters.append(ReconciliationChecklistTask.status.in_(status_values))
        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    ReconciliationChecklistUploadFile.original_name.ilike(like_pattern),
                    ReconciliationChecklistTask.error_message.ilike(like_pattern),
                )
            )

        stmt = (
            select(ReconciliationChecklistTask, ReconciliationChecklistUploadFile, Organization.name.label("org_name"))
            .join(ReconciliationChecklistUploadFile, ReconciliationChecklistUploadFile.id == ReconciliationChecklistTask.file_id)
            .outerjoin(Organization, Organization.id == ReconciliationChecklistTask.org_id)
            .where(*filters)
            .order_by(ReconciliationChecklistTask.id.desc())
        )
        count_stmt = (
            select(func.count())
            .select_from(ReconciliationChecklistTask)
            .join(ReconciliationChecklistUploadFile, ReconciliationChecklistUploadFile.id == ReconciliationChecklistTask.file_id)
            .where(*filters)
        )
        total = (await db.execute(count_stmt)).scalar() or 0
        result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        return list(result.all()), total

    @staticmethod
    async def get_dashboard_metrics(
        db: AsyncSession,
        *,
        user: User,
        year: int,
        org_id: str | int | None = None,
    ) -> dict[str, object]:
        org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=org_id)
        task_filters = [
            ReconciliationChecklistTask.is_deleted.is_(False),
            ReconciliationChecklistTask.status.in_(CHECKLIST_PROCESSED_TASK_STATUSES),
        ]
        all_task_filters = [
            ReconciliationChecklistTask.is_deleted.is_(False),
        ]
        failed_task_filters = [
            ReconciliationChecklistTask.is_deleted.is_(False),
            ReconciliationChecklistTask.status == "failed",
        ]
        detail_filters = [
            ReconciliationChecklistDetail.is_deleted.is_(False),
        ]
        if org_ids is not None:
            task_filters.append(ReconciliationChecklistTask.org_id.in_(org_ids))
            all_task_filters.append(ReconciliationChecklistTask.org_id.in_(org_ids))
            failed_task_filters.append(ReconciliationChecklistTask.org_id.in_(org_ids))
            detail_filters.append(ReconciliationChecklistDetail.org_id.in_(org_ids))

        processed_task_count = await db.scalar(
            select(func.count())
            .select_from(ReconciliationChecklistTask)
            .where(*task_filters)
        )
        total_task_count = await db.scalar(
            select(func.count())
            .select_from(ReconciliationChecklistTask)
            .where(*all_task_filters)
        )
        failed_task_count = await db.scalar(
            select(func.count())
            .select_from(ReconciliationChecklistTask)
            .where(*failed_task_filters)
        )
        total_rows = await db.scalar(
            select(func.coalesce(func.sum(ReconciliationChecklistTask.total_rows), 0))
            .select_from(ReconciliationChecklistTask)
            .where(*task_filters)
        )
        total_order_amount = await db.scalar(
            select(func.coalesce(func.sum(ReconciliationChecklistDetail.order_amount), Decimal("0.00")))
            .select_from(ReconciliationChecklistDetail)
            .where(*detail_filters)
        )
        merchant_count = await db.scalar(
            select(func.count(func.distinct(ReconciliationChecklistDetail.merchant_id)))
            .select_from(ReconciliationChecklistDetail)
            .where(
                *detail_filters,
                ReconciliationChecklistDetail.merchant_id.is_not(None),
            )
        )
        covered_month_count = await db.scalar(
            select(func.count(func.distinct(ReconciliationChecklistDetail.accounting_period)))
            .select_from(ReconciliationChecklistDetail)
            .where(*detail_filters)
        )

        monthly_result = await db.execute(
            select(
                func.extract("month", ReconciliationChecklistTask.finished_at).label("month"),
                func.count().label("task_count"),
            )
            .select_from(ReconciliationChecklistTask)
            .where(
                *task_filters,
                ReconciliationChecklistTask.finished_at.is_not(None),
                func.extract("year", ReconciliationChecklistTask.finished_at) == year,
            )
            .group_by("month")
            .order_by("month")
        )
        monthly_counts = {month: 0 for month in range(1, 13)}
        for month, task_count in monthly_result.all():
            if month is not None:
                monthly_counts[int(month)] = int(task_count or 0)

        monthly_amount_result = await db.execute(
            select(
                ReconciliationChecklistDetail.accounting_month.label("month"),
                func.coalesce(func.sum(ReconciliationChecklistDetail.order_amount), Decimal("0.00")).label("total_order_amount"),
            )
            .select_from(ReconciliationChecklistDetail)
            .where(
                *detail_filters,
                ReconciliationChecklistDetail.accounting_year == year,
            )
            .group_by(ReconciliationChecklistDetail.accounting_month)
            .order_by(ReconciliationChecklistDetail.accounting_month)
        )
        monthly_amounts = {month: Decimal("0.00") for month in range(1, 13)}
        for month, total_amount in monthly_amount_result.all():
            if month is not None:
                monthly_amounts[int(month)] = total_amount or Decimal("0.00")

        top_merchant_result = await db.execute(
            select(
                ReconciliationChecklistDetail.merchant_id.label("merchant_id"),
                func.max(ReconciliationChecklistDetail.merchant_name).label("merchant_name"),
                func.coalesce(func.sum(ReconciliationChecklistDetail.order_amount), Decimal("0.00")).label("total_order_amount"),
            )
            .select_from(ReconciliationChecklistDetail)
            .where(
                *detail_filters,
                ReconciliationChecklistDetail.merchant_id.is_not(None),
            )
            .group_by(ReconciliationChecklistDetail.merchant_id)
            .order_by(func.coalesce(func.sum(ReconciliationChecklistDetail.order_amount), Decimal("0.00")).desc())
            .limit(5)
        )
        top_merchants = [
            {
                "merchant_id": int(row.merchant_id),
                "merchant_name": safe_str(row.merchant_name),
                "total_order_amount": row.total_order_amount or Decimal("0.00"),
            }
            for row in top_merchant_result.all()
        ]

        recent_task_result = await db.execute(
            select(
                ReconciliationChecklistTask.id.label("id"),
                ReconciliationChecklistUploadFile.original_name.label("original_name"),
                ReconciliationChecklistTask.status.label("status"),
                ReconciliationChecklistTask.total_rows.label("total_rows"),
                ReconciliationChecklistTask.success_rows.label("success_rows"),
                ReconciliationChecklistTask.failed_rows.label("failed_rows"),
                ReconciliationChecklistTask.inserted_rows.label("inserted_rows"),
                ReconciliationChecklistTask.finished_at.label("finished_at"),
            )
            .select_from(ReconciliationChecklistTask)
            .join(ReconciliationChecklistUploadFile, ReconciliationChecklistUploadFile.id == ReconciliationChecklistTask.file_id)
            .where(
                *task_filters,
                ReconciliationChecklistUploadFile.is_deleted.is_(False),
            )
            .order_by(ReconciliationChecklistTask.finished_at.desc().nullslast(), ReconciliationChecklistTask.id.desc())
            .limit(5)
        )
        recent_tasks = [
            {
                "id": int(row.id),
                "original_name": safe_str(row.original_name),
                "status": safe_str(row.status),
                "total_rows": int(row.total_rows or 0),
                "success_rows": int(row.success_rows or 0),
                "failed_rows": int(row.failed_rows or 0),
                "inserted_rows": int(row.inserted_rows or 0),
                "finished_at": row.finished_at,
            }
            for row in recent_task_result.all()
        ]

        processed_count = int(processed_task_count or 0)
        all_count = int(total_task_count or 0)
        completion_rate = (
            Decimal(processed_count * 100)
            / Decimal(all_count)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if all_count else Decimal("0.00")

        return {
            "processed_task_count": processed_count,
            "total_task_count": all_count,
            "failed_task_count": int(failed_task_count or 0),
            "total_rows": int(total_rows or 0),
            "total_order_amount": total_order_amount or Decimal("0.00"),
            "merchant_count": int(merchant_count or 0),
            "covered_month_count": int(covered_month_count or 0),
            "completion_rate": completion_rate,
            "year": year,
            "monthly_task_counts": [
                {"month": month, "task_count": monthly_counts[month]}
                for month in range(1, 13)
            ],
            "monthly_order_amounts": [
                {"month": month, "total_order_amount": monthly_amounts[month]}
                for month in range(1, 13)
            ],
            "top_merchants": top_merchants,
            "recent_tasks": recent_tasks,
        }

    @staticmethod
    async def list_summary(
        db: AsyncSession,
        *,
        user: User,
        org_id: str | int | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        shop_ids: str | int | None = None,
        merchant_name: str | None = None,
        live_promoter: str | None = None,
        receipt_merchant: str | None = None,
        merchant_ids: str | int | None = None,
        live_promoter_ids: str | int | None = None,
        receipt_merchant_ids: str | int | None = None,
        keyword: str | None = None,
        ids: list[str] | None = None,
        page: int | None = 1,
        page_size: int | None = 20,
    ) -> tuple[list[dict[str, object]], int]:
        source_model = ReconciliationChecklistSummaryProductRow if keyword else ReconciliationChecklistSummaryRow
        filters = ReconciliationChecklistService._summary_filters(
            user=user,
            source_model=source_model,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            shop_ids=shop_ids,
            merchant_name=merchant_name,
            live_promoter=live_promoter,
            receipt_merchant=receipt_merchant,
            merchant_ids=merchant_ids,
            live_promoter_ids=live_promoter_ids,
            receipt_merchant_ids=receipt_merchant_ids,
            keyword=keyword,
            ids=ids,
        )
        group_columns = (
            source_model.org_id,
            Organization.name,
            source_model.accounting_year,
            source_model.accounting_month,
            source_model.accounting_period,
            source_model.merchant_id,
            source_model.live_promoter_id,
            source_model.receipt_merchant_id,
            source_model.merchant_name,
            source_model.live_promoter,
            source_model.receipt_merchant,
        )
        stmt = (
            select(
                source_model.org_id.label("org_id"),
                Organization.name.label("org_name"),
                source_model.accounting_year.label("accounting_year"),
                source_model.accounting_month.label("accounting_month"),
                source_model.accounting_period.label("accounting_period"),
                source_model.merchant_id.label("merchant_id"),
                source_model.live_promoter_id.label("live_promoter_id"),
                source_model.receipt_merchant_id.label("receipt_merchant_id"),
                source_model.merchant_name.label("merchant_name"),
                source_model.live_promoter.label("live_promoter"),
                source_model.receipt_merchant.label("receipt_merchant"),
                func.sum(source_model.product_quantity).label("product_quantity"),
                func.sum(source_model.total_order_amount).label("total_order_amount"),
                func.sum(source_model.total_live_commission).label("total_live_commission"),
                func.sum(source_model.total_merchant_net_amount).label("total_merchant_net_amount"),
            )
            .outerjoin(Organization, Organization.id == source_model.org_id)
            .where(*filters)
            .group_by(*group_columns)
            .order_by(
                source_model.accounting_year.desc(),
                source_model.accounting_month.desc(),
                source_model.receipt_merchant,
                source_model.live_promoter,
            )
        )
        total = 0
        if page is not None and page_size is not None:
            count_stmt = select(func.count()).select_from(
                select(*group_columns).outerjoin(Organization, Organization.id == source_model.org_id).where(*filters).group_by(*group_columns).subquery()
            )
            total = (await db.execute(count_stmt)).scalar() or 0
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            item["key"] = _summary_key(
                org_id=int(item["org_id"]),
                period=int(item["accounting_period"]),
                merchant_id=item.get("merchant_id"),
                receipt_merchant_id=item.get("receipt_merchant_id"),
                live_promoter_id=item.get("live_promoter_id"),
                merchant_name=safe_str(item["merchant_name"]),
                receipt_merchant=safe_str(item["receipt_merchant"]),
                live_promoter=safe_str(item["live_promoter"]),
            )
            rows.append(item)
        return rows, total

    @staticmethod
    async def list_summary_details(
        db: AsyncSession,
        *,
        user: User,
        org_id: str | int | None = None,
        accounting_year: int,
        accounting_month: int,
        merchant_name: str,
        live_promoter: str,
        receipt_merchant: str,
        merchant_id: int | None = None,
        live_promoter_id: int | None = None,
        receipt_merchant_id: int | None = None,
        shop_ids: str | int | None = None,
        keyword: str | None = None,
        page: int | None = 1,
        page_size: int | None = 50,
    ) -> tuple[list[dict[str, object]], int]:
        source_model = ReconciliationChecklistSummaryProductRow
        filters = ReconciliationChecklistService._summary_filters(
            user=user,
            source_model=source_model,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            shop_ids=shop_ids,
            merchant_name=None if merchant_id else merchant_name,
            live_promoter=None if live_promoter_id else live_promoter,
            receipt_merchant=None if receipt_merchant_id else receipt_merchant,
            merchant_ids=merchant_id,
            live_promoter_ids=live_promoter_id,
            receipt_merchant_ids=receipt_merchant_id,
            keyword=keyword,
        )
        stmt = (
            select(
                source_model.product_name.label("product_name"),
                func.sum(source_model.product_quantity).label("product_quantity"),
                func.sum(source_model.total_order_amount).label("total_order_amount"),
                func.sum(source_model.total_live_commission).label("total_live_commission"),
                func.sum(source_model.total_merchant_net_amount).label("total_merchant_net_amount"),
            )
            .where(*filters)
            .group_by(source_model.product_name)
            .order_by(source_model.product_name)
        )
        count_stmt = select(func.count()).select_from(select(source_model.product_name).where(*filters).group_by(source_model.product_name).subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return [dict(row) for row in result.mappings().all()], total

    @staticmethod
    async def list_entity_options(
        db: AsyncSession,
        *,
        user: User,
        entity_type: str,
        accounting_year: int,
        accounting_month: int,
        org_id: str | int | None = None,
        parent_ids: str | int | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        if entity_type not in CHECKLIST_ENTITY_TYPES:
            raise ValueError("不支持的筛选类型")
        period = _accounting_period(accounting_year, accounting_month)
        org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=org_id)

        entity_id_column = {
            "live_promoter": ReconciliationChecklistDetail.live_promoter_id,
            "merchant": ReconciliationChecklistDetail.merchant_id,
            "receipt_merchant": ReconciliationChecklistDetail.receipt_merchant_id,
        }[entity_type]

        filters = [
            ReconciliationChecklistEntity.is_deleted.is_(False),
            ReconciliationChecklistEntity.entity_type == entity_type,
            ReconciliationChecklistEntity.status == "active",
            ReconciliationChecklistDetail.is_deleted.is_(False),
            ReconciliationChecklistDetail.accounting_period == period,
            entity_id_column == ReconciliationChecklistEntity.id,
        ]
        if org_ids is not None:
            filters.append(ReconciliationChecklistEntity.org_id.in_(org_ids))
            filters.append(ReconciliationChecklistDetail.org_id.in_(org_ids))
        parent_id_values = _split_id_values(parent_ids)
        if parent_id_values:
            filters.append(ReconciliationChecklistEntity.parent_id.in_(parent_id_values))
        if keyword:
            filters.append(ReconciliationChecklistEntity.name.ilike(f"%{keyword.strip()}%"))

        stmt = (
            select(
                ReconciliationChecklistEntity.id.label("id"),
                ReconciliationChecklistEntity.org_id.label("org_id"),
                ReconciliationChecklistEntity.parent_id.label("parent_id"),
                ReconciliationChecklistEntity.platform_code.label("platform_code"),
                ReconciliationChecklistEntity.entity_type.label("entity_type"),
                ReconciliationChecklistEntity.name.label("name"),
            )
            .select_from(ReconciliationChecklistEntity)
            .join(ReconciliationChecklistDetail, entity_id_column == ReconciliationChecklistEntity.id)
            .where(*filters)
            .group_by(
                ReconciliationChecklistEntity.id,
                ReconciliationChecklistEntity.org_id,
                ReconciliationChecklistEntity.parent_id,
                ReconciliationChecklistEntity.platform_code,
                ReconciliationChecklistEntity.entity_type,
                ReconciliationChecklistEntity.name,
            )
            .order_by(ReconciliationChecklistEntity.platform_code, ReconciliationChecklistEntity.name)
            .limit(min(max(limit, 1), 100))
        )
        result = await db.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def _iter_export_summary_detail_rows(
        db: AsyncSession,
        *,
        user: User,
        org_id: str | int | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        shop_ids: str | int | None = None,
        merchant_name: str | None = None,
        live_promoter: str | None = None,
        receipt_merchant: str | None = None,
        merchant_ids: str | int | None = None,
        live_promoter_ids: str | int | None = None,
        receipt_merchant_ids: str | int | None = None,
        keyword: str | None = None,
        summary_keys: list[str] | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        source_model = ReconciliationChecklistSummaryProductRow
        filters = ReconciliationChecklistService._summary_filters(
            user=user,
            source_model=source_model,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            shop_ids=shop_ids,
            merchant_name=merchant_name,
            live_promoter=live_promoter,
            receipt_merchant=receipt_merchant,
            merchant_ids=merchant_ids,
            live_promoter_ids=live_promoter_ids,
            receipt_merchant_ids=receipt_merchant_ids,
            keyword=keyword,
            ids=summary_keys,
        )
        group_columns = (
            source_model.org_id,
            source_model.accounting_year,
            source_model.accounting_month,
            source_model.accounting_period,
            source_model.merchant_id,
            source_model.live_promoter_id,
            source_model.receipt_merchant_id,
            source_model.merchant_name,
            source_model.live_promoter,
            source_model.receipt_merchant,
            source_model.product_name,
        )
        stmt = (
            select(
                source_model.org_id.label("org_id"),
                source_model.accounting_year.label("accounting_year"),
                source_model.accounting_month.label("accounting_month"),
                source_model.accounting_period.label("accounting_period"),
                source_model.merchant_id.label("merchant_id"),
                source_model.live_promoter_id.label("live_promoter_id"),
                source_model.receipt_merchant_id.label("receipt_merchant_id"),
                source_model.merchant_name.label("merchant_name"),
                source_model.live_promoter.label("live_promoter"),
                source_model.receipt_merchant.label("receipt_merchant"),
                source_model.product_name.label("product_name"),
                func.sum(source_model.product_quantity).label("product_quantity"),
                func.sum(source_model.total_order_amount).label("total_order_amount"),
                func.sum(source_model.total_live_commission).label("total_live_commission"),
                func.sum(source_model.total_merchant_net_amount).label("total_merchant_net_amount"),
            )
            .where(*filters)
            .group_by(*group_columns)
            .order_by(
                source_model.accounting_year.desc(),
                source_model.accounting_month.desc(),
                source_model.receipt_merchant,
                source_model.live_promoter,
                source_model.product_name,
            )
        )
        result = await db.stream(stmt)
        async for row in result.mappings():
            item = dict(row)
            if "summary_key" not in item:
                item["summary_key"] = _summary_key(
                    org_id=int(item["org_id"]),
                    period=int(item["accounting_period"]),
                    merchant_id=item.get("merchant_id"),
                    receipt_merchant_id=item.get("receipt_merchant_id"),
                    live_promoter_id=item.get("live_promoter_id"),
                    merchant_name=safe_str(item["merchant_name"]),
                    receipt_merchant=safe_str(item["receipt_merchant"]),
                    live_promoter=safe_str(item["live_promoter"]),
                )
            yield item

    @staticmethod
    async def export_summary_to_file(
        db: AsyncSession,
        *,
        user: User,
        output_path: Path,
        org_id: str | int | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        shop_ids: str | int | None = None,
        merchant_name: str | None = None,
        live_promoter: str | None = None,
        receipt_merchant: str | None = None,
        merchant_ids: str | int | None = None,
        live_promoter_ids: str | int | None = None,
        receipt_merchant_ids: str | int | None = None,
        keyword: str | None = None,
        ids: list[str] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> int:
        summaries, _ = await ReconciliationChecklistService.list_summary(
            db,
            user=user,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            shop_ids=shop_ids,
            merchant_name=merchant_name,
            live_promoter=live_promoter,
            receipt_merchant=receipt_merchant,
            merchant_ids=merchant_ids,
            live_promoter_ids=live_promoter_ids,
            receipt_merchant_ids=receipt_merchant_ids,
            keyword=keyword,
            ids=ids,
            page=page,
            page_size=page_size,
        )
        if not summaries:
            raise ValueError("未找到符合条件的对账清单数据")

        workbook = Workbook(write_only=True)
        worksheets: dict[str, object] = {}
        row_numbers: dict[str, int] = {}
        summary_keys: list[str] = []
        restrict_detail_keys = ids is not None or (page is not None and page_size is not None)

        for index, summary in enumerate(summaries, start=1):
            year = int(summary["accounting_year"])
            month = int(summary["accounting_month"])
            merchant_name_value = safe_str(summary["merchant_name"])
            promoter = safe_str(summary["live_promoter"])
            receipt_merchant_value = safe_str(summary["receipt_merchant"])
            key = _summary_row_key(summary)
            summary_keys.append(key)

            sheet_name = _sheet_title(year, month, merchant_name_value)
            if sheet_name in workbook.sheetnames:
                sheet_name = f"{sheet_name[:27]}_{index}"
            worksheet = workbook.create_sheet(sheet_name)
            _prepare_write_only_export_sheet(worksheet)
            worksheet.append(_export_row(worksheet, ["", "直播推广佣金明细", "", "", ""], bold=True, font_size=16))
            worksheet.append(_export_row(worksheet, ["商家", merchant_name_value, f"{year}年{month}月", "直播推广方", promoter], bold=True))
            worksheet.append(_export_row(worksheet, ["收款商家", receipt_merchant_value, "", "", ""], bold=True))
            worksheet.append(_export_row(worksheet, CHECKLIST_SUMMARY_HEADERS, bold=True))
            worksheets[key] = worksheet
            row_numbers[key] = 0

        row_count = 0
        async for row in ReconciliationChecklistService._iter_export_summary_detail_rows(
            db,
            user=user,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            shop_ids=shop_ids,
            merchant_name=merchant_name,
            live_promoter=live_promoter,
            receipt_merchant=receipt_merchant,
            merchant_ids=merchant_ids,
            live_promoter_ids=live_promoter_ids,
            receipt_merchant_ids=receipt_merchant_ids,
            keyword=keyword,
            summary_keys=summary_keys if restrict_detail_keys else None,
        ):
            key = safe_str(row.get("summary_key"))
            worksheet = worksheets.get(key)
            if worksheet is None:
                continue
            row_numbers[key] += 1
            worksheet.append(
                _export_row(
                    worksheet,
                    [
                        row_numbers[key],
                        row.get("product_name") or "",
                        float(row.get("total_order_amount") or 0),
                        float(row.get("total_live_commission") or 0),
                        float(row.get("total_merchant_net_amount") or 0),
                    ],
                )
            )
            row_count += 1

        for summary in summaries:
            key = _summary_row_key(summary)
            worksheet = worksheets[key]
            worksheet.append(
                _export_row(
                    worksheet,
                    [
                        "总计",
                        "",
                        float(summary.get("total_order_amount") or 0),
                        float(summary.get("total_live_commission") or 0),
                        float(summary.get("total_merchant_net_amount") or 0),
                    ],
                )
            )
        workbook.save(output_path)
        workbook.close()
        return row_count

    @staticmethod
    def parse_file(file_path: str) -> dict:
        result = {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "warnings": [],
            "fatal_error": False,
            "rows": [],
        }

        def add_file_error(message: str) -> dict:
            result["errors"].append(message)
            result["failed_rows"] = max(int(result["failed_rows"]), 1)
            result["fatal_error"] = True
            return result

        with open_tabular_rows(file_path) as rows:
            if rows is None:
                return add_file_error("无法打开表格文件")

            row_iter = iter(rows)
            header_result = ReconciliationChecklistService._find_header_row(row_iter)
            if header_result is None:
                return add_file_error("无法读取对账清单表头")

            headers, canonical_headers, header_row_number = header_result
            missing = [header for header in CHECKLIST_HEADERS if header not in canonical_headers]
            if missing:
                return add_file_error(f"缺少对账清单必要表头: {', '.join(missing)}")

            col_idx = {header: canonical_headers.index(header) for header in CHECKLIST_HEADERS}
            for row_number, row in enumerate(row_iter, start=header_row_number + 1):
                if not any(safe_str(value) for value in row):
                    continue
                result["total_rows"] += 1
                try:
                    values = FinancialSummaryExcelProcessorMixin._row_to_values(row, col_idx)
                    transaction_time = parse_datetime(values.get("动账时间"))
                    if transaction_time is None:
                        raise ValueError("动账时间无法解析")
                    platform_code = safe_str(values.get("平台"))
                    shop_name = safe_str(values.get("店铺"))
                    flow_no = safe_str(values.get("动账流水号"))
                    if not platform_code:
                        raise ValueError("平台不能为空")
                    if not shop_name:
                        raise ValueError("店铺不能为空")
                    if not flow_no:
                        raise ValueError("动账流水号不能为空")
                    period = _accounting_period(transaction_time.year, transaction_time.month)
                    result["rows"].append(
                        {
                            "source_row_number": row_number,
                            "platform_code": platform_code,
                            "shop_name": shop_name,
                            "transaction_time": transaction_time,
                            "accounting_year": transaction_time.year,
                            "accounting_month": transaction_time.month,
                            "accounting_period": period,
                            "transaction_flow_no": flow_no,
                            "product_name": safe_str(values.get("商品名称")),
                            "live_promoter": safe_str(values.get("直播推广方")),
                            "merchant_name": safe_str(values.get("商家")),
                            "receipt_merchant": safe_str(values.get("收款商家")),
                            "order_amount": _money(values.get("订单金额")),
                            "live_commission": _money(values.get("直播推广佣金")),
                            "merchant_net_amount": _money(values.get("应付商家净额")),
                        }
                    )
                    result["success_rows"] += 1
                except Exception as exc:
                    result["failed_rows"] += 1
                    if len(result["errors"]) < CHECKLIST_ERROR_SAMPLE_LIMIT:
                        result["errors"].append(f"Row {row_number}: {exc}")
        if result["total_rows"] == 0:
            result["warnings"].append("空表，没有数据")
        return result

    @staticmethod
    def _find_header_row(row_iter: Iterable[Iterable[object]]) -> tuple[list[str], list[str], int] | None:
        for row_number, row in enumerate(row_iter, start=1):
            headers = [safe_str(value) for value in row]
            canonical_headers = [_canonical_header(value) for value in headers]
            if any(header in canonical_headers for header in CHECKLIST_HEADERS):
                return headers, canonical_headers, row_number
        return None
