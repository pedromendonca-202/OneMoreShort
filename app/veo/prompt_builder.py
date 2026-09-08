"""Build bounded, continuity-first Veo prompts."""
from __future__ import annotations

import math
from typing import Any

from app.continuity.schemas import ContinuityBible, SegmentEndState
from app.storyboard.schemas import Segment, Storyboard
from app.veo.schemas import BrandStyle, VeoPrompt

MAX_PROMPT_TOKENS = 1024
MAX_PROMPT_CHARS = 3_500  # conservative for English prompt text


def estimate_tokens(text: str) -> int:
    """A deliberately conservative local bound; no tokenizer/API call needed."""
    return math.ceil(len(text) / 3.5)


def _segment(value: int | Segment, storyboard: Storyboard) -> Segment:
    if isinstance(value, Segment):
        return value
    for segment in storyboard.segments:
        if segment.segment == value:
            return segment
    raise ValueError(f"storyboard has no segment {value}")


def _clip(text: str, length: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= length else text[: max(1, length - 1)].rstrip() + "…"


def _render_sections(sections: list[tuple[str, str]]) -> str:
    overhead = sum(len(name) + 3 for name, _ in sections)
    content_limit = max(40, (MAX_PROMPT_CHARS - overhead) // len(sections))
    rendered = "\n\n".join(f"{name}:\n{_clip(text, content_limit)}" for name, text in sections)
    # Keep every required heading even with unusually large source models.
    if len(rendered) > MAX_PROMPT_CHARS:
        content_limit = max(20, content_limit - (len(rendered) - MAX_PROMPT_CHARS) // len(sections) - 1)
        rendered = "\n\n".join(f"{name}:\n{_clip(text, content_limit)}" for name, text in sections)
    return rendered


def build_prompt(
    segment: int | Segment,
    bible: ContinuityBible,
    storyboard: Storyboard,
    prev_end_state: SegmentEndState | None,
    brand: BrandStyle,
) -> VeoPrompt:
    scene = _segment(segment, storyboard)
    previous = prev_end_state.description if prev_end_state else bible.previous_scene_ending
    continuity = (
        f"Continue EXACTLY from previous ending: {previous}. "
        f"Character positions: {prev_end_state.character_positions if prev_end_state else bible.current_scene_state}. "
        f"Never reset an action, change identity, wardrobe, location, light direction, lens, or motion direction."
    )
    sections = [
        ("SCENE CONTEXT", f"Segment {scene.segment} of one uninterrupted 40-second vertical Short. {scene.visual_description}"),
        ("CHARACTER CONTINUITY", f"{bible.characters}. Appearance: {bible.appearance}; clothing: {bible.clothing}; hair: {bible.hair}; accessories: {bible.accessories}."),
        ("ENVIRONMENT", f"{bible.environment}. Segment setting: {scene.environment}. Temporal state: {bible.temporal_state}."),
        ("OBJECT CONTINUITY", f"{bible.objects}. Positions: {bible.object_positions}. Segment objects: {scene.objects}."),
        ("ACTION", f"{scene.action}. Planned continuity state at end: {scene.continuity_state}."),
        ("CAMERA", f"{bible.camera}. Segment direction: {scene.camera}."),
        ("LENS", f"{bible.lens}. Segment lens: {scene.lens}."),
        ("LIGHTING", f"{bible.lighting}. Segment lighting: {scene.lighting}."),
        ("COLOR", f"{bible.color_palette}. Brand palette: {brand.palette}."),
        ("MOTION", f"{bible.camera_movement}. Continue action without a cut or restart."),
        ("AUDIO", f"{scene.sound_design}; ambient effects only. No spoken words or voiceover."),
        ("DIALOGUE / NARRATION", "none — silent characters, no voiceover; narration is added later in post-production."),
        ("TIMING", f"Exactly {scene.duration:g} seconds, portrait 9:16. Show a clear continuation into the next segment: {scene.transition_to_next}."),
        ("CONTINUITY REQUIREMENTS", continuity),
        ("NEGATIVE CONSTRAINTS", "No scene reset, new character, wardrobe change, new setting, camera jump, lighting change, on-screen text, subtitles, logos, speech, dialogue, voiceover, copyrighted character, or graphic content."),
    ]
    text = _render_sections(sections)
    return VeoPrompt(
        segment=scene.segment, prompt=text,
        negative_prompt="No speech, dialogue, narration, subtitles, on-screen text, logos, scene reset, new characters, camera jump, or continuity break.",
        previous_end_state=previous if prev_end_state else None,
        config={"duration_seconds": scene.duration, "aspect_ratio": "9:16", "generate_audio": True, "person_generation": "allow_adult"},
    )
