"""ORM models. One production (OMS-YYYYMMDD-NNNN) owns every artifact of one Short."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.states import State


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


StateColumn = SAEnum(State, native_enum=False, length=32, values_callable=lambda e: [x.value for x in e])


class Production(TimestampMixin, Base):
    __tablename__ = "productions"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    state: Mapped[State] = mapped_column(StateColumn, default=State.DISCOVERING, nullable=False, index=True)
    previous_state: Mapped[Optional[State]] = mapped_column(StateColumn, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text)
    error_detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    config_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stage_timings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    human_action: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    features: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # content-intelligence feature vector

    topics: Mapped[list["Topic"]] = relationship(back_populates="production", cascade="all, delete-orphan")
    research: Mapped[Optional["Research"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    script: Mapped[Optional["Script"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    storyboard: Mapped[Optional["Storyboard"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    bible: Mapped[Optional["ContinuityBible"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="production", cascade="all, delete-orphan", order_by="Prompt.segment_index")
    segments: Mapped[list["Segment"]] = relationship(back_populates="production", cascade="all, delete-orphan", order_by="Segment.index")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="production", cascade="all, delete-orphan")
    caption: Mapped[Optional["Caption"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    final_video: Mapped[Optional["FinalVideo"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    video_metadata: Mapped[Optional["VideoMetadata"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    upload: Mapped[Optional["Upload"]] = relationship(back_populates="production", uselist=False, cascade="all, delete-orphan")
    snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(back_populates="production", cascade="all, delete-orphan", order_by="AnalyticsSnapshot.captured_at")
    retention_curves: Mapped[list["RetentionCurve"]] = relationship(back_populates="production", cascade="all, delete-orphan")
    reports: Mapped[list["VideoReport"]] = relationship(back_populates="production", cascade="all, delete-orphan")

    @property
    def selected_topic(self) -> Optional["Topic"]:
        return next((t for t in self.topics if t.selected), None)


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    topic: Mapped[str] = mapped_column(String(300))
    category: Mapped[Optional[str]] = mapped_column(String(80))
    trend_score: Mapped[float] = mapped_column(Float, default=0)
    viral_potential: Mapped[float] = mapped_column(Float, default=0)
    us_relevance: Mapped[float] = mapped_column(Float, default=0)
    competition: Mapped[float] = mapped_column(Float, default=0)
    shorts_fit: Mapped[float] = mapped_column(Float, default=0)
    originality: Mapped[float] = mapped_column(Float, default=0)
    risk: Mapped[float] = mapped_column(Float, default=0)
    final_score: Mapped[float] = mapped_column(Float, default=0)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    selection_reason: Mapped[Optional[str]] = mapped_column(Text)
    reasons: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    signals: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="topics")


class TrendSignalRow(Base):
    __tablename__ = "trend_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[Optional[str]] = mapped_column(ForeignKey("productions.id"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(80))
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Optional[Production]] = relationship(Production)


class Research(Base):
    __tablename__ = "research"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    topic: Mapped[str] = mapped_column(String(300))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    sources: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="research")


class Script(Base):
    __tablename__ = "scripts"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    text: Mapped[str] = mapped_column(Text)
    hook_type: Mapped[Optional[str]] = mapped_column(String(40))
    ending_type: Mapped[Optional[str]] = mapped_column(String(40))
    total_words: Mapped[int] = mapped_column(Integer, default=0)
    est_duration_s: Mapped[float] = mapped_column(Float, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="script")


class Storyboard(Base):
    __tablename__ = "storyboards"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    visual_style: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="storyboard")


class ContinuityBible(Base):
    __tablename__ = "continuity_bibles"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="bible")


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    segment_index: Mapped[int] = mapped_column(Integer)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    previous_end_state: Mapped[Optional[str]] = mapped_column(Text)
    first_frame_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="prompts")


class Segment(TimestampMixin, Base):
    __tablename__ = "segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|generating|generated|validated|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    operation_id: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    normalized_path: Mapped[Optional[str]] = mapped_column(Text)
    probe: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    first_frame_path: Mapped[Optional[str]] = mapped_column(Text)
    last_frame_path: Mapped[Optional[str]] = mapped_column(Text)
    observed_end_state: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    continuity_score: Mapped[Optional[float]] = mapped_column(Float)
    continuity_issues: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[Optional[str]] = mapped_column(Text)
    production: Mapped[Production] = relationship(back_populates="segments")


class AudioAsset(Base):
    __tablename__ = "audio_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # narration_beat | narration_full | mix | music | sfx
    beat_index: Mapped[Optional[int]] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    duration_s: Mapped[float] = mapped_column(Float, default=0)
    start_s: Mapped[Optional[float]] = mapped_column(Float)
    words: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    voice: Mapped[Optional[str]] = mapped_column(String(80))
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="audio_assets")


class Caption(Base):
    __tablename__ = "captions"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    ass_path: Mapped[str] = mapped_column(Text)
    words: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    style: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    phrase_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="caption")


class FinalVideo(Base):
    __tablename__ = "final_videos"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    path: Mapped[str] = mapped_column(Text)
    probe: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    quality_report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="final_video")


class VideoMetadata(Base):
    __tablename__ = "video_metadata"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    tags: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    hashtags: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    keywords: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    category_id: Mapped[str] = mapped_column(String(8), default="24")
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pinned_comment: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_time_s: Mapped[Optional[float]] = mapped_column(Float)
    ab_variants: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(back_populates="video_metadata")


class Upload(TimestampMixin, Base):
    __tablename__ = "uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), unique=True)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    url: Mapped[Optional[str]] = mapped_column(Text)
    privacy: Mapped[str] = mapped_column(String(16), default="private")
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending|uploading|uploaded|scheduled|published|failed
    error: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    production: Mapped[Production] = relationship(back_populates="upload")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    youtube_video_id: Mapped[str] = mapped_column(String(32), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    age_minutes: Mapped[int] = mapped_column(Integer)
    schedule_slot_min: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="data_api")  # data_api | analytics_api
    views: Mapped[int] = mapped_column(Integer, default=0)
    engaged_views: Mapped[Optional[int]] = mapped_column(Integer)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    dislikes: Mapped[Optional[int]] = mapped_column(Integer)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[Optional[int]] = mapped_column(Integer)
    subscribers_gained: Mapped[Optional[int]] = mapped_column(Integer)
    subscribers_lost: Mapped[Optional[int]] = mapped_column(Integer)
    watch_time_min: Mapped[Optional[float]] = mapped_column(Float)
    avg_view_duration_s: Mapped[Optional[float]] = mapped_column(Float)
    avg_view_pct: Mapped[Optional[float]] = mapped_column(Float)
    traffic_sources: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    production: Mapped[Production] = relationship(back_populates="snapshots")


class RetentionCurve(Base):
    __tablename__ = "retention_curves"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    youtube_video_id: Mapped[str] = mapped_column(String(32), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    points: Mapped[list[Any]] = mapped_column(JSON)
    analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    production: Mapped[Production] = relationship(back_populates="retention_curves")


class VideoReport(Base):
    __tablename__ = "video_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    markdown: Mapped[str] = mapped_column(Text)
    verdict: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    virality_score: Mapped[Optional[float]] = mapped_column(Float)
    production: Mapped[Production] = relationship(back_populates="reports")


class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    feature: Mapped[str] = mapped_column(String(60), index=True)
    value: Mapped[str] = mapped_column(String(120))
    metric: Mapped[str] = mapped_column(String(60))
    effect: Mapped[float] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)


class StrategyWeightsRow(Base):
    __tablename__ = "strategy_weights"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON)
    exploration_ratio: Mapped[float] = mapped_column(Float)
    based_on_n: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(40), index=True)  # topic|hook|script|structure|prompt|visual_style|ending|failed_experiment|insight
    production_id: Mapped[Optional[str]] = mapped_column(ForeignKey("productions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    score: Mapped[Optional[float]] = mapped_column(Float)
    tags: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    production: Mapped[Optional[Production]] = relationship(Production)


class CostLedger(Base):
    __tablename__ = "cost_ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[Optional[str]] = mapped_column(ForeignKey("productions.id"), index=True, nullable=True)
    api: Mapped[str] = mapped_column(String(40), index=True)
    units: Mapped[float] = mapped_column(Float, default=0)
    unit_cost: Mapped[float] = mapped_column(Float, default=0)
    usd: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[Optional[str]] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    production: Mapped[Optional[Production]] = relationship(Production)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    production_id: Mapped[Optional[str]] = mapped_column(String(24), index=True)
    stage: Mapped[Optional[str]] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    api: Mapped[Optional[str]] = mapped_column(String(40))
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)


class ABAssignment(Base):
    __tablename__ = "ab_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[str] = mapped_column(ForeignKey("productions.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(40))
    variant: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    production: Mapped[Production] = relationship(Production)


class HumanAction(Base):
    __tablename__ = "human_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_id: Mapped[Optional[str]] = mapped_column(ForeignKey("productions.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | resolved
    problem: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    automated: Mapped[str] = mapped_column(Text)
    remains: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    next_step: Mapped[str] = mapped_column(Text)
    production: Mapped[Optional[Production]] = relationship(Production)
