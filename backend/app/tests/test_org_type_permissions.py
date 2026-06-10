import pytest
from fastapi import HTTPException

from app.core.deps import ensure_internal_org_access
from app.models.user import User


def _build_user(*, role: str = "member", org_id: int | None = 1) -> User:
    return User(
        id=1,
        username="tester",
        phone="13800000000",
        password_hash="hashed",
        display_name="测试用户",
        role=role,
        org_id=org_id,
        status=1,
    )


@pytest.mark.asyncio
async def test_superadmin_can_access_internal_only_features_without_org() -> None:
    user = _build_user(role="superadmin", org_id=None)

    returned_user = await ensure_internal_org_access(user=user)

    assert returned_user is user


@pytest.mark.asyncio
async def test_internal_org_user_can_access_internal_only_features(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()

    async def fake_resolve_org_type(_db, _org_id):
        return "internal"

    monkeypatch.setattr("app.core.deps._resolve_user_org_type", fake_resolve_org_type)

    returned_user = await ensure_internal_org_access(user=user, db=object())

    assert returned_user is user


@pytest.mark.asyncio
async def test_external_org_user_is_blocked_from_internal_only_features(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _build_user()

    async def fake_resolve_org_type(_db, _org_id):
        return "external"

    monkeypatch.setattr("app.core.deps._resolve_user_org_type", fake_resolve_org_type)

    with pytest.raises(HTTPException, match="当前组织类型无权访问该功能"):
        await ensure_internal_org_access(user=user, db=object())
