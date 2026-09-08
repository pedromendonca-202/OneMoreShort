"""Hacker News public Firebase API source."""
from __future__ import annotations

from datetime import UTC, datetime

from app.trends.base import HTTPTrendSource, TrendSignal, as_float, bounded_limit


class HackerNewsSource(HTTPTrendSource):
    name = "hackernews"
    base_url = "https://hacker-news.firebaseio.com/v0"

    def fetch(self, limit: int) -> list[TrendSignal]:
        try:
            ids = self._get(f"{self.base_url}/topstories.json").json()
            out: list[TrendSignal] = []
            for story_id in ids[: bounded_limit(limit * 3, 150)]:
                item = self._get(f"{self.base_url}/item/{story_id}.json").json()
                if item.get("type") != "story" or item.get("dead") or item.get("deleted") or not item.get("title"):
                    continue
                out.append(TrendSignal(
                    source=self.name, title=str(item["title"]),
                    url=item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id', story_id)}",
                    category="technology", metrics={"score": as_float(item.get("score")), "comments": as_float(item.get("descendants"))},
                    published_at=datetime.fromtimestamp(as_float(item.get("time")), tz=UTC) if item.get("time") else None,
                ))
                if len(out) >= limit:
                    return out
            return out
        except Exception as exc:
            return self._failure(exc, limit=limit)
