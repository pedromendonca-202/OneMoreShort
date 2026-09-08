"""Data API and Analytics API adapters parse Google's response shapes without any network."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.errors import ExternalAPIError, RateLimited
from app.youtube.analytics_api import YouTubeAnalyticsAPI
from app.youtube.data_api import YouTubeDataAPI


class _Exec:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error

    def execute(self):
        if self.error:
            raise self.error
        return self.payload


class FakeDataService:
    def __init__(self, payload):
        self.payload, self.calls = payload, []

    def videos(self):
        return self

    def list(self, **params):
        self.calls.append(params)
        return _Exec(self.payload)


class FakeAnalyticsService:
    """Routes by requested metrics/dimensions; records every query."""

    def __init__(self, responses: dict[str, dict], errors: dict[str, Exception] | None = None):
        self.responses, self.errors, self.calls = responses, errors or {}, []

    def reports(self):
        return self

    def query(self, **params):
        self.calls.append(params)
        key = params.get("dimensions") or "metrics"
        if key in self.errors:
            return _Exec(error=self.errors.pop(key))
        return _Exec(self.responses[key])


def _http_error(status: int, reason: str = "backendError"):
    from googleapiclient.errors import HttpError
    import httplib2

    resp = httplib2.Response({"status": status, "reason": reason})
    return HttpError(resp, f'{{"error": {{"errors": [{{"reason": "{reason}"}}], "message": "{reason}"}}}}'.encode())


def test_data_api_parses_statistics_and_batches_ids():
    service = FakeDataService({"items": [
        {"id": "abc", "statistics": {"viewCount": "1200", "likeCount": "45", "commentCount": "7"}},
        {"id": "def", "statistics": {"viewCount": "10"}},
    ]})
    api = YouTubeDataAPI(service=service)
    stats = {s.video_id: s for s in api.video_stats(["abc", "def"])}
    assert stats["abc"].views == 1200 and stats["abc"].likes == 45 and stats["abc"].comments == 7
    assert stats["def"].views == 10 and stats["def"].likes == 0
    assert service.calls[0]["id"] == "abc,def" and "statistics" in service.calls[0]["part"]


def test_data_api_quota_error_is_rate_limited():
    class Boom(FakeDataService):
        def list(self, **params):
            return _Exec(error=_http_error(403, "quotaExceeded"))

    with pytest.raises(RateLimited):
        YouTubeDataAPI(service=Boom({})).video_stats(["abc"])


def test_analytics_api_video_metrics_maps_column_headers():
    service = FakeAnalyticsService({"metrics": {
        "columnHeaders": [{"name": n} for n in ["views", "engagedViews", "estimatedMinutesWatched", "averageViewDuration",
                                                 "averageViewPercentage", "likes", "dislikes", "comments", "shares",
                                                 "subscribersGained", "subscribersLost"]],
        "rows": [[5000, 4100, 2500.5, 30.2, 75.5, 300, 4, 25, 60, 40, 2]],
    }})
    api = YouTubeAnalyticsAPI(service=service)
    metrics = api.video_metrics("abc", date(2026, 9, 1), date(2026, 9, 8))
    assert metrics["views"] == 5000 and metrics["engagedViews"] == 4100
    assert metrics["averageViewPercentage"] == 75.5 and metrics["subscribersLost"] == 2
    assert service.calls[0]["filters"] == "video==abc" and service.calls[0]["ids"] == "channel==MINE"


def test_analytics_api_retries_without_engaged_views_when_unsupported():
    bad = _http_error(400, "badRequest")
    service = FakeAnalyticsService({"metrics": {"columnHeaders": [{"name": "views"}, {"name": "likes"}], "rows": [[10, 1]]}},
                                   errors={"metrics": bad})
    metrics = YouTubeAnalyticsAPI(service=service).video_metrics("abc", date(2026, 9, 1), date(2026, 9, 8))
    assert metrics["views"] == 10 and "engagedViews" not in metrics
    assert "engagedViews" not in service.calls[-1]["metrics"]


def test_analytics_api_retention_and_traffic():
    service = FakeAnalyticsService({
        "elapsedVideoTimeRatio": {"columnHeaders": [{"name": "elapsedVideoTimeRatio"}, {"name": "audienceWatchRatio"},
                                                    {"name": "relativeRetentionPerformance"}],
                                  "rows": [[0.0, 1.0, 0.5], [0.5, 0.7, 0.6], [1.0, 0.4, 0.4]]},
        "insightTrafficSourceType": {"columnHeaders": [{"name": "insightTrafficSourceType"}, {"name": "views"}],
                                     "rows": [["SHORTS", 900], ["SUBSCRIBER", 100]]},
    })
    api = YouTubeAnalyticsAPI(service=service)
    curve = api.retention_curve("abc", date(2026, 9, 1), date(2026, 9, 8))
    assert [p.elapsed_ratio for p in curve] == [0.0, 0.5, 1.0] and curve[1].watch_ratio == 0.7
    traffic = api.traffic_sources("abc", date(2026, 9, 1), date(2026, 9, 8))
    assert traffic == {"SHORTS": 900, "SUBSCRIBER": 100}


def test_analytics_api_maps_server_errors_to_external_api_error():
    service = FakeAnalyticsService({}, errors={"metrics": _http_error(503, "backendError")})
    with pytest.raises(ExternalAPIError):
        YouTubeAnalyticsAPI(service=service).video_metrics("abc", date(2026, 9, 1), date(2026, 9, 8))
