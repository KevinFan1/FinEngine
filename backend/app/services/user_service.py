from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService


def split_int_filter_values(value: str | int | None) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    values: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values


class UserService:
    @staticmethod
    async def list_users(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        org_id: str | int | None = None,
        operator: User | None = None,
    ) -> tuple[list[User], int]:
        """List users with pagination. Superadmin sees all; org_admin sees own org."""
        stmt = select(User).where(User.is_deleted.is_(False)).order_by(User.id.desc())
        count_stmt = select(func.count()).select_from(User).where(User.is_deleted.is_(False))

        # Scope filter
        if operator and operator.role != "superadmin":
            # Non-superadmin only sees their own org
            stmt = stmt.where(User.org_id == operator.org_id)
            count_stmt = count_stmt.where(User.org_id == operator.org_id)
        else:
            org_ids = split_int_filter_values(org_id)
            if org_ids:
                stmt = stmt.where(User.org_id.in_(org_ids))
                count_stmt = count_stmt.where(User.org_id.in_(org_ids))

        if keyword:
            like_pattern = f"%{keyword}%"
            filter_cond = User.username.ilike(like_pattern) | User.display_name.ilike(like_pattern) | User.phone.ilike(like_pattern)
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    @staticmethod
    async def get_user(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        *,
        data: UserCreate,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Create a new user. Raises ValueError if phone already exists."""
        # Check phone uniqueness
        existing = await db.execute(select(User).where(User.phone == data.phone, User.is_deleted.is_(False)))
        if existing.scalar_one_or_none() is not None:
            raise ValueError("手机号已被注册")

        user = User(
            org_id=data.org_id,
            username=data.username,
            phone=data.phone,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            email=data.email,
            role=data.role,
            status=1,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # Get org name for description
        org_name = ""
        if data.org_id:
            org_result = await db.execute(select(Organization.name).where(Organization.id == data.org_id, Organization.is_deleted.is_(False)))
            org_name = org_result.scalar() or ""

        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=operator.org_id,
            module="user",
            action="create",
            description=f"管理员创建用户 [{user.display_name}]，所属组织 [{org_name}]",
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            ip=ip,
            user_agent=user_agent,
        )

        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        *,
        user_id: int,
        data: UserUpdate,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        user = await UserService.get_user(db, user_id)
        if user is None:
            return None

        old_value = {
            "phone": user.phone,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "org_id": user.org_id,
            "status": user.status,
        }

        update_data = data.model_dump(exclude_unset=True)

        # Check phone uniqueness if changing
        if "phone" in update_data and update_data["phone"] != user.phone:
            existing = await db.execute(select(User).where(User.phone == update_data["phone"], User.is_deleted.is_(False)))
            if existing.scalar_one_or_none() is not None:
                raise ValueError("手机号已被注册")

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.flush()
        await db.refresh(user)

        new_value = {
            "phone": user.phone,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "org_id": user.org_id,
            "status": user.status,
        }

        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=operator.org_id,
            module="user",
            action="update",
            description=f"管理员修改用户 [{user.display_name}] 信息",
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            ip=ip,
            user_agent=user_agent,
            old_value=old_value,
            new_value=new_value,
        )

        return user

    @staticmethod
    async def update_user_status(
        db: AsyncSession,
        *,
        user_id: int,
        status_val: int,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        user = await UserService.get_user(db, user_id)
        if user is None:
            return None

        old_status = user.status
        user.status = status_val
        await db.flush()
        await db.refresh(user)

        action_desc = "启用" if status_val == 1 else "禁用"
        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=operator.org_id,
            module="user",
            action="disable" if status_val == 0 else "enable",
            description=f"管理员{action_desc}用户 [{user.display_name}]",
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            ip=ip,
            user_agent=user_agent,
            old_value={"status": old_status},
            new_value={"status": status_val},
        )

        return user

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        *,
        user_id: int,
        new_password: str,
        operator: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        user = await UserService.get_user(db, user_id)
        if user is None:
            return None

        user.password_hash = hash_password(new_password)
        await db.flush()

        await AuditService.log(
            db,
            user_id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
            org_id=operator.org_id,
            module="user",
            action="reset_pwd",
            description=f"管理员重置用户 [{user.display_name}] 密码",
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            ip=ip,
            user_agent=user_agent,
        )

        return user
