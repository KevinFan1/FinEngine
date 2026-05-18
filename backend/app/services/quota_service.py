"""组织配额管理服务。"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.upload import UploadFile
from app.models.user import User


class QuotaService:
    """组织配额管理服务。"""

    @staticmethod
    def _current_month_range() -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        return month_start, next_month

    @staticmethod
    async def get_monthly_upload_usage(db: AsyncSession, org_id: int) -> int:
        """Return bytes uploaded by the organization in the current month."""
        month_start, next_month = QuotaService._current_month_range()
        result = await db.execute(
            select(func.sum(UploadFile.file_size)).where(
                UploadFile.org_id == org_id,
                UploadFile.is_deleted.is_(False),
                UploadFile.created_at >= month_start,
                UploadFile.created_at < next_month,
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def check_user_quota(db: AsyncSession, org_id: int) -> tuple[bool, str]:
        """检查组织是否可以创建新用户。

        Returns:
            (can_create, message): 是否可以创建和提示信息
        """
        # 获取组织信息
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted.is_(False)
            )
        )
        org = org_result.scalar_one_or_none()
        if not org:
            return False, "组织不存在"

        # 统计当前用户数
        user_count_result = await db.execute(
            select(func.count(User.id)).where(
                User.org_id == org_id,
                User.is_deleted.is_(False)
            )
        )
        current_users = user_count_result.scalar() or 0

        # 检查是否超过配额
        if current_users >= org.max_users:
            return False, f"已达到用户数量上限（{org.max_users} 个），请升级套餐"

        return True, f"当前用户数: {current_users}/{org.max_users}"

    @staticmethod
    async def check_storage_quota(
        db: AsyncSession,
        org_id: int,
        additional_bytes: int
    ) -> tuple[bool, str]:
        """检查组织存储配额是否足够。

        Args:
            db: 数据库会话
            org_id: 组织 ID
            additional_bytes: 需要增加的字节数

        Returns:
            (can_upload, message): 是否可以上传和提示信息
        """
        # 获取组织信息
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted.is_(False)
            )
        )
        org = org_result.scalar_one_or_none()
        if not org:
            return False, "组织不存在"

        monthly_used_bytes = await QuotaService.get_monthly_upload_usage(db, org_id)

        # 检查本月上传额度是否足够
        if monthly_used_bytes + additional_bytes > org.max_storage_bytes:
            used_gb = monthly_used_bytes / (1024 ** 3)
            max_gb = org.max_storage_bytes / (1024 ** 3)
            return False, f"本月上传额度不足（本月已用 {used_gb:.2f}GB / {max_gb:.2f}GB），请升级套餐"

        return True, "本月上传额度充足"

    @staticmethod
    async def update_storage_usage(
        db: AsyncSession,
        org_id: int,
        delta_bytes: int
    ) -> None:
        """更新组织存储使用量。

        Args:
            db: 数据库会话
            org_id: 组织 ID
            delta_bytes: 变化的字节数（正数为增加，负数为减少）
        """
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted.is_(False)
            )
        )
        org = org_result.scalar_one_or_none()
        if not org:
            return

        org.used_storage_bytes = max(0, org.used_storage_bytes + delta_bytes)
        await db.flush()

    @staticmethod
    async def recalculate_storage_usage(db: AsyncSession, org_id: int) -> int:
        """重新计算组织的实际存储使用量。

        Args:
            db: 数据库会话
            org_id: 组织 ID

        Returns:
            实际使用的字节数
        """
        # 统计所有未删除文件的大小总和
        result = await db.execute(
            select(func.sum(UploadFile.file_size)).where(
                UploadFile.org_id == org_id,
                UploadFile.is_deleted.is_(False)
            )
        )
        total_bytes = result.scalar() or 0

        # 更新组织记录
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted.is_(False)
            )
        )
        org = org_result.scalar_one_or_none()
        if org:
            org.used_storage_bytes = total_bytes
            await db.flush()

        return total_bytes

    @staticmethod
    async def get_quota_info(db: AsyncSession, org_id: int) -> dict:
        """获取组织配额信息。

        Returns:
            包含配额详情的字典
        """
        # 获取组织信息
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted.is_(False)
            )
        )
        org = org_result.scalar_one_or_none()
        if not org:
            return {}

        # 统计用户数
        user_count_result = await db.execute(
            select(func.count(User.id)).where(
                User.org_id == org_id,
                User.is_deleted.is_(False)
            )
        )
        current_users = user_count_result.scalar() or 0

        monthly_upload_bytes = await QuotaService.get_monthly_upload_usage(db, org_id)

        # 计算使用率
        storage_usage_percent = (org.used_storage_bytes / org.max_storage_bytes * 100) if org.max_storage_bytes > 0 else 0
        monthly_upload_percent = (monthly_upload_bytes / org.max_storage_bytes * 100) if org.max_storage_bytes > 0 else 0
        user_usage_percent = (current_users / org.max_users * 100) if org.max_users > 0 else 0

        # 检查套餐是否过期
        is_expired = False
        if org.plan_expires_at:
            is_expired = org.plan_expires_at < datetime.now(timezone.utc)

        return {
            "plan_type": org.plan_type,
            "plan_expires_at": org.plan_expires_at,
            "is_expired": is_expired,
            "users": {
                "current": current_users,
                "max": org.max_users,
                "usage_percent": round(user_usage_percent, 2),
                "is_exceeded": current_users > org.max_users,
            },
            "storage": {
                "current_bytes": org.used_storage_bytes,
                "max_bytes": org.max_storage_bytes,
                "current_gb": round(org.used_storage_bytes / (1024 ** 3), 2),
                "max_gb": round(org.max_storage_bytes / (1024 ** 3), 2),
                "usage_percent": round(storage_usage_percent, 2),
                "is_exceeded": org.used_storage_bytes > org.max_storage_bytes,
            },
            "monthly_upload": {
                "current_bytes": monthly_upload_bytes,
                "max_bytes": org.max_storage_bytes,
                "current_gb": round(monthly_upload_bytes / (1024 ** 3), 2),
                "max_gb": round(org.max_storage_bytes / (1024 ** 3), 2),
                "usage_percent": round(monthly_upload_percent, 2),
                "is_exceeded": monthly_upload_bytes > org.max_storage_bytes,
            },
        }
