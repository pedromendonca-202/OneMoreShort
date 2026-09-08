"""Adaptive selection policy (spec section 46): learned priors with exploration, persisted per learn run."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.models import StrategyWeightsRow
from app.intelligence.schemas import Insight
from app.research.schemas import StrategyWeights

_MIN_WEIGHT, _MAX_WEIGHT = 0.4, 1.8
_BUCKET_MIDPOINT = {"<25s": 22.0, "25-32s": 29.0, "32-40s": 36.0}


def _weights(insights: list[Insight], feature: str, metric: str = "retention") -> dict[str, float]:
    out: dict[str, float] = {}
    for insight in insights:
        if insight.feature != feature or insight.metric != metric:
            continue
        weight = 1.0 + insight.effect_vs_channel * insight.confidence
        out[insight.value] = round(max(_MIN_WEIGHT, min(_MAX_WEIGHT, weight)), 4)
    return out


def _cfg(cfg: Any, name: str, default: Any) -> Any:
    return getattr(getattr(cfg, "intelligence", cfg), name, default)


def update_strategy(session: Session | None, insights: list[Insight], cfg: Any, *, based_on: int = 0) -> StrategyWeights:
    metric = "retention" if any(i.metric == "retention" for i in insights) else "engagement"
    durations = _weights(insights, "duration_bucket", metric)
    duration_pref = None
    if durations:
        best = max(durations, key=durations.get)
        duration_pref = _BUCKET_MIDPOINT.get(best)
    strategy = StrategyWeights(
        category_weights=_weights(insights, "category", metric),
        hook_weights=_weights(insights, "hook_type", metric),
        style_weights=_weights(insights, "visual_style", metric),
        duration_pref=duration_pref,
        exploration_ratio=float(_cfg(cfg, "exploration_ratio", 0.3)),
    )
    if session is not None:
        session.query(StrategyWeightsRow).delete()
        session.add(StrategyWeightsRow(weights=strategy.model_dump(), exploration_ratio=strategy.exploration_ratio, based_on_n=based_on))
        session.flush()
    return strategy


def load_strategy(session: Session, cfg: Any) -> StrategyWeights:
    row = session.query(StrategyWeightsRow).order_by(StrategyWeightsRow.created_at.desc(), StrategyWeightsRow.id.desc()).first()
    exploration = float(_cfg(cfg, "exploration_ratio", 0.3))
    if row is None:
        return StrategyWeights(exploration_ratio=exploration)
    data = dict(row.weights or {})
    data["exploration_ratio"] = exploration
    return StrategyWeights.model_validate(data)
