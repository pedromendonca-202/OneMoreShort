from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class VideoMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5_000)
    hashtags: list[str] = Field(min_length=3, max_length=6)
    tags: list[str] = Field(default_factory=list)
    category_id: str = Field(default="24", pattern=r"^\d{1,3}$")
    publish_at: datetime | None = None
    pinned_comment: str | None = Field(default=None, max_length=10_000)
    thumbnail_time_s: float = Field(default=1, ge=0)

    @field_validator("hashtags")
    @classmethod
    def shorts_hashtag_and_format(cls, hashtags: list[str]) -> list[str]:
        if "#Shorts" not in hashtags:
            raise ValueError("hashtags must include #Shorts")
        if any(not tag.startswith("#") for tag in hashtags):
            raise ValueError("each hashtag must begin with #")
        return hashtags

    @field_validator("tags")
    @classmethod
    def tags_fit_youtube_limit(cls, tags: list[str]) -> list[str]:
        if sum(len(tag) for tag in tags) + max(0, len(tags) - 1) > 500:
            raise ValueError("tags exceed YouTube's 500-character limit")
        return tags


class PolicyVerdict(BaseModel):
    ok: bool
    flags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
