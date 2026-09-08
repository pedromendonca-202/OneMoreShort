"""Request-scoped access to the shared panel context (settings, orchestrator, event bus, jobs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Request

from app.core.config import Settings
from app.web.events import EventBus, JobRunner
from app.web.security import RateLimiter, new_csrf_token


@dataclass
class WebContext:
    settings: Settings
    orchestrator: Any
    bus: EventBus
    jobs: JobRunner
    csrf_token: str = field(default_factory=new_csrf_token)
    limiters: dict[str, RateLimiter] = field(default_factory=lambda: {
        "chat": RateLimiter(20, 60), "analytics": RateLimiter(2, 60), "test_connection": RateLimiter(5, 60),
        "learn": RateLimiter(2, 60),
    })
    clock: Any = None

    def now(self) -> datetime:
        return self.orchestrator.now() if self.clock is None else self.clock()

    def local_now(self) -> datetime:
        return self.now().astimezone(ZoneInfo(self.settings.timezone))

    def limit(self, key: str) -> bool:
        limiter = self.limiters.get(key)
        return True if limiter is None else limiter.check(key)


def get_ctx(request: Request) -> WebContext:
    return request.app.state.ctx
