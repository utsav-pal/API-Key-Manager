"""
Redis connection management.
"""
import redis.asyncio as redis
from app.config import settings

# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)


async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    return redis.Redis(connection_pool=redis_pool)


async def close_redis():
    """Close Redis connection pool."""
    await redis_pool.disconnect()
