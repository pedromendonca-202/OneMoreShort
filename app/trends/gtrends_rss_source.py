"""Google Trends daily RSS feed (does not require the gated API)."""
from __future__ import annotations

import re

import feedparser

from app.trends.news_rss_source import _rss_date
from app.trends.base import HTTPTrendSource, TrendSignal, bounded_limit


_TRAFFIC_RE = re.compile(r"([\d,.]+)\s*([KMB])?", re.IGNORECASE)
_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_traffic(value: str | None) -> float:
    match = _TRAFFIC_RE.search(value or "")
    if not match:
        return 0.0
    amount = float(match.group(1).replace(",", ""))
    return amount * _MULTIPLIERS.get((match.group(2) or "").upper(), 1)


class GoogleTrendsRSSSource(HTTPTrendSource):
    name = "gtrends_rss"
    endpoint = "https://trends.google.com/trending/rss"

    def __init__(self, *, region: str = "US", timeout_s: float = 20, client=None):
        super().__init__(timeout_s=timeout_s, client=client)
        self.region = region

    def fetch(self, limit: int) -> list[TrendSignal]:
        try:
            feed = feedparser.parse(self._get(self.endpoint, params={"geo": self.region}).content)
            if getattr(feed, "bozo", False) and not feed.entries:
                raise ValueError("malformed Google Trends RSS feed")
            out: list[TrendSignal] = []
            for entry in feed.entries[: bounded_limit(limit)]:
                title = str(entry.get("title") or "").strip()
                if not title:
                    continue
                url = entry.get("ht_news_item_url") or entry.get("link")
                summary = entry.get("ht_news_item_title")
                out.append(TrendSignal(
                    source=self.name, title=title, url=url, summary=str(summary) if summary else None,
                    category="search trend", metrics={"traffic": parse_traffic(entry.get("ht_approx_traffic"))},
                    published_at=_rss_date(entry.get("published")),
                ))
            return out
        except Exception as exc:
            return self._failure(exc, limit=limit)
