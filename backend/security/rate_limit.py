from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return RateLimitDecision(allowed=False, retry_after=retry_after)
        bucket.append(now)
        return RateLimitDecision(allowed=True, retry_after=0)


rate_limiter = InMemoryRateLimiter()
