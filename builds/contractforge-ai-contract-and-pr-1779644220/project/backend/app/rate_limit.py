from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .config import settings


class _InMemoryLimiter:
    def __init__(self, capacity: int = 60, window: float = 60.0) -> None:
        self.capacity = capacity
        self.window = window
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.capacity:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        bucket.append(now)


_limiter = _InMemoryLimiter()


async def rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "anonymous"
    _limiter.check(key)


RateLimitDep = Annotated[None, Depends(rate_limit)]
