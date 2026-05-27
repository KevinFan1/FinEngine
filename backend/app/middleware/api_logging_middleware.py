"""Request/response logging middleware."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from typing import Any

from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SENSITIVE_KEYS = {
    "access_key_secret",
    "access_token",
    "authorization",
    "captcha_code",
    "captcha_id",
    "new_password",
    "old_password",
    "password",
    "security_token",
    "token",
}
REQUEST_ID_HEADER = b"x-request-id"
MAX_BODY_BYTES = 8192


class ApiLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        request_scope = dict(scope)
        request_headers = list(scope.get("headers") or [])
        request_id = _ensure_request_id(request_headers)
        request_scope["headers"] = request_headers
        request_content_type = _header_value(request_headers, b"content-type")
        request_body = bytearray()
        request_body_truncated = False
        response_status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        response_body = bytearray()
        response_body_truncated = False

        async def receive_wrapper() -> Message:
            nonlocal request_body_truncated
            message = await receive()
            if message["type"] == "http.request" and _should_log_body(request_content_type):
                body = message.get("body", b"")
                request_body_truncated = _append_limited(request_body, body) or request_body_truncated
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_body_truncated, response_headers, response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = list(message.get("headers") or [])
            elif message["type"] == "http.response.body":
                if _should_log_body(_header_value(response_headers, b"content-type")):
                    body = message.get("body", b"")
                    response_body_truncated = _append_limited(response_body, body) or response_body_truncated
            await send(message)

        exc_info: BaseException | None = None
        try:
            await self.app(request_scope, receive_wrapper, send_wrapper)
        except Exception:
            exc_info = sys.exc_info()[1]
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            method = str(request_scope.get("method") or "-")
            path = str(request_scope.get("path") or "-")
            api_code, api_message = _api_code_message(
                response_body, _header_value(response_headers, b"content-type"),
            )
            level = _log_level(response_status, api_code, exc_info is not None)

            bind_fields: dict[str, Any] = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": response_status,
                "duration_ms": round(duration_ms, 1),
                "client_ip": _client_ip(request_scope, request_headers),
            }
            if api_code and api_code != "-":
                bind_fields["api_code"] = api_code
            if api_message and api_message != "-":
                bind_fields["api_message"] = api_message

            if exc_info is not None:
                bind_fields["request_body"] = _format_body(
                    bytes(request_body), request_content_type, request_body_truncated,
                )

            message = f"{method} {path} {response_status} {duration_ms:.1f}ms"

            log = logger.opt(depth=1).bind(**bind_fields)
            if exc_info is not None:
                log.opt(exception=exc_info).error(message)
            else:
                log.log(level, message)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_request_id(headers: list[tuple[bytes, bytes]]) -> str:
    request_id = _header_value(headers, REQUEST_ID_HEADER).strip()
    if request_id:
        return request_id
    request_id = str(uuid.uuid4())
    headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
    return request_id


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    lowered = name.lower()
    for key, value in headers:
        if key.lower() == lowered:
            return value.decode("latin-1")
    return ""


def _client_ip(scope: Scope, headers: list[tuple[bytes, bytes]]) -> str:
    forwarded_for = _header_value(headers, b"x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


def _should_log_body(content_type: str) -> bool:
    if not content_type:
        return True
    lowered = content_type.lower()
    if "multipart/" in lowered or "octet-stream" in lowered:
        return False
    return "json" in lowered or lowered.startswith("text/") or "x-www-form-urlencoded" in lowered


def _append_limited(target: bytearray, chunk: bytes) -> bool:
    if not chunk or len(target) >= MAX_BODY_BYTES:
        return bool(chunk)
    remaining = MAX_BODY_BYTES - len(target)
    target.extend(chunk[:remaining])
    return len(chunk) > remaining


def _format_body(body: bytes, content_type: str, truncated: bool) -> Any:
    if not body:
        return "-"
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type.lower():
        try:
            payload: Any = _redact(json.loads(text))
            return {"truncated": True, "payload": payload} if truncated else payload
        except json.JSONDecodeError:
            pass
    return {"truncated": True, "payload": text} if truncated else text


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _log_level(http_status: int, api_code: str, is_exception: bool) -> str:
    if is_exception:
        return "ERROR"
    business_code = _safe_int(api_code)
    effective = business_code if business_code is not None and business_code != 200 else http_status
    if effective >= 500:
        return "ERROR"
    if effective >= 400:
        return "WARNING"
    return "INFO"


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _api_code_message(body: bytearray, content_type: str) -> tuple[str, str]:
    if not body or "json" not in content_type.lower():
        return "-", "-"
    text = bytes(body).decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _api_code_message_from_partial(text)
    if not isinstance(parsed, dict):
        return "-", "-"
    return str(parsed.get("code", "-")), str(parsed.get("message", "-"))


def _api_code_message_from_partial(text: str) -> tuple[str, str]:
    code_match = re.search(r'"code"\s*:\s*("?[^",}\s]+"?)', text)
    message_match = re.search(r'"message"\s*:\s*"([^"]*)"', text)
    code = code_match.group(1).strip('"') if code_match else "-"
    message = message_match.group(1) if message_match else "-"
    return code, message
