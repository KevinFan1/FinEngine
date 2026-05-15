from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_access_token
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_async_session),
):
    """Extract and validate user from Authorization header."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")

    result = await db.execute(select(User).where(User.id == int(user_id), User.is_deleted.is_(False)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    token_session_id = payload.get("sid")
    if not token_session_id or token_session_id != user.active_session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已在其他端登录，请重新登录")

    return user


def require_superadmin(user=Depends(get_current_user)):
    """Check that current user is a superadmin."""
    if user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return user


def require_org_admin_or_above(user=Depends(get_current_user)):
    """Check that current user is org_admin or superadmin."""
    if user.role not in ("superadmin", "org_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def require_same_org_or_superadmin(user=Depends(get_current_user), org_id: int | None = None):
    """Superadmin can access any org; org_admin/member must match org_id."""
    if user.role == "superadmin":
        return user
    if user.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该组织的数据")
    return user
