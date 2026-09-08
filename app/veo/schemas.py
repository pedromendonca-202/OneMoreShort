"""Contracts for Veo generation and the persisted chain of segments."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.editing.probe import MediaInfo


class BrandStyle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = "OneMoreShort"
    visual_style: str = "bold, cinematic, high-contrast"
    palette: str = "deep black, vivid red, crisp white"
    narrator_persona: str = "confident American narrator"
    audience: str = "United States, mobile-first viewers"


class VeoPrompt(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    segment: int = Field(ge=1, le=5)
    prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)
    first_frame: Path | None = None
    previous_end_state: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class VeoResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    operation_id: str
    seconds: float
    cost_usd: float
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class VeoClient(Protocol):
    name: str

    def generate(self, prompt: VeoPrompt, out_path: Path) -> VeoResult: ...


class ValidationReport(BaseModel):
    ok: bool
    issues: list[str] = Field(default_factory=list)
    media: MediaInfo | None = None


class SegmentRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int
    status: str
    path: Path
    first_frame_path: Path | None = None
    last_frame_path: Path | None = None
    operation_id: str | None = None
    cost_usd: float = 0
    continuity_score: float | None = None


class ContinuityScore(BaseModel):
    # A missing score is never a reason to reject an otherwise valid mock
    # boundary. Live callers still ask the model for an explicit assessment.
    score: float = Field(default=1.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
