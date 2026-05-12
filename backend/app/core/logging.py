"""Loguru logging setup for the backend."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    """Forward stdlib logging records to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | {message}",
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        log_dir / "api.log",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION_TIME,
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        serialize=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
