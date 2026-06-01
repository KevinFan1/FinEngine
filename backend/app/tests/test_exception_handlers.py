from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.exc import DataError

from app.core.exception_handlers import (
    SYSTEM_ERROR_MESSAGE,
    _integrity_error_message,
    _user_facing_http_message,
    api_json_response,
    register_exception_handlers,
)


def test_rate_limit_message_is_user_facing() -> None:
    assert _user_facing_http_message(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded") == "操作太频繁了，请稍后再试"


def test_api_error_envelope_keeps_http_200() -> None:
    response = api_json_response(code=status.HTTP_429_TOO_MANY_REQUESTS, message="操作太频繁了，请稍后再试")

    assert response.status_code == status.HTTP_200_OK


def test_integrity_error_message_maps_org_name_unique_constraint() -> None:
    message = '(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) constraint "uq_fin_org_name"'

    assert _integrity_error_message(Exception(message)) == "组织名称已存在，请更换后再试"


def test_integrity_error_message_maps_org_code_unique_constraint() -> None:
    message = '(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) constraint "uq_fin_org_code"'

    assert _integrity_error_message(Exception(message)) == "组织编码已存在，请更换后再试"


def test_integrity_error_message_hides_unknown_database_details() -> None:
    message = '(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) duplicate key value violates unique constraint "some_other_constraint"'

    assert _integrity_error_message(Exception(message)) == SYSTEM_ERROR_MESSAGE


def test_data_error_returns_system_error_and_logs_at_error_level(monkeypatch) -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/data-error")
    async def data_error_route():
        raise DataError("bad data", {}, Exception("boom"))

    logged = []

    def fake_error(message, *args):
        logged.append((message, args))

    monkeypatch.setattr("app.core.exception_handlers.logger.error", fake_error)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/data-error")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == SYSTEM_ERROR_MESSAGE
    assert logged
    assert logged[0][0] == "api.data_error path={} message={}"


def test_unhandled_exception_returns_system_error_and_logs_exception(monkeypatch) -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom_route():
        raise RuntimeError("sensitive internal detail")

    logged = []

    def fake_exception(message, *args):
        logged.append((message, args))

    monkeypatch.setattr("app.core.exception_handlers.logger.exception", fake_exception)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["message"] == SYSTEM_ERROR_MESSAGE
    assert "sensitive internal detail" not in response.json()["message"]
    assert logged
    assert logged[0][0] == "api.unhandled_exception path={} message={}"
