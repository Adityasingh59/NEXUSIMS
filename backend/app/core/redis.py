"""NEXUS IMS — Redis client for cache (Block 2)."""
from typing import Optional

import redis.asyncio as redis

from app.config import get_settings

_settings = get_settings()
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis connection (application cache DB 1)."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(_settings.REDIS_URL, decode_responses=True)
    return _redis


def stock_cache_key(tenant_id: str, sku_id: str, warehouse_id: str) -> str:
    """Cache key for stock level: stock:{tid}:{sku}:{wh}"""
    return f"stock:{tenant_id}:{sku_id}:{warehouse_id}"


STOCK_CACHE_TTL = 30
