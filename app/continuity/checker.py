"""Compare adjacent segment boundary frames before accepting continuity."""
from __future__ import annotations

from pathlib import Path

from app.llm.base import LLMProvider, LLMRequest, structured
from app.veo.schemas import ContinuityScore


def check_continuity(llm: LLMProvider, last_frame_n: Path, first_frame_n1: Path) -> ContinuityScore:
    return structured(llm, LLMRequest(
        task="check_continuity", role="vision", temperature=0, images=[last_frame_n, first_frame_n1], response_model=ContinuityScore,
        system="You are a strict film-continuity supervisor. Score whether image two continues directly from image one.",
        prompt="Compare frame 1 (previous segment end) to frame 2 (next segment start). Score 0 to 1 and list concrete mismatches only.",
    ))
