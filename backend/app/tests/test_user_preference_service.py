import pytest

from app.models.user_preference import UserPreference
from app.services.user_preference_service import UserPreferenceService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _PreferenceSession:
    def __init__(self, existing: UserPreference | None = None) -> None:
        self.existing = existing
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        if getattr(stmt, "is_select", False):
            return _ScalarResult(self.existing)
        return _ScalarResult(
            UserPreference(
                id=1,
                user_id=9,
                preference_key="table.columns",
                preference_value=["platform", "shop_name"],
            )
        )


@pytest.mark.asyncio
async def test_get_preference_returns_existing_preference() -> None:
    pref = UserPreference(
        id=2,
        user_id=9,
        preference_key="table.columns",
        preference_value=["platform"],
    )
    db = _PreferenceSession(existing=pref)

    result = await UserPreferenceService.get_preference(
        db,  # type: ignore[arg-type]
        user_id=9,
        preference_key="table.columns",
    )

    assert result is pref


@pytest.mark.asyncio
async def test_set_preference_uses_upsert() -> None:
    db = _PreferenceSession()

    result = await UserPreferenceService.set_preference(
        db,  # type: ignore[arg-type]
        user_id=9,
        preference_key="table.columns",
        preference_value=["platform", "shop_name"],
    )

    assert result.preference_key == "table.columns"
    assert result.preference_value == ["platform", "shop_name"]
    assert len(db.statements) == 1
