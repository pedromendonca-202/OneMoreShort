from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.metadata.schemas import VideoMetadata


class UploadResult(BaseModel):
    video_id: str
    status: str
    url: str | None = None


class VideoStats(BaseModel):
    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    subscribers_gained: int = 0


class RetentionPoint(BaseModel):
    elapsed_ratio: float = Field(ge=0, le=1)
    watch_ratio: float = Field(ge=0)
    relative: float | None = None


@runtime_checkable
class YouTubeClient(Protocol):
    def upload(self, video, metadata: VideoMetadata, privacy: str, publish_at: datetime | None) -> UploadResult: ...
    def video_stats(self, ids: list[str], age_minutes: int = 0) -> list[VideoStats]: ...
