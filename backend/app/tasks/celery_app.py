"""Celery application and platform-specific file processing tasks."""

import asyncio
import logging
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from celery import Celery
from celery.signals import worker_process_shutdown

from app.core.config import settings
from app.tasks.processors.base import safe_str

celery_app = Celery("finengine", broker=settings.CELERY_REDIS_URL, backend=settings.CELERY_REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_soft_time_limit=3600,
    task_time_limit=7200,
)

celery_app.autodiscover_tasks(["app.tasks"])

logger = logging.getLogger("finengine.worker")
_worker_loop: asyncio.AbstractEventLoop | None = None
SUPPORTED_TEMP_SUFFIXES = {".xlsx", ".xlsm", ".xls", ".csv"}
FILENAME_TYPE_PATTERN = re.compile(r"^\d{2,4}年\d{1,2}月[ _](动账|gmv|bic|运费险|订单|其他服务款)[ _].+\.(?:xlsx|xlsm|xls|csv)$", re.IGNORECASE)


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


def _mark_task_failed(task, upload_file, error_message: str) -> None:
    task.status = "failed"
    task.error_message = error_message
    task.finished_at = datetime.now(timezone.utc)
    if upload_file:
        upload_file.status = "failed"
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
    return grouped_return_cost, list(dict.fromkeys(missing_order_nos))


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

    return grouped, list(dict.fromkeys(missing_order_nos)), list(dict.fromkeys(fallback_order_nos))


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
    return grouped, list(dict.fromkeys(missing_order_nos))


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
    effective_success_rows = max(int(proc_result.get("success_rows") or 0) - missing_order_count, 0)
    effective_failed_rows = int(proc_result.get("failed_rows") or 0) + missing_order_count
    errors = list(proc_result.get("errors") or [])[:10]
    if missing_order_nos:
        sample_text = "、".join(missing_order_nos)
        errors.append(f"缺少订单创建时间 {missing_order_count} 条，已按 0 统计；订单号: {sample_text}")

    return {
        "type": type_code,
        "dependency_type": "order_index",
        "summary_ids": summary_ids,
        "total_rows": proc_result.get("total_rows", 0),
        "success_rows": effective_success_rows,
        "failed_rows": effective_failed_rows,
        "parse_success_rows": proc_result.get("success_rows", 0),
        "parse_failed_rows": proc_result.get("failed_rows", 0),
        "missing_order_count": missing_order_count,
        "missing_order_samples": missing_order_nos[:20],
        "groups": groups,
        "errors": _json_safe(errors),
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
    summary["fallback_time_label"] = fallback_label
    summary["fallback_time_count"] = fallback_count
    summary["fallback_time_samples"] = fallback_order_nos[:20]
    if fallback_order_nos:
        sample_text = "、".join(fallback_order_nos[:20])
        errors = list(summary.get("errors") or [])
        errors.append(f"订单索引未命中 {fallback_count} 条，已使用{fallback_label}归属年月；订单号: {sample_text}")
        summary["errors"] = _json_safe(errors)
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
    return grouped, list(dict.fromkeys(missing_order_nos))


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
            ProcessingTask.status.notin_(["queued", "running"]),
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


def _reset_task_for_requeue(task, upload_file) -> None:
    task.status = "queued"
    task.progress = 0
    task.celery_task_id = None
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.error_message = None
    task.result_summary = None
    task.started_at = None
    task.finished_at = None
    upload_file.status = "uploaded"
    upload_file.error_message = None


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

        task.status = "running"
        task.celery_task_id = task_instance.request.id
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        # 2. Update file status
        file_stmt = select(UploadFile).where(UploadFile.id == file_id, UploadFile.is_deleted.is_(False))
        file_result = await db.execute(file_stmt)
        upload_file = file_result.scalar_one_or_none()
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
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": "订单",
                            "order_index_rows": upserted_rows,
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
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
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": "动账",
                            "summary_ids": [],
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "missing_order_count": 0,
                            "groups": 0,
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
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

                    task.status = "success"
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
                    task.success_rows = task.result_summary["success_rows"]
                    task.failed_rows = task.result_summary["failed_rows"]
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
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": file_type,
                            "summary_ids": [],
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "missing_order_count": 0,
                            "groups": 0,
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
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

                    task.status = "success"
                    task.progress = 100
                    task.result_summary = _build_order_dependency_summary(
                        type_code=file_type,
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_return_cost),
                        missing_order_nos=missing_order_nos,
                    )
                    task.success_rows = task.result_summary["success_rows"]
                    task.failed_rows = task.result_summary["failed_rows"]
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
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": "运费险",
                            "summary_ids": [],
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "missing_order_count": 0,
                            "groups": 0,
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
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

                    task.status = "success"
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
                    task.success_rows = task.result_summary["success_rows"]
                    task.failed_rows = task.result_summary["failed_rows"]
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
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": "动账",
                            "summary_ids": [],
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "missing_order_count": 0,
                            "groups": 0,
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
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

                    task.status = "success"
                    task.progress = 100
                    task.result_summary = _build_order_dependency_summary(
                        type_code="动账",
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_values),
                        missing_order_nos=missing_order_nos,
                    )
                    task.success_rows = task.result_summary["success_rows"]
                    task.failed_rows = task.result_summary["failed_rows"]
                    task.finished_at = datetime.now(timezone.utc)
                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]
                    await db.commit()
                    return

                if file_type == "bic" and "bic_rows" in proc_result:
                    from app.services.order_index_service import OrderIndexService
                    from app.tasks.aggregation import AggregationService

                    task.progress = 80
                    await db.commit()

                    bic_rows = proc_result.get("bic_rows", [])
                    if not bic_rows:
                        task.status = "success"
                        task.progress = 100
                        task.success_rows = proc_result["success_rows"]
                        task.failed_rows = proc_result["failed_rows"]
                        task.result_summary = {
                            "type": "bic",
                            "summary_ids": [],
                            "total_rows": proc_result["total_rows"],
                            "success_rows": proc_result["success_rows"],
                            "failed_rows": proc_result["failed_rows"],
                            "missing_order_count": 0,
                            "groups": 0,
                            "errors": _json_safe(proc_result["errors"][:10]),
                        }
                        task.finished_at = datetime.now(timezone.utc)
                        if upload_file:
                            upload_file.status = "success"
                            upload_file.row_count = proc_result["total_rows"]
                        await db.commit()
                        return

                    order_created_times = await OrderIndexService.get_order_created_times(
                        db,
                        platform_code=order_scope_code,
                        order_nos=[safe_str(row.get("order_no")) for row in bic_rows],
                    )
                    grouped_bic, missing_order_nos = _group_money_by_order_created_time(
                        bic_rows,
                        order_created_times=order_created_times,
                        amount_key="bic",
                    )

                    summary_ids: list[int] = []
                    for (g_year, g_month), bic in grouped_bic.items():
                        summary = await AggregationService.upsert_summary_dict(
                            db,
                            org_id=org_id,
                            shop_id=shop_id,
                            year=g_year,
                            month=g_month,
                            platform_name=platform_code,
                            shop_name=shop_name,
                            values={"bic": bic},
                            source_file_id=file_id,
                            source_year=source_year,
                            source_month=source_month,
                            source_platform_code=platform_code,
                            report_platform_code=report_platform_code,
                            shop_platform_code=report_platform_code,
                        )
                        summary_ids.append(summary.id)

                    task.status = "success"
                    task.progress = 100
                    task.result_summary = _build_order_dependency_summary(
                        type_code="bic",
                        proc_result=proc_result,
                        summary_ids=summary_ids,
                        groups=len(grouped_bic),
                        missing_order_nos=missing_order_nos,
                    )
                    task.success_rows = task.result_summary["success_rows"]
                    task.failed_rows = task.result_summary["failed_rows"]
                    task.finished_at = datetime.now(timezone.utc)
                    if upload_file:
                        upload_file.status = "success"
                        upload_file.row_count = proc_result["total_rows"]
                    await db.commit()
                    return

                if not proc_result["groups"]:
                    if proc_result.get("errors"):
                        raise ValueError(f"解析结果为空，错误: {proc_result['errors'][:3]}")

                    task.status = "success"
                    task.progress = 100
                    task.success_rows = proc_result["success_rows"]
                    task.failed_rows = proc_result["failed_rows"]
                    task.result_summary = {
                        "summary_ids": [],
                        "total_rows": proc_result["total_rows"],
                        "success_rows": proc_result["success_rows"],
                        "failed_rows": proc_result["failed_rows"],
                        "groups": 0,
                        "errors": [],
                    }
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

                # 8. Update final status
                task.status = "success"
                task.progress = 100
                task.success_rows = proc_result["success_rows"]
                task.failed_rows = proc_result["failed_rows"]
                task.result_summary = {
                    "summary_ids": summary_ids,
                    "total_rows": proc_result["total_rows"],
                    "success_rows": proc_result["success_rows"],
                    "failed_rows": proc_result["failed_rows"],
                    "groups": len(proc_result["groups"]),
                    "errors": _json_safe(proc_result["errors"][:10]),
                }
                task.finished_at = datetime.now(timezone.utc)

                if upload_file:
                    upload_file.status = "success"
                    upload_file.row_count = proc_result["total_rows"]

                await db.commit()
                if should_requeue_order_dependents:
                    await _requeue_order_dependent_tasks_after_order_upload_async(file_id)

        except Exception as e:
            _mark_task_failed(task, upload_file, str(e))
            await db.commit()
            logger.exception("任务处理失败 file_id=%s oss_key=%s", file_id, oss_key)
            raise
