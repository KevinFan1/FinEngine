"""Async export center service."""

from __future__ import annotations

import json
import io
import re
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.export_job import ExportJob
from app.models.user import User
from app.schemas.export_job import ExportJobCreate
from app.services.bic_accounting_service import BicAccountingService
from app.services.douyin_dongzhang_detail_service import DouyinDongzhangDetailService
from app.services.merchant_reconciliation_service import MerchantReconciliationService
from app.services.oss_service import assume_sts_role, oss_service
from app.services.reconciliation_checklist_service import ReconciliationChecklistService
from app.services.summary_service import SummaryService
from app.services.transaction_accounting_service import TransactionAccountingService
from app.utils.query_filters import resolve_org_ids


EXPORT_JOB_STATUSES = {"queued", "running", "success", "failed", "expired"}


@dataclass(frozen=True)
class ExportSpec:
    module: str
    handler: Callable[[AsyncSession, User, dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ExportArtifact:
    payload: io.BytesIO | Path
    row_count: int | None = None


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if value in ("", None):
            continue
        cleaned[key] = value
    return cleaned


def _bool_param(params: dict[str, Any], key: str, default: bool = False) -> bool:
    value = params.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _int_param(params: dict[str, Any], key: str, default: int | None = None) -> int | None:
    value = params.get(key, default)
    if value in (None, ""):
        return default
    return int(value)


def _parse_int_ids(raw: Any) -> list[int] | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, list):
        return [int(item) for item in raw if str(item).strip()]
    ids: list[int] = []
    for item in str(raw).split(","):
        item = item.strip()
        if item:
            ids.append(int(item))
    return ids


def _parse_str_ids(raw: Any) -> list[str] | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n]+", "_", filename).strip(" ._")
    if not cleaned:
        cleaned = "导出文件.xlsx"
    if not cleaned.lower().endswith(".xlsx"):
        cleaned += ".xlsx"
    return cleaned[:500]



def _export_oss_key(job: ExportJob) -> str:
    now = datetime.now(timezone.utc)
    org_part = str(job.org_id or "global")
    return (
        f"{settings.EXPORT_OSS_PREFIX.strip('/')}/{org_part}/{job.user_id}/"
        f"{now:%Y/%m/%d}/{job.id}_{uuid.uuid4().hex}.xlsx"
    )


def _new_temp_export_path() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        return Path(tmp.name)


async def _summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=params.get("org_id"))
    scope = str(params.get("scope") or "all")
    return await SummaryService.export_summaries(
        db,
        org_ids=org_ids,
        summary_year=_int_param(params, "summary_year"),
        summary_month=_int_param(params, "summary_month"),
        summary_start_year=_int_param(params, "summary_start_year"),
        summary_start_month=_int_param(params, "summary_start_month"),
        summary_end_year=_int_param(params, "summary_end_year"),
        summary_end_month=_int_param(params, "summary_end_month"),
        source_year=_int_param(params, "source_year"),
        source_month=_int_param(params, "source_month"),
        source_start_year=_int_param(params, "source_start_year"),
        source_start_month=_int_param(params, "source_start_month"),
        source_end_year=_int_param(params, "source_end_year"),
        source_end_month=_int_param(params, "source_end_month"),
        platform_name=params.get("platform_name"),
        report_platform_name=params.get("report_platform_name"),
        shop_ids=params.get("shop_ids"),
        shop_name=params.get("shop_name"),
        keyword=params.get("keyword"),
        ids=_parse_int_ids(params.get("ids")) if scope == "selected" else None,
        page=_int_param(params, "page") if scope == "current_page" else None,
        page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        include_dongzhang_details=_bool_param(params, "include_dongzhang_details"),
    )


async def _summary_report_export(db: AsyncSession, user: User, params: dict[str, Any]):
    org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=params.get("org_id"))
    scope = str(params.get("scope") or "all")
    return await SummaryService.export_report_summaries(
        db,
        org_ids=org_ids,
        source_year=_int_param(params, "accounting_year") or _int_param(params, "source_year"),
        source_month=_int_param(params, "accounting_month") or _int_param(params, "source_month"),
        source_start_year=_int_param(params, "accounting_start_year"),
        source_start_month=_int_param(params, "accounting_start_month"),
        source_end_year=_int_param(params, "accounting_end_year"),
        source_end_month=_int_param(params, "accounting_end_month"),
        platform_name=params.get("platform_name"),
        report_platform_name=params.get("report_platform_name"),
        shop_ids=params.get("shop_ids"),
        shop_name=params.get("shop_name"),
        keyword=params.get("keyword"),
        ids=_parse_str_ids(params.get("ids")) if scope == "selected" else None,
        page=_int_param(params, "page") if scope == "current_page" else None,
        page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        include_dongzhang_details=_bool_param(params, "include_dongzhang_details"),
    )


async def _summary_dongzhang_detail_export(db: AsyncSession, user: User, params: dict[str, Any]):
    org_ids = resolve_org_ids(user_role=user.role, user_org_id=user.org_id, requested_org_id=params.get("org_id"))
    scope = str(params.get("scope") or "all")
    output_path = _new_temp_export_path()
    try:
        _summary, row_count = await DouyinDongzhangDetailService.export_summary_details_to_file(
            db,
            summary_id=int(params["summary_id"]),
            org_ids=org_ids,
            output_path=output_path,
            ids=_parse_int_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)



async def _transaction_detail_export(db: AsyncSession, user: User, params: dict[str, Any]):
    scope = str(params.get("scope") or "all")
    return await TransactionAccountingService.export_details(
        db,
        user=user,
        org_id=params.get("org_id"),
        task_id=_int_param(params, "task_id"),
        status=params.get("status"),
        platform_code=params.get("platform_code"),
        shop_name=params.get("shop_name"),
        shop_ids=params.get("shop_ids"),
        major_category_id=params.get("major_category_id"),
        subject_id=params.get("subject_id"),
        category_id=params.get("category_id"),
        transaction_direction=params.get("transaction_direction"),
        accounting_year=_int_param(params, "accounting_year"),
        accounting_month=_int_param(params, "accounting_month"),
        accounting_start_year=_int_param(params, "accounting_start_year"),
        accounting_start_month=_int_param(params, "accounting_start_month"),
        accounting_end_year=_int_param(params, "accounting_end_year"),
        accounting_end_month=_int_param(params, "accounting_end_month"),
        upload_accounting_year=_int_param(params, "upload_accounting_year"),
        upload_accounting_month=_int_param(params, "upload_accounting_month"),
        upload_accounting_start_year=_int_param(params, "upload_accounting_start_year"),
        upload_accounting_start_month=_int_param(params, "upload_accounting_start_month"),
        upload_accounting_end_year=_int_param(params, "upload_accounting_end_year"),
        upload_accounting_end_month=_int_param(params, "upload_accounting_end_month"),
        keyword=params.get("keyword"),
        ids=_parse_int_ids(params.get("ids")) if scope == "selected" else None,
        page=_int_param(params, "page") if scope == "current_page" else None,
        page_size=_int_param(params, "page_size") if scope == "current_page" else None,
    )


async def _transaction_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    scope = str(params.get("scope") or "all")
    return await TransactionAccountingService.export_summaries(
        db,
        user=user,
        org_id=params.get("org_id"),
        task_id=_int_param(params, "task_id"),
        platform_code=params.get("platform_code"),
        shop_name=params.get("shop_name"),
        shop_ids=params.get("shop_ids"),
        major_category_id=params.get("major_category_id"),
        subject_id=params.get("subject_id"),
        category_id=params.get("category_id"),
        transaction_direction=params.get("transaction_direction"),
        accounting_year=_int_param(params, "accounting_year"),
        accounting_month=_int_param(params, "accounting_month"),
        accounting_start_year=_int_param(params, "accounting_start_year"),
        accounting_start_month=_int_param(params, "accounting_start_month"),
        accounting_end_year=_int_param(params, "accounting_end_year"),
        accounting_end_month=_int_param(params, "accounting_end_month"),
        upload_accounting_year=_int_param(params, "upload_accounting_year"),
        upload_accounting_month=_int_param(params, "upload_accounting_month"),
        upload_accounting_start_year=_int_param(params, "upload_accounting_start_year"),
        upload_accounting_start_month=_int_param(params, "upload_accounting_start_month"),
        upload_accounting_end_year=_int_param(params, "upload_accounting_end_year"),
        upload_accounting_end_month=_int_param(params, "upload_accounting_end_month"),
        keyword=params.get("keyword"),
        ids=_parse_int_ids(params.get("ids")) if scope == "selected" else None,
        page=_int_param(params, "page") if scope == "current_page" else None,
        page_size=_int_param(params, "page_size") if scope == "current_page" else None,
    )


async def _transaction_annual_export(db: AsyncSession, user: User, params: dict[str, Any]):
    return await TransactionAccountingService.export_annual_summary(
        db,
        user=user,
        year=int(params["year"]),
        org_id=params.get("org_id"),
        task_id=_int_param(params, "task_id"),
        platform_code=params.get("platform_code"),
        shop_name=params.get("shop_name"),
        shop_ids=params.get("shop_ids"),
        major_category_id=params.get("major_category_id"),
        subject_id=params.get("subject_id"),
        category_id=params.get("category_id"),
        transaction_direction=params.get("transaction_direction"),
        upload_accounting_year=_int_param(params, "upload_accounting_year"),
        upload_accounting_month=_int_param(params, "upload_accounting_month"),
        upload_accounting_start_year=_int_param(params, "upload_accounting_start_year"),
        upload_accounting_start_month=_int_param(params, "upload_accounting_start_month"),
        upload_accounting_end_year=_int_param(params, "upload_accounting_end_year"),
        upload_accounting_end_month=_int_param(params, "upload_accounting_end_month"),
        keyword=params.get("keyword"),
    )


async def _bic_detail_export(db: AsyncSession, user: User, params: dict[str, Any]):
    payload = dict(params)
    if payload.get("ids") is not None:
        payload["ids"] = _parse_int_ids(payload.get("ids"))
    return await BicAccountingService.export_details(db, user=user, **payload)


async def _bic_source_export(db: AsyncSession, user: User, params: dict[str, Any]):
    payload = dict(params)
    if payload.get("ids") is not None:
        payload["ids"] = _parse_int_ids(payload.get("ids"))
    output_path = _new_temp_export_path()
    try:
        row_count = await BicAccountingService.export_source_rows_to_file(db, user=user, output_path=output_path, **payload)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _bic_reconciliation_export(db: AsyncSession, user: User, params: dict[str, Any]):
    return await BicAccountingService.export_reconciliation(
        db,
        user=user,
        org_id=params.get("org_id"),
        accounting_year=int(params["accounting_year"]),
        accounting_month=int(params["accounting_month"]),
        service_provider=str(params["service_provider"]),
        platform_code=params.get("platform_code"),
        shop_name=params.get("shop_name"),
        shop_ids=params.get("shop_ids"),
        qic_warehouse=params.get("qic_warehouse"),
    )


async def _merchant_reconciliation_detail_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await MerchantReconciliationService.export_details_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=int(params["accounting_year"]),
            accounting_month=int(params["accounting_month"]),
            shop_id=int(params["shop_id"]),
            keyword=params.get("keyword"),
            match_status=params.get("match_status"),
            ids=_parse_int_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _merchant_reconciliation_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await MerchantReconciliationService.export_summary_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=int(params["accounting_year"]),
            accounting_month=int(params["accounting_month"]),
            shop_id=_int_param(params, "shop_id"),
            keyword=params.get("keyword"),
            bank_status=params.get("bank_status"),
            ids=_parse_str_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
            include_related_details=_bool_param(params, "include_related_details"),
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _reconciliation_checklist_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await ReconciliationChecklistService.export_summary_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=_int_param(params, "accounting_year"),
            accounting_month=_int_param(params, "accounting_month"),
            accounting_start_year=_int_param(params, "accounting_start_year"),
            accounting_start_month=_int_param(params, "accounting_start_month"),
            accounting_end_year=_int_param(params, "accounting_end_year"),
            accounting_end_month=_int_param(params, "accounting_end_month"),
            merchant_subject_name=params.get("merchant_subject_name") or params.get("merchant_name"),
            receipt_merchant=params.get("receipt_merchant"),
            product_name=params.get("product_name"),
            keyword=params.get("keyword"),
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _reconciliation_checklist_product_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await ReconciliationChecklistService.export_product_summary_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=_int_param(params, "accounting_year"),
            accounting_month=_int_param(params, "accounting_month"),
            accounting_start_year=_int_param(params, "accounting_start_year"),
            accounting_start_month=_int_param(params, "accounting_start_month"),
            accounting_end_year=_int_param(params, "accounting_end_year"),
            accounting_end_month=_int_param(params, "accounting_end_month"),
            merchant_subject_name=params.get("merchant_subject_name"),
            receipt_merchant=params.get("receipt_merchant"),
            product_name=params.get("product_name"),
            keyword=params.get("keyword"),
            ids=_parse_str_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _reconciliation_checklist_receipt_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await ReconciliationChecklistService.export_receipt_summary_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=_int_param(params, "accounting_year"),
            accounting_month=_int_param(params, "accounting_month"),
            accounting_start_year=_int_param(params, "accounting_start_year"),
            accounting_start_month=_int_param(params, "accounting_start_month"),
            accounting_end_year=_int_param(params, "accounting_end_year"),
            accounting_end_month=_int_param(params, "accounting_end_month"),
            merchant_subject_name=params.get("merchant_subject_name"),
            receipt_merchant=params.get("receipt_merchant"),
            live_platform=params.get("live_platform"),
            keyword=params.get("keyword"),
            ids=_parse_str_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


async def _reconciliation_checklist_payable_balance_summary_export(db: AsyncSession, user: User, params: dict[str, Any]):
    output_path = _new_temp_export_path()
    scope = str(params.get("scope") or "all")
    try:
        row_count = await ReconciliationChecklistService.export_payable_balance_summary_to_file(
            db,
            user=user,
            output_path=output_path,
            org_id=params.get("org_id"),
            accounting_year=_int_param(params, "accounting_year"),
            accounting_month=_int_param(params, "accounting_month"),
            accounting_start_year=_int_param(params, "accounting_start_year"),
            accounting_start_month=_int_param(params, "accounting_start_month"),
            accounting_end_year=_int_param(params, "accounting_end_year"),
            accounting_end_month=_int_param(params, "accounting_end_month"),
            merchant_subject_name=params.get("merchant_subject_name"),
            receipt_merchant=params.get("receipt_merchant"),
            keyword=params.get("keyword"),
            ids=_parse_str_ids(params.get("ids")) if scope == "selected" else None,
            page=_int_param(params, "page") if scope == "current_page" else None,
            page_size=_int_param(params, "page_size") if scope == "current_page" else None,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return ExportArtifact(output_path, row_count=row_count)


EXPORT_SPECS: dict[str, ExportSpec] = {
    "summary.detail": ExportSpec("summary", _summary_export),
    "summary.report": ExportSpec("summary", _summary_report_export),
    "summary.dongzhang_details": ExportSpec("summary", _summary_dongzhang_detail_export),
    "transaction.details": ExportSpec("transaction_accounting", _transaction_detail_export),
    "transaction.summary": ExportSpec("transaction_accounting", _transaction_summary_export),
    "transaction.annual": ExportSpec("transaction_accounting", _transaction_annual_export),
    "bic.details": ExportSpec("bic_accounting", _bic_detail_export),
    "bic.source_rows": ExportSpec("bic_accounting", _bic_source_export),
    "bic.reconciliation": ExportSpec("bic_accounting", _bic_reconciliation_export),
    "merchant_reconciliation.details": ExportSpec("merchant_reconciliation", _merchant_reconciliation_detail_export),
    "merchant_reconciliation.summary": ExportSpec("merchant_reconciliation", _merchant_reconciliation_summary_export),
    "reconciliation_checklist.summary": ExportSpec("reconciliation_checklist", _reconciliation_checklist_summary_export),
    "reconciliation_checklist.product_summary": ExportSpec("reconciliation_checklist", _reconciliation_checklist_product_summary_export),
    "reconciliation_checklist.receipt_summary": ExportSpec("reconciliation_checklist", _reconciliation_checklist_receipt_summary_export),
    "reconciliation_checklist.payable_balance_summary": ExportSpec("reconciliation_checklist", _reconciliation_checklist_payable_balance_summary_export),
}


class ExportJobService:
    @staticmethod
    async def create_job(db: AsyncSession, *, data: ExportJobCreate, user: User) -> ExportJob:
        spec = EXPORT_SPECS.get(data.export_type)
        if spec is None:
            raise ValueError("不支持的导出类型")
        job = ExportJob(
            org_id=user.org_id,
            user_id=user.id,
            module=spec.module,
            export_type=data.export_type,
            title=data.title.strip(),
            filename=_safe_filename(data.filename),
            params=_clean_params(data.params),
            status="queued",
            progress=0,
        )
        setattr(job, "operator_name", user.display_name)
        db.add(job)
        await db.flush()
        return job

    @staticmethod
    async def dispatch_job(db: AsyncSession, job: ExportJob) -> ExportJob:
        from app.tasks.export_jobs import run_export_job

        result = run_export_job.delay(job.id)
        job.celery_task_id = result.id
        await db.flush()
        return job

    @staticmethod
    def dispatch_job_after_commit(db: AsyncSession, job: ExportJob) -> None:
        from app.core.database import register_after_commit

        async def dispatch() -> None:
            try:
                await ExportJobService.dispatch_job(db, job)
            except Exception as exc:
                job.status = "failed"
                job.progress = 100
                job.error_message = f"导出任务投递失败: {exc}"
                job.finished_at = datetime.now(timezone.utc)
                await db.flush()

        register_after_commit(db, dispatch)

    @staticmethod
    async def dispatch_job_by_id(job_id: int) -> None:
        from app.core.database import async_session_factory
        from app.tasks.export_jobs import run_export_job

        async with async_session_factory() as session:
            job = await session.get(ExportJob, job_id)
            if job is None or job.is_deleted:
                return
            try:
                result = run_export_job.delay(job.id)
                job.celery_task_id = result.id
            except Exception as exc:
                job.status = "failed"
                job.progress = 100
                job.error_message = f"导出任务投递失败: {exc}"
                job.finished_at = datetime.now(timezone.utc)
            await session.commit()

    @staticmethod
    def _visibility_filters(user: User, *, mine_only: bool = False) -> list[Any]:
        if mine_only:
            return [ExportJob.user_id == user.id]
        if user.role == "superadmin":
            return []
        if user.role == "org_admin":
            return [ExportJob.org_id == user.org_id]
        return [ExportJob.user_id == user.id]

    @staticmethod
    async def dispatch_unsubmitted_jobs(
        db: AsyncSession,
        *,
        user: User,
        limit: int = 20,
        mine_only: bool = False,
    ) -> int:
        from app.tasks.export_jobs import run_export_job

        result = await db.execute(
            select(ExportJob)
            .where(
                ExportJob.status == "queued",
                ExportJob.celery_task_id.is_(None),
                ExportJob.is_deleted.is_(False),
                *ExportJobService._visibility_filters(user, mine_only=mine_only),
            )
            .order_by(ExportJob.id.asc())
            .limit(limit)
        )
        jobs = list(result.scalars().all())
        dispatched = 0
        now = datetime.now(timezone.utc)
        for job in jobs:
            try:
                async_result = run_export_job.delay(job.id)
                job.celery_task_id = async_result.id
                dispatched += 1
            except Exception as exc:
                job.status = "failed"
                job.progress = 100
                job.error_message = f"导出任务投递失败: {exc}"
                job.finished_at = now
        if jobs:
            await db.flush()
        return dispatched

    @staticmethod
    async def recover_queued_jobs(db: AsyncSession, *, limit: int = 100) -> int:
        from app.tasks.export_jobs import run_export_job

        result = await db.execute(
            select(ExportJob)
            .where(
                ExportJob.status == "queued",
                ExportJob.is_deleted.is_(False),
            )
            .order_by(ExportJob.id.asc())
            .limit(limit)
        )
        jobs = list(result.scalars().all())
        dispatched = 0
        for job in jobs:
            async_result = run_export_job.delay(job.id)
            job.celery_task_id = async_result.id
            dispatched += 1
        if jobs:
            await db.flush()
        return dispatched

    @staticmethod
    async def mark_job_running(
        db: AsyncSession,
        *,
        job_id: int,
        celery_task_id: str | None = None,
    ) -> ExportJob:
        job = await db.get(ExportJob, job_id)
        if job is None or job.is_deleted:
            raise ValueError("导出任务不存在")
        if job.status in {"success", "failed", "expired"}:
            return job

        job.status = "running"
        job.progress = max(int(job.progress or 0), 10)
        job.started_at = datetime.now(timezone.utc)
        job.finished_at = None
        job.error_message = None
        if celery_task_id:
            job.celery_task_id = celery_task_id
        await db.flush()
        return job

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        *,
        user: User,
        status: str | None = None,
        module: str | None = None,
        page: int = 1,
        page_size: int = 20,
        mine_only: bool = False,
    ) -> tuple[list[ExportJob], int]:
        filters = [
            ExportJob.is_deleted.is_(False),
            *ExportJobService._visibility_filters(user, mine_only=mine_only),
        ]
        if status:
            filters.append(ExportJob.status == status)
        if module:
            filters.append(ExportJob.module == module)

        total = (await db.execute(select(func.count()).select_from(ExportJob).where(*filters))).scalar() or 0
        result = await db.execute(
            select(ExportJob)
            .where(*filters)
            .order_by(ExportJob.created_at.desc(), ExportJob.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_job_for_user(db: AsyncSession, *, job_id: int, user: User) -> ExportJob | None:
        result = await db.execute(select(ExportJob).where(ExportJob.id == job_id, ExportJob.is_deleted.is_(False)))
        job = result.scalar_one_or_none()
        if job is None:
            return None
        if user.role == "superadmin":
            return job
        if user.role == "org_admin" and job.org_id == user.org_id:
            return job
        if job.user_id == user.id:
            return job
        return None

    @staticmethod
    async def run_job(db: AsyncSession, *, job_id: int, mark_running: bool = True) -> ExportJob:
        job = await db.get(ExportJob, job_id)
        if job is None or job.is_deleted:
            raise ValueError("导出任务不存在")
        if job.status in {"success", "failed", "expired"}:
            return job
        user = await db.get(User, job.user_id)
        if user is None or user.is_deleted:
            raise ValueError("导出用户不存在")
        spec = EXPORT_SPECS.get(job.export_type)
        if spec is None:
            raise ValueError("不支持的导出类型")

        if mark_running:
            job.status = "running"
            job.progress = max(int(job.progress or 0), 10)
            job.started_at = datetime.now(timezone.utc)
            job.finished_at = None
            job.error_message = None
            await db.flush()

        try:
            artifact = await spec.handler(db, user, dict(job.params or {}))
            job.progress = 80
            await db.flush()

            oss_key = _export_oss_key(job)
            payload = artifact.payload if isinstance(artifact, ExportArtifact) else artifact
            if isinstance(artifact, ExportArtifact):
                job.row_count = artifact.row_count

            if isinstance(payload, Path):
                tmp_path = payload
            else:
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    payload.seek(0)
                    tmp.write(payload.read())
            try:
                file_size = tmp_path.stat().st_size
                oss_service.upload_file(
                    oss_key,
                    tmp_path,
                    internal=settings.INTERNAL_DOWNLOAD,
                    headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                )
            finally:
                tmp_path.unlink(missing_ok=True)

            job.oss_key = oss_key
            job.file_size = file_size
            job.status = "success"
            job.progress = 100
            job.finished_at = datetime.now(timezone.utc)
            job.expires_at = job.finished_at + timedelta(days=max(settings.EXPORT_FILE_EXPIRE_DAYS, 1))
            job.result_summary = None
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
        await db.flush()
        return job

    @staticmethod
    def download_sts(job: ExportJob) -> dict[str, Any]:
        if not settings.ALIYUN_STS_ROLE_ARN or not settings.ALIYUN_ACCESS_KEY_ID:
            raise ValueError("阿里云 OSS STS 未配置")
        if job.status != "success" or not job.oss_key:
            raise ValueError("导出文件尚未生成")
        if job.expires_at and job.expires_at < datetime.now(timezone.utc):
            raise ValueError("导出文件已过期，请重新导出")

        policy = {
            "Version": "1",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["oss:GetObject"],
                    "Resource": [f"acs:oss:*:*:{settings.ALIYUN_OSS_BUCKET}/{job.oss_key}"],
                }
            ],
        }
        creds = assume_sts_role(
            role_arn=settings.ALIYUN_STS_ROLE_ARN,
            session_name=f"finengine-export-{job.id}-{job.user_id}",
            duration_seconds=settings.ALIYUN_STS_EXPIRE_SECONDS,
            policy=json.dumps(policy, ensure_ascii=False, separators=(",", ":")),
        )
        return {
            **creds,
            "region": settings.ALIYUN_OSS_REGION,
            "bucket": settings.ALIYUN_OSS_BUCKET,
            "endpoint": oss_service.normalized_endpoint(),
            "oss_key": job.oss_key,
            "filename": job.filename,
            "file_size": job.file_size,
        }
