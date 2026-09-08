"""Wikimedia's previous-day most-viewed English Wikipedia pages."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Callable
from urllib.parse import quote

from app.trends.base import HTTPTrendSource, TrendSignal, as_float, bounded_limit


class WikipediaTopViewedSource(HTTPTrendSource):
    name = "wikipedia"
    endpoint = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access"

    def __init__(self, *, today: Callable[[], date] | None = None, timeout_s: float = 20, client=None):
        super().__init__(timeout_s=timeout_s, client=client)
        self._today = today or (lambda: datetime.now(UTC).date())

    def fetch(self, limit: int) -> list[TrendSignal]:
        try:
            day = self._today() - timedelta(days=1)
            payload = self._get(f"{self.endpoint}/{day:%Y}/{day:%m}/{day:%d}").json()
            articles = ((payload.get("items") or [{}])[0].get("articles") or [])
            out: list[TrendSignal] = []
            for article in articles:
                title = str(article.get("article") or "")
                if not title or title in {"Main_Page", "Special:Search"}:
                    continue
                out.append(TrendSignal(
                    source=self.name, title=title.replace("_", " "),
                    url=f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}", category="reference",
                    metrics={"views": as_float(article.get("views")), "rank": as_float(article.get("rank"))},
                    published_at=datetime(day.year, day.month, day.day, tzinfo=UTC),
                ))
                if len(out) >= limit:
                    return out
            return out
        except Exception as exc:
            return self._failure(exc, limit=limit)
