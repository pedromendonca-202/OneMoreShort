"""Grounded research brief for the selected topic."""
from __future__ import annotations

from app.llm.base import LLMProvider, LLMRequest, structured
from app.research.schemas import Research


def deep_research(llm: LLMProvider, topic: str, *, use_search: bool = True) -> Research:
    """Produce a source-aware brief without copying other creators' scripts."""
    return structured(llm, LLMRequest(
        task="deep_research", role="smart", temperature=0.2, use_search=use_search, response_model=Research,
        system=(
            "You are a rigorous research editor for an original American-English YouTube Short. Search authoritative primary "
            "sources where possible. Separate facts from interpretation; if a claim is uncertain, name the uncertainty in risks. "
            "Never copy a creator's script or recommend copyrighted footage."
        ),
        prompt=(
            f"Research the topic: {topic!r}. Return a compact research brief for an original video of at most 40 seconds. "
            "For every fact, include the direct source URL when known and a calibrated confidence. Identify a genuinely useful "
            "angle, a truthful curiosity hook, risks, and the clearest 40-second approach."
        ),
    ))
