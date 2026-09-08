"""Visual detail needed to generate a coherent eight-second video segment."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Segment(BaseModel):
    segment: int = Field(ge=1)
    duration: float = Field(gt=0, le=12)
    purpose: str = Field(min_length=1)
    visual_description: str = Field(min_length=1)
    camera: str = Field(min_length=1)
    lens: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    characters: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    objects: str = Field(min_length=1)
    action: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    dialogue: str | None = None
    sound_design: str = Field(min_length=1)
    transition_to_next: str = Field(min_length=1)
    continuity_state: str = Field(min_length=1)


class Storyboard(BaseModel):
    segments: list[Segment] = Field(min_length=5, max_length=5)
    visual_style: str = Field(min_length=1)
    palette: str = Field(min_length=1)
