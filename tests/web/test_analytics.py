"""Analytics and intelligence read models over synthetic published productions."""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.db import session_scope
from app.core.models import AnalyticsSnapshot, Insight, Production, RetentionCurve, Script, Topic, Upload, VideoMetadata, VideoReport
from app.core.states import State
from tests.web.conftest import FIXED_NOW


def _beats():
    return [
        {"index": 1, "start_s": 0, "end_s": 3, "purpose": "hook", "narration": "You've probably seen this map your whole life. It's wrong."},
        {"index": 2, "start_s": 3, "end_s": 9, "purpose": "setup", "narration": "Here is what maps show."},
        {"index": 3, "start_s": 9, "end_s": 17, "purpose": "escalation", "narration": "But that is not quite true. Greenland is tiny."},
        {"index": 4, "start_s": 17, "end_s": 25, "purpose": "revelation", "narration": "The real explanation."},
        {"index": 5, "start_s": 25, "end_s": 33, "purpose": "payoff", "narration": "Examples and comparison."},
        {"index": 6, "start_s": 33, "end_s": 35, "purpose": "ending", "narration": "Now you will never look at it the same way."},
    ]


def seed_published(engine, pid: str, *, title: str, category: str, views: int, retention_pct: float, days_ago: int,
                   curve: list[float] | None = None, subs: int = 100, likes: int = 500, report: bool = False, structure="hook-setup-escalation-revelation-payoff-ending"):
    published = FIXED_NOW - timedelta(days=days_ago)
    with session_scope(engine) as session:
        session.add(Production(id=pid, state=State.ANALYZING, started_at=published, created_at=published,
                               features={"production_id": pid, "title": title, "category": category, "hook_type": "shock", "ending_type": "loop",
                                         "duration_s": 34, "retention": retention_pct / 100, "completion": retention_pct / 100 * 0.6,
                                         "views": views, "sub_conversion": subs / views, "narrative_structure": structure}))
        session.add(Topic(production_id=pid, topic=title, category=category, final_score=84, selected=True, selection_reason="test"))
        session.add(Script(production_id=pid, data={"title_working": title, "beats": _beats(), "hook_type": "shock", "ending_type": "loop",
                                                     "est_duration_s": 35, "total_words": 80}, text="", hook_type="shock", ending_type="loop", est_duration_s=35, total_words=80))
        session.add(VideoMetadata(production_id=pid, title=title, description="desc", hashtags=["#Shorts"]))
        session.add(Upload(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", url="https://youtu.be/x", status="published", published_at=published, uploaded_at=published))
        session.add(AnalyticsSnapshot(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", captured_at=FIXED_NOW, age_minutes=days_ago * 1440,
                                      schedule_slot_min=1440, source="analytics_api", views=views, likes=likes, comments=10, shares=20,
                                      subscribers_gained=subs, avg_view_pct=retention_pct, avg_view_duration_s=28))
        if curve:
            points = [{"elapsed_ratio": i / (len(curve) - 1), "watch_ratio": v} for i, v in enumerate(curve)]
            from app.analytics.retention import analyze_retention
            from app.scripting.schemas import Script as ScriptModel

            analysis = analyze_retention(points, ScriptModel.model_validate({"title_working": title, "beats": _beats(), "hook_type": "shock", "ending_type": "loop",
                                                                             "cta_used": False, "loop_used": True, "total_words": 80, "est_duration_s": 35}), None, 0.08)
            session.add(RetentionCurve(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", captured_at=FIXED_NOW, points=points, analysis=analysis.model_dump()))
        if report:
            session.add(VideoReport(production_id=pid, youtube_video_id=f"yt-{pid[-4:]}", markdown="# r", virality_score=88,
                                    verdict={"what_worked": ["Strong shock hook: 92% still watching after the first seconds", "Loop ending"],
                                             "what_failed": ["Retention dropped 12% at 22s (beat 4): retention drop at transition or pacing change"],
                                             "next_recommendation": "Use: same shock hook style; similar pacing; tighten the segment around the first retention drop",
                                             "growth": "viral"}))


@pytest.fixture
def channel(ctx):
    engine = ctx.orchestrator.engine
    seed_published(engine, "OMS-20260907-0001", title="The viral world map mistake", category="science", views=312480, retention_pct=81, days_ago=1,
                   curve=[1.0, 0.92, 0.85, 0.8, 0.74, 0.68, 0.55, 0.5, 0.42, 0.35, 0.28], subs=2140, likes=18204, report=True)
    seed_published(engine, "OMS-20260906-0001", title="The color that does not exist", category="curiosities", views=18000, retention_pct=64, days_ago=2,
                   curve=[1.0, 0.8, 0.7, 0.6, 0.5, 0.42, 0.35, 0.3, 0.25, 0.18, 0.12], subs=40, likes=600, structure="hook-setup-revelation-payoff-ending")
    seed_published(engine, "OMS-20260905-0001", title="Why coffee wakes you up", category="health", views=24000, retention_pct=67, days_ago=3,
                   curve=[1.0, 0.85, 0.7, 0.62, 0.55, 0.45, 0.4, 0.33, 0.28, 0.2, 0.12], subs=60, likes=800)
    with session_scope(engine) as session:
        session.add_all([
            Insight(feature="hook_type", value="shock", metric="retention", effect=0.19, n=18, confidence=0.92),
            Insight(feature="category", value="science", metric="sub_conversion", effect=2.2, n=18, confidence=0.84),
            Insight(feature="duration_bucket", value="32-40s", metric="completion", effect=0.27, n=16, confidence=0.87),
            Insight(feature="ending_type", value="loop", metric="sub_conversion", effect=1.8, n=14, confidence=0.78),
            Insight(feature="visual_style", value="dynamic", metric="retention", effect=0.32, n=12, confidence=0.71),
        ])
    return engine


def test_today_lists_last_published_and_channel_summary(client, channel):
    data = client.get("/api/today").json()
    titles = [item["title"] for item in data["last_published"]]
    assert titles == ["The viral world map mistake", "The color that does not exist", "Why coffee wakes you up"]
    assert data["last_published"][0]["date_label"] == "Ontem"
    assert data["last_published"][0]["retention"] == 81
    assert data["channel"]["published"] == 3 and data["channel"]["avg_retention"] == 71
    assert len(data["channel"]["series"]) == 30


def test_analytics_view_kpis_curve_and_script_mapping(client, channel):
    data = client.get("/api/analytics/OMS-20260907-0001").json()
    assert data["available"] is True
    kpis = {k["key"]: k for k in data["kpis"]}
    assert kpis["views"]["value"] == 312480 and kpis["views"]["delta"] > 1000
    assert kpis["retention"]["value"] == 81 and kpis["retention"]["delta"] in (15, 16)  # 81 vs mean(64, 67)
    assert kpis["likes"]["share"] == "5,8%"
    assert data["curve"]["points"][0]["value"] == 100 and len(data["curve"]["points"]) == 11
    major = next(a for a in data["curve"]["annotations"] if a["kind"] == "major")
    assert major["label"].startswith("queda de 13% aos 24s") and major["scene"] == 4
    assert major["sentence"]  # the script sentence being narrated at the drop
    highlighted = [s for s in data["script_timeline"] if s["highlight"]]
    assert len(highlighted) == 1 and highlighted[0]["range"].startswith("00:17")
    assert data["worked"][0]["title"].startswith("Strong shock hook")
    assert data["failed"][0]["title"].startswith("Retention dropped")
    assert len(data["recommendation"]) == 3
    assert data["comparison"]["gain"] > 100 and len(data["comparison"]["video"]) == 11
    assert data["published_label"].startswith("publicado ontem")
    assert client.get("/api/analytics/latest").json()["id"] == "OMS-20260907-0001"


def test_analytics_without_snapshots_is_explicitly_unavailable(client, ctx):
    data = client.post("/api/productions", json={"force": False}).json()
    view = client.get(f"/api/analytics/{data['id']}").json()
    assert view["available"] is False and "analytics" in view["reason"].lower()


def test_intelligence_view(client, channel):
    data = client.get("/api/intelligence").json()
    assert data["available"] is True and data["sample"] == 3
    highlights = {h["key"]: h for h in data["highlights"]}
    assert highlights["hooks"]["value"].endswith("pts") and highlights["hooks"]["n"] == 18
    assert highlights["themes"]["value"] == "3,2x"
    assert highlights["duration"]["value"] == "32s – 40s"
    assert highlights["endings"]["value"] == "2,8x"
    assert len(data["patterns"]) == 5 and data["patterns"][0]["confidence"] == 92 and data["patterns"][0]["feature"] == "hook_type"
    themes = {t["category"]: t for t in data["themes"]}
    assert themes["ciência"]["retention"] == 81 and themes["ciência"]["subs_per_1k"] == 6.8
    assert data["structures"][0]["name"].startswith("Gancho → Contexto")
    assert len(data["scatter"]["points"]) == 3
    assert 1 <= len(data["tests"]) <= 3 and data["tests"][0]["number"] == 1


def test_intelligence_empty_state(client):
    data = client.get("/api/intelligence").json()
    assert data["available"] is False and data["sample"] == 0


def test_collect_and_learn_are_rate_limited(client):
    assert client.post("/api/analytics/collect").status_code == 200
    assert client.post("/api/analytics/collect").status_code == 200
    assert client.post("/api/analytics/collect").status_code == 429
