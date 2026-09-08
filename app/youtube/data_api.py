"""YouTube Data API v3 read side: near-real-time counters (1 quota unit per call, free tier)."""
from __future__ import annotations

from typing import Any, Iterable

from app.youtube.errors import map_http_error
from app.youtube.schemas import VideoStats
from app.youtube.uploader import GoogleYouTubeClient

__all__ = ["GoogleYouTubeClient", "YouTubeDataAPI"]


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class YouTubeDataAPI:
    def __init__(self, credentials: Any | None = None, api_key: str | None = None, service: Any | None = None):
        if service is None:
            from googleapiclient.discovery import build

            service = build("youtube", "v3", credentials=credentials, developerKey=api_key, cache_discovery=False)
        self.service = service

    def video_stats(self, ids: list[str], age_minutes: int = 0) -> list[VideoStats]:
        """`age_minutes` is accepted for protocol compatibility with the mock client and ignored here."""
        results: list[VideoStats] = []
        for chunk in _chunks(list(ids), 50):
            try:
                response = self.service.videos().list(part="statistics,contentDetails", id=",".join(chunk)).execute()
            except Exception as err:  # googleapiclient.errors.HttpError and transport failures
                raise map_http_error("youtube_data", err) from err
            for item in response.get("items", []):
                stats = item.get("statistics") or {}
                results.append(VideoStats(video_id=item["id"], views=_int(stats.get("viewCount")), likes=_int(stats.get("likeCount")),
                                          comments=_int(stats.get("commentCount")), shares=0, subscribers_gained=0))
        return results

    def channel_id(self) -> str | None:
        try:
            response = self.service.channels().list(part="id", mine=True).execute()
        except Exception as err:
            raise map_http_error("youtube_data", err) from err
        items = response.get("items") or []
        return items[0]["id"] if items else None
