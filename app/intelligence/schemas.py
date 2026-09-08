"""Feature vectors and insight records shared by analytics and content intelligence (spec sections 36, 41)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class VideoOutcome(BaseModel):
    production_id: str = ""
    title: str = ""
    topic: str = ""
    category: str = "general"
    hook_type: str = "curiosity"
    narrative_structure: str = ""
    ending_type: str = ""
    loop_used: bool = False
    cta_used: bool = False
    duration_s: float = 0
    scene_count: int = 0
    words: int = 0
    pacing_wps: float = 0
    visual_style: str = ""
    narrator: str = ""
    caption_style: str = ""
    published_at: str | None = None
    # outcomes
    views: float = 0
    views_24h: float = 0
    views_per_hour: float = 0
    retention: float = 0
    completion: float = 0
    engagement: float = 0
    like_rate: float = 0
    share_rate: float = 0
    sub_conversion: float = 0
    drop_offs: list[float] = Field(default_factory=list)

    @property
    def duration_bucket(self) -> str:
        if self.duration_s <= 0:
            return ""
        if self.duration_s < 25:
            return "<25s"
        if self.duration_s < 32:
            return "25-32s"
        return "32-40s"

    @property
    def pacing_bucket(self) -> str:
        if self.pacing_wps <= 0:
            return ""
        if self.pacing_wps < 2.2:
            return "slow"
        if self.pacing_wps <= 2.8:
            return "medium"
        return "fast"


class Insight(BaseModel):
    feature: str
    value: str
    metric: str
    effect_vs_channel: float
    n: int
    confidence: float


class IntelligenceSummary(BaseModel):
    insights: list[Insight] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    best: dict[str, str] = Field(default_factory=dict)
    worst: dict[str, str] = Field(default_factory=dict)
    videos: int = 0


class ABResult(BaseModel):
    dimension: str
    winner: str | None = None
    confidence: float = 0
    variants: dict[str, float] = Field(default_factory=dict)
