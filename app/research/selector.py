"""Safety-first exploit/explore topic selection."""
from __future__ import annotations

import random
from typing import Protocol

from app.research.schemas import StrategyWeights, TopicScore


class RandomLike(Protocol):
    def random(self) -> float: ...
    def choice(self, sequence): ...


def eligible_topics(scores: list[TopicScore], strategy: StrategyWeights) -> list[TopicScore]:
    """Hard policy filters happen before ranking or random exploration."""
    return [
        score for score in scores
        if score.risk < strategy.risk_threshold and score.competition < strategy.competition_threshold
    ]


def _strategy_score(score: TopicScore, strategy: StrategyWeights) -> float:
    multiplier = strategy.category_weights.get((score.category or "").lower(), 1.0)
    return score.final_score * max(0.0, multiplier)


def select_topic(
    scores: list[TopicScore],
    strategy: StrategyWeights,
    exploration_ratio: float | None = None,
    rng: RandomLike | None = None,
) -> tuple[TopicScore, str]:
    """Choose the strongest eligible candidate, reserving bounded exploration."""
    eligible = eligible_topics(scores, strategy)
    if not eligible:
        raise ValueError("no eligible topics remain after risk and saturation policy")
    ordered = sorted(eligible, key=lambda score: _strategy_score(score, strategy), reverse=True)
    rng = rng or random.Random()
    ratio = strategy.exploration_ratio if exploration_ratio is None else max(0.0, min(1.0, exploration_ratio))
    if len(ordered) > 1 and rng.random() < ratio:
        # The top candidate is exploitation; exploration samples alternatives,
        # but never reintroduces filtered high-risk/saturated content.
        chosen = rng.choice(ordered[1:])
        return chosen, f"Exploration selection among eligible alternatives (base score {chosen.final_score:.1f})."
    chosen = ordered[0]
    return chosen, f"Highest eligible strategy-adjusted score ({_strategy_score(chosen, strategy):.1f})."
