from __future__ import annotations

import random

import pytest

from app.research.schemas import StrategyWeights, TopicScore
from app.research.selector import eligible_topics, select_topic


def score(name: str, final: float, *, risk: float = 10, competition: float = 10, category: str = "science") -> TopicScore:
    return TopicScore(topic=name, category=category, trend_score=80, viral_potential=80, us_relevance=80,
                      competition=competition, shorts_fit=80, originality=80, risk=risk, final_score=final, reasons=[])


def test_hard_avoid_removes_risky_and_saturated_topics():
    candidates = [score("safe", 80), score("risky", 99, risk=65), score("saturated", 98, competition=90)]
    assert [x.topic for x in eligible_topics(candidates, StrategyWeights(risk_threshold=60, competition_threshold=85))] == ["safe"]


def test_exploration_can_pick_eligible_non_top_topic_with_seeded_rng():
    candidates = [score("top", 95), score("other", 70), score("third", 60)]
    chosen, reason = select_topic(candidates, StrategyWeights(), exploration_ratio=1.0, rng=random.Random(4))
    assert chosen.topic in {"other", "third"}
    assert "exploration" in reason.lower()


def test_selector_rejects_when_every_candidate_is_unsafe():
    with pytest.raises(ValueError, match="eligible"):
        select_topic([score("unsafe", 99, risk=99)], StrategyWeights(), exploration_ratio=0, rng=random.Random(1))
