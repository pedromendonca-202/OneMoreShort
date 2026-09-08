"""Google News RSS feed."""
from __future__ import annotations

from email.utils import parsedate_to_datetime

import feedparser

from app.trends.base import HTTPTrendSource, TrendSignal, bounded_limit


def _rss_date(value: str | None):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


class GoogleNewsRSSSource(HTTPTrendSource):
    name = "news_rss"
    endpoint = "https://news.google.com/rss"

    def __init__(self, *, region: str = "US", language: str = "en", timeout_s: float = 20, client=None):
        super().__init__(timeout_s=timeout_s, client=client)
        self.region, self.language = region, language

    def fetch(self, limit: int) -> list[TrendSignal]:
        try:
            response = self._get(self.endpoint, params={"hl": f"{self.language}-{self.region}", "gl": self.region, "ceid": f"{self.region}:{self.language}"})
            feed = feedparser.parse(response.content)
            if getattr(feed, "bozo", False) and not feed.entries:
                raise ValueError("malformed Google News RSS feed")
            signals: list[TrendSignal] = []
            for entry in feed.entries[: bounded_limit(limit)]:
                title = str(entry.get("title") or "").strip()
                if not title:
                    continue
                tags = entry.get("tags") or []
                category = str(tags[0].get("term")) if tags else None
                signals.append(TrendSignal(
                    source=self.name, title=title, url=entry.get("link"),
                    summary=str(entry.get("summary") or "")[:2_000] or None,
                    category=category, metrics={}, published_at=_rss_date(entry.get("published")),
                ))
            return signals
        except Exception as exc:
            return self._failure(exc, limit=limit)
