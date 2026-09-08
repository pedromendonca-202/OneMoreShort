"""The promptable source of truth for visual and audio continuity."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ContinuityBible(BaseModel):
    characters: str = Field(min_length=1)
    appearance: str = Field(min_length=1)
    clothing: str = Field(min_length=1)
    hair: str = Field(min_length=1)
    accessories: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    color_palette: str = Field(min_length=1)
    camera: str = Field(min_length=1)
    lens: str = Field(min_length=1)
    camera_movement: str = Field(min_length=1)
    objects: str = Field(min_length=1)
    object_positions: str = Field(min_length=1)
    actions: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    narrator: str = Field(min_length=1)
    accent: str = Field(min_length=1)
    audio_style: str = Field(min_length=1)
    visual_style: str = Field(min_length=1)
    temporal_state: str = Field(min_length=1)
    current_scene_state: str = Field(min_length=1)
    previous_scene_ending: str = Field(min_length=1)
    next_scene_starting_state: str = Field(min_length=1)


class SegmentEndState(BaseModel):
    description: str = Field(min_length=1)
    character_positions: str = Field(min_length=1)
    camera: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    objects: str = Field(min_length=1)
    motion: str = Field(min_length=1)
