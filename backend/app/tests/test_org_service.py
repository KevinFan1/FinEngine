import pytest

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate
from app.services.org_service import DEFAULT_ORG_MAX_STORAGE_BYTES, DEFAULT_ORG_MAX_USERS, OrgService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _CreateOrgRaceSession:
    def __init__(
        self,
        inserted_org: Organization | None,
        *,
        existing_name: Organization | None = None,
        existing_code: Organization | None = None,
    ) -> None:
        self.inserted_org = inserted_org
        self.existing_name = existing_name
        self.existing_code = existing_code
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        if getattr(stmt, "is_insert", False):
            return _ScalarResult(self.inserted_org)
        if getattr(stmt, "is_select", False):
            if not any(getattr(item, "is_insert", False) for item in self.statements):
                return _ScalarResult(None)
            params = stmt.compile().params
            if "name_1" in params:
                return _ScalarResult(self.existing_name)
            if "code_1" in params:
                return _ScalarResult(self.existing_code)
        raise AssertionError(f"unexpected statement: {stmt!r}")

    def add(self, _instance):
        raise AssertionError("create_org must use an atomic insert")

    async def flush(self):
        raise AssertionError("create_org must not use select-then-flush")

    async def refresh(self, _instance):
        raise AssertionError("create_org should return the inserted row")


@pytest.mark.asyncio
async def test_create_org_uses_atomic_insert_with_expected_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    created_org = Organization(id=8, name="并发组织", code="race-org", status=1, org_type="external")
    db = _CreateOrgRaceSession(created_org)
    audit_calls = []

    async def fake_log(*args, **kwargs):
        audit_calls.append(kwargs)
        return None

    monkeypatch.setattr("app.services.org_service.AuditService.log", fake_log)

    org = await OrgService.create_org(
        db,  # type: ignore[arg-type]
        data=OrganizationCreate(name="并发组织", code="race-org"),
        operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
    )

    assert org is created_org
    assert len(db.statements) == 3
    insert_stmt = db.statements[-1]
    assert getattr(insert_stmt, "is_insert", False)
    params = insert_stmt.compile().params
    assert params["max_users"] == DEFAULT_ORG_MAX_USERS
    assert params["max_storage_bytes"] == DEFAULT_ORG_MAX_STORAGE_BYTES
    assert params["used_storage_bytes"] == 0
    assert params["plan_type"] == "free"
    assert params["org_type"] == "external"
    assert len(audit_calls) == 1


@pytest.mark.asyncio
async def test_create_org_reports_name_duplicate_after_concurrent_insert() -> None:
    existing_org = Organization(id=9, name="并发组织", code="other-code", status=1, org_type="external")
    db = _CreateOrgRaceSession(None, existing_name=existing_org)

    with pytest.raises(ValueError, match="组织名称已存在"):
        await OrgService.create_org(
            db,  # type: ignore[arg-type]
            data=OrganizationCreate(name="并发组织", code="race-org"),
            operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
        )

    assert any(getattr(stmt, "is_insert", False) for stmt in db.statements)


@pytest.mark.asyncio
async def test_create_org_reports_code_duplicate_after_concurrent_insert() -> None:
    existing_org = Organization(id=9, name="其他组织", code="race-org", status=1, org_type="external")
    db = _CreateOrgRaceSession(None, existing_code=existing_org)

    with pytest.raises(ValueError, match="组织编码已存在"):
        await OrgService.create_org(
            db,  # type: ignore[arg-type]
            data=OrganizationCreate(name="并发组织", code="race-org"),
            operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
        )

    assert any(getattr(stmt, "is_insert", False) for stmt in db.statements)


@pytest.mark.asyncio
async def test_create_org_persists_explicit_external_type(monkeypatch: pytest.MonkeyPatch) -> None:
    created_org = Organization(id=10, name="外部组织", code="external-org", status=1, org_type="external")
    db = _CreateOrgRaceSession(created_org)

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.org_service.AuditService.log", fake_log)

    org = await OrgService.create_org(
        db,  # type: ignore[arg-type]
        data=OrganizationCreate(name="外部组织", code="external-org", org_type="external"),
        operator=type("UserStub", (), {"id": 3, "username": "u3", "display_name": "用户3"})(),
    )

    assert org.org_type == "external"
    insert_stmt = next(stmt for stmt in db.statements if getattr(stmt, "is_insert", False))
    params = insert_stmt.compile().params
    assert params["org_type"] == "external"
