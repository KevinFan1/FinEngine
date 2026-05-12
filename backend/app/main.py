from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware.api_logging_middleware import ApiLoggingMiddleware
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

register_exception_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API request/response logs
app.add_middleware(ApiLoggingMiddleware)

# Mount API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
