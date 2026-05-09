import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("finengine.access")


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests with timing info."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            "%s %s → %d (%.1fms) [%s]",
            method,
            path,
            status_code,
            elapsed_ms,
            client_host,
        )

        return response
