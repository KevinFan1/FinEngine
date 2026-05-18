"""请求 ID 中间件，用于分布式追踪。"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求添加唯一的请求 ID，用于追踪。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 从请求头获取请求 ID，如果没有则生成新的
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 存储在请求状态中，供处理器访问
        request.state.request_id = request_id

        # 处理请求
        response = await call_next(request)

        # 将请求 ID 添加到响应头
        response.headers["X-Request-ID"] = request_id

        return response
