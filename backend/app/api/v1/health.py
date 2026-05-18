"""Health check endpoints for monitoring."""

from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.database import async_session_factory
from app.schemas.common import ApiResponse
from app.services.captcha_service import captcha_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check - returns 200 if service is running."""
    return ApiResponse(data={"status": "ok", "service": "finengine"})


@router.get("/health/detailed", response_model=ApiResponse)
async def detailed_health_check():
    """Detailed health check - checks all dependencies."""
    checks = {
        "api": "ok",
        "database": "unknown",
        "redis": "unknown",
    }
    overall_status = "healthy"

    # Check database connection
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        overall_status = "unhealthy"

    # Check Redis connection
    try:
        redis_client = captcha_service.redis
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        overall_status = "unhealthy"

    response_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return ApiResponse(
        code=response_code,
        message=overall_status,
        data=checks,
    )


@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe - checks if service can accept traffic."""
    try:
        # Check database
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

        # Check Redis
        redis_client = captcha_service.redis
        await redis_client.ping()

        return ApiResponse(data={"status": "ready"})
    except Exception:
        return ApiResponse(code=status.HTTP_503_SERVICE_UNAVAILABLE, message="not_ready", data={"status": "not_ready"})


@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe - checks if service is alive."""
    # Simple check - if this endpoint responds, the service is alive
    return ApiResponse(data={"status": "alive"})
