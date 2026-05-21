import pytest

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


def make_user(*, user_id: int, org_id: int | None, role: str = "org_admin") -> User:
    return User(
        id=user_id,
        org_id=org_id,
        username=f"user{user_id}",
        phone=f"1380000{user_id:04d}",
        password_hash="hash",
        display_name=f"用户{user_id}",
        role=role,
        status=1,
        must_change_password=False,
    )


def test_org_admin_create_user_is_limited_to_own_org() -> None:
    operator = make_user(user_id=1, org_id=10)
    body = UserCreate(
        org_id=20,
        username="new_user",
        phone="13800009999",
        password="Password1",
        display_name="新用户",
        role="member",
    )

    with pytest.raises(ValueError, match="无权管理其他组织"):
        UserService.validate_create_scope(data=body, operator=operator)


def test_org_admin_cannot_create_superadmin() -> None:
    operator = make_user(user_id=1, org_id=10)
    body = UserCreate(
        org_id=10,
        username="new_admin",
        phone="13800008888",
        password="Password1",
        display_name="新管理员",
        role="superadmin",
    )

    with pytest.raises(ValueError, match="无权创建超级管理员"):
        UserService.validate_create_scope(data=body, operator=operator)


def test_org_admin_cannot_manage_user_from_other_org() -> None:
    operator = make_user(user_id=1, org_id=10)
    target = make_user(user_id=2, org_id=20, role="member")

    with pytest.raises(ValueError, match="用户不存在"):
        UserService.validate_target_scope(user=target, operator=operator)


def test_org_admin_cannot_move_user_or_grant_superadmin() -> None:
    operator = make_user(user_id=1, org_id=10)
    target = make_user(user_id=2, org_id=10, role="member")

    with pytest.raises(ValueError, match="无权变更用户所属组织"):
        UserService.validate_update_scope(
            user=target,
            data=UserUpdate(org_id=20),
            operator=operator,
        )

    with pytest.raises(ValueError, match="无权授予超级管理员"):
        UserService.validate_update_scope(
            user=target,
            data=UserUpdate(role="superadmin"),
            operator=operator,
        )


def test_superadmin_can_manage_any_org_user() -> None:
    operator = make_user(user_id=1, org_id=None, role="superadmin")
    target = make_user(user_id=2, org_id=20, role="member")

    UserService.validate_target_scope(user=target, operator=operator)
    UserService.validate_update_scope(
        user=target,
        data=UserUpdate(org_id=30, role="org_admin"),
        operator=operator,
    )


@pytest.mark.asyncio
async def test_change_my_password_clears_must_change_flag(monkeypatch) -> None:
    from app.core.security import hash_password, verify_password

    operator = make_user(user_id=1, org_id=10, role="member")
    operator.password_hash = hash_password("OldPass1")
    operator.must_change_password = True

    class _FakeResult:
        def scalar_one_or_none(self):
            return None

    class _FakeDB:
        async def execute(self, _statement):
            return _FakeResult()

        async def flush(self):
            return None

    logged = {}

    async def fake_log(*args, **kwargs):
        logged["called"] = True

    monkeypatch.setattr("app.services.user_service.AuditService.log", fake_log)

    updated = await UserService.change_current_user_password(
        _FakeDB(),
        current_user=operator,
        old_password="OldPass1",
        new_password="NewPass1",
    )

    assert updated.must_change_password is False
    assert updated.password_hash != hash_password("OldPass1")
    assert verify_password("NewPass1", updated.password_hash)
    assert logged["called"] is True
