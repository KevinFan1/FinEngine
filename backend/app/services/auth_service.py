from datetime import datetime, timezone
from uuid import uuid4

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
        stmt = (
            select(User)
            .where(or_(User.username == username, User.phone == username), User.is_deleted.is_(False))
            .with_for_update()
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if user.status != 1:
            return None

        login_at = datetime.now(timezone.utc)
        # A new login invalidates all older JWTs for the same account.
        user.last_login_at = login_at
        user.active_session_id = uuid4().hex
        user.active_session_ip = ip
        user.active_session_user_agent = user_agent[:500] if user_agent else None
        user.active_session_at = login_at
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
        stmt = select(User).where(User.username == "superadmin", User.is_deleted.is_(False))
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
            must_change_password=True,
            role="superadmin",
            status=1,
        )
        db.add(superadmin)
        await db.flush()
