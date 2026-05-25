"""Loguru logging setup for the backend."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


STANDARD_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}{extra[_serialized_context]}{exception}"
)
EXTRA_CONTEXT_ORDER = (
    "event",
    "request_id",
    "method",
    "path",
    "query",
    "http_status",
    "api_code",
    "api_message",
    "duration_ms",
    "response_bytes",
    "client_ip",
    "referer",
    "user_agent",
    "request_content_type",
    "response_content_type",
    "request_body",
)


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


def _serialize_log_value(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)


def _format_extra_context(extra: dict[str, Any]) -> str:
    if not extra:
        return ""

    context_parts: list[str] = []
    seen: set[str] = set()
    for key in EXTRA_CONTEXT_ORDER:
        if key in extra:
            context_parts.append(f"{key}={_serialize_log_value(extra[key])}")
            seen.add(key)

    for key in sorted(extra):
        if key in seen or key.startswith("_"):
            continue
        context_parts.append(f"{key}={_serialize_log_value(extra[key])}")

    return " ".join(context_parts)


def _structured_log_format(record: dict[str, Any]) -> str:
    serialized_context = _format_extra_context(record["extra"])
    record["extra"]["_serialized_context"] = f" | {serialized_context}" if serialized_context else ""
    return STANDARD_LOG_FORMAT


def setup_logging() -> None:
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        log_dir / "api.log",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION_TIME,
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=_structured_log_format,
    )
    logger.add(
        log_dir / "api_error.log",
        level="ERROR",
        rotation=settings.LOG_ROTATION_TIME,
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=_structured_log_format,
    )
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=_structured_log_format,
        backtrace=False,
        diagnose=False,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
