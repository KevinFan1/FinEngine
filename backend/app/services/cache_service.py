"""Redis cache service for frequently accessed data."""

import json
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings


class CacheService:
    """Service for caching frequently accessed data in Redis."""

    def __init__(self):
        self.redis: redis.Redis | None = None

    async def init(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info("Cache service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            self.redis = None

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (default 1 hour)."""
        if not self.redis:
            return False

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str):
        """Delete value from cache."""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        if not self.redis:
            return False

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Deleted {len(keys)} keys matching pattern: {pattern}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return False

    # Specific cache methods for common use cases

    async def get_organization(self, org_id: int):
        """Get organization from cache."""
        return await self.get(f"org:{org_id}")

    async def set_organization(self, org_id: int, org_data: dict, ttl: int = 3600):
        """Cache organization data."""
        return await self.set(f"org:{org_id}", org_data, ttl)

    async def invalidate_organization(self, org_id: int):
        """Invalidate organization cache."""
        return await self.delete(f"org:{org_id}")

    async def get_platform(self, platform_id: int):
        """Get platform from cache."""
        return await self.get(f"platform:{platform_id}")

    async def set_platform(self, platform_id: int, platform_data: dict, ttl: int = 3600):
        """Cache platform data."""
        return await self.set(f"platform:{platform_id}", platform_data, ttl)

    async def invalidate_platform(self, platform_id: int):
        """Invalidate platform cache."""
        return await self.delete(f"platform:{platform_id}")

    async def get_category_dict(self, dict_id: int):
        """Get category dictionary from cache."""
        return await self.get(f"category_dict:{dict_id}")

    async def set_category_dict(self, dict_id: int, dict_data: dict, ttl: int = 7200):
        """Cache category dictionary (2 hours TTL)."""
        return await self.set(f"category_dict:{dict_id}", dict_data, ttl)

    async def invalidate_category_dict(self, dict_id: int):
        """Invalidate category dictionary cache."""
        return await self.delete(f"category_dict:{dict_id}")

    async def invalidate_all_category_dicts(self):
        """Invalidate all category dictionary caches."""
        return await self.delete_pattern("category_dict:*")


# Global cache service instance
cache_service = CacheService()
