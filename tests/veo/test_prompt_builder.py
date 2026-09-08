from __future__ import annotations

from app.veo.prompt_builder import build_prompt, estimate_tokens


def test_prompt_contains_all_required_sections_and_forbids_speech(bible, storyboard, brand):
    prompt = build_prompt(1, bible, storyboard, None, brand)
    for heading in (
        "SCENE CONTEXT", "CHARACTER CONTINUITY", "ENVIRONMENT", "OBJECT CONTINUITY", "ACTION", "CAMERA", "LENS",
        "LIGHTING", "COLOR", "MOTION", "AUDIO", "DIALOGUE / NARRATION", "TIMING", "CONTINUITY REQUIREMENTS", "NEGATIVE CONSTRAINTS",
    ):
        assert heading in prompt.prompt
    assert "silent characters" in prompt.prompt.lower()
    assert "speech" in prompt.negative_prompt.lower()
    assert estimate_tokens(prompt.prompt) <= 1024
