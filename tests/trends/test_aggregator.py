from __future__ import annotations

from datetime import UTC, datetime

from app.llm.mock import MockLLM
from app.trends.aggregator import ClusterProposal, aggregate
from app.trends.base import TrendSignal


def signal(source: str, title: str, **metrics: float) -> TrendSignal:
    return TrendSignal(source=source, title=title, metrics=metrics, fetched_at=datetime(2026, 9, 7, tzinfo=UTC))


def test_aggregate_merges_duplicate_topics_across_sources():
    clusters = aggregate([
        signal("youtube", "NASA discovers evidence of water on Mars", views=1_000_000),
        signal("reddit", "Evidence of water found on Mars by NASA", score=30_000),
        signal("hackernews", "A new battery breakthrough", score=800),
    ])
    mars = next(c for c in clusters if "mars" in c.topic.lower())
    assert len(mars.signals) == 2
    assert mars.sources == {"youtube", "reddit"}
    assert mars.momentum > 0


def test_aggregate_honours_valid_llm_semantic_merge():
    signals = [
        signal("youtube", "The moon is shrinking", views=1000),
        signal("reddit", "New lunar surface cracks", score=100),
    ]
    llm = MockLLM(handlers={
        "ClusterProposal": lambda req: ClusterProposal.model_validate({
            "clusters": [{"topic": "Moon changes", "signal_indexes": [0, 1]}]
        })
    })
    clusters = aggregate(signals, llm=llm)
    assert len(clusters) == 1
    assert clusters[0].topic == "Moon changes"


def test_invalid_llm_cluster_proposal_falls_back_to_deterministic_clusters():
    signals = [signal("youtube", "Mars news"), signal("reddit", "Battery news")]
    llm = MockLLM(handlers={
        "ClusterProposal": lambda req: {"clusters": [{"topic": "bad", "signal_indexes": [99]}]}
    })
    assert len(aggregate(signals, llm=llm)) == 2
