import pytest

from app.models.shop import Shop
from app.schemas.shop import ShopCreate
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


class _CreateShopRaceSession:
    def __init__(self, inserted_shop: Shop | None) -> None:
        self.inserted_shop = inserted_shop
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        if getattr(stmt, "is_insert", False):
            return _ScalarResult(self.inserted_shop)
        raise AssertionError("create_shop must rely on a single atomic insert")

    def add(self, _instance):
        raise AssertionError("create_shop must not use select-then-add")

    async def flush(self):
        raise AssertionError("create_shop must not use select-then-flush")

    async def refresh(self, _instance):
        raise AssertionError("create_shop should return the inserted row")


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


@pytest.mark.asyncio
async def test_create_shop_uses_atomic_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    created_shop = Shop(
        id=8,
        org_id=1,
        platform_name="douyin",
        shop_name="并发店铺",
        shop_color="#22C55E",
    )
    db = _CreateShopRaceSession(created_shop)
    audit_calls = []

    async def fake_log(*args, **kwargs):
        audit_calls.append(kwargs)
        return None

    monkeypatch.setattr("app.services.shop_service.AuditService.log", fake_log)

    shop = await ShopService.create_shop(
        db,  # type: ignore[arg-type]
        data=ShopCreate(platform_name="douyin", shop_name="并发店铺"),
        org_id=1,
        operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
    )

    assert shop is created_shop
    assert len(db.statements) == 1
    assert getattr(db.statements[0], "is_insert", False)
    assert len(audit_calls) == 1


@pytest.mark.asyncio
async def test_create_shop_reports_duplicate_after_concurrent_insert() -> None:
    db = _CreateShopRaceSession(None)

    with pytest.raises(ValueError, match="已存在同名店铺"):
        await ShopService.create_shop(
            db,  # type: ignore[arg-type]
            data=ShopCreate(platform_name="douyin", shop_name="并发店铺"),
            org_id=1,
            operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
        )

    assert len(db.statements) == 1
    assert getattr(db.statements[0], "is_insert", False)
