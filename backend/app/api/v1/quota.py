"""组织配额管理 API。"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_superadmin
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.quota_service import QuotaService

router = APIRouter()


class QuotaInfo(BaseModel):
    """配额信息响应。"""
    plan_type: str
    plan_expires_at: datetime | None
    is_expired: bool
    users: dict
    storage: dict


class UpdateQuotaRequest(BaseModel):
    """更新配额请求。"""
    max_users: int | None = Field(None, ge=1, le=10000, description="最大用户数")
    max_storage_gb: Decimal | None = Field(None, gt=0, le=10000, description="最大存储容量（GB）")
    plan_type: str | None = Field(None, description="套餐类型")
    plan_expires_at: datetime | None = Field(None, description="套餐到期时间")


class CheckUploadRequest(BaseModel):
    """检查上传配额请求。"""
    total_bytes: int = Field(..., ge=0, description="计划上传的总字节数")


class CheckUploadResponse(BaseModel):
    """检查上传配额响应。"""
    can_upload: bool
    message: str


@router.get("/quota", response_model=ApiResponse[QuotaInfo])
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取当前组织的配额信息。"""
    if not current_user.org_id:
        return ApiResponse(code=400, message="超级管理员无组织配额")

    quota_info = await QuotaService.get_quota_info(db, current_user.org_id)
    return ApiResponse(data=QuotaInfo(**quota_info))


@router.post("/quota/check-upload", response_model=ApiResponse[CheckUploadResponse])
async def check_upload_quota(
    body: CheckUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """检查本月上传额度是否足够。"""
    if not current_user.org_id:
        return ApiResponse(code=400, message="超级管理员无需检查配额")

    can_upload, message = await QuotaService.check_storage_quota(
        db,
        org_id=current_user.org_id,
        additional_bytes=body.total_bytes
    )

    return ApiResponse(data=CheckUploadResponse(can_upload=can_upload, message=message))


@router.get("/quota/{org_id}", response_model=ApiResponse[QuotaInfo])
async def get_org_quota(
    org_id: int,
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """获取指定组织的配额信息（仅超级管理员）。"""
    quota_info = await QuotaService.get_quota_info(db, org_id)
    return ApiResponse(data=QuotaInfo(**quota_info))


@router.post("/quota/{org_id}/update", response_model=ApiResponse)
async def update_quota(
    org_id: int,
    body: UpdateQuotaRequest,
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """更新组织配额（仅超级管理员）。"""
    # 获取组织
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.is_deleted.is_(False)
        )
    )
    org = org_result.scalar_one_or_none()
    if not org:
        return ApiResponse(code=404, message="组织不存在")

    # 更新配额
    if body.max_users is not None:
        org.max_users = body.max_users

    if body.max_storage_gb is not None:
        org.max_storage_bytes = int(body.max_storage_gb * 1024 * 1024 * 1024)

    if body.plan_type is not None:
        org.plan_type = body.plan_type

    if body.plan_expires_at is not None:
        org.plan_expires_at = body.plan_expires_at

    await db.flush()

    return ApiResponse(message="配额更新成功")


@router.post("/quota/{org_id}/recalculate", response_model=ApiResponse)
async def recalculate_storage(
    org_id: int,
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """重新计算组织存储使用量（仅超级管理员）。"""
    total_bytes = await QuotaService.recalculate_storage_usage(db, org_id)
    total_gb = round(total_bytes / (1024 ** 3), 2)

    return ApiResponse(message=f"存储使用量已重新计算: {total_gb}GB")
