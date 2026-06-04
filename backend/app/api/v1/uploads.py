"""上传批次与文件回调接口。"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.upload import UploadBatchCreate, UploadBatchDetail, UploadBatchOut, UploadFileCallback, UploadFileOut
from app.services.upload_service import UploadService

router = APIRouter()


@router.post("/batch", response_model=ApiResponse[UploadBatchOut])
async def create_upload_batch(
    body: UploadBatchCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """创建新的上传批次。"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        batch = await UploadService.create_batch(
            db,
            data=body,
            user=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    return ApiResponse(data=UploadBatchOut.model_validate(batch))


@router.post("/callback", response_model=ApiResponse[UploadFileOut])
async def upload_file_callback(
    body: UploadFileCallback,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """登记上传完成的文件并自动创建处理任务。"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        upload_file = await UploadService.handle_file_callback(
            db,
            batch_id=body.batch_id,
            data=body,
            user=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    return ApiResponse(data=UploadFileOut.model_validate(upload_file))


@router.get("/batches", response_model=ApiResponse[PageResponse[UploadBatchOut]])
async def list_upload_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """分页查询当前用户可见的上传批次。"""
    org_id = current_user.org_id if current_user.role != "superadmin" else None
    batches, total = await UploadService.list_batches(db, org_id=org_id, page=page, page_size=page_size)
    return ApiResponse(
        data=PageResponse(
            items=[UploadBatchOut.model_validate(b) for b in batches],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/batches/{batch_id}", response_model=ApiResponse[UploadBatchDetail])
async def get_upload_batch_detail(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取上传批次详情及文件列表。"""
    batch = await UploadService.get_batch_detail(db, batch_id, user=current_user)
    if batch is None:
        return ApiResponse(code=404, message="批次不存在")

    files = await UploadService.get_batch_files(db, batch_id, user=current_user)

    batch_data = UploadBatchDetail.model_validate(batch)
    batch_data.files = [UploadFileOut.model_validate(f) for f in files]
    return ApiResponse(data=batch_data)
