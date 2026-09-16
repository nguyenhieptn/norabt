"""Shared token bucket for the OKX `copytrading` request budget.

OKX caps this endpoint group at 5 requests / 2 seconds per source IP. 30 bots
polled once each already spends the whole budget for a round (plus more for
any bot whose positions just closed, since that costs a second request), so
every caller -- current call, and any future one -- has to draw from the same
bucket or the process as a whole can blow through the limit even though each
individual call site looks fine in isolation. Hence a single object that is
constructed once and passed around, not one bucket per bot.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

# OKX's own documented limit for the copytrading group. Decided once, from
# outside this module -- see the task's architecture notes -- and must not
# drift out of sync with what OKX actually enforces.
DEFAULT_CAPACITY = 5
DEFAULT_PERIOD_SECONDS = 2.0


class TokenBucket:
    """Classic continuous-refill token bucket, safe to share across threads.

    Refill is computed lazily from elapsed wall-clock time on every call
    instead of a background timer thread, so there is nothing to start, stop,
    or leak -- the bucket is exactly as fresh as of the last time anyone
    touched it, which is all `acquire`/`try_acquire` ever need.
    """

    def __init__(
        self,
        capacity: float = DEFAULT_CAPACITY,
        period_seconds: float = DEFAULT_PERIOD_SECONDS,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity phải > 0")
        if period_seconds <= 0:
            raise ValueError("period_seconds phải > 0")
        self.capacity = float(capacity)
        self.period_seconds = float(period_seconds)
        # Injectable so a test can drive the bucket with a fake clock/sleep
        # instead of burning real wall-clock time to prove blocking works.
        self._clock = clock
        self._sleep = sleep
        self._tokens = float(capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    @property
    def _refill_rate(self) -> float:
        return self.capacity / self.period_seconds

    def _refill_locked(self) -> None:
        # Caller already holds self._lock; split out only for readability.
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Non-blocking: take `tokens` now if available, else leave the bucket alone."""
        with self._lock:
            self._refill_locked()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0) -> None:
        """Block (via the injected sleep) until `tokens` are available, then take them.

        Loops instead of computing one sleep and trusting it: another thread
        can drain the bucket between this thread computing its wait and it
        actually waking up, since the lock is released during the sleep.
        """
        while True:
            with self._lock:
                self._refill_locked()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait_seconds = deficit / self._refill_rate
            # Sleep happens outside the lock so other threads can still poll
            # or refill while this one waits.
            self._sleep(max(wait_seconds, 0.0))
