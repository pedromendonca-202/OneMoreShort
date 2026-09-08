"""Public trend feeds and resilient topic clustering."""

from app.trends.aggregator import TrendCluster, aggregate
from app.trends.base import TrendSignal, TrendSource

__all__ = ["TrendCluster", "TrendSignal", "TrendSource", "aggregate"]
