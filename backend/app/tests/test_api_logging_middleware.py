from app.core import logging as logging_module
from app.middleware import api_logging_middleware as middleware


def test_request_log_message_uses_combined_access_format() -> None:
    message = middleware._request_log_message(
        method="POST",
        path="/api/v1/auth/login",
        query="next=%2Fdashboard",
        http_version="1.1",
        http_status=200,
        response_bytes=321,
        api_code="200",
        api_message="登录成功",
        duration_ms=12.34,
        client_ip="127.0.0.1",
        referer="-",
        user_agent="pytest-agent/1.0",
        request_id="req-123",
    )

    assert (
        message
        == '127.0.0.1 - "POST /api/v1/auth/login?next=%2Fdashboard HTTP/1.1" 200 321 '
        '"-" "pytest-agent/1.0" duration_ms=12.3 request_id="req-123" '
        'api_code="200" api_message="登录成功"'
    )


def test_format_extra_context_keeps_priority_keys_visible() -> None:
    context = logging_module._format_extra_context(
        {
            "custom": {"nested": True},
            "request_body": {"password": "***", "username": "alice"},
            "request_id": "req-123",
            "user_agent": "pytest-agent/1.0",
        }
    )

    assert (
        context
        == 'request_id="req-123" user_agent="pytest-agent/1.0" '
        'request_body={"password":"***","username":"alice"} custom={"nested":true}'
    )
