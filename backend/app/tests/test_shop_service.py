import pytest

from app.models.shop import Shop
from app.services.shop_service import ShopService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _UploadRaceSession:
    def __init__(self, existing_shop: Shop) -> None:
        self.existing_shop = existing_shop
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        if getattr(stmt, "is_insert", False):
            return _ScalarResult(None)
        if getattr(stmt, "is_select", False):
            if not any(getattr(item, "is_insert", False) for item in self.statements):
                return _ScalarResult(None)
            return _ScalarResult(self.existing_shop)
        raise AssertionError(f"unexpected statement: {stmt!r}")

    def add(self, _instance):
        raise AssertionError("get_or_create_shop must use an atomic insert for upload races")

    async def flush(self):
        raise AssertionError("get_or_create_shop must not rely on select-then-flush")


@pytest.mark.asyncio
async def test_get_or_create_shop_uses_atomic_insert_for_upload_races() -> None:
    existing_shop = Shop(
        id=7,
        org_id=1,
        platform_name="douyin",
        shop_name="琢木承珠",
        shop_color="#F97316",
    )
    db = _UploadRaceSession(existing_shop)

    shop = await ShopService.get_or_create_shop(
        db,  # type: ignore[arg-type]
        org_id=1,
        platform_name="douyin",
        shop_name="琢木承珠",
    )

    assert shop is existing_shop
    assert getattr(db.statements[0], "is_insert", False)
    assert any(getattr(item, "is_select", False) for item in db.statements[1:])
