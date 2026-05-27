"""Upload service — batch management and uploaded-file callback."""

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.models.organization import Organization
from app.models.task import ProcessingTask
from app.models.upload import UploadBatch, UploadFile
from app.models.user import User
from app.schemas.upload import UploadBatchCreate, UploadFileCallback
from app.services.audit_service import AuditService
from app.services.bic_accounting_service import BicAccountingService
from app.services.platform_profile_service import resolve_platform_profile
from app.services.quota_service import QuotaService
from app.services.shop_service import ShopService
from app.services.shop_visibility import active_shop_filter
from app.services.transaction_accounting_service import TransactionAccountingService


def _format_file_size(bytes_size: int) -> str:
    if bytes_size <= 0:
        return "0 B"

    units = ("B", "KB", "MB", "GB", "TB")
    index = min(int(math.log(bytes_size, 1024)), len(units) - 1)
    value = bytes_size / (1024 ** index)
    decimals = 0 if index == 0 else 2
    return f"{value:.{decimals}f} {units[index]}"


class UploadService:
    @staticmethod
    def validate_batch_scope(*, batch: UploadBatch, user: User) -> None:
        if user.role == "superadmin":
            return
        if batch.org_id != user.org_id:
            raise ValueError("批次不存在")

    @staticmethod
    async def create_batch(
        db: AsyncSession,
        *,
        data: UploadBatchCreate,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> UploadBatch:
        org_id = data.org_id if user.role == "superadmin" else user.org_id
        if org_id is None:
            raise ValueError("请选择上传数据所属组织")

        org_result = await db.execute(select(Organization).where(Organization.id == org_id, Organization.status == 1, Organization.is_deleted.is_(False)))
        if org_result.scalar_one_or_none() is None:
            raise ValueError("组织不存在或已禁用")

        if data.total_bytes > 0:
            can_upload, quota_msg = await QuotaService.check_storage_quota(
                db,
                org_id=org_id,
                additional_bytes=data.total_bytes,
            )
            if not can_upload:
                raise ValueError(quota_msg)

        batch = UploadBatch(
            org_id=org_id,
            user_id=user.id,
            file_count=data.file_count,
            status="pending",
            remark=data.remark,
        )
        db.add(batch)
        await db.flush()
        await db.refresh(batch)

        await AuditService.log(
            db,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            org_id=org_id,
            module="upload",
            action="upload_start",
            description=f"用户 [{user.display_name}] 发起批量上传，共 {data.file_count} 个文件",
            target_type="batch",
            target_id=batch.id,
            ip=ip,
            user_agent=user_agent,
            extra_data={"file_count": data.file_count, "total_bytes": data.total_bytes},
        )

        return batch

    @staticmethod
    async def get_batch_for_user(db: AsyncSession, *, batch_id: int, user: User) -> UploadBatch | None:
        result = await db.execute(select(UploadBatch).where(UploadBatch.id == batch_id, UploadBatch.is_deleted.is_(False)))
        batch = result.scalar_one_or_none()
        if batch is None:
            return None
        try:
            UploadService.validate_batch_scope(batch=batch, user=user)
        except ValueError:
            return None
        return batch

    @staticmethod
    async def handle_file_callback(
        db: AsyncSession,
        *,
        batch_id: int,
        data: UploadFileCallback,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> UploadFile:
        """Record an uploaded file, auto-create a processing task, and dispatch Celery job."""
        batch = await UploadService.get_batch_for_user(db, batch_id=batch_id, user=user)
        if batch is None:
            raise ValueError("上传批次不存在或无权访问")

        # Check storage quota
        can_upload, quota_msg = await QuotaService.check_storage_quota(
            db,
            org_id=batch.org_id,
            additional_bytes=data.file_size
        )
        if not can_upload:
            raise ValueError(quota_msg)

        shop = None
        platform_profile = None
        if data.detected_platform and data.parsed_shop:
            platform_profile = await resolve_platform_profile(db, data.detected_platform)
            shop = await ShopService.get_or_create_shop(
                db,
                org_id=batch.org_id,
                platform_name=platform_profile.report_platform_code,
                shop_name=data.parsed_shop,
            )
        elif data.detected_platform:
            platform_profile = await resolve_platform_profile(db, data.detected_platform)

        upload_file = UploadFile(
            batch_id=batch_id,
            org_id=batch.org_id,
            user_id=user.id,
            shop_id=shop.id if shop else None,
            original_name=data.original_name,
            oss_key=data.oss_key,
            file_size=data.file_size,
            file_hash=data.file_hash,
            parsed_year=data.parsed_year,
            parsed_month=data.parsed_month,
            parsed_type=data.parsed_type,
            parsed_shop=data.parsed_shop,
            detected_platform=data.detected_platform,
            source_platform_code=platform_profile.source_platform_code if platform_profile else data.detected_platform,
            report_platform_code=platform_profile.report_platform_code if platform_profile else data.detected_platform,
            processor_code=platform_profile.processor_code if platform_profile else data.detected_platform,
            order_scope_code=platform_profile.order_scope_code if platform_profile else data.detected_platform,
            status="uploaded",
        )
        db.add(upload_file)
        await db.flush()

        # Auto-create processing task for each file
        task = ProcessingTask(
            file_id=upload_file.id,
            org_id=batch.org_id,
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
            org_id=batch.org_id,
            module="upload",
            action="upload_file",
            description=f"用户 [{user.display_name}] 上传文件 [{data.original_name}]，大小 {_format_file_size(data.file_size)}",
            target_type="upload_file",
            target_id=upload_file.id,
            target_name=data.original_name,
            ip=ip,
            user_agent=user_agent,
            extra_data={"file_size": data.file_size, "task_id": task.id},
        )

        # Update storage usage
        await QuotaService.update_storage_usage(db, batch.org_id, data.file_size)

        # Dispatch Celery task — use hardcoded platform processor
        from app.tasks.processors import PLATFORM_PROCESSORS

        processor_code = platform_profile.processor_code if platform_profile else data.detected_platform
        if data.detected_platform and processor_code in PLATFORM_PROCESSORS:
            UploadService.dispatch_processing_task_after_commit(
                db,
                task=task,
                upload_file=upload_file,
                platform_code=data.detected_platform,
                shop_id=shop.id if shop else None,
                shop_name=data.parsed_shop or "",
            )
        else:
            # No processor found — mark task as failed
            task.status = "failed"
            task.error_message = f"未找到平台 [{data.detected_platform}] 的处理器" if data.detected_platform else "未检测到平台类型，请检查文件名格式"
            upload_file.status = "failed"
            upload_file.error_message = task.error_message

        await UploadService.dispatch_independent_tasks(
            db,
            upload_file=upload_file,
            user=user,
            ip=ip,
            user_agent=user_agent,
        )

        await db.flush()
        await db.refresh(upload_file)
        return upload_file

    @staticmethod
    def dispatch_processing_task_after_commit(
        db: AsyncSession,
        *,
        task: ProcessingTask,
        upload_file: UploadFile,
        platform_code: str,
        shop_id: int | None,
        shop_name: str,
    ) -> None:
        async def dispatch() -> None:
            try:
                from app.tasks.celery_app import process_file_platform

                async_result = process_file_platform.delay(
                    file_id=upload_file.id,
                    oss_key=upload_file.oss_key,
                    org_id=task.org_id,
                    platform_code=platform_code,
                    shop_id=shop_id,
                    shop_name=shop_name,
                )
                task.celery_task_id = async_result.id
            except Exception as exc:
                task.status = "failed"
                task.error_message = f"文件处理任务投递失败: {exc}"
                upload_file.status = "failed"
                upload_file.error_message = task.error_message
            await db.flush()

        register_after_commit(db, dispatch)

    @staticmethod
    async def dispatch_independent_tasks(
        db: AsyncSession,
        *,
        upload_file: UploadFile,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        parsed_type = (upload_file.parsed_type or "").lower()
        source_platform = (
            upload_file.source_platform_code
            or upload_file.detected_platform
            or ""
        ).lower()

        if source_platform == "douyin" and parsed_type == "动账":
            await TransactionAccountingService.create_from_shared_upload(
                db,
                upload_file=upload_file,
                user=user,
                ip=ip,
                user_agent=user_agent,
            )

        if source_platform == "douyin" and parsed_type == "bic":
            await BicAccountingService.create_from_shared_upload(
                db,
                upload_file=upload_file,
                user=user,
                ip=ip,
                user_agent=user_agent,
            )

    @staticmethod
    async def list_batches(
        db: AsyncSession,
        *,
        org_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UploadBatch], int]:
        stmt = select(UploadBatch).where(UploadBatch.is_deleted.is_(False)).order_by(UploadBatch.id.desc())
        count_stmt = select(func.count()).select_from(UploadBatch).where(UploadBatch.is_deleted.is_(False))

        if org_id is not None:
            stmt = stmt.where(UploadBatch.org_id == org_id)
            count_stmt = count_stmt.where(UploadBatch.org_id == org_id)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        batches = list(result.scalars().all())

        return batches, total

    @staticmethod
    async def get_batch_detail(db: AsyncSession, batch_id: int, user: User | None = None) -> UploadBatch | None:
        result = await db.execute(select(UploadBatch).where(UploadBatch.id == batch_id, UploadBatch.is_deleted.is_(False)))
        batch = result.scalar_one_or_none()
        if batch is None:
            return None
        if user is not None:
            try:
                UploadService.validate_batch_scope(batch=batch, user=user)
            except ValueError:
                return None
        return batch

    @staticmethod
    async def get_batch_files(db: AsyncSession, batch_id: int, user: User | None = None) -> list[UploadFile]:
        stmt = (
            select(UploadFile)
            .where(
                UploadFile.batch_id == batch_id,
                UploadFile.is_deleted.is_(False),
                active_shop_filter(UploadFile.shop_id),
            )
            .order_by(UploadFile.id)
        )
        if user is not None and user.role != "superadmin":
            stmt = stmt.where(UploadFile.org_id == user.org_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
