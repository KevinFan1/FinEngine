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


def test_setup_logging_falls_back_when_queue_creation_fails(tmp_path, monkeypatch) -> None:
    added_handlers: list[dict[str, object]] = []

    monkeypatch.setattr(logging_module.settings, "LOG_DIR", str(tmp_path))
    monkeypatch.setattr(logging_module.settings, "LOG_LEVEL", "INFO")
    monkeypatch.setattr(logging_module.settings, "LOG_ROTATION_TIME", "00:00")
    monkeypatch.setattr(logging_module.settings, "LOG_RETENTION_DAYS", 15)
    monkeypatch.setattr(logging_module.logger, "remove", lambda: None)

    def fake_add(*args, **kwargs):
        added_handlers.append({"args": args, "kwargs": dict(kwargs)})
        if kwargs.get("enqueue") is True:
            raise OSError(28, "No space left on device")
        return len(added_handlers)

    monkeypatch.setattr(logging_module.logger, "add", fake_add)
    monkeypatch.setattr(logging_module.logging, "basicConfig", lambda **kwargs: None)

    logging_module.setup_logging()

    file_handler_calls = [
        call for call in added_handlers if call["args"] and call["args"][0] != logging_module.sys.stderr
    ]
    stderr_handler_calls = [
        call for call in added_handlers if call["args"] and call["args"][0] == logging_module.sys.stderr
    ]

    assert [call["kwargs"].get("enqueue") for call in file_handler_calls] == [True, False, True, False]
    assert len(stderr_handler_calls) == 1
    assert stderr_handler_calls[0]["kwargs"].get("enqueue") is None
