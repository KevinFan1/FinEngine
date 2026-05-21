"""Service layer for independent BIC accounting."""

import io
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.models.bic_accounting import BicDetail, BicReportRow, BicTask, BicUploadFile
from app.models.shop import Shop
from app.models.upload import UploadFile
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.oss_service import oss_service
from app.services.shop_service import ShopService
from app.services.transaction_accounting_service import TransactionAccountingService
from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, open_tabular_rows, safe_str
from app.tasks.processors.douyin import DOUYIN_BIC_HEADERS
from app.utils.money import safe_decimal

BIC_TARGET_FEE_ITEM = "质检费(通过)"
BIC_DETAIL_EXPORT_HEADERS = ["序号", "平台", "店铺", "核算年月", "QIC仓", "结算金额"]
BIC_REPORT_EXPORT_HEADERS = ["序号", "平台", "店铺", "核算年月", "结算金额"]
BIC_RESULT_TASK_STATUSES = ("success", "partial_success")


class BicAccountingService:
    @staticmethod
    def resolve_org_id(*, user: User, requested_org_id: int | None = None) -> int | None:
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
    ) -> BicTask:
        if (upload_file.parsed_type or "").lower() != "bic":
            raise ValueError("仅 BIC 文件可创建 BIC 任务")
        if (upload_file.source_platform_code or upload_file.detected_platform or "").lower() != "douyin":
            raise ValueError("BIC 核算当前仅支持抖音文件")

        source_platform = (upload_file.source_platform_code or upload_file.detected_platform or "").lower()
        shop_id = upload_file.shop_id
        shop_name = upload_file.parsed_shop
        if shop_id is None and shop_name:
            shop = await ShopService.get_or_create_shop(
                db,
                org_id=upload_file.org_id,
                platform_name=source_platform,
                shop_name=shop_name,
            )
            shop_id = shop.id
            shop_name = shop.shop_name

        existing_stmt = select(BicUploadFile).where(
            BicUploadFile.source_upload_file_id == upload_file.id,
            BicUploadFile.is_deleted.is_(False),
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        bic_upload_file = existing
        if bic_upload_file is not None and shop_id is not None and bic_upload_file.shop_id is None:
            bic_upload_file.shop_id = shop_id
        if existing is not None:
            task_stmt = (
                select(BicTask)
                .where(
                    BicTask.file_id == existing.id,
                    BicTask.is_deleted.is_(False),
                )
                .order_by(BicTask.id.desc())
            )
            current_task = (await db.execute(task_stmt)).scalars().first()
            if current_task is not None:
                return current_task

        if shop_id is not None and upload_file.parsed_year is not None and upload_file.parsed_month is not None:
            existing_business_file = await BicAccountingService._get_existing_business_upload_file(
                db,
                org_id=upload_file.org_id,
                platform_code=source_platform,
                shop_id=shop_id,
                accounting_year=upload_file.parsed_year,
                accounting_month=upload_file.parsed_month,
            )
            if existing_business_file is not None:
                if shop_id is not None and existing_business_file.shop_id is None:
                    existing_business_file.shop_id = shop_id
                current_task = await BicAccountingService._get_latest_task_for_upload_file(
                    db,
                    file_id=existing_business_file.id,
                )
                if current_task is not None:
                    return current_task
                bic_upload_file = existing_business_file

        if bic_upload_file is None:
            bic_upload_file = BicUploadFile(
                org_id=upload_file.org_id,
                user_id=user.id,
                shop_id=shop_id,
                source_upload_file_id=upload_file.id,
                original_name=upload_file.original_name,
                oss_key=upload_file.oss_key,
                file_size=upload_file.file_size,
                file_hash=upload_file.file_hash,
                platform_code=source_platform,
                shop_name=shop_name,
                accounting_year=upload_file.parsed_year,
                accounting_month=upload_file.parsed_month,
                status="uploaded",
            )
            db.add(bic_upload_file)
            await db.flush()

        task = BicTask(
            file_id=bic_upload_file.id,
            org_id=bic_upload_file.org_id,
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
            org_id=bic_upload_file.org_id,
            module="bic_accounting",
            action="upload_file",
            description=f"上传 BIC 文件 [{bic_upload_file.original_name}]",
            target_type="bic_upload_file",
            target_id=bic_upload_file.id,
            target_name=bic_upload_file.original_name,
            ip=ip,
            user_agent=user_agent,
            extra_data={
                "task_id": task.id,
                "file_size": bic_upload_file.file_size,
                "source_upload_file_id": upload_file.id,
            },
        )

        BicAccountingService.dispatch_task_after_commit(
            db,
            task=task,
            upload_file=bic_upload_file,
        )
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def rerun_task(
        db: AsyncSession,
        *,
        task_id: int,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> BicTask | None:
        task = await db.get(BicTask, task_id)
        if task is None or task.is_deleted:
            return None
        BicAccountingService.validate_org_scope(org_id=task.org_id, user=user)

        task.status = "queued"
        task.progress = 0
        task.processed_rows = 0
        task.success_rows = 0
        task.failed_rows = 0
        task.error_message = None
        task.result_summary = None
        task.started_at = None
        task.finished_at = None

        await db.execute(delete(BicDetail).where(BicDetail.task_id == task.id))
        await db.execute(delete(BicReportRow).where(BicReportRow.task_id == task.id))

        await AuditService.log(
            db,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            org_id=task.org_id,
            module="bic_accounting",
            action="task_rerun",
            description=f"重跑 BIC 任务 [{task.id}]",
            target_type="bic_task",
            target_id=task.id,
            ip=ip,
            user_agent=user_agent,
        )

        upload_file = await db.get(BicUploadFile, task.file_id)
        BicAccountingService.dispatch_task_after_commit(
            db,
            task=task,
            upload_file=upload_file,
        )
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    def dispatch_task_after_commit(
        db: AsyncSession,
        *,
        task: BicTask,
        upload_file: BicUploadFile | None,
    ) -> None:
        async def dispatch() -> None:
            try:
                from app.tasks.bic_accounting import run_bic_accounting_task

                async_result = run_bic_accounting_task.delay(task.id)
                task.celery_task_id = async_result.id
            except Exception as exc:
                task.status = "failed"
                task.progress = 100
                task.error_message = f"BIC任务投递失败: {exc}"
                task.finished_at = datetime.now(timezone.utc)
                if upload_file is not None:
                    upload_file.status = "failed"
                    upload_file.error_message = task.error_message
            await db.flush()

        register_after_commit(db, dispatch)

    @staticmethod
    async def _get_latest_task_for_upload_file(db: AsyncSession, *, file_id: int) -> BicTask | None:
        stmt = (
            select(BicTask)
            .where(
                BicTask.file_id == file_id,
                BicTask.is_deleted.is_(False),
            )
            .order_by(BicTask.id.desc())
        )
        return (await db.execute(stmt)).scalars().first()

    @staticmethod
    async def _get_existing_business_upload_file(
        db: AsyncSession,
        *,
        org_id: int,
        platform_code: str,
        shop_id: int,
        accounting_year: int,
        accounting_month: int,
    ) -> BicUploadFile | None:
        stmt = (
            select(BicUploadFile)
            .where(
                BicUploadFile.org_id == org_id,
                BicUploadFile.platform_code == platform_code,
                BicUploadFile.shop_id == shop_id,
                BicUploadFile.accounting_year == accounting_year,
                BicUploadFile.accounting_month == accounting_month,
                BicUploadFile.is_deleted.is_(False),
            )
            .order_by(BicUploadFile.id.desc())
        )
        return (await db.execute(stmt)).scalars().first()

    @staticmethod
    def _latest_result_task_ids_select():
        return (
            select(func.max(BicTask.id).label("task_id"))
            .select_from(BicTask)
            .join(BicUploadFile, BicUploadFile.id == BicTask.file_id)
            .where(
                BicTask.is_deleted.is_(False),
                BicUploadFile.is_deleted.is_(False),
                BicTask.status.in_(BIC_RESULT_TASK_STATUSES),
            )
            .group_by(
                BicUploadFile.org_id,
                BicUploadFile.platform_code,
                BicUploadFile.shop_id,
                BicUploadFile.accounting_year,
                BicUploadFile.accounting_month,
            )
        )

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        *,
        user: User,
        org_id: int | None = None,
        status: str | None = None,
        platform_code: str | None = None,
        shop_name: str | None = None,
        shop_id: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[BicTask, BicUploadFile, str | None]], int]:
        filters = [BicTask.is_deleted.is_(False), BicUploadFile.is_deleted.is_(False)]
        scoped_org_id = BicAccountingService.resolve_org_id(user=user, requested_org_id=org_id)
        if scoped_org_id is not None:
            filters.append(BicTask.org_id == scoped_org_id)
        if status:
            filters.append(BicTask.status.in_(TransactionAccountingService._split_filter_values(status)))
        platform_codes = TransactionAccountingService._split_filter_values(platform_code)
        if platform_codes:
            filters.append(BicUploadFile.platform_code.in_(platform_codes))
        shop_names = TransactionAccountingService._split_filter_values(shop_name)
        if shop_names:
            filters.append(BicUploadFile.shop_name.in_(shop_names))
        if shop_id is not None:
            filters.append(BicUploadFile.shop_id == shop_id)
        filters.extend(
            TransactionAccountingService._period_filters(
                BicUploadFile.accounting_year * 100 + BicUploadFile.accounting_month,
                start_year=accounting_start_year,
                start_month=accounting_start_month,
                end_year=accounting_end_year,
                end_month=accounting_end_month,
            )
        )
        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    BicUploadFile.original_name.ilike(like_pattern),
                    BicUploadFile.shop_name.ilike(like_pattern),
                    BicTask.error_message.ilike(like_pattern),
                )
            )

        stmt = (
            select(BicTask, BicUploadFile, Shop.shop_color)
            .join(BicUploadFile, BicUploadFile.id == BicTask.file_id)
            .outerjoin(Shop, Shop.id == BicUploadFile.shop_id)
            .where(*filters)
            .order_by(BicTask.id.desc())
        )
        count_stmt = select(func.count()).select_from(BicTask).join(BicUploadFile, BicUploadFile.id == BicTask.file_id).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0
        result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        return list(result.all()), total

    @staticmethod
    async def list_details(
        db: AsyncSession,
        *,
        user: User,
        org_id: int | None = None,
        task_id: int | None = None,
        platform_code: str | None = None,
        shop_name: str | None = None,
        shop_id: int | None = None,
        qic_warehouse: str | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        ids: list[int] | None = None,
        page: int | None = 1,
        page_size: int | None = 50,
    ) -> tuple[list[BicDetail], int]:
        filters = [BicDetail.is_deleted.is_(False)]
        scoped_org_id = BicAccountingService.resolve_org_id(user=user, requested_org_id=org_id)
        if scoped_org_id is not None:
            filters.append(BicDetail.org_id == scoped_org_id)
        if ids is not None:
            if not ids:
                return [], 0
            filters.append(BicDetail.id.in_(ids))
        if task_id is not None:
            filters.append(BicDetail.task_id == task_id)
        else:
            filters.append(BicDetail.task_id.in_(BicAccountingService._latest_result_task_ids_select()))
        platform_codes = TransactionAccountingService._split_filter_values(platform_code)
        if platform_codes:
            filters.append(BicDetail.platform_code.in_(platform_codes))
        shop_names = TransactionAccountingService._split_filter_values(shop_name)
        if shop_names:
            filters.append(BicDetail.shop_name.in_(shop_names))
        if shop_id is not None:
            filters.append(BicDetail.shop_id == shop_id)
        qic_values = TransactionAccountingService._split_filter_values(qic_warehouse)
        if qic_values:
            filters.append(BicDetail.qic_warehouse.in_(qic_values))
        if accounting_year is not None:
            filters.append(BicDetail.accounting_year == accounting_year)
        if accounting_month is not None:
            filters.append(BicDetail.accounting_month == accounting_month)
        filters.extend(
            TransactionAccountingService._period_filters(
                BicDetail.accounting_year * 100 + BicDetail.accounting_month,
                start_year=accounting_start_year,
                start_month=accounting_start_month,
                end_year=accounting_end_year,
                end_month=accounting_end_month,
            )
        )

        stmt = (
            select(BicDetail)
            .where(*filters)
            .order_by(
                BicDetail.accounting_year.desc(),
                BicDetail.accounting_month.desc(),
                BicDetail.platform_code,
                BicDetail.shop_id,
                BicDetail.shop_name,
                BicDetail.qic_warehouse,
            )
        )
        count_stmt = select(func.count()).select_from(BicDetail).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0
        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def list_reports(
        db: AsyncSession,
        *,
        user: User,
        org_id: int | None = None,
        task_id: int | None = None,
        platform_code: str | None = None,
        shop_name: str | None = None,
        shop_id: int | None = None,
        accounting_year: int | None = None,
        accounting_month: int | None = None,
        accounting_start_year: int | None = None,
        accounting_start_month: int | None = None,
        accounting_end_year: int | None = None,
        accounting_end_month: int | None = None,
        ids: list[int] | None = None,
        page: int | None = 1,
        page_size: int | None = 50,
    ) -> tuple[list[BicReportRow], int]:
        filters = [BicReportRow.is_deleted.is_(False)]
        scoped_org_id = BicAccountingService.resolve_org_id(user=user, requested_org_id=org_id)
        if scoped_org_id is not None:
            filters.append(BicReportRow.org_id == scoped_org_id)
        if ids is not None:
            if not ids:
                return [], 0
            filters.append(BicReportRow.id.in_(ids))
        if task_id is not None:
            filters.append(BicReportRow.task_id == task_id)
        else:
            filters.append(BicReportRow.task_id.in_(BicAccountingService._latest_result_task_ids_select()))
        platform_codes = TransactionAccountingService._split_filter_values(platform_code)
        if platform_codes:
            filters.append(BicReportRow.platform_code.in_(platform_codes))
        shop_names = TransactionAccountingService._split_filter_values(shop_name)
        if shop_names:
            filters.append(BicReportRow.shop_name.in_(shop_names))
        if shop_id is not None:
            filters.append(BicReportRow.shop_id == shop_id)
        if accounting_year is not None:
            filters.append(BicReportRow.accounting_year == accounting_year)
        if accounting_month is not None:
            filters.append(BicReportRow.accounting_month == accounting_month)
        filters.extend(
            TransactionAccountingService._period_filters(
                BicReportRow.accounting_year * 100 + BicReportRow.accounting_month,
                start_year=accounting_start_year,
                start_month=accounting_start_month,
                end_year=accounting_end_year,
                end_month=accounting_end_month,
            )
        )

        stmt = (
            select(BicReportRow)
            .where(*filters)
            .order_by(
                BicReportRow.accounting_year.desc(),
                BicReportRow.accounting_month.desc(),
                BicReportRow.platform_code,
                BicReportRow.shop_id,
                BicReportRow.shop_name,
            )
        )
        count_stmt = select(func.count()).select_from(BicReportRow).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0
        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def execute_task(db: AsyncSession, *, task_id: int) -> BicTask:
        task = await db.get(BicTask, task_id)
        if task is None or task.is_deleted:
            raise ValueError("BIC任务不存在")
        upload_file = await db.get(BicUploadFile, task.file_id)
        if upload_file is None or upload_file.is_deleted:
            raise ValueError("BIC上传文件不存在")

        task.status = "processing"
        task.progress = 5
        task.started_at = datetime.now(timezone.utc)
        task.finished_at = None
        task.error_message = None
        await db.flush()

        try:
            suffix = Path(upload_file.original_name).suffix or ".xlsx"
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
                oss_service.download_to_temp(upload_file.oss_key, tmp.name)
                summary = await BicAccountingService.persist_task_result(
                    db,
                    task=task,
                    upload_file=upload_file,
                    file_path=tmp.name,
                    platform_code=upload_file.platform_code or "douyin",
                    shop_id=upload_file.shop_id,
                    shop_name=upload_file.shop_name or "",
                )

            task.processed_rows = int(summary.get("total_rows", 0))
            task.success_rows = int(summary.get("success_rows", 0))
            task.failed_rows = int(summary.get("failed_rows", 0))
            task.result_summary = summary
            task.progress = 100
            task.status = "success" if task.failed_rows == 0 else "partial_success"
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "processed"
        except Exception as exc:
            await db.rollback()
            task = await db.get(BicTask, task_id)
            if task is None or task.is_deleted:
                raise ValueError("BIC任务不存在") from exc
            upload_file = await db.get(BicUploadFile, task.file_id)
            if upload_file is None or upload_file.is_deleted:
                raise ValueError("BIC上传文件不存在") from exc
            task.status = "failed"
            task.progress = 100
            task.error_message = str(exc)
            task.finished_at = datetime.now(timezone.utc)
            upload_file.status = "failed"
            upload_file.error_message = str(exc)

        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def persist_task_result(
        db: AsyncSession,
        *,
        task: BicTask,
        upload_file: BicUploadFile,
        file_path: str,
        platform_code: str,
        shop_id: int | None,
        shop_name: str,
    ) -> dict:
        if upload_file.accounting_year is None or upload_file.accounting_month is None:
            raise ValueError("BIC文件缺少文件名年月")
        shop_name = shop_name or upload_file.shop_name or ""
        if not shop_name:
            raise ValueError("BIC文件缺少店铺名称")
        if shop_id is None:
            shop = await ShopService.get_or_create_shop(
                db,
                org_id=task.org_id,
                platform_name=platform_code,
                shop_name=shop_name,
            )
            shop_id = shop.id
            upload_file.shop_id = shop_id
            upload_file.shop_name = shop.shop_name

        await db.execute(delete(BicDetail).where(BicDetail.task_id == task.id))
        await db.execute(delete(BicReportRow).where(BicReportRow.task_id == task.id))

        parse_result = BicAccountingService.parse_file(file_path)
        detail_rows = BicAccountingService._build_detail_rows(
            task=task,
            upload_file=upload_file,
            rows=parse_result.get("bic_rows", []),
            platform_code=platform_code,
            shop_id=shop_id,
            shop_name=shop_name,
        )
        db.add_all(detail_rows)

        report_total = sum((safe_decimal(row.total_amount) for row in detail_rows), Decimal("0"))
        report_row = BicReportRow(
            task_id=task.id,
            file_id=upload_file.id,
            org_id=task.org_id,
            shop_id=shop_id,
            platform_code=platform_code,
            shop_name=shop_name,
            accounting_year=int(upload_file.accounting_year),
            accounting_month=int(upload_file.accounting_month),
            row_count=sum(row.row_count for row in detail_rows),
            total_amount=report_total,
        )
        db.add(report_row)
        await db.flush()

        return {
            "type": "bic",
            "total_rows": parse_result.get("total_rows", 0),
            "success_rows": parse_result.get("success_rows", 0),
            "failed_rows": parse_result.get("failed_rows", 0),
            "groups": len(detail_rows),
            "detail_ids": [row.id for row in detail_rows],
            "report_id": report_row.id,
            "errors": parse_result.get("errors", [])[:10],
        }

    @staticmethod
    def parse_file(file_path: str) -> dict:
        result = {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "bic_rows": [],
        }
        required_headers = tuple(DOUYIN_BIC_HEADERS)
        with open_tabular_rows(file_path) as rows:
            if rows is None:
                result["errors"].append("无法打开表格文件")
                return result

            row_iter = iter(rows)
            header_result = FinancialSummaryExcelProcessorMixin._find_header_row(row_iter, required_headers)
            if header_result is None:
                result["errors"].append("无法读取BIC表头")
                return result

            headers, header_row_number = header_result
            col_idx = FinancialSummaryExcelProcessorMixin._build_col_idx(headers, required_headers)
            missing = FinancialSummaryExcelProcessorMixin._missing_headers(col_idx, required_headers)
            if missing:
                result["errors"].append(f"缺少BIC必要表头: {', '.join(missing)}")
                return result

            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = FinancialSummaryExcelProcessorMixin._row_to_values(row, col_idx)
                    if safe_str(vals.get("费用项")) != BIC_TARGET_FEE_ITEM:
                        continue
                    result["bic_rows"].append(
                        {
                            "qic_warehouse": safe_str(vals.get("QIC仓")) or "-",
                            "amount": safe_decimal(vals.get("结算金额")),
                            "fee_item": BIC_TARGET_FEE_ITEM,
                            "raw_row": TransactionAccountingService._json_safe_raw_row(vals),
                        }
                    )
                    result["success_rows"] += 1
                except Exception as exc:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + header_row_number}: {exc}")
        return result

    @staticmethod
    def _build_detail_rows(
        *,
        task: BicTask,
        upload_file: BicUploadFile,
        rows: Iterable[dict],
        platform_code: str,
        shop_id: int | None,
        shop_name: str,
    ) -> list[BicDetail]:
        groups: dict[str, dict[str, object]] = {}
        for row in rows:
            qic_warehouse = safe_str(row.get("qic_warehouse")) or "-"
            group = groups.setdefault(qic_warehouse, {"amount": Decimal("0"), "row_count": 0, "raw_rows": []})
            group["amount"] = safe_decimal(group["amount"]) + safe_decimal(row.get("amount"))
            group["row_count"] = int(group["row_count"]) + 1
            raw_rows = group["raw_rows"]
            if isinstance(raw_rows, list):
                raw_rows.append(row.get("raw_row") or {})

        return [
            BicDetail(
                task_id=task.id,
                file_id=upload_file.id,
                org_id=task.org_id,
                shop_id=shop_id,
                platform_code=platform_code,
                shop_name=shop_name,
                accounting_year=int(upload_file.accounting_year),
                accounting_month=int(upload_file.accounting_month),
                qic_warehouse=qic_warehouse,
                row_count=int(group["row_count"]),
                total_amount=safe_decimal(group["amount"]),
                raw_rows=group["raw_rows"],
            )
            for qic_warehouse, group in groups.items()
        ]

    @staticmethod
    async def export_details(db: AsyncSession, **kwargs) -> io.BytesIO:
        rows, _ = await BicAccountingService.list_details(db, page=None, page_size=None, **kwargs)
        return BicAccountingService._build_detail_workbook(rows)

    @staticmethod
    async def export_reports(db: AsyncSession, **kwargs) -> io.BytesIO:
        rows, _ = await BicAccountingService.list_reports(db, page=None, page_size=None, **kwargs)
        return BicAccountingService._build_report_workbook(rows)

    @staticmethod
    def _build_detail_workbook(rows: list[BicDetail]) -> io.BytesIO:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "BIC明细"
        worksheet.append(BIC_DETAIL_EXPORT_HEADERS)
        for index, row in enumerate(rows, start=1):
            worksheet.append(
                [
                    index,
                    TransactionAccountingService._format_platform(row.platform_code),
                    row.shop_name,
                    TransactionAccountingService._format_month(row.accounting_year, row.accounting_month),
                    row.qic_warehouse,
                    float(row.total_amount or 0),
                ]
            )
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _build_report_workbook(rows: list[BicReportRow]) -> io.BytesIO:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "BIC报表"
        worksheet.append(BIC_REPORT_EXPORT_HEADERS)
        for index, row in enumerate(rows, start=1):
            worksheet.append(
                [
                    index,
                    TransactionAccountingService._format_platform(row.platform_code),
                    row.shop_name,
                    TransactionAccountingService._format_month(row.accounting_year, row.accounting_month),
                    float(row.total_amount or 0),
                ]
            )
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer
