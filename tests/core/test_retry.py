import pytest

from app.core.errors import CircuitOpen
from app.core.retry import CircuitBreaker, retrying


class Flaky(Exception):
    pass


def test_retry_eventually_succeeds():
    calls = {"n": 0}

    @retrying("test-api", max_attempts=3, wait_initial=0, wait_max=0, exceptions=(Flaky,))
    def f():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Flaky("boom")
        return "ok"

    assert f() == "ok"
    assert calls["n"] == 3


def test_retry_gives_up():
    @retrying("test-api", max_attempts=2, wait_initial=0, wait_max=0, exceptions=(Flaky,))
    def f():
        raise Flaky("always")

    with pytest.raises(Flaky):
        f()


def test_circuit_breaker_opens_and_resets():
    clock = {"t": 0.0}
    cb = CircuitBreaker("veo", failure_threshold=2, reset_after_s=10, clock=lambda: clock["t"])
    assert cb.allow()
    cb.record_failure()
    cb.record_failure()
    assert not cb.allow()
    with pytest.raises(CircuitOpen):
        cb.guard()
    clock["t"] = 11
    assert cb.allow()  # half-open
    cb.record_success()
    assert cb.state == "closed"
