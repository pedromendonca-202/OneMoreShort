"""A strict, continuous timeline for a ≤40-second Short."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MAX_DURATION_S = 40.0


class HookType(StrEnum):
    CURIOSITY = "curiosity"
    QUESTION = "question"
    SHOCK = "shock"
    CONTRARIAN = "contrarian"
    STORY = "story"
    VISUAL = "visual"
    MYSTERY = "mystery"


class Beat(BaseModel):
    index: int = Field(ge=1)
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    purpose: Literal["hook", "setup", "escalation", "revelation", "payoff", "ending"]
    narration: str = Field(min_length=1, max_length=1_500)
    on_screen_note: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def ends_after_start(self):
        if self.end_s <= self.start_s:
            raise ValueError("beat end_s must be greater than start_s")
        return self


class Script(BaseModel):
    title_working: str = Field(min_length=2, max_length=120)
    beats: list[Beat] = Field(min_length=1)
    hook_type: HookType
    ending_type: Literal["loop", "cta", "cliff", "statement"]
    cta_used: bool
    loop_used: bool
    total_words: int = Field(ge=1)
    est_duration_s: float = Field(gt=0, le=MAX_DURATION_S)

    @model_validator(mode="after")
    def has_monotonic_timeline(self):
        previous_end = 0.0
        previous_index = 0
        for beat in self.beats:
            if beat.index <= previous_index:
                raise ValueError("beat indexes must be strictly increasing")
            if beat.start_s < previous_end:
                raise ValueError("beats may not overlap")
            if beat.end_s > MAX_DURATION_S:
                raise ValueError(f"beat timeline exceeds maximum duration of {MAX_DURATION_S:g} seconds")
            previous_index, previous_end = beat.index, beat.end_s
        return self

    @property
    def text(self) -> str:
        return "\n".join(beat.narration for beat in self.beats)


class HookAssessment(BaseModel):
    hook_type: HookType
