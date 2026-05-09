from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.audit_service import AuditService


class AuthService:
    @staticmethod
    async def login(
        db: AsyncSession,
        *,
        username: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        """Authenticate user by username or phone. Returns User on success, None on failure."""
        stmt = select(User).where(or_(User.username == username, User.phone == username), User.is_deleted.is_(False))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if user.status != 1:
            return None

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        # Log login
        await AuditService.log(
            db,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            org_id=user.org_id,
            module="auth",
            action="login",
            description=f"用户 [{user.display_name}] 登录系统",
            ip=ip,
            user_agent=user_agent,
        )

        return user

    @staticmethod
    async def create_default_superadmin(db: AsyncSession, password: str) -> None:
        """Create default superadmin account if it doesn't exist."""
        stmt = select(User).where(User.role == "superadmin", User.is_deleted.is_(False))
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            return

        superadmin = User(
            org_id=None,
            username="superadmin",
            phone="00000000000",
            password_hash=hash_password(password),
            display_name="超级管理员",
            email=None,
            role="superadmin",
            status=1,
        )
        db.add(superadmin)
        await db.flush()
