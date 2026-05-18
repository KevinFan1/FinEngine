"""Rate limiting middleware and utilities."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
    default_limits=["200/minute"],  # Default: 200 requests per minute
)


def get_limiter():
    """Dependency to get the rate limiter instance."""
    return limiter
