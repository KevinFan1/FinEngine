from fastapi import status

from app.core.exception_handlers import _integrity_error_message, _user_facing_http_message, api_json_response


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
