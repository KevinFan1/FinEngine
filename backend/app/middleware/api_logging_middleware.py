"""Request/response logging middleware."""

from __future__ import annotations

import json
import re
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


class ApiLoggingMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int = 8192) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        request_headers = scope.get("headers") or []
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
                request_body_truncated = _append_limited(request_body, body, self.max_body_bytes) or request_body_truncated
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_body_truncated, response_headers, response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = list(message.get("headers") or [])
            elif message["type"] == "http.response.body":
                response_content_type = _header_value(response_headers, b"content-type")
                if _should_log_body(response_content_type):
                    body = message.get("body", b"")
                    response_body_truncated = _append_limited(response_body, body, self.max_body_bytes) or response_body_truncated
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.bind(
                event="api.exception",
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
                query=_query_string(scope),
                duration_ms=round(duration_ms, 1),
                client_ip=_client_ip(scope, request_headers),
                user_agent=_header_value(request_headers, b"user-agent") or "-",
                request_content_type=request_content_type or "-",
                request_body=_format_body(bytes(request_body), request_content_type, request_body_truncated),
            ).exception("api.exception")
            raise
        finally:
            if response_headers:
                duration_ms = (time.perf_counter() - start) * 1000
                response_content_type = _header_value(response_headers, b"content-type")
                api_code, api_message = _api_code_message(response_body, response_content_type)
                logger.bind(
                    event="api.request",
                    request_id=request_id,
                    method=scope.get("method"),
                    path=scope.get("path"),
                    query=_query_string(scope),
                    http_status=response_status,
                    api_code=api_code,
                    api_message=api_message,
                    duration_ms=round(duration_ms, 1),
                    client_ip=_client_ip(scope, request_headers),
                    user_agent=_header_value(request_headers, b"user-agent") or "-",
                    request_content_type=request_content_type or "-",
                    response_content_type=response_content_type or "-",
                    request_body=_format_body(bytes(request_body), request_content_type, request_body_truncated),
                ).info("api.request")


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    lowered = name.lower()
    for key, value in headers:
        if key.lower() == lowered:
            return value.decode("latin-1")
    return ""


def _query_string(scope: Scope) -> str:
    query = scope.get("query_string") or b""
    return query.decode("latin-1") if query else "-"


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


def _append_limited(target: bytearray, chunk: bytes, limit: int) -> bool:
    if not chunk or len(target) >= limit:
        return bool(chunk)
    remaining = limit - len(target)
    target.extend(chunk[:remaining])
    return len(chunk) > remaining


def _format_body(body: bytes, content_type: str, truncated: bool) -> Any:
    if not body:
        return "-"

    text = body.decode("utf-8", errors="replace")
    if "json" in content_type.lower():
        try:
            payload: Any = _redact(json.loads(text))
            if truncated:
                return {
                    "truncated": True,
                    "payload": payload,
                }
            return payload
        except json.JSONDecodeError:
            pass
    if truncated:
        return {
            "truncated": True,
            "payload": text,
        }
    return text


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


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
    code = parsed.get("code", "-")
    message = parsed.get("message", "-")
    return str(code), str(message)


def _api_code_message_from_partial(text: str) -> tuple[str, str]:
    code_match = re.search(r'"code"\s*:\s*("?[^",}\s]+"?)', text)
    message_match = re.search(r'"message"\s*:\s*"([^"]*)"', text)
    code = code_match.group(1).strip('"') if code_match else "-"
    message = message_match.group(1) if message_match else "-"
    return code, message
