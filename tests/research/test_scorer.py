from __future__ import annotations

from app.llm.mock import MockLLM
from app.research.schemas import KnowledgeContext, ScoringWeights, TopicScore
from app.research.scorer import compute_final, score_topics
from app.trends.aggregator import TrendCluster
from app.trends.base import TrendSignal


def topic(**changes) -> TopicScore:
    values = dict(topic="Mars water", category="science", trend_score=80, viral_potential=70, us_relevance=60,
                  competition=20, shorts_fit=90, originality=80, risk=10, reasons=["Strong visual reveal"])
    values.update(changes)
    return TopicScore(**values)


def test_compute_final_penalizes_competition_and_risk_deterministically():
    weights = ScoringWeights(trend_score=0.5, viral_potential=0, us_relevance=0, competition=0.25, shorts_fit=0, originality=0, risk=0.25)
    assert compute_final(topic(), weights) == 82.5  # 80*.5 + (100-20)*.25 + (100-10)*.25


def test_score_topics_uses_llm_dimensions_but_owns_final_score():
    cluster = TrendCluster(topic="Mars water", sources={"youtube"}, momentum=7.0, signals=[TrendSignal(source="youtube", title="Mars water")])
    llm = MockLLM(handlers={
        "TopicScore": lambda req: topic(topic="different title", final_score=0),
    })
    result = score_topics(llm, [cluster], weights=ScoringWeights(), knowledge=KnowledgeContext())
    assert result[0].topic == "Mars water"
    assert result[0].final_score == compute_final(result[0], ScoringWeights())
    assert result[0].final_score != 0
