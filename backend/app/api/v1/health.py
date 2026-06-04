"""服务健康检查接口。"""

from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.database import async_session_factory
from app.schemas.common import ApiResponse
from app.services.captcha_service import captcha_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """执行基础健康检查。"""
    return ApiResponse(data={"status": "ok", "service": "finengine"})


@router.get("/health/detailed", response_model=ApiResponse)
async def detailed_health_check():
    """执行包含依赖状态的详细健康检查。"""
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
        redis_client = captcha_service._redis_client()
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
    """执行就绪检查，确认服务是否可对外提供流量。"""
    try:
        # Check database
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

        # Check Redis
        redis_client = captcha_service._redis_client()
        await redis_client.ping()

        return ApiResponse(data={"status": "ready"})
    except Exception:
        return ApiResponse(code=status.HTTP_503_SERVICE_UNAVAILABLE, message="not_ready", data={"status": "not_ready"})


@router.get("/health/liveness")
async def liveness_check():
    """执行存活检查，确认服务进程仍然可用。"""
    # Simple check - if this endpoint responds, the service is alive
    return ApiResponse(data={"status": "alive"})
