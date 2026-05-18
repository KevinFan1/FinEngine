"""Middleware for collecting HTTP metrics."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import http_request_duration_seconds, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract endpoint (remove query params and IDs)
        endpoint = self._normalize_endpoint(request.url.path)

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """Normalize endpoint path by removing IDs."""
        parts = path.split("/")
        normalized = []
        for part in parts:
            # Replace numeric IDs with placeholder
            if part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)
