import pytest

from app.models.shop import Shop
from app.models.upload import UploadBatch
from app.models.user import User
from app.services.shop_service import ShopService
from app.services.upload_service import UploadService


def make_user(*, user_id: int, org_id: int | None, role: str = "org_admin") -> User:
    return User(
        id=user_id,
        org_id=org_id,
        username=f"user{user_id}",
        phone=f"1390000{user_id:04d}",
        password_hash="hash",
        display_name=f"用户{user_id}",
        role=role,
        status=1,
    )


def test_non_superadmin_cannot_manage_other_org_shop() -> None:
    operator = make_user(user_id=1, org_id=10)
    shop = Shop(id=2, org_id=20, platform_name="douyin", shop_name="跨组织店铺")

    with pytest.raises(ValueError, match="店铺不存在"):
        ShopService.validate_shop_scope(shop=shop, operator=operator)


def test_superadmin_can_manage_any_org_shop() -> None:
    operator = make_user(user_id=1, org_id=None, role="superadmin")
    shop = Shop(id=2, org_id=20, platform_name="douyin", shop_name="跨组织店铺")

    ShopService.validate_shop_scope(shop=shop, operator=operator)


def test_non_superadmin_cannot_read_other_org_upload_batch_files() -> None:
    operator = make_user(user_id=1, org_id=10)
    batch = UploadBatch(id=2, org_id=20, user_id=9, file_count=1)

    with pytest.raises(ValueError, match="批次不存在"):
        UploadService.validate_batch_scope(batch=batch, user=operator)


def test_superadmin_can_read_any_org_upload_batch_files() -> None:
    operator = make_user(user_id=1, org_id=None, role="superadmin")
    batch = UploadBatch(id=2, org_id=20, user_id=9, file_count=1)

    UploadService.validate_batch_scope(batch=batch, user=operator)
