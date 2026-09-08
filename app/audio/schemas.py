"""Typed audio artifacts shared by TTS, captions, and mixing."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.scripting.schemas import Beat


class WordTiming(BaseModel):
    word: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)


class TTSResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    duration_s: float = Field(gt=0)
    words: list[WordTiming] | None = None
    cost_usd: float = Field(default=0, ge=0)


class BeatAudio(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    beat: Beat
    path: Path
    start_s: float = Field(ge=0)
    duration_s: float = Field(gt=0)
    words: list[WordTiming] | None = None


class NarrationPlan(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    beats: list[BeatAudio]
    total_s: float = Field(ge=0)


class TightenedText(BaseModel):
    text: str = Field(min_length=1)
