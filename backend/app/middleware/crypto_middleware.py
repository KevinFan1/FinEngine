"""Transparent request/response payload encryption middleware."""

from __future__ import annotations

import json

from fastapi import status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.schemas.common import ApiResponse
from app.services.crypto_service import api_crypto_service, api_replay_guard, replay_aad


ENCRYPTED_HEADER = b"x-api-encrypted"
ENCRYPTED_KEY_HEADER = b"x-api-crypto-key"
ENCRYPTED_RESPONSE_HEADER = b"x-api-encrypted-response"
NONCE_HEADER = b"x-api-nonce"
TIMESTAMP_HEADER = b"x-api-timestamp"
API_PREFIX = "/api/v1"
CRYPTO_OPTIONAL_PATHS = ("/api/v1/health",)


class ApiCryptoMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.API_CRYPTO_ENABLED or not _requires_crypto(scope):
            await self.app(scope, receive, send)
            return

        headers = list(scope.get("headers") or [])
        encrypted = _header_value(headers, ENCRYPTED_HEADER) == "1"
        encrypted_key = _header_value(headers, ENCRYPTED_KEY_HEADER)
        nonce = _header_value(headers, NONCE_HEADER)
        timestamp = _header_value(headers, TIMESTAMP_HEADER)
        if not encrypted:
            await _api_error("接口必须使用加密请求", status.HTTP_400_BAD_REQUEST)(scope, receive, send)
            return

        try:
            aes_key = api_crypto_service.decrypt_aes_key(encrypted_key, timestamp=timestamp, nonce=nonce)
        except Exception:
            await _api_error("请求加密数据解密失败", status.HTTP_400_BAD_REQUEST)(scope, receive, send)
            return

        replay_check = await api_replay_guard.verify(timestamp, nonce)
        if not replay_check.ok:
            await _api_error(replay_check.message, status.HTTP_400_BAD_REQUEST)(scope, receive, send)
            return

        request_scope = dict(scope)
        receive_for_app = receive

        if _should_decrypt_body(scope, headers):
            try:
                body = await _read_body(receive)
                aad = replay_aad(timestamp, nonce)
                decrypted_body = _decrypt_body(aes_key, body, aad=aad) if body.strip() else body
            except Exception:
                await _api_error("请求加密数据解密失败", status.HTTP_400_BAD_REQUEST)(scope, receive, send)
                return
            request_scope["headers"] = _replace_content_headers(headers, len(decrypted_body))
            receive_for_app = _receive_once(decrypted_body)

        response_status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        response_body = bytearray()

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = list(message.get("headers") or [])
                return
            if message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))
                if message.get("more_body", False):
                    return
                await _send_encrypted_response(send, aes_key, response_status, response_headers, bytes(response_body))
                return
            await send(message)

        await self.app(request_scope, receive_for_app, send_wrapper)


def _requires_crypto(scope: Scope) -> bool:
    if str(scope.get("method") or "").upper() == "OPTIONS":
        return False

    path = str(scope.get("path") or "")
    if not path.startswith(API_PREFIX):
        return False
    return not any(path == optional or path.startswith(f"{optional}/") for optional in CRYPTO_OPTIONAL_PATHS)


def _should_decrypt_body(scope: Scope, headers: list[tuple[bytes, bytes]]) -> bool:
    method = str(scope.get("method") or "").upper()
    if method in {"GET", "HEAD"}:
        return False
    content_type = _header_value(headers, b"content-type").lower()
    return "multipart/form-data" not in content_type


def _decrypt_body(aes_key: bytes, body: bytes, *, aad: bytes) -> bytes:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("encrypted") is not True:
        raise ValueError("Encrypted request body is invalid")
    return api_crypto_service.decrypt_payload(
        aes_key,
        iv=str(payload.get("iv") or ""),
        data=str(payload.get("data") or ""),
        aad=aad,
    )


async def _send_encrypted_response(
    send: Send,
    aes_key: bytes,
    status_code: int,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
) -> None:
    content_type = _header_value(headers, b"content-type")
    if "json" not in content_type.lower():
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        await send({"type": "http.response.body", "body": body})
        return

    encrypted = api_crypto_service.encrypt_payload(aes_key, body)
    payload = json.dumps(
        {
            "encrypted": True,
            "iv": encrypted.iv,
            "data": encrypted.data,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    response_headers = _replace_header(headers, b"content-length", str(len(payload)).encode("ascii"))
    response_headers = _replace_header(response_headers, ENCRYPTED_RESPONSE_HEADER, b"1")
    await send({"type": "http.response.start", "status": status_code, "headers": response_headers})
    await send({"type": "http.response.body", "body": payload})


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _receive_once(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _replace_content_headers(headers: list[tuple[bytes, bytes]], body_length: int) -> list[tuple[bytes, bytes]]:
    output = [
        (key, value)
        for key, value in headers
        if key.lower() not in {b"content-length", b"content-type"}
    ]
    if body_length:
        output.append((b"content-type", b"application/json"))
        output.append((b"content-length", str(body_length).encode("ascii")))
    return output


def _replace_header(headers: list[tuple[bytes, bytes]], name: bytes, value: bytes) -> list[tuple[bytes, bytes]]:
    lowered = name.lower()
    output = [(key, header_value) for key, header_value in headers if key.lower() != lowered]
    output.append((name, value))
    return output


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    lowered = name.lower()
    for key, value in headers:
        if key.lower() == lowered:
            return value.decode("latin-1")
    return ""


def _api_error(message: str, code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(code=code, message=message).model_dump(mode="json"),
    )
