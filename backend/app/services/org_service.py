import re

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.organization import ORG_TYPE_INTERNAL, Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.audit_service import AuditService


ORG_NAME_DUPLICATE_MESSAGE = "组织名称已存在，请更换后再试"
ORG_CODE_DUPLICATE_MESSAGE = "组织编码已存在，请更换后再试"
ORG_DUPLICATE_MESSAGE = "组织名称或编码已存在，请更换后再试"
DEFAULT_ORG_MAX_USERS = 5
DEFAULT_ORG_MAX_STORAGE_BYTES = 1 * 1024 * 1024 * 1024


def _org_integrity_error_message(exc: IntegrityError) -> str:
    message = str(exc)
    constraint_match = re.search(r'constraint "([^"]+)"', message)
    constraint_name = constraint_match.group(1) if constraint_match else ""
    if constraint_name == "uq_fin_org_name":
        return ORG_NAME_DUPLICATE_MESSAGE
    if constraint_name == "uq_fin_org_code":
        return ORG_CODE_DUPLICATE_MESSAGE
    return ORG_DUPLICATE_MESSAGE


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
    async def _raise_for_duplicate(
        db: AsyncSession,
        *,
        name: str | None = None,
        code: str | None = None,
        exclude_org_id: int | None = None,
    ) -> None:
        if name is not None:
            stmt = select(Organization).where(
                Organization.name == name,
                Organization.is_deleted.is_(False),
            )
            if exclude_org_id is not None:
                stmt = stmt.where(Organization.id != exclude_org_id)
            existing_name = await db.execute(stmt)
            if existing_name.scalar_one_or_none() is not None:
                raise ValueError(ORG_NAME_DUPLICATE_MESSAGE)

        if code is not None:
            stmt = select(Organization).where(
                Organization.code == code,
                Organization.is_deleted.is_(False),
            )
            if exclude_org_id is not None:
                stmt = stmt.where(Organization.id != exclude_org_id)
            existing_code = await db.execute(stmt)
            if existing_code.scalar_one_or_none() is not None:
                raise ValueError(ORG_CODE_DUPLICATE_MESSAGE)

    @staticmethod
    async def create_org(
        db: AsyncSession,
        *,
        data: OrganizationCreate,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Organization:
        await OrgService._raise_for_duplicate(db, name=data.name, code=data.code)

        stmt = (
            insert(Organization)
            .values(
                name=data.name,
                code=data.code,
                org_type=data.org_type,
                remark=data.remark,
                status=1,
                max_users=DEFAULT_ORG_MAX_USERS,
                max_storage_bytes=DEFAULT_ORG_MAX_STORAGE_BYTES,
                used_storage_bytes=0,
                plan_type="free",
                plan_expires_at=None,
                is_deleted=False,
                deleted_at=None,
            )
            .on_conflict_do_nothing()
            .returning(Organization)
        )
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        if org is None:
            await OrgService._raise_for_duplicate(db, name=data.name, code=data.code)
            raise ValueError(ORG_DUPLICATE_MESSAGE)

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
        old_value["org_type"] = org.org_type

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != org.name:
            await OrgService._raise_for_duplicate(db, name=update_data["name"], exclude_org_id=org.id)
        if "code" in update_data and update_data["code"] != org.code:
            await OrgService._raise_for_duplicate(db, code=update_data["code"], exclude_org_id=org.id)

        for field, value in update_data.items():
            setattr(org, field, value)

        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(_org_integrity_error_message(exc)) from exc
        await db.refresh(org)

        new_value = {"name": org.name, "code": org.code, "org_type": org.org_type, "remark": org.remark, "status": org.status}

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
