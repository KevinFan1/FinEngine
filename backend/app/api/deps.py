"""API dependency shortcuts re-exports."""

from app.core.deps import (
    get_current_user,
    require_org_admin_or_above,
    require_same_org_or_superadmin,
    require_superadmin,
)

__all__ = [
    "get_current_user",
    "require_superadmin",
    "require_org_admin_or_above",
    "require_same_org_or_superadmin",
]
