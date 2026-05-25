"""Per-target rate limiting (architecture §11.2)."""
import asyncio
import time


class TargetRateLimiter:
    """Token-bucket style limiter: max requests per second per target."""

    def __init__(self, requests_per_second: float = 10.0):
        self.interval = 1.0 / max(requests_per_second, 0.1)
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, target_key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            last = self._last.get(target_key, 0.0)
            wait = self.interval - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[target_key] = time.monotonic()
