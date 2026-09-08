"""Classify the opening hook separately for later analytics."""
from __future__ import annotations

from app.llm.base import LLMProvider, LLMRequest, structured
from app.scripting.schemas import HookAssessment, HookType


def classify_hook(llm: LLMProvider, first_beat_text: str) -> HookType:
    assessment = structured(llm, LLMRequest(
        task="classify_hook", role="fast", temperature=0, response_model=HookAssessment,
        prompt=f"Classify this opening line into its primary hook type.\n\n{first_beat_text}",
    ))
    return assessment.hook_type
