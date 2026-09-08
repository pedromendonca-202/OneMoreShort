from __future__ import annotations

from app.analytics.comparison import compare
from app.analytics.engagement import engagement_rates
from app.analytics.report import build_report, rate_engagement, rate_retention
from app.analytics.retention import analyze_retention
from app.analytics.schemas import GrowthClass
from app.intelligence.schemas import VideoOutcome
from app.llm.mock import MockLLM


def test_ratings_follow_spec_bands():
    assert rate_retention(0.87) == "Excellent"
    assert rate_retention(0.70) == "Good"
    assert rate_retention(0.55) == "Average"
    assert rate_retention(0.30) == "Below Average"
    assert rate_engagement(1.8) == "Above Average"
    assert rate_engagement(0.5) == "Below Average"


def test_report_markdown_has_spec_sections_and_numbers():
    stats = {"views": 1_240_832, "likes": 62_401, "comments": 3_842, "shares": 9_214, "subscribers_gained": 8_104}
    rates = engagement_rates(stats)
    retention = analyze_retention([{"elapsed_ratio": i / 10, "watch_ratio": 1 - i * 0.04} for i in range(11)])
    comparison = compare(stats, [{"views": 100_000}, {"views": 300_000}, stats])
    outcome = VideoOutcome(production_id="OMS-20260907-0001", hook_type="curiosity", category="science", views=stats["views"],
                           retention=retention.avg_pct, engagement=rates.engagement_rate, duration_s=35, ending_type="loop")
    report = build_report(MockLLM(), outcome, stats, rates, retention, comparison, GrowthClass.VIRAL,
                          title="The Strange Reason...", avg_view_duration_s=34.8)
    md = report.markdown
    assert "VIDEO PERFORMANCE REPORT" in md and "The Strange Reason..." in md
    assert "1,240,832" in md and "34.8s" in md and "8,104" in md
    assert "WHAT WORKED" in md and "WHAT FAILED" in md and "NEXT VIDEO RECOMMENDATION" in md
    assert report.what_worked and report.next_recommendation
    assert 0 <= report.virality_score <= 100
    assert "Retention:" in md and "Hook:" in md and "Engagement:" in md
