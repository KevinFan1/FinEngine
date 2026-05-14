from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above, require_superadmin
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.organization import OrganizationCreate, OrganizationOut, OrganizationUpdate
from app.services.org_service import OrgService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResponse[OrganizationOut]])
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """List organizations (superadmin only)."""
    orgs, total = await OrgService.list_orgs(db, current_user, page=page, page_size=page_size, keyword=keyword)
    return ApiResponse(
        data=PageResponse(
            items=[OrganizationOut.model_validate(o) for o in orgs],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[OrganizationOut])
async def create_organization(
    body: OrganizationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new organization (superadmin only)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        org = await OrgService.create_org(
            db,
            data=body,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    return ApiResponse(data=OrganizationOut.model_validate(org))


@router.get("/{org_id}", response_model=ApiResponse[OrganizationOut])
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """Get organization detail (superadmin only)."""
    org = await OrgService.get_org(db, org_id)
    if org is None:
        return ApiResponse(code=404, message="组织不存在")
    return ApiResponse(data=OrganizationOut.model_validate(org))


@router.put("/{org_id}", response_model=ApiResponse[OrganizationOut])
async def update_organization(
    org_id: int,
    body: OrganizationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """Update organization (superadmin only)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        org = await OrgService.update_org(
            db,
            org_id=org_id,
            data=body,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    if org is None:
        return ApiResponse(code=404, message="组织不存在")
    return ApiResponse(data=OrganizationOut.model_validate(org))


@router.put("/{org_id}/status", response_model=ApiResponse[OrganizationOut])
async def update_organization_status(
    org_id: int,
    status_val: int = Query(..., alias="status"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """Enable/disable organization (superadmin only)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent") if request else None

    org = await OrgService.update_org_status(
        db,
        org_id=org_id,
        status_val=status_val,
        operator=current_user,
        ip=ip,
        user_agent=ua,
    )
    if org is None:
        return ApiResponse(code=404, message="组织不存在")
    return ApiResponse(data=OrganizationOut.model_validate(org))
