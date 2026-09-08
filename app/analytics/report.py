"""Per-video performance report (spec section 44): computed facts first, LLM narrative second."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.analytics.schemas import Comparison, EngagementRates, GrowthClass, RetentionAnalysis, VideoReport
from app.intelligence.schemas import VideoOutcome
from app.llm.base import LLMRequest, structured


class ReportNarrative(BaseModel):
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    next_recommendation: str = ""


def rate_retention(avg_pct: float) -> str:
    if avg_pct >= 0.80:
        return "Excellent"
    if avg_pct >= 0.65:
        return "Good"
    if avg_pct >= 0.50:
        return "Average"
    return "Below Average"


def rate_hook(hold_ratio: float) -> str:
    if hold_ratio >= 0.90:
        return "Excellent"
    if hold_ratio >= 0.80:
        return "Good"
    if hold_ratio >= 0.70:
        return "Average"
    return "Below Average"


def rate_engagement(vs_channel: float) -> str:
    if vs_channel >= 2.5:
        return "Excellent"
    if vs_channel >= 1.25:
        return "Above Average"
    if vs_channel >= 0.8:
        return "Average"
    return "Below Average"


_GROWTH_BONUS = {GrowthClass.DEAD: 0, GrowthClass.SLOW: 3, GrowthClass.NORMAL: 6, GrowthClass.ACCELERATING: 10,
                 GrowthClass.VIRAL: 13, GrowthClass.EXPLOSIVE: 15}


def virality_score(retention: RetentionAnalysis, rates: EngagementRates, comparison: Comparison, growth: GrowthClass) -> float:
    score = retention.avg_pct * 40 + min(1.0, rates.engagement_rate / 0.08) * 25 + min(1.0, comparison.vs_mean / 3) * 20
    score += _GROWTH_BONUS.get(growth, 0)
    return round(max(0.0, min(100.0, score)), 1)


def _hook_hold(retention: RetentionAnalysis) -> float:
    early = [ratio for elapsed, ratio in retention.points if 0 < elapsed <= 0.12]
    return early[0] if early else (retention.points[1][1] if len(retention.points) > 1 else retention.avg_pct)


def _get(stats: Any, key: str) -> int:
    value = stats.get(key, 0) if isinstance(stats, dict) else getattr(stats, key, 0)
    return int(value or 0)


def _deterministic(outcome: VideoOutcome, rates: EngagementRates, retention: RetentionAnalysis, comparison: Comparison,
                   growth: GrowthClass, hook_hold: float) -> ReportNarrative:
    worked: list[str] = []
    failed: list[str] = []
    if hook_hold >= 0.85:
        worked.append(f"Strong {outcome.hook_type} hook: {hook_hold:.0%} still watching after the first seconds")
    if retention.avg_pct >= 0.65:
        worked.append(f"High retention ({retention.avg_pct:.0%} average percentage viewed)")
    if rates.share_rate >= 0.004:
        worked.append(f"Strong shareability ({rates.share_rate:.2%} share rate)")
    if rates.sub_conversion >= 0.004:
        worked.append(f"Subscriber conversion above target ({rates.sub_conversion:.2%})")
    if 0 < outcome.duration_s <= 35:
        worked.append(f"Short {outcome.duration_s:.0f}-second runtime")
    if comparison.vs_mean >= 1.5:
        worked.append(f"Views {comparison.vs_mean:.1f}x the channel average")
    if growth in (GrowthClass.VIRAL, GrowthClass.EXPLOSIVE):
        worked.append(f"{growth.value.capitalize()} growth velocity")
    for drop in retention.drops[:3]:
        where = f" (beat {drop.beat})" if drop.beat else ""
        failed.append(f"Retention dropped {drop.delta:.0%} at {drop.t_s:.0f}s{where}: {drop.likely_cause}")
    if hook_hold < 0.70:
        failed.append(f"Weak hook: only {hook_hold:.0%} watching after the first seconds")
    if retention.avg_pct < 0.50:
        failed.append(f"Low average percentage viewed ({retention.avg_pct:.0%})")
    if outcome.cta_used and retention.drops and retention.drops[-1].t_s >= 0.75 * max(outcome.duration_s, 1):
        failed.append("CTA near the ending reduced momentum")
    if rates.engagement_rate < 0.02:
        failed.append(f"Engagement rate below 2% ({rates.engagement_rate:.2%})")
    if not worked:
        worked.append("Initial distribution recorded; no strong positive signal yet")
    recommendation = "Use: " + "; ".join(filter(None, [
        f"same {outcome.hook_type} hook style" if hook_hold >= 0.80 else "a stronger first-two-second hook",
        "similar pacing" if retention.avg_pct >= 0.65 else "faster pacing with shorter sentences",
        f"similar {outcome.duration_s:.0f}s runtime" if 0 < outcome.duration_s <= 36 else "a shorter runtime under 36s",
        "tighten the segment around the first retention drop" if retention.drops else "a stronger payoff",
        "no interruption before the ending" if outcome.cta_used else f"keep the {outcome.ending_type} ending",
    ]))
    return ReportNarrative(what_worked=worked, what_failed=failed, next_recommendation=recommendation)


def build_report(llm, outcome: VideoOutcome | Any, stats: Any, rates: EngagementRates, retention: RetentionAnalysis,
                 comparison: Comparison, growth: GrowthClass, *, title: str | None = None,
                 avg_view_duration_s: float | None = None, engagement_vs_channel: float | None = None) -> VideoReport:
    if not isinstance(outcome, VideoOutcome):
        from app.intelligence.features import extract_features

        outcome = extract_features(outcome)
    hook_hold = _hook_hold(retention)
    facts = _deterministic(outcome, rates, retention, comparison, growth, hook_hold)
    narrative = facts
    if llm is not None:
        try:
            generated = structured(llm, LLMRequest(
                task="video_report", role="fast", temperature=0.2, response_model=ReportNarrative,
                system="You write terse, factual post-mortems for YouTube Shorts. Only use the numbers provided; never invent metrics.",
                prompt=f"Facts: {facts.model_dump()}\nMetrics: retention={retention.avg_pct:.2f}, hook_hold={hook_hold:.2f}, "
                       f"rates={rates.model_dump()}, comparison={comparison.model_dump()}, growth={growth.value}, "
                       f"features={outcome.model_dump()}\nReturn 3-5 'what worked', 1-4 'what failed', and one next-video recommendation.",
            ))
            if generated.what_worked or generated.what_failed or generated.next_recommendation:
                narrative = ReportNarrative(what_worked=generated.what_worked or facts.what_worked,
                                            what_failed=generated.what_failed or facts.what_failed,
                                            next_recommendation=generated.next_recommendation or facts.next_recommendation)
        except Exception:
            narrative = facts
    score = virality_score(retention, rates, comparison, growth)
    eng_vs = engagement_vs_channel if engagement_vs_channel is not None else (comparison.vs_mean if comparison.vs_mean else 1.0)
    views = _get(stats, "views")
    avd = avg_view_duration_s if avg_view_duration_s is not None else outcome.duration_s * retention.avg_pct
    lines = [
        "ONE MORE SHORT", "VIDEO PERFORMANCE REPORT", "",
        f'Video: "{title or outcome.title or outcome.production_id}"', "",
        f"Views: {views:,}",
        f"Average Percentage Viewed: {retention.avg_pct:.0%}",
        f"Average View Duration: {avd:.1f}s",
        f"Likes: {_get(stats, 'likes'):,}",
        f"Comments: {_get(stats, 'comments'):,}",
        f"Shares: {_get(stats, 'shares'):,}",
        f"Subscribers: {_get(stats, 'subscribers_gained'):,}", "",
        f"Retention: {rate_retention(retention.avg_pct)}",
        f"Hook: {rate_hook(hook_hold)}",
        f"Engagement: {rate_engagement(eng_vs)}",
        f"Growth: {growth.value.replace('_', ' ').title()}",
        f"Virality Score: {score:.0f}/100", "",
        f"vs channel average: views {comparison.vs_mean:+.0%}, rank #{comparison.rank}",
        f"Like rate {rates.like_rate:.2%} | Comment rate {rates.comment_rate:.2%} | Share rate {rates.share_rate:.2%} | "
        f"Subscriber conversion {rates.sub_conversion:.2%}", "",
        "WHAT WORKED", *[f"{i}. {item}" for i, item in enumerate(narrative.what_worked, 1)], "",
        "WHAT FAILED", *([f"{i}. {item}" for i, item in enumerate(narrative.what_failed, 1)] or ["1. Nothing significant detected"]), "",
        "NEXT VIDEO RECOMMENDATION", narrative.next_recommendation, "",
    ]
    return VideoReport(markdown="\n".join(lines), what_worked=narrative.what_worked, what_failed=narrative.what_failed,
                       next_recommendation=narrative.next_recommendation, virality_score=score)
