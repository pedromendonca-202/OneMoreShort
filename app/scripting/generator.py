"""Prompt and validate original, fast American-English Short scripts."""
from __future__ import annotations

import re
from typing import Any

from app.llm.base import LLMProvider, LLMRequest, structured
from app.research.schemas import KnowledgeContext, Research, TopicScore
from app.scripting.schemas import MAX_DURATION_S, Script


def estimate_duration(words: str | int, wpm: int | float) -> float:
    """Estimate spoken duration in seconds from text or an already counted total."""
    if wpm <= 0:
        raise ValueError("wpm must be positive")
    count = len(re.findall(r"\b[\w'-]+\b", words)) if isinstance(words, str) else words
    return round(float(count) / float(wpm) * 60, 3)


def _cfg_value(cfg: Any, section: str, field: str, default: Any) -> Any:
    target = getattr(cfg, section, cfg)
    return getattr(target, field, default)


def generate_script(llm: LLMProvider, topic: TopicScore | str, research: Research, knowledge: KnowledgeContext, cfg: Any) -> Script:
    max_duration = float(_cfg_value(cfg, "video", "max_duration_s", MAX_DURATION_S))
    wpm = int(_cfg_value(cfg, "tts", "wpm", 165))
    title = topic.topic if isinstance(topic, TopicScore) else str(topic)
    script = structured(llm, LLMRequest(
        task="generate_script", role="smart", temperature=0.65, response_model=Script,
        system=(
            "You write original American-English YouTube Shorts. Use short spoken sentences and a continuous escalating arc. "
            "Never copy another creator, present uncertain claims as fact, give medical/financial/legal advice, or use a CTA that harms retention."
        ),
        prompt=(
            f"Write an original script about {title!r}, maximum {max_duration:g} seconds at about {wpm} words per minute. "
            "Use timestamped beats: hook, setup, escalation, revelation, payoff, ending as appropriate. The opening must earn attention; "
            "the ending must resolve or cleanly loop.\n\n"
            f"Research brief: {research.model_dump()}\n\nHistorical guidance: {knowledge.model_dump()}"
        ),
    ))
    actual_words = len(re.findall(r"\b[\w'-]+\b", script.text))
    actual_duration = estimate_duration(actual_words, wpm)
    if actual_duration > max_duration:
        raise ValueError(f"script narration is estimated at {actual_duration:.1f}s, above configured maximum {max_duration:.1f}s")
    if any(beat.end_s > max_duration for beat in script.beats):
        raise ValueError(f"script timeline exceeds configured maximum {max_duration:.1f}s")
    return script.model_copy(update={"total_words": actual_words, "est_duration_s": actual_duration})
