"""YouTube Data API most-popular videos, normalized as trend signals."""
from __future__ import annotations

from typing import Any

from app.trends.base import HTTPTrendSource, TrendSignal, as_float, bounded_limit, parse_datetime


_CATEGORY_NAMES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals",
    "17": "Sports", "20": "Gaming", "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style", "27": "Education", "28": "Science & Technology",
}


class YouTubeTrendSource(HTTPTrendSource):
    name = "youtube"
    endpoint = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, api_key: str | None, *, region: str = "US", categories: list[str] | None = None, timeout_s: float = 20, client=None):
        super().__init__(timeout_s=timeout_s, client=client)
        self.api_key = api_key
        self.region = region
        self.categories = categories or ["0"]

    def fetch(self, limit: int) -> list[TrendSignal]:
        if not self.api_key:
            self._log.info("trend_source_skipped", reason="youtube_api_key_missing")
            return []
        try:
            # Category 0 means the official all-category most-popular feed.
            per_category = max(1, bounded_limit(limit) // max(1, len(self.categories)))
            out: list[TrendSignal] = []
            seen: set[str] = set()
            for category in self.categories:
                params: dict[str, Any] = {
                    "key": self.api_key,
                    "part": "snippet,statistics",
                    "chart": "mostPopular",
                    "regionCode": self.region,
                    "maxResults": per_category,
                }
                if category and category != "0":
                    params["videoCategoryId"] = category
                for item in self._get(self.endpoint, params=params).json().get("items", []):
                    video_id = str(item.get("id") or "")
                    snippet = item.get("snippet") or {}
                    if not video_id or not snippet.get("title") or video_id in seen:
                        continue
                    seen.add(video_id)
                    stats = item.get("statistics") or {}
                    category_id = str(snippet.get("categoryId") or category)
                    out.append(TrendSignal(
                        source=self.name,
                        title=str(snippet["title"]),
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        summary=(str(snippet["description"]) or None) if snippet.get("description") else None,
                        category=_CATEGORY_NAMES.get(category_id, category_id or None),
                        metrics={
                            "views": as_float(stats.get("viewCount")),
                            "likes": as_float(stats.get("likeCount")),
                            "comments": as_float(stats.get("commentCount")),
                        },
                        published_at=parse_datetime(snippet.get("publishedAt")),
                    ))
                    if len(out) >= limit:
                        return out
            return out
        except Exception as exc:
            return self._failure(exc, limit=limit)
