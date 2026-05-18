"""Convert backend exceptions to the API response envelope."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from loguru import logger
from sqlalchemy.exc import DataError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.schemas.common import ApiResponse


FIELD_LABELS = {
    "username": "用户名",
    "password": "密码",
    "new_password": "新密码",
    "confirmPassword": "确认密码",
    "phone": "手机号",
    "email": "邮箱",
    "display_name": "显示名称",
    "role": "角色",
    "status": "状态",
    "status_val": "状态",
    "org_id": "组织",
    "orgIds": "组织",
    "name": "名称",
    "code": "编码",
    "remark": "备注",
    "platform_id": "平台",
    "platform_name": "平台",
    "platform_code": "平台",
    "report_platform_name": "归集平台",
    "type_code": "文件类型",
    "shop_id": "店铺",
    "shop_name": "店铺名称",
    "shop_color": "店铺颜色",
    "entity_name": "主体名称",
    "captcha_id": "验证码",
    "captcha_code": "验证码",
    "batch_id": "上传批次",
    "file_count": "文件数量",
    "original_name": "文件名",
    "oss_key": "文件存储路径",
    "file_size": "文件大小",
    "file_hash": "文件校验值",
    "parsed_year": "年份",
    "parsed_month": "月份",
    "parsed_type": "文件类型",
    "parsed_shop": "店铺名称",
    "detected_platform": "平台",
    "source_year": "数据年份",
    "source_month": "数据月份",
    "summary_year": "核算年份",
    "summary_month": "核算月份",
    "accounting_year": "核算年份",
    "accounting_month": "核算月份",
    "accounting_start_year": "核算开始年份",
    "accounting_start_month": "核算开始月份",
    "accounting_end_year": "核算结束年份",
    "accounting_end_month": "核算结束月份",
    "metric_key": "调整指标",
    "direction": "调整方向",
    "amount": "调整金额",
    "ids": "选中记录",
    "scope": "导出范围",
    "task_ids": "任务",
    "page": "页码",
    "page_size": "每页条数",
    "keyword": "搜索关键词",
    "module": "模块",
    "action": "操作类型",
    "user_id": "用户",
    "start_time": "开始时间",
    "end_time": "结束时间",
    "text": "分类文本",
    "texts": "分类文本",
    "categories": "分类字典",
}


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
    return str(detail)


def _field_label(loc_parts: list[Any]) -> str:
    meaningful = [str(part) for part in loc_parts if part not in {"body", "query", "path"}]
    if not meaningful:
        return "参数"

    last = meaningful[-1]
    if last.isdigit() and len(meaningful) >= 2:
        last = meaningful[-2]
    return FIELD_LABELS.get(last, last)


def _constraint_value(ctx: dict[str, Any] | None, *keys: str) -> Any:
    if not ctx:
        return None
    for key in keys:
        if key in ctx:
            return ctx[key]
    return None


def _friendly_validation_reason(error: dict[str, Any]) -> str:
    error_type = str(error.get("type") or "")
    ctx = error.get("ctx") if isinstance(error.get("ctx"), dict) else None

    if error_type == "missing":
        return "不能为空"
    if error_type in {"string_too_short", "too_short"}:
        min_length = _constraint_value(ctx, "min_length", "min_length")
        return f"至少 {min_length} 个字符" if min_length is not None else "长度太短"
    if error_type in {"string_too_long", "too_long"}:
        max_length = _constraint_value(ctx, "max_length", "max_length")
        return f"最多 {max_length} 个字符" if max_length is not None else "长度太长"
    if error_type in {"greater_than_equal", "int_parsing", "int_type"}:
        ge = _constraint_value(ctx, "ge")
        if ge is not None:
            return f"不能小于 {ge}"
        return "必须是整数"
    if error_type == "less_than_equal":
        le = _constraint_value(ctx, "le")
        return f"不能大于 {le}" if le is not None else "数值太大"
    if error_type == "greater_than":
        gt = _constraint_value(ctx, "gt")
        return f"必须大于 {gt}" if gt is not None else "数值太小"
    if error_type == "less_than":
        lt = _constraint_value(ctx, "lt")
        return f"必须小于 {lt}" if lt is not None else "数值太大"
    if error_type in {"string_pattern_mismatch", "literal_error"}:
        return "格式不正确"
    if error_type in {"decimal_max_places", "decimal_parsing"}:
        return "金额格式不正确"
    if error_type in {"list_type", "dict_type"}:
        return "格式不正确"

    message = str(error.get("msg") or "").strip()
    if message == "Field required":
        return "不能为空"
    if message.startswith("Value error, "):
        return message.removeprefix("Value error, ")
    if message:
        return "格式不正确"
    return "参数错误"


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "参数校验失败"

    first = errors[0]
    field = _field_label(list(first.get("loc", [])))
    reason = _friendly_validation_reason(first)
    return f"{field}{reason}"


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

    @app.exception_handler(IntegrityError)
    async def integrity_error_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("api.integrity_error path={} message={}", request.url.path, exc)
        return api_json_response(code=status.HTTP_400_BAD_REQUEST, message="数据已存在或不符合唯一性要求，请检查后重试")

    @app.exception_handler(DataError)
    async def data_error_exception_handler(request: Request, exc: DataError) -> JSONResponse:
        logger.warning("api.data_error path={} message={}", request.url.path, exc)
        return api_json_response(code=status.HTTP_400_BAD_REQUEST, message="参数格式不正确，请检查后重试")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        message = str(exc) or "服务器内部错误"
        logger.exception("api.unhandled_exception path={} message={}", request.url.path, message)
        return api_json_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误，请稍后重试")
