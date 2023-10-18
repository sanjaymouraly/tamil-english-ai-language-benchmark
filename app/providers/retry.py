"""Bounded retries with exponential backoff and jitter."""

from __future__ import annotations

import random
import time

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class RetryPolicy:
    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0
    ) -> None:
        self.max_retries = max(0, max_retries)
        self.base_delay = base_delay
        self.max_delay = max_delay

    def sleep_for(self, attempt: int) -> float:
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        return delay * (0.5 + random.random())  # jitter


def retry_call(fn, *, policy: RetryPolicy | None = None, on_retry=None):
    """Call fn(); retry on transient errors with backoff.

    `fn` may raise ProviderError with a status_code; only retryable
    failures are retried. Other errors propagate immediately.
    """
    from app.core.errors import ProviderError

    policy = policy or RetryPolicy()
    attempt = 0
    while True:
        try:
            return fn()
        except ProviderError as exc:
            if exc.status_code is not None and exc.status_code not in RETRYABLE_STATUS:
                raise
            if attempt >= policy.max_retries:
                raise
            delay = policy.sleep_for(attempt)
            if on_retry:
                on_retry(attempt, delay, exc)
            time.sleep(delay)
            attempt += 1
        except (TimeoutError, ConnectionError) as exc:
            if attempt >= policy.max_retries:
                raise ProviderError(f"connection failed after retries: {exc}") from exc
            delay = policy.sleep_for(attempt)
            if on_retry:
                on_retry(attempt, delay, exc)
            time.sleep(delay)
            attempt += 1
