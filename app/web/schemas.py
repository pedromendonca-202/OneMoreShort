"""Request bodies accepted by the panel API. Every mutating endpoint validates through one of these."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NewProduction(BaseModel):
    force: bool = False
    prepare: bool = True


class Confirm(BaseModel):
    confirm: bool = False


class MetadataEdit(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    hashtags: list[str] = Field(default_factory=list, max_length=6)
    visibility: Literal["private", "unlisted", "public", "scheduled"] = "private"
    publish_hour_local: int | None = Field(default=None, ge=0, le=23)


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class TestConnection(BaseModel):
    api_key: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=80)


class AISettings(BaseModel):
    api_key: str | None = Field(default=None, max_length=200)  # write-only; None keeps the saved key
    model: str | None = Field(default=None, max_length=80)
    clear_key: bool = False


class PublishSettings(BaseModel):
    visibility: Literal["private", "unlisted", "public", "scheduled"] | None = None
    publish_hour_local: int | None = Field(default=None, ge=0, le=23)
    title_suffix: str | None = Field(default=None, max_length=40)
    description_template: str | None = Field(default=None, max_length=2000)
    default_hashtags: str | None = Field(default=None, max_length=300)
    auto_publish: bool | None = None


class BrandSettings(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    tone: str | None = Field(default=None, max_length=80)
    cta: str | None = Field(default=None, max_length=120)
    watermark: str | None = Field(default=None, max_length=60)
    use_brand_identity: bool | None = None


class RulesSettings(BaseModel):
    target_duration_s: int | None = Field(default=None, ge=15, le=60)
    scenes: int | None = Field(default=None, ge=3, le=10)
    cost_limit_usd: float | None = Field(default=None, ge=0.01, le=1.0)
    safety_moderation: bool | None = None
    avoid_sensitive: bool | None = None
    auto_captions: bool | None = None


class FilesSettings(BaseModel):
    inbox_dir: str | None = Field(default=None, max_length=500)
    ffmpeg_binary: str | None = Field(default=None, max_length=500)
    exports_dir: str | None = Field(default=None, max_length=500)


class SettingsUpdate(BaseModel):
    ai: AISettings | None = None
    publish: PublishSettings | None = None
    brand: BrandSettings | None = None
    rules: RulesSettings | None = None
    files: FilesSettings | None = None


class OpenFolder(BaseModel):
    key: Literal["project", "inbox", "ffmpeg", "exports"]
