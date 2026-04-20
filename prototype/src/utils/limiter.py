import asyncio
import threading
import time
from typing import Callable


class RateLimiter:
    """Async fixed-window rate limiter for sequential scan loops."""

    def __init__(self, rate_limit: float) -> None:
        if rate_limit <= 0:
            raise ValueError("rate_limit must be greater than 0")

        self.rate_limit = float(rate_limit)
        self._interval = 1.0 / self.rate_limit
        self._lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    async def wait(self) -> None:
        """Wait until the next request slot is available."""
        async with self._lock:
            now = time.monotonic()
            if self._next_allowed_at <= now:
                self._next_allowed_at = now + self._interval
                return

            sleep_for = self._next_allowed_at - now
            self._next_allowed_at += self._interval

        await asyncio.sleep(sleep_for)


class TokenBucketLimiter:
    """Simple token bucket limiter for smoothing outbound request traffic."""

    def __init__(
        self,
        *,
        capacity: float,
        refill_rate: float,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be greater than 0")

        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._tokens = float(capacity)
        self._clock = clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._updated_at = self._clock()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        if tokens <= 0:
            raise ValueError("tokens must be greater than 0")

        while True:
            with self._lock:
                now = self._clock()
                self._refill(now)

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                deficit = tokens - self._tokens
                wait_seconds = deficit / self.refill_rate

            self._sleeper(wait_seconds)

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self._updated_at)
        if elapsed:
            replenished = elapsed * self.refill_rate
            self._tokens = min(self.capacity, self._tokens + replenished)
            self._updated_at = now