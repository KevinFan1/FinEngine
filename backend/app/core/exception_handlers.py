"""Convert backend exceptions to the API response envelope."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.schemas.common import ApiResponse


def api_json_response(code: int, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(code=code, message=message, data=data).model_dump(mode="json"),
    )


def _stringify_detail(detail: Any) -> str:
    if detail is None:
        return ""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list | dict):
        return json.dumps(detail, ensure_ascii=False, default=str)
    return str(detail)


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "参数校验失败"

    first = errors[0]
    loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
    msg = first.get("msg") or "参数错误"
    if loc:
        return f"参数校验失败：{loc} {msg}"
    return f"参数校验失败：{msg}"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = int(exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = _stringify_detail(exc.detail) or "请求失败"
        if code >= 500:
            logger.error("api.http_exception path={} code={} message={}", request.url.path, code, message)
        return api_json_response(code=code, message=message)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = int(exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR)
        message = _stringify_detail(exc.detail) or "请求失败"
        if code == status.HTTP_404_NOT_FOUND and message == "Not Found":
            message = "接口不存在"
        if code >= 500:
            logger.error("api.starlette_http_exception path={} code={} message={}", request.url.path, code, message)
        return api_json_response(code=code, message=message)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = _validation_message(exc)
        logger.warning("api.validation_error path={} message={} errors={}", request.url.path, message, exc.errors())
        return api_json_response(code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message)

    @app.exception_handler(ValueError)
    async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
        message = str(exc) or "请求参数错误"
        logger.warning("api.value_error path={} message={}", request.url.path, message)
        return api_json_response(code=status.HTTP_400_BAD_REQUEST, message=message)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        message = str(exc) or "服务器内部错误"
        logger.exception("api.unhandled_exception path={} message={}", request.url.path, message)
        return api_json_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=message)
