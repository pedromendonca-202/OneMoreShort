from __future__ import annotations

from app.llm.mock import MockLLM
from app.research.deep_research import deep_research
from app.research.schemas import Research


def test_deep_research_returns_typed_fixture_and_requests_grounding():
    expected = Research.model_validate({
        "facts": [{"text": "Mars has polar ice caps.", "source": "https://science.nasa.gov/mars/", "confidence": 0.95}],
        "context": "A concise context.", "angles": ["The unexpected location"], "hooks": ["Mars is hiding water where nobody expected."],
        "risks": ["Do not overstate preliminary evidence."], "curiosity_points": ["Why it matters"],
        "best_40s_approach": "Start with the surprise, then explain the evidence.",
    })
    llm = MockLLM(handlers={"Research": lambda req: expected})
    research = deep_research(llm, "Water on Mars")
    assert research == expected
    assert llm.calls[0].use_search is True
    assert llm.calls[0].role == "smart"
