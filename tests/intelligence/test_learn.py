"""Content intelligence turns snapshots into insights, strategy weights, knowledge and reports."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.models import (
    AnalyticsSnapshot,
    Insight as InsightRow,
    KnowledgeEntry,
    Production,
    RetentionCurve,
    Script as ScriptRow,
    StrategyWeightsRow,
    Storyboard as StoryRow,
    Topic,
    Upload,
    VideoMetadata as MetadataRow,
)
from app.core.states import State
from app.core.storage import Storage
from app.intelligence.features import extract_features
from app.intelligence.knowledge import Knowledge
from app.intelligence.learn import learn
from app.intelligence.strategy import load_strategy
from app.llm.mock import MockLLM

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _script(hook: str, ending: str, words: int, duration: float) -> dict:
    return {"title_working": f"{hook} video", "hook_type": hook, "ending_type": ending, "cta_used": ending == "cta",
            "loop_used": ending == "loop", "total_words": words, "est_duration_s": duration,
            "beats": [{"index": 1, "start_s": 0, "end_s": duration, "purpose": "hook", "narration": "w " * words}]}


def _video(session, pid, *, hook, category, ending, views, retention, likes, shares, subs, age_h=200, words=80, duration=32.0):
    p = Production(id=pid, state=State.ANALYZING)
    session.add(p)
    session.add(Topic(production_id=pid, topic=f"topic {pid}", category=category, selected=True, final_score=80))
    session.add(ScriptRow(production_id=pid, data=_script(hook, ending, words, duration), text="w", hook_type=hook, ending_type=ending,
                          total_words=words, est_duration_s=duration))
    session.add(StoryRow(production_id=pid, data={"segments": [], "visual_style": "cinematic", "palette": "red"}, visual_style="cinematic"))
    session.add(MetadataRow(production_id=pid, title=f"Title {pid}", description="d", hashtags=["#Shorts"], category_id="27"))
    published = T0
    session.add(Upload(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", status="uploaded", uploaded_at=published, published_at=published))
    session.add(AnalyticsSnapshot(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", captured_at=published + timedelta(hours=24),
                                  age_minutes=1440, schedule_slot_min=1440, views=views // 2, likes=likes // 2, comments=3, shares=shares // 2,
                                  subscribers_gained=subs // 2))
    session.add(AnalyticsSnapshot(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", captured_at=published + timedelta(hours=age_h),
                                  age_minutes=age_h * 60, schedule_slot_min=10080, source="analytics_api", views=views, likes=likes,
                                  comments=10, shares=shares, subscribers_gained=subs, avg_view_pct=retention * 100,
                                  avg_view_duration_s=duration * retention, engaged_views=int(views * 0.8)))
    session.add(RetentionCurve(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", captured_at=published + timedelta(hours=age_h),
                               points=[{"elapsed_ratio": i / 10, "watch_ratio": max(0.2, 1 - i * (1 - retention) / 5)} for i in range(11)],
                               analysis={"drops": [], "avg_pct": retention, "completion_est": retention * 0.8, "points": []}))
    session.flush()
    return p


def _seed(session):
    _video(session, "OMS-20260901-0001", hook="shock", category="science", ending="loop", views=200_000, retention=0.85, likes=9000, shares=2000, subs=1500)
    _video(session, "OMS-20260901-0002", hook="shock", category="science", ending="loop", views=150_000, retention=0.80, likes=6000, shares=1500, subs=900)
    _video(session, "OMS-20260901-0003", hook="question", category="history", ending="cta", views=8_000, retention=0.45, likes=100, shares=10, subs=5)


def test_extract_features_reads_script_snapshots_and_retention(session):
    _seed(session)
    p = session.get(Production, "OMS-20260901-0001")
    outcome = extract_features(p)
    assert outcome.hook_type == "shock" and outcome.category == "science" and outcome.ending_type == "loop"
    assert outcome.views == 200_000 and outcome.retention == 0.85 and outcome.loop_used is True
    assert outcome.duration_s == 32.0 and outcome.pacing_wps > 0 and outcome.visual_style == "cinematic"
    assert outcome.views_24h == 100_000 and outcome.share_rate > 0 and outcome.sub_conversion > 0


def test_learn_writes_insights_strategy_knowledge_and_reports(session, settings, tmp_path):
    _seed(session)
    settings.intelligence.min_samples = 1
    storage = Storage(tmp_path / "storage")
    summary = learn(session, storage, MockLLM(), settings, now=T0 + timedelta(days=10))

    insights = session.query(InsightRow).all()
    assert insights, "insight rows must be persisted"
    best_hook = max((i for i in insights if i.feature == "hook_type" and i.metric == "retention"), key=lambda i: i.effect)
    assert best_hook.value == "shock"
    assert summary.answers["What hooks work?"].startswith("shock")

    strategy = load_strategy(session, settings)
    assert strategy.category_weights["science"] > strategy.category_weights["history"]
    assert strategy.hook_weights["shock"] > 1.0 > strategy.hook_weights["question"]
    assert session.query(StrategyWeightsRow).count() == 1

    context = Knowledge().context_for("science", session=session)
    assert context.best_hooks and context.best_hooks[0].startswith("shock")
    assert any("question" in item for item in context.failed_patterns)
    assert session.query(KnowledgeEntry).count() >= 3

    for pid in ("OMS-20260901-0001", "OMS-20260901-0003"):
        p = session.get(Production, pid)
        assert p.reports and "WHAT WORKED" in p.reports[-1].markdown
        assert (storage.dir_for(pid, "reports") / "report.md").exists()
        assert p.features and p.features["hook_type"]
        assert p.state == State.LEARNED


def test_learn_is_idempotent_and_keeps_analyzing_before_threshold(session, settings, tmp_path):
    _seed(session)
    settings.intelligence.min_samples = 1
    settings.analytics.learn_after_hours = 24 * 30  # threshold not reached at day 10
    storage = Storage(tmp_path / "storage")
    learn(session, storage, MockLLM(), settings, now=T0 + timedelta(days=10))
    learn(session, storage, MockLLM(), settings, now=T0 + timedelta(days=10))
    assert session.query(StrategyWeightsRow).count() == 1
    assert session.query(InsightRow).filter_by(feature="hook_type", value="shock", metric="retention").count() == 1
    assert session.get(Production, "OMS-20260901-0001").state == State.ANALYZING
    assert len(session.get(Production, "OMS-20260901-0001").reports) == 1
