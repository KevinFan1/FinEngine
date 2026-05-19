from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.metrics import get_metrics
from app.core.rate_limit import limiter
from app.middleware.api_logging_middleware import ApiLoggingMiddleware
from app.middleware.crypto_middleware import ApiCryptoMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_id_middleware import RequestIDMiddleware
from app.services.auth_service import AuthService

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create default superadmin if not exists
    logger.info("FinEngine starting up...")
    async with async_session_factory() as session:
        await AuthService.create_default_superadmin(session, password=settings.SUPERADMIN_INIT_PASSWORD)
        await session.commit()
    logger.info("Default superadmin ready.")
    yield
    # Shutdown
    logger.info("FinEngine shutting down.")


app = FastAPI(
    title="FinEngine — 财务数据处理系统",
    version="0.1.0",
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Encrypted-Response", "X-Request-ID"],
)

# Request ID tracking for distributed tracing
app.add_middleware(RequestIDMiddleware)

# Metrics collection (optional, can be disabled in production if not needed)
app.add_middleware(MetricsMiddleware)

# API request/response logs
app.add_middleware(ApiLoggingMiddleware)

# Optional encrypted transport for frontend API payloads
app.add_middleware(ApiCryptoMiddleware)

# Mount API router
app.include_router(api_router, prefix="/api/v1")


# Keep legacy /health endpoint for backward compatibility
@app.get("/health")
async def health():
    return {"status": "ok"}


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return Response(content=get_metrics(), media_type="text/plain")
