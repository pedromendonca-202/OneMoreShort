"""YouTube Analytics API v2 reports: watch time, retention curve, traffic sources (24 to 48 h latency)."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.core.errors import ExternalAPIError
from app.youtube.errors import map_http_error
from app.youtube.schemas import RetentionPoint

DEEP_METRICS: list[str] = [
    "views", "engagedViews", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
    "likes", "dislikes", "comments", "shares", "subscribersGained", "subscribersLost",
]


def _number(value: Any) -> float | int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(number) if number.is_integer() else number


def _rows(response: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    headers = [str(header.get("name")) for header in response.get("columnHeaders") or []]
    return headers, list(response.get("rows") or [])


class YouTubeAnalyticsAPI:
    def __init__(self, credentials: Any | None = None, service: Any | None = None):
        if service is None:
            from googleapiclient.discovery import build

            service = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
        self.service = service

    def _query(self, **params: Any) -> dict[str, Any]:
        try:
            return self.service.reports().query(**params).execute() or {}
        except ExternalAPIError:
            raise
        except Exception as err:
            raise map_http_error("youtube_analytics", err) from err

    @staticmethod
    def _window(video_id: str, start: date, end: date, **extra: Any) -> dict[str, Any]:
        return {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
                "filters": f"video=={video_id}", **extra}

    def video_metrics(self, video_id: str, start: date, end: date) -> dict[str, float | int]:
        metrics = list(DEEP_METRICS)
        while True:
            try:
                response = self._query(**self._window(video_id, start, end, metrics=",".join(metrics)))
                break
            except ExternalAPIError as err:
                # Some channels/regions reject newer metrics (engagedViews); degrade gracefully once.
                if not err.retryable and "engagedViews" in metrics:
                    metrics.remove("engagedViews")
                    continue
                raise
        headers, rows = _rows(response)
        row = rows[0] if rows else [0] * len(headers)
        return {name: _number(value) for name, value in zip(headers, row)}

    def retention_curve(self, video_id: str, start: date, end: date) -> list[RetentionPoint]:
        response = self._query(**self._window(video_id, start, end, dimensions="elapsedVideoTimeRatio",
                                              metrics="audienceWatchRatio,relativeRetentionPerformance",
                                              sort="elapsedVideoTimeRatio"))
        headers, rows = _rows(response)
        points: list[RetentionPoint] = []
        for row in rows:
            record = dict(zip(headers, row))
            points.append(RetentionPoint(elapsed_ratio=min(1.0, max(0.0, float(record.get("elapsedVideoTimeRatio", 0)))),
                                         watch_ratio=max(0.0, float(record.get("audienceWatchRatio", 0))),
                                         relative=float(record["relativeRetentionPerformance"])
                                         if record.get("relativeRetentionPerformance") is not None else None))
        return points

    def traffic_sources(self, video_id: str, start: date, end: date) -> dict[str, int]:
        response = self._query(**self._window(video_id, start, end, dimensions="insightTrafficSourceType", metrics="views",
                                              sort="-views"))
        headers, rows = _rows(response)
        result: dict[str, int] = {}
        for row in rows:
            record = dict(zip(headers, row))
            result[str(record.get("insightTrafficSourceType"))] = int(_number(record.get("views")))
        return result

    def daily_views(self, video_id: str, start: date, end: date) -> dict[str, int]:
        response = self._query(**self._window(video_id, start, end, dimensions="day", metrics="views", sort="day"))
        headers, rows = _rows(response)
        return {str(dict(zip(headers, row)).get("day")): int(_number(dict(zip(headers, row)).get("views"))) for row in rows}
