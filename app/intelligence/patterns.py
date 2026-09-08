"""Detect which features move which outcomes (spec sections 35, 36, 40, 45)."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean

from app.intelligence.schemas import Insight, VideoOutcome

DIMENSIONS = ("hook_type", "category", "ending_type", "duration_bucket", "pacing_bucket", "visual_style", "narrator",
              "caption_style", "narrative_structure")
METRICS = ("retention", "engagement", "views", "share_rate", "sub_conversion", "completion")


def _value(video: VideoOutcome, dimension: str) -> str:
    return str(getattr(video, dimension, "") or "")


def detect_patterns(videos: list[VideoOutcome], *, dimensions: tuple[str, ...] = DIMENSIONS, metrics: tuple[str, ...] = METRICS,
                    min_samples: int = 1) -> list[Insight]:
    """Relative effect of each feature value on each metric versus the channel mean."""
    if not videos:
        return []
    insights: list[Insight] = []
    for metric in metrics:
        base = mean(getattr(v, metric, 0) or 0 for v in videos)
        if base <= 0:
            continue
        for dimension in dimensions:
            groups: dict[str, list[VideoOutcome]] = defaultdict(list)
            for video in videos:
                value = _value(video, dimension)
                if value:
                    groups[value].append(video)
            if len(groups) < 2 and dimension != "hook_type":
                continue
            for value, group in groups.items():
                if len(group) < min_samples:
                    continue
                effect = (mean(getattr(v, metric, 0) or 0 for v in group) - base) / base
                insights.append(Insight(feature=dimension, value=value, metric=metric, effect_vs_channel=round(effect, 4),
                                        n=len(group), confidence=round(min(1.0, len(group) / 5), 3)))
    return insights


def best_and_worst(insights: list[Insight], metric: str = "retention") -> tuple[dict[str, str], dict[str, str]]:
    best: dict[str, str] = {}
    worst: dict[str, str] = {}
    by_feature: dict[str, list[Insight]] = defaultdict(list)
    for insight in insights:
        if insight.metric == metric:
            by_feature[insight.feature].append(insight)
    for feature, items in by_feature.items():
        ranked = sorted(items, key=lambda i: i.effect_vs_channel * i.confidence, reverse=True)
        best[feature] = ranked[0].value
        if len(ranked) > 1:
            worst[feature] = ranked[-1].value
    return best, worst
