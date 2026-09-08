"""Checkpoint-based analytics collection (spec sections 33 and 34).

`oms analytics` runs periodically; each published video gets one snapshot per due checkpoint. If the
collector was not run for a while, the missed checkpoints collapse into a single snapshot labelled with
the latest due slot (the numbers are what they are *now*; we never fabricate earlier values).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.retention import analyze_retention
from app.core.logging import get_logger
from app.core.models import AnalyticsSnapshot, Production, RetentionCurve
from app.core.states import State

SNAPSHOT_SCHEDULE_MIN = [10, 30, 60, 180, 360, 720, 1440, 2880, 10080, 20160, 43200]
log = get_logger(component="analytics")


def due_snapshots(published_at: datetime, now: datetime, taken: list[int], schedule: list[int] | None = None) -> list[int]:
    age = max(0, (now - published_at).total_seconds() / 60)
    return [slot for slot in (schedule or SNAPSHOT_SCHEDULE_MIN) if slot <= age and slot not in taken]


def taken_slots(production: Production, schedule: list[int] | None = None) -> list[int]:
    slots = [snap.schedule_slot_min for snap in production.snapshots if snap.schedule_slot_min]
    if not slots:
        return []
    latest = max(slots)
    return [slot for slot in (schedule or SNAPSHOT_SCHEDULE_MIN) if slot <= latest]


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _script(production: Production):
    if production.script is None:
        return None
    from app.scripting.schemas import Script

    try:
        return Script.model_validate(production.script.data)
    except Exception:  # analysis must never fail because an old script row is malformed
        return None


def collect_for_production(session: Session, production: Production, stats_client: Any, analytics_client: Any | None,
                           *, now: datetime, cfg: Any) -> AnalyticsSnapshot | None:
    upload = production.upload
    if upload is None or not upload.youtube_video_id:
        return None
    published_at = _aware(upload.published_at or upload.uploaded_at)
    if published_at is None or published_at > now:
        return None
    analytics_cfg = getattr(cfg, "analytics", cfg)
    schedule = list(getattr(analytics_cfg, "snapshot_schedule_min", SNAPSHOT_SCHEDULE_MIN))
    due = due_snapshots(published_at, now, taken_slots(production, schedule), schedule)
    if not due:
        return None
    age_minutes = int((now - published_at).total_seconds() // 60)
    video_id = upload.youtube_video_id
    stats = stats_client.video_stats([video_id], age_minutes=age_minutes)
    stat = stats[0] if stats else None
    snapshot = AnalyticsSnapshot(
        production_id=production.id, youtube_video_id=video_id, captured_at=now, age_minutes=age_minutes,
        schedule_slot_min=max(due), source="data_api",
        views=stat.views if stat else 0, likes=stat.likes if stat else 0, comments=stat.comments if stat else 0,
        shares=stat.shares if stat else None, subscribers_gained=stat.subscribers_gained if stat else None,
        raw={"covers_slots": due},
    )
    deep_after_min = int(getattr(analytics_cfg, "deep_metrics_after_hours", 48)) * 60
    if analytics_client is not None and age_minutes >= deep_after_min:
        start, end = published_at.date(), now.date()
        try:
            deep = analytics_client.video_metrics(video_id, start, end)
            snapshot.source = "analytics_api"
            snapshot.views = int(deep.get("views", snapshot.views) or snapshot.views)
            snapshot.engaged_views = _opt_int(deep.get("engagedViews"))
            snapshot.likes = int(deep.get("likes", snapshot.likes) or snapshot.likes)
            snapshot.dislikes = _opt_int(deep.get("dislikes"))
            snapshot.comments = int(deep.get("comments", snapshot.comments) or snapshot.comments)
            snapshot.shares = _opt_int(deep.get("shares"))
            snapshot.subscribers_gained = _opt_int(deep.get("subscribersGained"))
            snapshot.subscribers_lost = _opt_int(deep.get("subscribersLost"))
            snapshot.watch_time_min = _opt_float(deep.get("estimatedMinutesWatched"))
            snapshot.avg_view_duration_s = _opt_float(deep.get("averageViewDuration"))
            snapshot.avg_view_pct = _opt_float(deep.get("averageViewPercentage"))
            snapshot.raw = {**snapshot.raw, "analytics": deep}
            snapshot.traffic_sources = analytics_client.traffic_sources(video_id, start, end)
            curve = analytics_client.retention_curve(video_id, start, end)
            if curve:
                threshold = float(getattr(analytics_cfg, "retention_drop_threshold", 0.08))
                analysis = analyze_retention(curve, _script(production), None, threshold)
                production.retention_curves.append(RetentionCurve(youtube_video_id=video_id, captured_at=now,
                                                                  points=[point.model_dump() for point in curve],
                                                                  analysis=analysis.model_dump()))
        except Exception as err:  # deep metrics are best-effort; the basic snapshot is still valuable
            log.warning("analytics.deep_metrics_failed", production_id=production.id, error=str(err))
            snapshot.raw = {**snapshot.raw, "analytics_error": str(err)[:500]}
    production.snapshots.append(snapshot)  # via the relationship so `taken_slots` sees it immediately
    if production.state == State.PUBLISHED:
        production.previous_state, production.state = production.state, State.ANALYZING
    session.flush()
    return snapshot


def collect_all_due(session: Session, stats_client: Any, analytics_client: Any | None, *, now: datetime, cfg: Any) -> list[str]:
    collected: list[str] = []
    candidates = session.query(Production).filter(Production.state.in_([State.PUBLISHED, State.ANALYZING, State.LEARNED])).all()
    for production in candidates:
        try:
            snapshot = collect_for_production(session, production, stats_client, analytics_client, now=now, cfg=cfg)
        except Exception as err:
            log.warning("analytics.collect_failed", production_id=production.id, error=str(err))
            continue
        if snapshot is not None:
            collected.append(production.id)
    return collected


def _opt_int(value: Any) -> int | None:
    try:
        return None if value is None else int(float(value))
    except (TypeError, ValueError):
        return None


def _opt_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
