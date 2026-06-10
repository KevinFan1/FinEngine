"""Celery application and platform-specific file processing tasks."""

import asyncio
import logging
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_shutdown

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.oss_service import SOURCE_FILE_UNAVAILABLE_MESSAGE, is_oss_object_unavailable_error
from app.services.upload_period_service import EmptyTabularDataError, extract_upload_period, resolve_upload_period_header
from app.tasks.processors.base import normalize_positive_summary_fields, safe_str

celery_app = Celery("finengine", broker=settings.CELERY_REDIS_URL, backend=settings.CELERY_REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_soft_time_limit=3600,
    task_time_limit=7200,
)
celery_app.conf.beat_schedule = {
    "ensure-source-partitions-daily": {
        "task": "app.tasks.partition_maintenance.ensure_source_partitions_task",
        "schedule": crontab(minute=0, hour=0),
    },
    "ensure-reconciliation-checklist-partitions-daily": {
        "task": "app.tasks.partition_maintenance.ensure_reconciliation_checklist_partitions_precreate_task",
        "schedule": crontab(minute=10, hour=0),
    }
}

celery_app.autodiscover_tasks(["app.tasks"])
celery_app.conf.imports = (
    "app.tasks.transaction_accounting",
    "app.tasks.bic_accounting",
    "app.tasks.reconciliation_checklist",
    "app.tasks.partition_maintenance",
    "app.tasks.export_jobs",
)

logger = logging.getLogger("finengine.worker")
_worker_loop: asyncio.AbstractEventLoop | None = None
SUPPORTED_TEMP_SUFFIXES = {".xlsx", ".xlsm", ".xls", ".csv"}
FILENAME_TYPE_PATTERN = re.compile(
    r"^(?:\d{2,4}年\d{1,2}月[ _])?(动账|gmv|bic|BIC|运费险|订单|其他服务款|GMV订单货款|GMV其他服务款|退货费用及其他|银行流水)[ _].+\.(?:xlsx|xlsm|xls|csv)$",
    re.IGNORECASE,
)


def _configure_worker_logging() -> None:
    setup_logging()


_configure_worker_logging()


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    """Reuse one event loop per Celery worker process.

    SQLAlchemy's async engine keeps pooled asyncpg connections that are bound
    to the loop that created them. Creating a fresh loop for every task can
    leave the pool holding futures attached to a closed/older loop.
    """
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def _run_async_in_worker(coro):
    loop = _get_worker_loop()
    return loop.run_until_complete(coro)


def _capture_processing_result_state(task, upload_file) -> dict[str, object]:
    return {
        "processed_rows": task.processed_rows,
        "success_rows": task.success_rows,
        "failed_rows": task.failed_rows,
        "result_summary": task.result_summary,
        "upload_row_count": getattr(upload_file, "row_count", None) if upload_file is not None else None,
    }


def _restore_processing_result_state(task, upload_file, state: dict[str, object] | None) -> None:
    if not state:
        return
    task.processed_rows = int(state.get("processed_rows") or 0)
    task.success_rows = int(state.get("success_rows") or 0)
    task.failed_rows = int(state.get("failed_rows") or 0)
    task.result_summary = state.get("result_summary")  # type: ignore[assignment]
    if upload_file is not None:
        upload_file.row_count = state.get("upload_row_count")  # type: ignore[assignment]


def _mark_task_failed(task, upload_file, error: Exception | str, *, previous_state: dict[str, object] | None = None) -> None:
    is_expired = is_oss_object_unavailable_error(error)
    error_message = SOURCE_FILE_UNAVAILABLE_MESSAGE if is_expired else str(error)
    _restore_processing_result_state(task, upload_file, previous_state)
    task.status = "expired" if is_expired else "failed"
    task.progress = 100
    task.error_message = error_message
    task.finished_at = datetime.now(timezone.utc)
    if upload_file:
        upload_file.status = "expired" if is_expired else "failed"
        upload_file.error_message = error_message


def _json_safe(value):
    """Convert processor internals to JSON-safe values for task.result_summary."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _result_task_status_from_failed_rows(failed_rows: object) -> str:
    try:
        return "partial_success" if int(failed_rows or 0) > 0 else "success"
    except (TypeError, ValueError):
        return "success"


def _result_task_status_from_processor_result(proc_result: dict) -> str:
    return _result_task_status_from_failed_rows(proc_result.get("failed_rows"))


def _result_task_status_from_summary(summary: dict) -> str:
    return _result_task_status_from_failed_rows(summary.get("失败行数", summary.get("failed_rows")))


def _set_task_result_from_processor(task, proc_result: dict) -> None:
    task.processed_rows = int(proc_result.get("total_rows") or 0)
    task.success_rows = int(proc_result.get("success_rows") or 0)
    task.failed_rows = int(proc_result.get("failed_rows") or 0)


def _set_task_result_from_summary(task, summary: dict) -> None:
    task.processed_rows = int(summary.get("总行数", summary.get("total_rows")) or 0)
    task.success_rows = int(summary.get("成功行数", summary.get("success_rows")) or 0)
    task.failed_rows = int(summary.get("失败行数", summary.get("failed_rows")) or 0)


def _mark_task_empty_success(task, upload_file, *, file_type: str) -> None:
    task.status = "success"
    task.progress = 100
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.error_message = "空表，没有数据"
    task.result_summary = {
        "文件类型": file_type,
        "总行数": 0,
        "成功行数": 0,
        "失败行数": 0,
        "汇总分组数": 0,
        "错误明细": ["空表，没有数据"],
    }
    task.finished_at = datetime.now(timezone.utc)
    if upload_file:
        upload_file.status = "success"
        upload_file.error_message = task.error_message
        upload_file.row_count = 0


def _group_return_cost_by_order_created_time(
    return_cost_rows: list[dict],
    order_created_times: dict[str, datetime],
) -> tuple[dict[tuple[int, int], Decimal], list[str]]:
    """Group return-cost rows by indexed order creation month."""
    grouped_return_cost: dict[tuple[int, int], Decimal] = {}
    missing_order_nos: list[str] = []
    for row in return_cost_rows:
        order_no = safe_str(row.get("order_no"))
        order_created_at = order_created_times.get(order_no)
        if order_created_at is None:
            if order_no:
                missing_order_nos.append(order_no)
            continue

        key = (order_created_at.year, order_created_at.month)
        grouped_return_cost[key] = grouped_return_cost.get(key, Decimal("0")) + Decimal(str(row.get("return_cost") or "0"))
    return grouped_return_cost, missing_order_nos


def _group_money_by_order_or_fallback_time(
    rows: list[dict],
    *,
    order_created_times: dict[str, datetime],
    amount_key: str,
    fallback_time_key: str,
) -> tuple[dict[tuple[int, int], Decimal], list[str], list[str]]:
    """Group money rows by order month, falling back to a row timestamp."""
    grouped: dict[tuple[int, int], Decimal] = {}
    fallback_order_nos: list[str] = []
    missing_order_nos: list[str] = []

    for row in rows:
        order_no = safe_str(row.get("order_no"))
        order_created_at = order_created_times.get(order_no)
        group_time = order_created_at

        if group_time is None:
            fallback_time = row.get(fallback_time_key)
            if isinstance(fallback_time, datetime):
                group_time = fallback_time
                if order_no:
                    fallback_order_nos.append(order_no)

        if group_time is None:
            if order_no:
                missing_order_nos.append(order_no)
            continue

        key = (group_time.year, group_time.month)
        grouped[key] = grouped.get(key, Decimal("0")) + Decimal(str(row.get(amount_key) or "0"))

    return grouped, missing_order_nos, fallback_order_nos


def _group_money_by_order_created_time(
    rows: list[dict],
    *,
    order_created_times: dict[str, datetime],
    amount_key: str,
) -> tuple[dict[tuple[int, int], Decimal], list[str]]:
    grouped: dict[tuple[int, int], Decimal] = {}
    missing_order_nos: list[str] = []
    for row in rows:
        order_no = safe_str(row.get("order_no"))
        order_created_at = order_created_times.get(order_no)
        if order_created_at is None:
            if order_no:
                missing_order_nos.append(order_no)
            continue

        key = (order_created_at.year, order_created_at.month)
        grouped[key] = grouped.get(key, Decimal("0")) + Decimal(str(row.get(amount_key) or "0"))
    return grouped, missing_order_nos


def _build_order_dependency_summary(
    *,
    type_code: str,
    proc_result: dict,
    summary_ids: list[int],
    groups: int,
    missing_order_nos: list[str],
) -> dict:
    """Build a successful task summary when missing orders are counted as zero."""
    missing_order_count = len(missing_order_nos)
    missing_order_samples = list(dict.fromkeys(missing_order_nos))[:20]
    effective_success_rows = max(int(proc_result.get("success_rows") or 0) - missing_order_count, 0)
    effective_failed_rows = int(proc_result.get("failed_rows") or 0) + missing_order_count
    errors = list(proc_result.get("errors") or [])[:10]
    if missing_order_nos:
        sample_text = "、".join(missing_order_samples)
        errors.append(f"缺少订单创建时间 {missing_order_count} 条，已按 0 统计；订单号: {sample_text}")

    return {
        "文件类型": type_code,
        "依赖数据": "订单索引",
        "汇总记录ID": summary_ids,
        "总行数": proc_result.get("total_rows", 0),
        "成功行数": effective_success_rows,
        "失败行数": effective_failed_rows,
        "解析成功行数": proc_result.get("success_rows", 0),
        "解析失败行数": proc_result.get("failed_rows", 0),
        "缺少订单创建时间行数": missing_order_count,
        "缺少订单创建时间订单样例": missing_order_samples,
        "汇总分组数": groups,
        "错误明细": _json_safe(errors),
    }


def _build_order_or_fallback_time_summary(
    *,
    type_code: str,
    proc_result: dict,
    summary_ids: list[int],
    groups: int,
    missing_order_nos: list[str],
    fallback_order_nos: list[str],
    fallback_label: str,
) -> dict:
    summary = _build_order_dependency_summary(
        type_code=type_code,
        proc_result=proc_result,
        summary_ids=summary_ids,
        groups=groups,
        missing_order_nos=missing_order_nos,
    )
    fallback_count = len(fallback_order_nos)
    fallback_samples = list(dict.fromkeys(fallback_order_nos))[:20]
    summary["兜底时间字段"] = fallback_label
    summary["兜底归属年月行数"] = fallback_count
    summary["兜底归属年月订单样例"] = fallback_samples
    if fallback_order_nos:
        sample_text = "、".join(fallback_samples)
        errors = list(summary.get("错误明细") or [])
        errors.append(f"订单索引未命中 {fallback_count} 条，已使用{fallback_label}归属年月；订单号: {sample_text}")
        summary["错误明细"] = _json_safe(errors)
    return summary


def _group_summary_rows_by_order_created_time(
    rows: list[dict],
    *,
    order_created_times: dict[str, datetime],
    fields: list[str] | tuple[str, ...],
) -> tuple[dict[tuple[int, int], dict[str, Decimal]], list[str]]:
    grouped: dict[tuple[int, int], dict[str, Decimal]] = {}
    missing_order_nos: list[str] = []
    for row in rows:
        order_no = safe_str(row.get("order_no"))
        order_created_at = order_created_times.get(order_no)
        if order_created_at is None:
            if order_no:
                missing_order_nos.append(order_no)
            continue

        key = (order_created_at.year, order_created_at.month)
        agg = grouped.setdefault(key, {field: Decimal("0") for field in fields})
        for field in fields:
            agg[field] = agg.get(field, Decimal("0")) + Decimal(str(row.get(field) or "0"))
    for agg in grouped.values():
        normalize_positive_summary_fields(agg)
    return grouped, missing_order_nos


def _infer_temp_suffix(upload_file, oss_key: str) -> str:
    """Preserve uploaded extension so processors can choose Excel vs CSV readers."""
    candidates = []
    if upload_file and upload_file.original_name:
        candidates.append(upload_file.original_name)
    candidates.append(oss_key)

    for candidate in candidates:
        suffix = Path(candidate).suffix.lower()
        if suffix in SUPPORTED_TEMP_SUFFIXES:
            return suffix
    return ".xlsx"


def _normalize_file_type(raw_type: str | None) -> str | None:
    if not raw_type:
        return None
    stripped = raw_type.strip()
    alias_map = {
        "BIC": "bic",
        "GMV": "gmv",
        "GMV订单货款": "gmv",
        "GMV其他服务款": "其他服务款",
        "退货费用及其他": "动账",
        "银行流水": "银行流水",
    }
    if stripped in alias_map:
        return alias_map[stripped]
    lower_type = stripped.lower()
    return lower_type if lower_type in {"bic", "gmv"} else stripped


def _parse_file_type_from_name(filename: str | None) -> str | None:
    if not filename:
        return None
    match = FILENAME_TYPE_PATTERN.match(filename)
    if not match:
        return None
    return _normalize_file_type(match.group(1))


def _infer_file_type(upload_file) -> str:
    """Use filename type as the source of truth; fall back to stored parsed_type."""
    filename_type = _parse_file_type_from_name(upload_file.original_name if upload_file else None)
    stored_type = _normalize_file_type(upload_file.parsed_type if upload_file else None)
    if filename_type:
        if stored_type and stored_type != filename_type:
            logger.warning(
                "文件类型和文件名不一致，使用文件名类型 file_id=%s original_name=%s stored_type=%s filename_type=%s",
                upload_file.id if upload_file else None,
                upload_file.original_name if upload_file else None,
                stored_type,
                filename_type,
            )
        return filename_type

    if stored_type:
        return stored_type

    return "动账"


@worker_process_shutdown.connect
def _close_worker_loop(**_kwargs):
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = None
        return

    asyncio.set_event_loop(_worker_loop)
    try:
        from app.core.database import engine

        _worker_loop.run_until_complete(engine.dispose())
    finally:
        _worker_loop.close()
        _worker_loop = None


@celery_app.task(bind=True, name="process_file_platform")
def process_file_platform(
    self,
    file_id: int,
    oss_key: str,
    org_id: int,
    platform_code: str,
    shop_name: str,
    shop_id: int | None = None,
):
    """Process an uploaded Excel/CSV file using a hardcoded platform processor.

    This bypasses the rule engine entirely. The processor handles column
    mapping, derived-column computation, and aggregation internally.
    """
    _run_async_in_worker(
        _process_file_platform_async(
            self,
            file_id,
            oss_key,
            org_id,
            platform_code,
            shop_name,
            shop_id,
        )
    )


@celery_app.task(bind=True, name="process_merchant_red_sheet")
def process_merchant_red_sheet(
    self,
    task_id: int,
    file_id: int,
    oss_key: str,
):
    """Process a merchant red-sheet upload from OSS."""
    _run_async_in_worker(
        _process_merchant_red_sheet_async(
            self,
            task_id=task_id,
            file_id=file_id,
            oss_key=oss_key,
        )
    )


@celery_app.task(bind=True, name="process_merchant_bank_flow")
def process_merchant_bank_flow(
    self,
    task_id: int,
    file_id: int,
    oss_key: str,
):
    """Process a merchant bank-flow upload from OSS."""
    _run_async_in_worker(
        _process_merchant_bank_flow_async(
            self,
            task_id=task_id,
            file_id=file_id,
            oss_key=oss_key,
        )
    )


@celery_app.task(name="app.tasks.scan_due_sync_tasks", ignore_result=True)
def scan_due_sync_tasks() -> int:
    """Compatibility shim for stale Celery beat messages from older builds.

    Current FinEngine processing is dispatched explicitly through
    process_file_platform; keeping this task registered lets workers consume
    already queued legacy messages instead of crashing with an unknown task.
    """
    logger.warning("忽略旧版 Celery 定时任务: app.tasks.scan_due_sync_tasks")
    return 0


def requeue_order_dependent_tasks_after_order_upload(
    order_file_id: int,
) -> None:
    _run_async_in_worker(_requeue_order_dependent_tasks_after_order_upload_async(order_file_id))


def recover_queued_processing_tasks(limit: int = 100) -> int:
    return _run_async_in_worker(_recover_queued_processing_tasks_async(limit=limit))


def reconcile_terminal_running_processing_tasks(limit: int = 100) -> int:
    return _run_async_in_worker(_reconcile_terminal_running_processing_tasks_async(limit=limit))


async def _recover_queued_processing_tasks_async(limit: int = 100) -> int:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile

    async with async_session_factory() as db:
        task_rows = await db.execute(
            select(ProcessingTask, UploadFile)
            .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
            .where(
                ProcessingTask.status == "queued",
                ProcessingTask.is_deleted.is_(False),
                UploadFile.is_deleted.is_(False),
            )
            .order_by(ProcessingTask.id.asc())
            .limit(limit)
        )
        rows = task_rows.all()
        dispatched = 0
        for task, upload_file in rows:
            file_type = _normalize_file_type(upload_file.parsed_type)
            if file_type == "红单":
                async_result = process_merchant_red_sheet.delay(
                    task_id=task.id,
                    file_id=upload_file.id,
                    oss_key=upload_file.oss_key,
                )
            elif file_type == "银行流水":
                async_result = process_merchant_bank_flow.delay(
                    task_id=task.id,
                    file_id=upload_file.id,
                    oss_key=upload_file.oss_key,
                )
            else:
                async_result = process_file_platform.delay(
                    file_id=upload_file.id,
                    oss_key=upload_file.oss_key,
                    org_id=task.org_id,
                    platform_code=upload_file.detected_platform or "",
                    shop_name=upload_file.parsed_shop or "",
                    shop_id=upload_file.shop_id,
                )
            task.celery_task_id = async_result.id
            dispatched += 1
        await db.commit()
        return dispatched


async def _reconcile_terminal_running_processing_tasks_async(limit: int = 100) -> int:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile

    terminal_failed_states = {"FAILURE", "REVOKED"}
    async with async_session_factory() as db:
        task_rows = await db.execute(
            select(ProcessingTask, UploadFile)
            .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
            .where(
                ProcessingTask.status == "running",
                ProcessingTask.celery_task_id.is_not(None),
                ProcessingTask.is_deleted.is_(False),
                UploadFile.is_deleted.is_(False),
            )
            .order_by(ProcessingTask.id.asc())
            .limit(limit)
        )
        rows = task_rows.all()
        reconciled = 0
        for task, upload_file in rows:
            celery_result = celery_app.AsyncResult(task.celery_task_id)
            if celery_result.state not in terminal_failed_states:
                continue

            error = celery_result.result
            if error is None:
                error = f"Celery任务已结束但数据库仍为运行中，状态: {celery_result.state}"
            _mark_task_failed(task, upload_file, error)
            reconciled += 1

        if reconciled:
            await db.commit()
        return reconciled


async def _requeue_order_dependent_tasks_after_order_upload_async(order_file_id: int) -> int:
    from sqlalchemy import or_, select

    from app.core.database import async_session_factory
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile
    from app.services.platform_profile_service import resolve_platform_profile

    async with async_session_factory() as db:
        result = await db.execute(select(UploadFile).where(UploadFile.id == order_file_id, UploadFile.is_deleted.is_(False)))
        order_file = result.scalar_one_or_none()
        if order_file is None:
            return 0

        order_profile = await resolve_platform_profile(db, order_file.detected_platform or "")
        order_scope_code = order_file.order_scope_code or order_profile.order_scope_code

        filters = [
            UploadFile.org_id == order_file.org_id,
            or_(UploadFile.order_scope_code == order_scope_code, UploadFile.detected_platform == order_file.detected_platform),
            UploadFile.parsed_type.in_(["动账", "运费险", "bic", "其他服务款"]),
            UploadFile.parsed_year == order_file.parsed_year,
            UploadFile.parsed_month == order_file.parsed_month,
            UploadFile.is_deleted.is_(False),
            ProcessingTask.is_deleted.is_(False),
            ProcessingTask.status.notin_(["queued", "running", "expired"]),
        ]
        if order_file.shop_id is not None:
            filters.append(UploadFile.shop_id == order_file.shop_id)
        elif order_file.parsed_shop:
            filters.append(or_(UploadFile.parsed_shop == order_file.parsed_shop, UploadFile.shop_id.is_(None)))

        task_rows = await db.execute(select(ProcessingTask, UploadFile).join(UploadFile, ProcessingTask.file_id == UploadFile.id).where(*filters).order_by(ProcessingTask.id.asc()))
        rows = task_rows.all()
        for task, upload_file in rows:
            _reset_task_for_requeue(task, upload_file)
        await db.commit()

        for task, upload_file in rows:
            async_result = process_file_platform.delay(
                file_id=upload_file.id,
                oss_key=upload_file.oss_key,
                org_id=task.org_id,
                platform_code=upload_file.detected_platform or "",
                shop_name=upload_file.parsed_shop or "",
                shop_id=upload_file.shop_id,
            )
            task.celery_task_id = async_result.id
        await db.commit()
        return len(rows)


async def _process_merchant_red_sheet_async(
    task_instance,
    *,
    task_id: int,
    file_id: int,
    oss_key: str,
) -> None:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile
    from app.models.user import User
    from app.services.merchant_reconciliation_service import MerchantReconciliationService
    from app.services.oss_service import oss_service

    async with async_session_factory() as db:
        task_result = await db.execute(
            select(ProcessingTask).where(
                ProcessingTask.id == task_id,
                ProcessingTask.file_id == file_id,
                ProcessingTask.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        file_result = await db.execute(
            select(UploadFile).where(
                UploadFile.id == file_id,
                UploadFile.is_deleted.is_(False),
            )
        )
        upload_file = file_result.scalar_one_or_none()
        if task is None or upload_file is None:
            return

        previous_result_state = _capture_processing_result_state(task, upload_file)
        task.status = "running"
        task.progress = 10
        task.celery_task_id = task_instance.request.id
        task.started_at = datetime.now(timezone.utc)
        upload_file.status = "processing"
        await db.commit()

        try:
            operator = await db.get(User, upload_file.user_id)
            if operator is None:
                raise ValueError("上传用户不存在，无法处理红单")
            if upload_file.parsed_year is None or upload_file.parsed_month is None:
                raise ValueError("红单任务缺少年月，请重新上传")

            with tempfile.NamedTemporaryFile(suffix=_infer_temp_suffix(upload_file, oss_key), delete=True) as tmp:
                oss_service.download_to_temp(oss_key, tmp.name)
                task.progress = 35
                await db.commit()

                with open(tmp.name, "rb") as file_obj:
                    content = file_obj.read()

            result = await MerchantReconciliationService.import_red_sheet(
                db,
                content=content,
                filename=upload_file.original_name,
                accounting_year=int(upload_file.parsed_year),
                accounting_month=int(upload_file.parsed_month),
                operator=operator,
                org_id=upload_file.org_id,
            )

            total_rows = result.purchase_rows + result.payment_rows
            task.status = "success"
            task.progress = 100
            task.processed_rows = total_rows
            task.success_rows = total_rows
            task.failed_rows = 0
            task.error_message = None
            task.result_summary = {
                "文件类型": "红单",
                "红单文件ID": result.red_sheet_id,
                "总行数": total_rows,
                "成功行数": total_rows,
                "失败行数": 0,
                "采购明细行数": result.purchase_rows,
                "货款明细行数": result.payment_rows,
                "处理提示": _json_safe(result.warnings[:50]),
                "错误明细": _json_safe(result.errors[:10]),
            }
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "success"
            upload_file.row_count = total_rows
            upload_file.error_message = None
            await db.commit()
        except Exception as exc:
            await db.rollback()
            task_result = await db.execute(
                select(ProcessingTask).where(
                    ProcessingTask.id == task_id,
                    ProcessingTask.is_deleted.is_(False),
                )
            )
            task = task_result.scalar_one_or_none()
            upload_file = None
            if task is not None:
                file_result = await db.execute(
                    select(UploadFile).where(
                        UploadFile.id == file_id,
                        UploadFile.is_deleted.is_(False),
                    )
                )
                upload_file = file_result.scalar_one_or_none()
                _mark_task_failed(task, upload_file, exc, previous_state=previous_result_state)
            await db.commit()
            logger.exception("红单任务处理失败 file_id=%s oss_key=%s", file_id, oss_key)
            raise


async def _process_merchant_bank_flow_async(
    task_instance,
    *,
    task_id: int,
    file_id: int,
    oss_key: str,
) -> None:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile
    from app.models.user import User
    from app.services.merchant_reconciliation_service import MerchantReconciliationService
    from app.services.oss_service import oss_service

    async with async_session_factory() as db:
        task_result = await db.execute(
            select(ProcessingTask).where(
                ProcessingTask.id == task_id,
                ProcessingTask.file_id == file_id,
                ProcessingTask.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        file_result = await db.execute(
            select(UploadFile).where(
                UploadFile.id == file_id,
                UploadFile.is_deleted.is_(False),
            )
        )
        upload_file = file_result.scalar_one_or_none()
        if task is None or upload_file is None:
            return

        previous_result_state = _capture_processing_result_state(task, upload_file)
        task.status = "running"
        task.progress = 10
        task.celery_task_id = task_instance.request.id
        task.started_at = datetime.now(timezone.utc)
        upload_file.status = "processing"
        await db.commit()

        try:
            operator = await db.get(User, upload_file.user_id)
            if operator is None:
                raise ValueError("上传用户不存在，无法处理银行流水")

            with tempfile.NamedTemporaryFile(suffix=_infer_temp_suffix(upload_file, oss_key), delete=True) as tmp:
                oss_service.download_to_temp(oss_key, tmp.name)
                task.progress = 35
                await db.commit()
                result = await MerchantReconciliationService.import_bank_flow(
                    db,
                    file_path=tmp.name,
                    filename=upload_file.original_name,
                    operator=operator,
                    org_id=upload_file.org_id,
                    file_size=upload_file.file_size,
                    file_hash=upload_file.file_hash,
                )

            task.status = "success"
            task.progress = 100
            task.processed_rows = result.row_count
            task.success_rows = result.row_count
            task.failed_rows = 0
            task.error_message = None
            task.result_summary = {
                "文件类型": "银行流水",
                "银行流水文件ID": result.bank_flow_file_id,
                "总行数": result.row_count,
                "成功行数": result.row_count,
                "失败行数": 0,
                "匹配行数": result.matched_row_count,
                "处理提示": _json_safe(result.warnings[:50]),
                "错误明细": _json_safe(result.errors[:10]),
            }
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "success"
            upload_file.row_count = result.row_count
            upload_file.error_message = None
            await db.commit()
        except Exception as exc:
            await db.rollback()
            task_result = await db.execute(
                select(ProcessingTask).where(
                    ProcessingTask.id == task_id,
                    ProcessingTask.is_deleted.is_(False),
                )
            )
            task = task_result.scalar_one_or_none()
            upload_file = None
            if task is not None:
                file_result = await db.execute(
                    select(UploadFile).where(
                        UploadFile.id == file_id,
                        UploadFile.is_deleted.is_(False),
                    )
                )
                upload_file = file_result.scalar_one_or_none()
                _mark_task_failed(task, upload_file, exc, previous_state=previous_result_state)
            await db.commit()
            logger.exception("银行流水任务处理失败 file_id=%s oss_key=%s", file_id, oss_key)
            raise


def _reset_task_for_requeue(task, upload_file) -> None:
    task.status = "queued"
    task.progress = 0
    task.celery_task_id = None
    task.error_message = None
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.result_summary = None
    task.started_at = None
    task.finished_at = None
    upload_file.status = "uploaded"
    upload_file.error_message = None
    upload_file.row_count = 0


async def _process_file_platform_async(
    task_instance,
    file_id: int,
    oss_key: str,
    org_id: int,
    platform_code: str,
    shop_name: str,
    shop_id: int | None = None,
):
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.platform import Platform
    from app.models.task import ProcessingTask
    from app.models.upload import UploadFile
    from app.services.category_dict_service import CategoryDictService
    from app.services.oss_service import oss_service
    from app.services.platform_profile_service import resolve_platform_profile
    from app.tasks.processors import PLATFORM_PROCESSORS

    async with async_session_factory() as db:
        # 1. Update task status to running
        stmt = select(ProcessingTask).where(ProcessingTask.file_id == file_id, ProcessingTask.is_deleted.is_(False))
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return
        task_id = task.id

        previous_result_state = _capture_processing_result_state(task, None)
        task.status = "running"
        task.celery_task_id = task_instance.request.id
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        # 2. Update file status
        file_stmt = select(UploadFile).where(UploadFile.id == file_id, UploadFile.is_deleted.is_(False))
        file_result = await db.execute(file_stmt)
        upload_file = file_result.scalar_one_or_none()
        previous_result_state["upload_row_count"] = getattr(upload_file, "row_count", None) if upload_file is not None else None
        if upload_file and upload_file.shop_id:
            shop_id = upload_file.shop_id
        file_type = _infer_file_type(upload_file)
        source_year = upload_file.parsed_year if upload_file else None
        source_month = upload_file.parsed_month if upload_file else None
        profile = await resolve_platform_profile(db, upload_file.detected_platform if upload_file else platform_code)
        processor = PLATFORM_PROCESSORS.get(profile.processor_code)
        platform_code = profile.source_platform_code
        report_platform_code = profile.report_platform_code
        order_scope_code = profile.order_scope_code
        if upload_file:
            upload_file.source_platform_code = profile.source_platform_code
            upload_file.report_platform_code = profile.report_platform_code
            upload_file.processor_code = profile.processor_code
            upload_file.order_scope_code = profile.order_scope_code
        if processor is None:
            error_message = f"未找到平台 [{profile.processor_code}] 的处理器"
            task.status = "failed"
            task.error_message = error_message
            task.finished_at = datetime.now(timezone.utc)
            if upload_file:
                upload_file.status = "failed"
                upload_file.error_message = error_message
            await db.commit()
            raise ValueError(error_message)
        if upload_file:
            upload_file.status = "processing"
            await db.commit()

        try:
            # 3. Download file from OSS
            with tempfile.NamedTemporaryFile(suffix=_infer_temp_suffix(upload_file, oss_key), delete=True) as tmp:
                oss_service.download_to_temp(oss_key, tmp.name)

                period_header = await resolve_upload_period_header(db, platform_code, file_type)
                try:
                    upload_period = extract_upload_period(
                        tmp.name,
                        platform_code=platform_code,
                        type_code=file_type,
                        header_name=period_header,
                    )
                    source_year = upload_period.year
                    source_month = upload_period.month
                    if upload_file:
                        if (
                            upload_file.parsed_year is not None
                            and upload_file.parsed_month is not None
                            and (upload_file.parsed_year, upload_file.parsed_month) != (source_year, source_month)
                        ):
                            logger.warning(
                                "上传年月和文件所属时间列不一致，使用文件内容 file_id=%s stored=%s-%s extracted=%s-%s header=%s",
                                upload_file.id,
                                upload_file.parsed_year,
                                upload_file.parsed_month,
                                source_year,
                                source_month,
                                upload_period.header,
                            )
                        upload_file.parsed_year = source_year
                        upload_file.parsed_month = source_month
                except EmptyTabularDataError:
                    _mark_task_empty_success(task, upload_file, file_type=file_type)
                    await db.commit()
                    return

                # 4. Load category dictionary (best-effort)
                platform_stmt = select(Platform).where(Platform.code == profile.processor_code, Platform.is_deleted.is_(False))
                platform_result = await db.execute(platform_stmt)
                platform = platform_result.scalar_one_or_none()

                category_dict = None
                if platform and file_type == "动账":
                    category_dict = await CategoryDictService.get_categories(
                        db,
                        platform_id=platform.id,
                        type_code=file_type,
                    )

                # 5. Update progress
                task.progress = 20
                await db.commit()

                # 6. Run platform processor
                proc_result = processor.process(
                    file_path=tmp.name,
                    shop_name=shop_name,
                    type_code=file_type,
                    category_dict=category_dict,
                )

                task.progress = 60
                task.processed_rows = proc_result["total_rows"]
                await db.commit()

                should_requeue_order_dependents = False
                if file_type in {"订单", "gmv"} and proc_result.get("orders"):
                    from app.services.order_index_service import OrderIndexService

                    task.progress = 80
                    await db.commit()

                    upserted_rows = await OrderIndexService.upsert_order_times(
                        db,
                        org_id=org_id,
                        shop_id=shop_id,
                        platform_code=order_scope_code,
                        orders=proc_result.get("orders", []),
                        source_file_id=file_id,
                    )
                    if file_type == "订单" and not upserted_rows:
                        raise ValueError(f"订单索引解析结果为空，错误: {proc_result['errors'][:3]}")

                    if file_type == "gmv":
                        should_requeue_order_dependents = upserted_rows > 0
                    else:
                        task.status = _result_task_status_from_processor_result(proc_result)
                        task.progress = 100
                        task.result_summary = {
                            "文件类型": "订单",
                            "订单索引写入行数": upserted_rows,
                            "总行数": proc_result["total_rows"],
                            "成功行数": proc_result["success_rows"],
                            "失败行数": proc_result["failed_rows"],
                            "错误明细": _json_safe(proc_result["errors"][:10]),
                        }
                        _set_task_result_from_processor(task, proc_result)
                        task.finished_at = datetime.now(timezone.utc)

                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]

                        await db.commit()
                        await _requeue_order_dependent_tasks_after_order_upload_async(file_id)
                        return

                if file_type == "订单":
                    raise ValueError(f"订单索引解析结果为空，错误: {proc_result['errors'][:3]}")

                if file_type == "动账" and "return_cost_rows" in proc_result:
                    from app.services.order_index_service import OrderIndexService
                    from app.tasks.aggregation import AggregationService

                    task.progress = 80
                    await db.commit()

                    return_cost_rows = proc_result.get("return_cost_rows", [])
                    if not return_cost_rows:
                        task.status = _result_task_status_from_processor_result(proc_result)
                        task.progress = 100
                        task.result_summary = {
                            "文件类型": "动账",
                            "汇总记录ID": [],
                            "总行数": proc_result["total_rows"],
                            "成功行数": proc_result["success_rows"],
                            "失败行数": proc_result["failed_rows"],
                            "缺少订单创建时间行数": 0,
                            "汇总分组数": 0,
                            "错误明细": _json_safe(proc_result["errors"][:10]),
                        }
                        _set_task_result_from_processor(task, proc_result)
                        task.finished_at = datetime.now(timezone.utc)

                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]

                        await db.commit()
                        return

                    order_created_times = await OrderIndexService.get_order_created_times(
                        db,
                        platform_code=order_scope_code,
                        order_nos=[safe_str(row.get("order_no")) for row in return_cost_rows],
                    )

                    grouped_return_cost, missing_order_nos, fallback_order_nos = _group_money_by_order_or_fallback_time(
                        return_cost_rows,
                        order_created_times=order_created_times,
                        amount_key="return_cost",
                        fallback_time_key="entry_time",
                    )

                    summary_ids: list[int] = []
                    for (g_year, g_month), return_cost in grouped_return_cost.items():
                        summary = await AggregationService.upsert_summary_dict(
                            db,
                            org_id=org_id,
                            shop_id=shop_id,
                            year=g_year,
                            month=g_month,
                            platform_name=platform_code,
                            shop_name=shop_name,
                            values={"return_cost": return_cost},
                            source_file_id=file_id,
                            source_year=source_year,
                            source_month=source_month,
                            source_platform_code=platform_code,
                            report_platform_code=report_platform_code,
                            shop_platform_code=report_platform_code,
                        )
                        summary_ids.append(summary.id)

                    task.progress = 100
                    task.result_summary = _build_order_or_fallback_time_summary(
                        type_code="动账",
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_return_cost),
                        missing_order_nos=missing_order_nos,
                        fallback_order_nos=fallback_order_nos,
                        fallback_label="入账时间",
                    )
                    task.status = _result_task_status_from_summary(task.result_summary)
                    _set_task_result_from_summary(task, task.result_summary)
                    task.finished_at = datetime.now(timezone.utc)

                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]

                    await db.commit()
                    return

                if file_type in {"动账", "其他服务款"} and "return_cost_contribution_rows" in proc_result:
                    from app.services.order_index_service import OrderIndexService
                    from app.tasks.aggregation import AggregationService

                    task.progress = 80
                    await db.commit()

                    logger.debug(f"Processor result: {proc_result}")

                    contribution_rows = proc_result.get("return_cost_contribution_rows", [])
                    if not contribution_rows:
                        task.status = _result_task_status_from_processor_result(proc_result)
                        task.progress = 100
                        task.result_summary = {
                            "文件类型": file_type,
                            "汇总记录ID": [],
                            "总行数": proc_result["total_rows"],
                            "成功行数": proc_result["success_rows"],
                            "失败行数": proc_result["failed_rows"],
                            "缺少订单创建时间行数": 0,
                            "汇总分组数": 0,
                            "错误明细": _json_safe(proc_result["errors"][:10]),
                        }
                        _set_task_result_from_processor(task, proc_result)
                        task.finished_at = datetime.now(timezone.utc)
                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]
                        await db.commit()
                        return

                    order_created_times = await OrderIndexService.get_order_created_times(
                        db,
                        platform_code=order_scope_code,
                        order_nos=[safe_str(row.get("order_no")) for row in contribution_rows],
                    )
                    grouped_return_cost, missing_order_nos = _group_money_by_order_created_time(
                        contribution_rows,
                        order_created_times=order_created_times,
                        amount_key="return_cost",
                    )

                    summary_ids: list[int] = []
                    for (g_year, g_month), return_cost in grouped_return_cost.items():
                        summary = await AggregationService.upsert_return_cost_contribution(
                            db,
                            org_id=org_id,
                            shop_id=shop_id,
                            year=g_year,
                            month=g_month,
                            platform_name=platform_code,
                            shop_name=shop_name,
                            contribution_key=file_type,
                            return_cost=return_cost,
                            source_file_id=file_id,
                            source_year=source_year,
                            source_month=source_month,
                            source_platform_code=platform_code,
                            report_platform_code=report_platform_code,
                            shop_platform_code=report_platform_code,
                        )
                        summary_ids.append(summary.id)

                    task.progress = 100
                    task.result_summary = _build_order_dependency_summary(
                        type_code=file_type,
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_return_cost),
                        missing_order_nos=missing_order_nos,
                    )
                    task.status = _result_task_status_from_summary(task.result_summary)
                    _set_task_result_from_summary(task, task.result_summary)
                    task.finished_at = datetime.now(timezone.utc)
                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]
                    await db.commit()
                    return

                if file_type == "运费险" and "insurance_fee_rows" in proc_result:
                    from app.services.order_index_service import OrderIndexService
                    from app.tasks.aggregation import AggregationService

                    task.progress = 80
                    await db.commit()

                    insurance_fee_rows = proc_result.get("insurance_fee_rows", [])
                    if not insurance_fee_rows:
                        task.status = _result_task_status_from_processor_result(proc_result)
                        task.progress = 100
                        task.result_summary = {
                            "文件类型": "运费险",
                            "汇总记录ID": [],
                            "总行数": proc_result["total_rows"],
                            "成功行数": proc_result["success_rows"],
                            "失败行数": proc_result["failed_rows"],
                            "缺少订单创建时间行数": 0,
                            "汇总分组数": 0,
                            "错误明细": _json_safe(proc_result["errors"][:10]),
                        }
                        _set_task_result_from_processor(task, proc_result)
                        task.finished_at = datetime.now(timezone.utc)
                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]
                        await db.commit()
                        return

                    order_created_times = await OrderIndexService.get_order_created_times(
                        db,
                        platform_code=order_scope_code,
                        order_nos=[safe_str(row.get("order_no")) for row in insurance_fee_rows],
                    )
                    grouped_insurance_fee, missing_order_nos, fallback_order_nos = _group_money_by_order_or_fallback_time(
                        insurance_fee_rows,
                        order_created_times=order_created_times,
                        amount_key="insurance_fee",
                        fallback_time_key="effective_time",
                    )

                    summary_ids: list[int] = []
                    for (g_year, g_month), insurance_fee in grouped_insurance_fee.items():
                        summary = await AggregationService.upsert_summary_dict(
                            db,
                            org_id=org_id,
                            shop_id=shop_id,
                            year=g_year,
                            month=g_month,
                            platform_name=platform_code,
                            shop_name=shop_name,
                            values={"insurance_fee": insurance_fee},
                            source_file_id=file_id,
                            source_year=source_year,
                            source_month=source_month,
                            source_platform_code=platform_code,
                            report_platform_code=report_platform_code,
                            shop_platform_code=report_platform_code,
                        )
                        summary_ids.append(summary.id)

                    task.progress = 100
                    task.result_summary = _build_order_or_fallback_time_summary(
                        type_code="运费险",
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_insurance_fee),
                        missing_order_nos=missing_order_nos,
                        fallback_order_nos=fallback_order_nos,
                        fallback_label="生效时间",
                    )
                    task.status = _result_task_status_from_summary(task.result_summary)
                    _set_task_result_from_summary(task, task.result_summary)
                    task.finished_at = datetime.now(timezone.utc)
                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]
                    await db.commit()
                    return

                if file_type == "动账" and "order_summary_rows" in proc_result:
                    from app.services.order_index_service import OrderIndexService
                    from app.tasks.aggregation import AggregationService

                    task.progress = 80
                    await db.commit()

                    order_summary_rows = proc_result.get("order_summary_rows", [])
                    summary_fields = tuple(proc_result.get("order_summary_fields") or [])
                    if not order_summary_rows:
                        task.status = _result_task_status_from_processor_result(proc_result)
                        task.progress = 100
                        task.result_summary = {
                            "文件类型": "动账",
                            "汇总记录ID": [],
                            "总行数": proc_result["total_rows"],
                            "成功行数": proc_result["success_rows"],
                            "失败行数": proc_result["failed_rows"],
                            "缺少订单创建时间行数": 0,
                            "汇总分组数": 0,
                            "错误明细": _json_safe(proc_result["errors"][:10]),
                        }
                        _set_task_result_from_processor(task, proc_result)
                        task.finished_at = datetime.now(timezone.utc)
                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]
                        await db.commit()
                        return

                    order_created_times = await OrderIndexService.get_order_created_times(
                        db,
                        platform_code=order_scope_code,
                        order_nos=[safe_str(row.get("order_no")) for row in order_summary_rows],
                    )
                    grouped_values, missing_order_nos = _group_summary_rows_by_order_created_time(
                        order_summary_rows,
                        order_created_times=order_created_times,
                        fields=summary_fields,
                    )

                    summary_ids: list[int] = []
                    for (g_year, g_month), values in grouped_values.items():
                        summary = await AggregationService.upsert_summary_dict(
                            db,
                            org_id=org_id,
                            shop_id=shop_id,
                            year=g_year,
                            month=g_month,
                            platform_name=platform_code,
                            shop_name=shop_name,
                            values=values,
                            source_file_id=file_id,
                            source_year=source_year,
                            source_month=source_month,
                            source_platform_code=platform_code,
                            report_platform_code=report_platform_code,
                            shop_platform_code=report_platform_code,
                        )
                        summary_ids.append(summary.id)

                    task.progress = 100
                    task.result_summary = _build_order_dependency_summary(
                        type_code="动账",
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_values),
                        missing_order_nos=missing_order_nos,
                    )
                    task.status = _result_task_status_from_summary(task.result_summary)
                    _set_task_result_from_summary(task, task.result_summary)
                    task.finished_at = datetime.now(timezone.utc)
                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]
                    await db.commit()
                    return

                if not proc_result["groups"]:
                    if proc_result.get("errors"):
                        raise ValueError(f"解析结果为空，错误: {proc_result['errors'][:3]}")

                    task.status = _result_task_status_from_processor_result(proc_result)
                    task.progress = 100
                    task.result_summary = {
                        "汇总记录ID": [],
                        "总行数": proc_result["total_rows"],
                        "成功行数": proc_result["success_rows"],
                        "失败行数": proc_result["failed_rows"],
                        "汇总分组数": 0,
                        "错误明细": [],
                    }
                    _set_task_result_from_processor(task, proc_result)
                    task.finished_at = datetime.now(timezone.utc)

                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]

                    await db.commit()
                    return

                # 7. Upsert each group into the summary table
                task.progress = 80
                await db.commit()

                from app.tasks.aggregation import AggregationService

                summary_ids: list[int] = []
                summary_lookup: dict[tuple[int, int], int] = {}
                for group_key_str, agg_values in proc_result["groups"].items():
                    parts = group_key_str.split("|")
                    g_shop, g_year, g_month = parts[0], int(parts[1]), int(parts[2])

                    summary = await AggregationService.upsert_summary_dict(
                        db,
                        org_id=org_id,
                        shop_id=shop_id,
                        year=g_year,
                        month=g_month,
                        platform_name=platform_code,
                        shop_name=g_shop,
                        values=agg_values,
                        source_file_id=file_id,
                        source_year=source_year,
                        source_month=source_month,
                        source_platform_code=platform_code,
                        report_platform_code=report_platform_code,
                        shop_platform_code=report_platform_code,
                    )
                    summary_ids.append(summary.id)
                    summary_lookup[(g_year, g_month)] = summary.id

                if (
                    file_type == "动账"
                    and platform_code == "douyin"
                    and proc_result.get("detail_rows")
                    and shop_id is not None
                    and source_year is not None
                    and source_month is not None
                ):
                    from app.services.douyin_dongzhang_detail_service import DouyinDongzhangDetailService

                    await DouyinDongzhangDetailService.sync_details(
                        db,
                        task_id=task.id,
                        file_id=file_id,
                        org_id=org_id,
                        shop_id=shop_id,
                        shop_name=shop_name,
                        source_year=int(source_year),
                        source_month=int(source_month),
                        source_platform_code=platform_code,
                        report_platform_code=report_platform_code,
                        detail_rows=list(proc_result.get("detail_rows") or []),
                        summary_lookup=summary_lookup,
                    )

                # 8. Update final status
                task.status = _result_task_status_from_processor_result(proc_result)
                task.progress = 100
                task.result_summary = {
                    "汇总记录ID": summary_ids,
                    "总行数": proc_result["total_rows"],
                    "成功行数": proc_result["success_rows"],
                    "失败行数": proc_result["failed_rows"],
                    "汇总分组数": len(proc_result["groups"]),
                    "错误明细": _json_safe(proc_result["errors"][:10]),
                }
                _set_task_result_from_processor(task, proc_result)
                task.finished_at = datetime.now(timezone.utc)

                if upload_file:
                    upload_file.status = "success"
                    upload_file.row_count = proc_result["total_rows"]

                await db.commit()
                if should_requeue_order_dependents:
                    await _requeue_order_dependent_tasks_after_order_upload_async(file_id)

        except Exception as e:
            await db.rollback()
            task_result = await db.execute(select(ProcessingTask).where(ProcessingTask.id == task_id, ProcessingTask.is_deleted.is_(False)))
            task = task_result.scalar_one_or_none()
            upload_file = None
            if task is not None:
                file_result = await db.execute(select(UploadFile).where(UploadFile.id == file_id, UploadFile.is_deleted.is_(False)))
                upload_file = file_result.scalar_one_or_none()
                _mark_task_failed(task, upload_file, e, previous_state=previous_result_state)
            await db.commit()
            logger.exception("任务处理失败 file_id=%s oss_key=%s", file_id, oss_key)
            raise
