"""Typed inputs and outputs for evidence-led topic research."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ScoringWeights(BaseModel):
    """Weights for a 0–100 score. Competition and risk are inverse signals."""

    trend_score: float = Field(default=0.20, ge=0)
    viral_potential: float = Field(default=0.20, ge=0)
    us_relevance: float = Field(default=0.12, ge=0)
    competition: float = Field(default=0.08, ge=0)
    shorts_fit: float = Field(default=0.16, ge=0)
    originality: float = Field(default=0.16, ge=0)
    risk: float = Field(default=0.08, ge=0)

    @property
    def total(self) -> float:
        return sum(self.model_dump().values())

    @model_validator(mode="after")
    def has_weight(self):
        if self.total <= 0:
            raise ValueError("at least one scoring weight must be positive")
        return self


class StrategyWeights(BaseModel):
    """Selection policy; later intelligence stages update these values."""

    category_weights: dict[str, float] = Field(default_factory=dict)
    hook_weights: dict[str, float] = Field(default_factory=dict)
    duration_pref: float | None = Field(default=None, ge=0, le=40)
    style_weights: dict[str, float] = Field(default_factory=dict)
    exploration_ratio: float = Field(default=0.30, ge=0, le=1)
    risk_threshold: float = Field(default=60, ge=0, le=100)
    competition_threshold: float = Field(default=85, ge=0, le=100)


class KnowledgeContext(BaseModel):
    """Compact historical guidance injected into scoring and script prompts."""

    best_hooks: list[str] = Field(default_factory=list)
    best_structures: list[str] = Field(default_factory=list)
    failed_patterns: list[str] = Field(default_factory=list)
    successful_prompts: list[str] = Field(default_factory=list)


class TopicScore(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    category: str | None = Field(default=None, max_length=80)
    trend_score: float = Field(ge=0, le=100)
    viral_potential: float = Field(ge=0, le=100)
    us_relevance: float = Field(ge=0, le=100)
    competition: float = Field(ge=0, le=100)
    shorts_fit: float = Field(ge=0, le=100)
    originality: float = Field(ge=0, le=100)
    risk: float = Field(ge=0, le=100)
    final_score: float = Field(default=0, ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)


class Fact(BaseModel):
    text: str = Field(min_length=4, max_length=1_500)
    source: str | None = Field(default=None, max_length=2_000)
    confidence: float = Field(ge=0, le=1)


class Research(BaseModel):
    facts: list[Fact] = Field(min_length=1)
    context: str = Field(min_length=1, max_length=6_000)
    angles: list[str] = Field(min_length=1)
    hooks: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    curiosity_points: list[str] = Field(min_length=1)
    best_40s_approach: str = Field(min_length=1, max_length=2_000)
