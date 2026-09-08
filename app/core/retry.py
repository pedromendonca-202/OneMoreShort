"""Retry with exponential backoff + jitter, and a per-API circuit breaker."""
from __future__ import annotations

import time
from functools import wraps
from typing import Callable, Iterable, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.core.errors import CircuitOpen
from app.core.logging import get_logger

T = TypeVar("T")


def retrying(
    api: str,
    max_attempts: int = 5,
    wait_initial: float = 1.0,
    wait_max: float = 30.0,
    exceptions: Iterable[type[BaseException]] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    exc_tuple = tuple(exceptions)
    log = get_logger(api=api)

    def _before_sleep(retry_state) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        log.warning("retrying", attempt=retry_state.attempt_number, error=repr(exc), sleep_s=round(retry_state.next_action.sleep, 2) if retry_state.next_action else None)

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        wrapped = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(initial=wait_initial, max=wait_max),
            retry=retry_if_exception_type(exc_tuple),
            reraise=True,
            before_sleep=_before_sleep,
        )(fn)

        @wraps(fn)
        def inner(*args, **kwargs):
            return wrapped(*args, **kwargs)

        return inner

    return decorator


class CircuitBreaker:
    """closed → (failures ≥ threshold) → open → (reset_after_s) → half_open → success → closed / failure → open."""

    def __init__(self, api: str, failure_threshold: int = 5, reset_after_s: float = 120.0, clock: Callable[[], float] = time.monotonic):
        self.api = api
        self.failure_threshold = failure_threshold
        self.reset_after_s = reset_after_s
        self._clock = clock
        self.failures = 0
        self.state = "closed"
        self.opened_at: float | None = None
        self._log = get_logger(api=api)

    def allow(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.opened_at is not None and self._clock() - self.opened_at >= self.reset_after_s:
                self.state = "half_open"
                return True
            return False
        return True  # half_open: allow one probe

    def guard(self) -> None:
        if not self.allow():
            raise CircuitOpen(f"circuit open for {self.api}; retry after {self.reset_after_s}s")

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = self._clock()
            self._log.error("circuit_opened", failures=self.failures)

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        self.guard()
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result
