"""Generate a single concrete continuity contract before video generation."""
from __future__ import annotations

from app.continuity.schemas import ContinuityBible
from app.llm.base import LLMProvider, LLMRequest, structured
from app.scripting.schemas import Script
from app.storyboard.schemas import Storyboard


def build_bible(llm: LLMProvider, script: Script, storyboard: Storyboard) -> ContinuityBible:
    return structured(llm, LLMRequest(
        task="build_continuity_bible", role="smart", temperature=0.2, response_model=ContinuityBible,
        system=(
            "You are a continuity supervisor. Produce precise, stable details that can be copied into every image-to-video prompt. "
            "Resolve ambiguity once; do not introduce new people, locations, wardrobe, lighting, camera setups, or speaking voices."
        ),
        prompt=(
            "Build the continuity bible for this one continuous five-segment Short. Make boundary states concrete: positions, "
            "object placement, camera geometry, light direction, and motion at each handoff. Characters stay silent because post-production adds narration.\n\n"
            f"Script: {script.model_dump()}\n\nStoryboard: {storyboard.model_dump()}"
        ),
    ))
