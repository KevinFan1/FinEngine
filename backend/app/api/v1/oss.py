"""OSS API — Alibaba Cloud STS temporary credentials for frontend direct upload."""

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.oss_service import assume_sts_role, oss_service
from app.services.upload_service import UploadService

router = APIRouter()


class StsCredentialOut(BaseModel):
    """Temporary STS credentials returned to the frontend.

    Note: access_key_secret and security_token are temporary and scoped
    to the org's upload path. They expire after ALIYUN_STS_EXPIRE_SECONDS.
    """

    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str

    # OSS connection info
    region: str
    bucket: str
    endpoint: str

    # Restrict uploads to this path prefix
    oss_key_prefix: str


@router.get("/sts", response_model=ApiResponse[StsCredentialOut])
async def get_oss_sts(
    batch_id: int = Query(..., description="上传批次 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get Alibaba Cloud OSS temporary credentials for direct frontend upload.

    The frontend uses these credentials with the `ali-oss` JS SDK to upload
    files directly to OSS without going through the backend.

    Upload path prefix: `{org_id}/{batch_id}/`.
    Credentials expire after `ALIYUN_STS_EXPIRE_SECONDS` (default 3600s).
    """
    if not settings.ALIYUN_STS_ROLE_ARN or not settings.ALIYUN_ACCESS_KEY_ID:
        return ApiResponse(code=501, message="阿里云 OSS STS 未配置")

    batch = await UploadService.get_batch_for_user(db, batch_id=batch_id, user=current_user)
    if batch is None:
        return ApiResponse(code=404, message="上传批次不存在或无权访问")

    prefix = f"user-upload/tmp/{batch.org_id}/{batch.id}/"

    session_name = f"finengine-{batch.org_id}-{batch.id}-{current_user.id}"

    try:
        creds = assume_sts_role(
            role_arn=settings.ALIYUN_STS_ROLE_ARN,
            session_name=session_name,
            duration_seconds=settings.ALIYUN_STS_EXPIRE_SECONDS,
        )
    except Exception as e:
        logger.warning("oss.sts_failed batch_id={} user_id={} error={}", batch_id, current_user.id, e)
        return ApiResponse(code=502, message="获取 OSS 上传凭证失败，请稍后重试")

    return ApiResponse(
        data=StsCredentialOut(
            access_key_id=creds["access_key_id"],
            access_key_secret=creds["access_key_secret"],
            security_token=creds["security_token"],
            expiration=creds["expiration"],
            region=settings.ALIYUN_OSS_REGION,
            bucket=settings.ALIYUN_OSS_BUCKET,
            endpoint=oss_service.normalized_endpoint(),
            oss_key_prefix=prefix,
        )
    )
