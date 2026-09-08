"""Describe the actual final frame, rather than trusting the intended plan."""
from __future__ import annotations

from pathlib import Path

from app.continuity.schemas import SegmentEndState
from app.llm.base import LLMProvider, LLMRequest, structured


def observe_end_state(llm: LLMProvider, frame_png: Path) -> SegmentEndState:
    return structured(llm, LLMRequest(
        task="observe_end_state", role="vision", temperature=0, images=[frame_png], response_model=SegmentEndState,
        system="You are a precise visual continuity observer. Describe only what is visible in the supplied final frame.",
        prompt="Record the character positions, camera geometry, lighting, object locations, and motion implied by this frame for the next video segment.",
    ))
