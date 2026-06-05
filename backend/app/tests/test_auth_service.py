import pytest

from app.services.auth_service import AuthService


class _CreateSuperadminResult:
    def __init__(self, *, existing: bool) -> None:
        self.existing = existing

    def scalar_one_or_none(self):
        if self.existing:
            return object()
        return None


class _CreateSuperadminSession:
    def __init__(self, *, existing: bool) -> None:
        self.existing = existing
        self.added: list[object] = []
        self.executed = 0
        self.flushed = 0
        self.last_statement = None

    async def execute(self, statement):
        self.executed += 1
        self.last_statement = statement
        return _CreateSuperadminResult(existing=self.existing)

    def add(self, item: object) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        self.flushed += 1


@pytest.mark.asyncio
async def test_create_default_superadmin_skips_when_default_account_exists() -> None:
    session = _CreateSuperadminSession(existing=True)

    await AuthService.create_default_superadmin(session, password="secret")  # type: ignore[arg-type]

    assert session.executed == 1
    assert session.added == []
    assert session.flushed == 0
    sql = str(session.last_statement)
    assert "fin_users.username = :username_1" in sql
    assert "fin_users.role = :role_1" not in sql


@pytest.mark.asyncio
async def test_create_default_superadmin_creates_user_when_missing() -> None:
    session = _CreateSuperadminSession(existing=False)

    await AuthService.create_default_superadmin(session, password="secret")  # type: ignore[arg-type]

    assert session.executed == 1
    assert len(session.added) == 1
    assert session.flushed == 1
