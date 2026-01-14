"""
Redis-based rate limiter using sliding window algorithm.
"""
import time
from typing import Optional
import redis.asyncio as redis
from app.config import settings


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    
    Features:
    - Per-key rate limiting
    - Configurable limits and windows
    - Returns remaining quota
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_rate_limit(
        self,
        key_id: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            key_id: Unique identifier for the API key
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            tuple: (allowed, remaining, reset_at)
            - allowed: True if request is allowed
            - remaining: Number of requests remaining
            - reset_at: Unix timestamp when limit resets
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key_id}"
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries outside window
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count requests in current window
        pipe.zcard(redis_key)
        
        # Add current request with timestamp as score
        pipe.zadd(redis_key, {f"{now}": now})
        
        # Set expiry on key
        pipe.expire(redis_key, window_seconds)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        # Calculate remaining and reset time
        remaining = max(0, max_requests - current_count - 1)
        reset_at = int(now + window_seconds)
        
        # Check if allowed
        allowed = current_count < max_requests
        
        if not allowed:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(redis_key, f"{now}")
            remaining = 0
        
        return allowed, remaining, reset_at
    
    async def get_usage(self, key_id: str, window_seconds: int) -> int:
        """Get current usage count for a key."""
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key_id}"
        
        # Count requests in current window
        count = await self.redis.zcount(redis_key, window_start, now)
        return count


class UsageLimiter:
    """
    Manages usage limits with optional refill.
    
    Unlike rate limiting, this tracks total uses across all time,
    with optional periodic refill.
    """
    
    @staticmethod
    async def check_and_decrement(
        key_id: str,
        remaining: Optional[int],
        max_uses: Optional[int]
    ) -> tuple[bool, Optional[int]]:
        """
        Check if key has remaining uses and decrement.
        
        Returns:
            tuple: (allowed, new_remaining)
        """
        # If no limit set, always allow
        if remaining is None:
            return True, None
        
        # Check if uses remaining
        if remaining <= 0:
            return False, 0
        
        # Decrement and return
        return True, remaining - 1
