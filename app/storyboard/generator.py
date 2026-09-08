"""Generate visual plans, then make their narration timing deterministic."""
from __future__ import annotations

from typing import Any

from app.llm.base import LLMProvider, LLMRequest, structured
from app.scripting.schemas import Script
from app.storyboard.schemas import Segment, Storyboard


def _cfg_value(cfg: Any, section: str, field: str, default: Any) -> Any:
    target = getattr(cfg, section, cfg)
    return getattr(target, field, default)


def _narration_for_window(script: Script, start: float, end: float) -> str:
    lines = [beat.narration for beat in script.beats if beat.end_s > start and beat.start_s < end]
    return " ".join(lines) or ""


def generate_storyboard(llm: LLMProvider, script: Script, cfg: Any) -> Storyboard:
    segment_count = int(_cfg_value(cfg, "veo", "segments", 5))
    duration = float(_cfg_value(cfg, "veo", "duration_seconds", 8))
    if segment_count != 5:
        raise ValueError("v1 storyboard requires exactly five Veo segments")
    raw = structured(llm, LLMRequest(
        task="generate_storyboard", role="smart", temperature=0.5, response_model=Storyboard,
        system=(
            "You are a cinematic short-form director. Plan one continuous vertical 9:16 video, not five unrelated clips. "
            "Preserve character, environment, objects, lighting, camera direction, and action state across all segment boundaries. "
            "Characters must be silent: narration is added in post."
        ),
        prompt=(
            f"Create five {duration:g}-second segments for this script. Specify concrete, filmable visuals for every field. "
            "Every segment must state how its end continues into the next one.\n\n"
            f"Script: {script.model_dump()}"
        ),
    ))
    # Bind LLM visuals to the immutable script time windows. This prevents a
    # visually good plan from drifting away from the narration that will drive
    # TTS/captions later.
    normalized: list[Segment] = []
    for index, segment in enumerate(raw.segments, start=1):
        start, end = (index - 1) * duration, index * duration
        narration = _narration_for_window(script, start, end)
        if not narration:
            narration = segment.narration
        normalized.append(segment.model_copy(update={"segment": index, "duration": duration, "narration": narration, "dialogue": None}))
    return Storyboard(segments=normalized, visual_style=raw.visual_style, palette=raw.palette)
