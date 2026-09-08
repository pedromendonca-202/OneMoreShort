"""Answer the standing Content Intelligence questions (spec section 41) from the detected patterns."""
from __future__ import annotations

from app.intelligence.patterns import best_and_worst
from app.intelligence.schemas import Insight, IntelligenceSummary, VideoOutcome

_QUESTIONS: list[tuple[str, str, str, bool]] = [
    # question, feature, metric, best(True)/worst(False)
    ("What topics work?", "category", "views", True),
    ("What hooks work?", "hook_type", "retention", True),
    ("What video lengths work?", "duration_bucket", "retention", True),
    ("What pacing works?", "pacing_bucket", "retention", True),
    ("What visual styles work?", "visual_style", "retention", True),
    ("What endings work?", "ending_type", "completion", True),
    ("What narration styles work?", "narrator", "retention", True),
    ("What topics generate shares?", "category", "share_rate", True),
    ("What topics generate subscribers?", "category", "sub_conversion", True),
    ("What topics generate retention?", "category", "retention", True),
    ("What topics fail?", "category", "retention", False),
]


def _pick(insights: list[Insight], feature: str, metric: str, best: bool) -> Insight | None:
    items = [i for i in insights if i.feature == feature and i.metric == metric]
    if not items:
        alt = [i for i in insights if i.feature == feature and i.metric == "retention"]
        items = alt
    if not items:
        return None
    return max(items, key=lambda i: i.effect_vs_channel * i.confidence) if best else min(items, key=lambda i: i.effect_vs_channel * i.confidence)


def _phrase(insight: Insight) -> str:
    sign = "+" if insight.effect_vs_channel >= 0 else "-"
    return f"{insight.value} ({sign}{abs(insight.effect_vs_channel):.0%} {insight.metric} vs channel, n={insight.n})"


def answer_questions(insights: list[Insight], outcomes: list[VideoOutcome] | None = None) -> IntelligenceSummary:
    answers: dict[str, str] = {}
    for question, feature, metric, best in _QUESTIONS:
        insight = _pick(insights, feature, metric, best)
        answers[question] = _phrase(insight) if insight else "not enough data yet"
    negatives = sorted((i for i in insights if i.effect_vs_channel < -0.05 and i.metric in {"retention", "views"}),
                       key=lambda i: i.effect_vs_channel * i.confidence)[:4]
    drops = [t for o in (outcomes or []) for t in o.drop_offs]
    reasons = [f"{i.feature}={i.value} underperforms ({i.effect_vs_channel:+.0%} {i.metric})" for i in negatives]
    if drops:
        reasons.append(f"retention drops cluster around {sum(drops) / len(drops):.0f}s")
    answers["Why do they fail?"] = "; ".join(reasons) if reasons else "not enough data yet"
    best, worst = best_and_worst(insights)
    return IntelligenceSummary(insights=insights, answers=answers, best=best, worst=worst, videos=len(outcomes or []))
