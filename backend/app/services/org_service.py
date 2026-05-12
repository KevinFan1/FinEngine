from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.audit_service import AuditService


class OrgService:
    @staticmethod
    async def list_orgs(
        db: AsyncSession,
        current_user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[Organization], int]:
        """List organizations with pagination and optional keyword search."""

        if current_user.role == "superadmin":
            stmt = select(Organization).where(Organization.is_deleted.is_(False)).order_by(Organization.id.desc())
            count_stmt = select(func.count()).select_from(Organization).where(Organization.is_deleted.is_(False))
        else:
            stmt = select(Organization).where(Organization.id == current_user.org_id, Organization.is_deleted.is_(False)).order_by(Organization.id.desc())
            count_stmt = select(func.count()).select_from(Organization).where(Organization.id == current_user.org_id, Organization.is_deleted.is_(False))

        if keyword:
            like_pattern = f"%{keyword}%"
            stmt = stmt.where(Organization.name.ilike(like_pattern) | Organization.code.ilike(like_pattern))
            count_stmt = count_stmt.where(Organization.name.ilike(like_pattern) | Organization.code.ilike(like_pattern))

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        orgs = list(result.scalars().all())

        return orgs, total

    @staticmethod
    async def get_org(db: AsyncSession, org_id: int) -> Organization | None:
        result = await db.execute(select(Organization).where(Organization.id == org_id, Organization.is_deleted.is_(False)))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_org(
        db: AsyncSession,
        *,
        data: OrganizationCreate,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Organization:
        org = Organization(
            name=data.name,
            code=data.code,
            remark=data.remark,
            status=1,
        )
        db.add(org)
        await db.flush()
        await db.refresh(org)

        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=None,
            module="org",
            action="create",
            description=f"超管创建组织 [{org.name}]",
            target_type="organization",
            target_id=org.id,
            target_name=org.name,
            ip=ip,
            user_agent=user_agent,
        )

        return org

    @staticmethod
    async def update_org(
        db: AsyncSession,
        *,
        org_id: int,
        data: OrganizationUpdate,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Organization | None:
        org = await OrgService.get_org(db, org_id)
        if org is None:
            return None

        old_value = {"name": org.name, "code": org.code, "remark": org.remark, "status": org.status}

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)

        await db.flush()
        await db.refresh(org)

        new_value = {"name": org.name, "code": org.code, "remark": org.remark, "status": org.status}

        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=None,
            module="org",
            action="update",
            description=f"超管修改组织 [{org.name}] 信息",
            target_type="organization",
            target_id=org.id,
            target_name=org.name,
            ip=ip,
            user_agent=user_agent,
            old_value=old_value,
            new_value=new_value,
        )

        return org

    @staticmethod
    async def update_org_status(
        db: AsyncSession,
        *,
        org_id: int,
        status_val: int,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Organization | None:
        org = await OrgService.get_org(db, org_id)
        if org is None:
            return None

        old_status = org.status
        org.status = status_val
        await db.flush()
        await db.refresh(org)

        action_desc = "启用" if status_val == 1 else "禁用"
        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=None,
            module="org",
            action="disable" if status_val == 0 else "enable",
            description=f"超管{action_desc}组织 [{org.name}]",
            target_type="organization",
            target_id=org.id,
            target_name=org.name,
            ip=ip,
            user_agent=user_agent,
            old_value={"status": old_status},
            new_value={"status": status_val},
        )

        return org
