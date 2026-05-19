from unittest.mock import AsyncMock

import pytest

from app.api.v1 import health


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _statement):
        return None


class _FakeSessionFactory:
    def __call__(self):
        return _FakeSession()


@pytest.mark.asyncio
async def test_detailed_health_uses_captcha_redis_client(monkeypatch):
    redis_client = AsyncMock()
    redis_client.ping.return_value = True

    monkeypatch.setattr(health, "async_session_factory", _FakeSessionFactory())
    monkeypatch.setattr(health.captcha_service, "_redis_client", lambda: redis_client)

    response = await health.detailed_health_check()

    assert response.code == 200
    assert response.message == "healthy"
    assert response.data["redis"] == "ok"
    redis_client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_readiness_uses_captcha_redis_client(monkeypatch):
    redis_client = AsyncMock()
    redis_client.ping.return_value = True

    monkeypatch.setattr(health, "async_session_factory", _FakeSessionFactory())
    monkeypatch.setattr(health.captcha_service, "_redis_client", lambda: redis_client)

    response = await health.readiness_check()

    assert response.code == 200
    assert response.data == {"status": "ready"}
    redis_client.ping.assert_awaited_once()
