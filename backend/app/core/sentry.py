"""Sentry error tracking integration."""

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings


def init_sentry():
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Send default PII (Personally Identifiable Information)
        send_default_pii=False,
        # Attach stack traces to messages
        attach_stacktrace=True,
        # Release version (use git commit hash in production)
        release="finengine@0.1.0",
        # Before send hook to filter sensitive data
        before_send=before_send_hook,
    )
    logger.info(f"Sentry initialized for environment: {settings.SENTRY_ENVIRONMENT}")


def before_send_hook(event, hint):
    """Filter sensitive data before sending to Sentry."""
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-crypto-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    # Remove sensitive query parameters
    if "request" in event and "query_string" in event["request"]:
        # Filter password, token, etc.
        pass

    return event
