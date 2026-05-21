from datetime import datetime, timezone

from app.models.user import User
from app.schemas.auth import UserInfo


def test_user_info_schema_includes_must_change_password() -> None:
    user = UserInfo(
        id=1,
        org_id=10,
        username="demo",
        phone="13800000000",
        display_name="演示用户",
        email=None,
        must_change_password=True,
        role="member",
        status=1,
        org_name="示例组织",
        last_login_at=str(datetime.now(timezone.utc)),
    )

    assert user.must_change_password is True


def test_user_info_schema_defaults_must_change_password_false() -> None:
    user = UserInfo(
        id=1,
        org_id=10,
        username="demo",
        phone="13800000000",
        display_name="演示用户",
        email=None,
        role="member",
        status=1,
        org_name=None,
        last_login_at=None,
    )

    assert user.must_change_password is False
