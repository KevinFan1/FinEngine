from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above
from app.models.organization import Organization
from app.models.operation_log import OperationLog
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.common import ApiResponse, PageResponse
from app.utils.query_filters import split_int_filter_values

router = APIRouter()


def split_filter_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=ApiResponse[PageResponse[AuditLogOut]])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    module: str | None = Query(None),
    action: str | None = Query(None),
    user_id: int | None = Query(None),
    username: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    _admin=Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Query operation logs.

    Superadmin can see all logs. Organization admins only see logs in their
    own organization.
    """
    stmt = (
        select(OperationLog, Organization.name.label("org_name"))
        .outerjoin(Organization, Organization.id == OperationLog.org_id)
        .order_by(OperationLog.id.desc())
    )
    count_stmt = select(func.count()).select_from(OperationLog)

    if current_user.role != "superadmin":
        stmt = stmt.where(OperationLog.org_id == current_user.org_id)
        count_stmt = count_stmt.where(OperationLog.org_id == current_user.org_id)
    else:
        org_ids = split_int_filter_values(org_id)
        if org_ids:
            stmt = stmt.where(OperationLog.org_id.in_(org_ids))
            count_stmt = count_stmt.where(OperationLog.org_id.in_(org_ids))

    module_values = split_filter_values(module)
    if module_values:
        stmt = stmt.where(OperationLog.module.in_(module_values))
        count_stmt = count_stmt.where(OperationLog.module.in_(module_values))

    action_values = split_filter_values(action)
    if action_values:
        stmt = stmt.where(OperationLog.action.in_(action_values))
        count_stmt = count_stmt.where(OperationLog.action.in_(action_values))

    if user_id is not None:
        stmt = stmt.where(OperationLog.user_id == user_id)
        count_stmt = count_stmt.where(OperationLog.user_id == user_id)

    if username:
        like = f"%{username}%"
        stmt = stmt.where(OperationLog.username.ilike(like) | OperationLog.display_name.ilike(like))
        count_stmt = count_stmt.where(OperationLog.username.ilike(like) | OperationLog.display_name.ilike(like))

    if start_time:
        stmt = stmt.where(OperationLog.created_at >= start_time)
        count_stmt = count_stmt.where(OperationLog.created_at >= start_time)

    if end_time:
        stmt = stmt.where(OperationLog.created_at <= end_time)
        count_stmt = count_stmt.where(OperationLog.created_at <= end_time)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.all()

    return ApiResponse(
        data=PageResponse(
            items=[
                AuditLogOut.model_validate(log).model_copy(update={"org_name": org_name})
                for log, org_name in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    )
