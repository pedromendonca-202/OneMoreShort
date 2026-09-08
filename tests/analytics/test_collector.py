"""Snapshot collection follows the checkpoint schedule and enriches with deep metrics after 48 h."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.analytics.collector import collect_all_due, collect_for_production, taken_slots
from app.core.models import Production, Script as ScriptRow, Upload
from app.core.states import State
from app.youtube.mock import MockYouTubeClient
from app.youtube.schemas import RetentionPoint

PUBLISHED = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


class FakeAnalytics:
    def __init__(self):
        self.calls = 0

    def video_metrics(self, video_id, start, end):
        self.calls += 1
        return {"views": 5000, "engagedViews": 4200, "estimatedMinutesWatched": 2600.0, "averageViewDuration": 31.2,
                "averageViewPercentage": 78.0, "likes": 400, "dislikes": 3, "comments": 40, "shares": 90,
                "subscribersGained": 50, "subscribersLost": 1}

    def retention_curve(self, video_id, start, end):
        return [RetentionPoint(elapsed_ratio=i / 10, watch_ratio=max(0.3, 1 - i * 0.06 - (0.2 if i == 3 else 0)), relative=1.0)
                for i in range(11)]

    def traffic_sources(self, video_id, start, end):
        return {"SHORTS": 4500, "SUBSCRIBER": 500}


def _published_production(session, pid="OMS-20260907-0001", video_id="vid-1"):
    production = Production(id=pid, state=State.PUBLISHED)
    session.add(production)
    session.add(Upload(production_id=pid, youtube_video_id=video_id, status="uploaded", uploaded_at=PUBLISHED, published_at=PUBLISHED))
    session.add(ScriptRow(production_id=pid, data={"title_working": "test title", "hook_type": "curiosity", "ending_type": "loop", "cta_used": False,
                                                    "loop_used": True, "total_words": 20, "est_duration_s": 30,
                                                    "beats": [{"index": 1, "start_s": 0, "end_s": 8, "purpose": "hook", "narration": "a b c"},
                                                              {"index": 2, "start_s": 8, "end_s": 30, "purpose": "payoff", "narration": "d e f"}]},
                          text="a b c d e f", hook_type="curiosity", ending_type="loop", total_words=6, est_duration_s=30))
    session.flush()
    return production


def test_first_checkpoint_creates_snapshot_and_moves_to_analyzing(session, settings):
    production = _published_production(session)
    snapshot = collect_for_production(session, production, MockYouTubeClient(), None, now=PUBLISHED + timedelta(minutes=12), cfg=settings)
    assert snapshot is not None and snapshot.schedule_slot_min == 10 and snapshot.views > 0
    assert production.state == State.ANALYZING
    assert taken_slots(production) == [10]


def test_nothing_due_returns_none(session, settings):
    production = _published_production(session)
    collect_for_production(session, production, MockYouTubeClient(), None, now=PUBLISHED + timedelta(minutes=12), cfg=settings)
    assert collect_for_production(session, production, MockYouTubeClient(), None, now=PUBLISHED + timedelta(minutes=13), cfg=settings) is None


def test_missed_checkpoints_collapse_into_one_snapshot(session, settings):
    production = _published_production(session)
    snapshot = collect_for_production(session, production, MockYouTubeClient(), None, now=PUBLISHED + timedelta(hours=7), cfg=settings)
    assert snapshot.schedule_slot_min == 360
    assert snapshot.raw["covers_slots"] == [10, 30, 60, 180, 360]
    assert taken_slots(production) == [10, 30, 60, 180, 360]


def test_deep_metrics_and_retention_after_threshold(session, settings):
    production = _published_production(session)
    analytics = FakeAnalytics()
    early = collect_for_production(session, production, MockYouTubeClient(), analytics, now=PUBLISHED + timedelta(hours=1), cfg=settings)
    assert early.source == "data_api" and analytics.calls == 0
    late = collect_for_production(session, production, MockYouTubeClient(), analytics, now=PUBLISHED + timedelta(hours=49), cfg=settings)
    assert late.source == "analytics_api" and late.avg_view_pct == 78.0 and late.engaged_views == 4200
    assert late.shares == 90 and late.subscribers_gained == 50 and late.traffic_sources["SHORTS"] == 4500
    curve = production.retention_curves[-1]
    assert len(curve.points) == 11
    assert curve.analysis["drops"], "the engineered dip at 30% must be detected"
    assert curve.analysis["drops"][0]["beat"] in (1, 2)


def test_collect_all_due_skips_unpublished_and_reports_ids(session, settings):
    _published_production(session, "OMS-20260907-0001", "vid-1")
    session.add(Production(id="OMS-20260907-0002", state=State.READY))
    session.flush()
    collected = collect_all_due(session, MockYouTubeClient(), None, now=PUBLISHED + timedelta(minutes=45), cfg=settings)
    assert collected == ["OMS-20260907-0001"]
