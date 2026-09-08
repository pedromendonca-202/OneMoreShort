"""No-network YouTube adapter for pipeline and analytics tests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.metadata.schemas import VideoMetadata
from app.youtube.schemas import RetentionPoint, UploadResult, VideoStats


class MockYouTubeClient:
    def __init__(self):
        self.uploads: dict[str, VideoMetadata] = {}

    def upload(self, video: Path | str, metadata: VideoMetadata, privacy: str, publish_at: datetime | None) -> UploadResult:
        video_id = f"mock-{len(self.uploads) + 1:06d}"
        self.uploads[video_id] = metadata
        return UploadResult(video_id=video_id, status="scheduled" if publish_at else "uploaded",
                            url=f"https://www.youtube.com/watch?v={video_id}")

    def video_stats(self, ids: list[str], age_minutes: int = 0) -> list[VideoStats]:
        scale = max(1, age_minutes + 1)
        return [VideoStats(video_id=video_id, views=scale * 17, likes=scale // 6, comments=scale // 25,
                           shares=scale // 40, subscribers_gained=scale // 80) for video_id in ids]

    def retention_curve(self, video_id: str) -> list[RetentionPoint]:
        return [RetentionPoint(elapsed_ratio=i / 10, watch_ratio=max(.25, 1 - i * .07), relative=1.0) for i in range(11)]

    def post_comment(self, video_id: str, text: str) -> str:
        return f"comment-{video_id}"


class MockAnalyticsClient:
    """Deterministic stand-in for the YouTube Analytics API (deep metrics after 48 h)."""

    def video_metrics(self, video_id: str, start, end) -> dict:
        seed = sum(ord(ch) for ch in video_id) % 7
        views = 4000 + seed * 500
        return {"views": views, "engagedViews": int(views * 0.82), "estimatedMinutesWatched": round(views * 0.5, 1),
                "averageViewDuration": 29.5 + seed * 0.5, "averageViewPercentage": 74.0 + seed, "likes": views // 12,
                "dislikes": seed, "comments": views // 90, "shares": views // 45, "subscribersGained": views // 70,
                "subscribersLost": seed}

    def retention_curve(self, video_id: str, start, end) -> list[RetentionPoint]:
        return [RetentionPoint(elapsed_ratio=i / 10, watch_ratio=max(.3, 1 - i * .06 - (.12 if i == 3 else 0)), relative=1.0)
                for i in range(11)]

    def traffic_sources(self, video_id: str, start, end) -> dict[str, int]:
        return {"SHORTS": 3600, "SUBSCRIBER": 300, "EXTERNAL": 100}
