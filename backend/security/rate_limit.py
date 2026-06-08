from __future__ import annotations

import time
from dataclasses import dataclass

from core.redis import redis_client


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int


class RedisRateLimiter:
    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        pipe.zadd(key, {str(now_ms): now_ms})
        pipe.zcard(key)
        pipe.expire(key, window_seconds + 1)
        _, _, count, _ = pipe.execute()
        if count > limit:
            return RateLimitDecision(allowed=False, retry_after=window_seconds)
        return RateLimitDecision(allowed=True, retry_after=0)


rate_limiter = RedisRateLimiter()
