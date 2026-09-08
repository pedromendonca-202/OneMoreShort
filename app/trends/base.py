"""Shared contracts and HTTP safety helpers for trend sources."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.retry import retrying


class TrendSignal(BaseModel):
    """One raw observation from a public or official trend feed."""

    source: str
    title: str
    url: str | None = None
    summary: str | None = None
    category: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class TrendSource(Protocol):
    name: str

    def fetch(self, limit: int) -> list[TrendSignal]: ...


class HTTPTrendSource:
    """Small synchronous HTTP base with bounded retry and failure isolation.

    A source failure must never prevent another source from contributing to
    discovery.  Tests inject an ``httpx.Client`` backed by ``MockTransport``;
    production instances own and reuse a normal client.
    """

    name = "http"

    def __init__(self, *, timeout_s: float = 20, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout_s), follow_redirects=True)
        self._owns_client = client is None
        self._log = get_logger(source=self.name)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _get(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
        @retrying(self.name, max_attempts=3, wait_initial=0.5, wait_max=8, exceptions=(httpx.HTTPError,))
        def request() -> httpx.Response:
            response = self._client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response

        return request()

    def _failure(self, exc: Exception, *, limit: int) -> list[TrendSignal]:
        self._log.warning("trend_source_failed", error=str(exc)[:500], limit=limit)
        return []


def as_float(value: Any, default: float = 0.0) -> float:
    """Turn public API numeric strings into a consistent float metric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_datetime(value: Any) -> datetime | None:
    """Parse the ISO-8601 timestamps commonly returned by JSON APIs."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def bounded_limit(limit: int, maximum: int = 50) -> int:
    return max(1, min(int(limit), maximum))
