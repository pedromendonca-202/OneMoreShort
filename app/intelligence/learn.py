"""The feedback loop (spec sections 42 to 48): snapshots -> features -> insights -> strategy + knowledge + reports."""
from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.comparison import compare
from app.analytics.engagement import engagement_rates
from app.analytics.growth import classify_growth
from app.analytics.report import build_report
from app.analytics.retention import analyze_retention
from app.analytics.schemas import ChannelBaseline, GrowthClass, RetentionAnalysis
from app.core.logging import get_logger
from app.core.models import Insight as InsightRow, Production, VideoReport as ReportRow
from app.core.states import State
from app.core.storage import Storage
from app.intelligence.features import extract_features
from app.intelligence.insights import answer_questions
from app.intelligence.knowledge import Knowledge
from app.intelligence.patterns import detect_patterns
from app.intelligence.schemas import IntelligenceSummary, VideoOutcome
from app.intelligence.strategy import update_strategy

DEFAULT_VIEWS_PER_HOUR = 50.0  # baseline for a brand-new channel until enough videos exist
log = get_logger(component="intelligence")


def _aware(value: datetime | None) -> datetime | None:
    return None if value is None else (value if value.tzinfo else value.replace(tzinfo=UTC))


def _measured(session: Session) -> list[Production]:
    rows = session.query(Production).filter(Production.state.in_([State.PUBLISHED, State.ANALYZING, State.LEARNED])).all()
    return [p for p in rows if p.upload is not None and p.snapshots]


def channel_baseline(outcomes: list[VideoOutcome], exclude: str | None, cfg: Any) -> ChannelBaseline:
    minimum = int(getattr(getattr(cfg, "analytics", cfg), "growth_baseline_min_videos", 3))
    rates = [o.views_per_hour for o in outcomes if o.production_id != exclude and o.views_per_hour > 0]
    if len(rates) < minimum:
        return ChannelBaseline(views_per_hour=DEFAULT_VIEWS_PER_HOUR)
    return ChannelBaseline(views_per_hour=max(1e-6, mean(rates)))


def _needs_report(production: Production) -> bool:
    if not production.reports:
        return True
    last_report = _aware(production.reports[-1].created_at) or datetime.min.replace(tzinfo=UTC)
    latest_snapshot = max((_aware(s.captured_at) or datetime.min.replace(tzinfo=UTC)) for s in production.snapshots)
    return latest_snapshot > last_report


def _retention(production: Production, cfg: Any) -> RetentionAnalysis:
    if production.retention_curves:
        curve = production.retention_curves[-1]
        script = None
        if production.script is not None:
            from app.scripting.schemas import Script

            try:
                script = Script.model_validate(production.script.data)
            except Exception:
                script = None
        return analyze_retention(curve.points, script, None, float(getattr(getattr(cfg, "analytics", cfg), "retention_drop_threshold", 0.08)))
    latest = production.snapshots[-1]
    avg = (latest.avg_view_pct or 0) / 100
    return RetentionAnalysis(points=[], drops=[], completion_est=avg * 0.8, avg_pct=avg)


def report_for(session: Session, storage: Storage, llm: Any, production: Production, outcomes: list[VideoOutcome], cfg: Any,
               *, now: datetime) -> ReportRow:
    outcome = next((o for o in outcomes if o.production_id == production.id), None) or extract_features(production)
    latest = production.snapshots[-1]
    stats = {"views": latest.views, "likes": latest.likes, "comments": latest.comments, "shares": latest.shares or 0,
             "subscribers_gained": latest.subscribers_gained or 0}
    rates = engagement_rates(stats)
    retention = _retention(production, cfg)
    others = [{"views": o.views} for o in outcomes if o.production_id != production.id]
    comparison = compare(stats, others + [stats])
    growth = classify_growth(outcome.views_per_hour, channel_baseline(outcomes, production.id, cfg)) if outcome.views_per_hour else GrowthClass.DEAD
    channel_engagement = [o.engagement for o in outcomes if o.production_id != production.id and o.engagement > 0]
    eng_vs = (outcome.engagement / mean(channel_engagement)) if channel_engagement and outcome.engagement else 1.0
    report = build_report(llm, outcome, stats, rates, retention, comparison, growth, title=outcome.title or outcome.topic,
                          avg_view_duration_s=latest.avg_view_duration_s, engagement_vs_channel=eng_vs)
    path = storage.path_for(production.id, "reports", "report.md")
    path.write_text(report.markdown, encoding="utf-8")
    row = ReportRow(production_id=production.id, youtube_video_id=production.upload.youtube_video_id if production.upload else None,
                    created_at=now, markdown=report.markdown, virality_score=report.virality_score,
                    verdict={"what_worked": report.what_worked, "what_failed": report.what_failed,
                             "next_recommendation": report.next_recommendation, "growth": growth.value,
                             "retention_rating": None, "path": str(path)})
    session.add(row)
    production.reports.append(row)
    return row


def learn(session: Session, storage: Storage, llm: Any, cfg: Any, *, now: datetime | None = None) -> IntelligenceSummary:
    now = now or datetime.now(UTC)
    intelligence_cfg = getattr(cfg, "intelligence", cfg)
    analytics_cfg = getattr(cfg, "analytics", cfg)
    productions = _measured(session)
    outcomes: list[VideoOutcome] = []
    for production in productions:
        outcome = extract_features(production)
        production.features = outcome.model_dump()
        outcomes.append(outcome)
    for outcome in outcomes:  # views/hour baseline needs everyone first
        pass
    insights = detect_patterns(outcomes, min_samples=int(getattr(intelligence_cfg, "min_samples", 3)))

    session.query(InsightRow).delete()
    session.add_all(InsightRow(feature=i.feature, value=i.value, metric=i.metric, effect=i.effect_vs_channel, n=i.n,
                               confidence=i.confidence, detail={"computed_at": now.isoformat()}) for i in insights)
    update_strategy(session, insights, cfg, based_on=len(outcomes))
    Knowledge().rebuild(session, insights, outcomes, productions)

    learn_after_min = int(getattr(analytics_cfg, "learn_after_hours", 168)) * 60
    for production in productions:
        if _needs_report(production):
            try:
                report_for(session, storage, llm, production, outcomes, cfg, now=now)
            except Exception as err:
                log.warning("intelligence.report_failed", production_id=production.id, error=str(err))
        published = _aware(production.upload.published_at or production.upload.uploaded_at)
        age_min = (now - published).total_seconds() / 60 if published else 0
        if production.state == State.ANALYZING and age_min >= learn_after_min and production.reports:
            production.previous_state, production.state = production.state, State.LEARNED
    session.flush()
    summary = answer_questions(insights, outcomes)
    log.info("intelligence.learned", videos=len(outcomes), insights=len(insights))
    return summary
