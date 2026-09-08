"""Topic scoring, automatic selection, and fact-aware deep research."""

from app.research.deep_research import deep_research
from app.research.schemas import Research, TopicScore
from app.research.scorer import score_topics
from app.research.selector import select_topic

__all__ = ["Research", "TopicScore", "deep_research", "score_topics", "select_topic"]
