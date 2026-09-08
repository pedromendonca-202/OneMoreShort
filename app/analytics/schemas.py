from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field

class GrowthClass(StrEnum):
    DEAD="dead"; SLOW="slow"; NORMAL="normal"; ACCELERATING="accelerating"; VIRAL="viral"; EXPLOSIVE="explosive"
class ChannelBaseline(BaseModel):
    views_per_hour: float = 1
class EngagementRates(BaseModel):
    like_rate: float=0; comment_rate: float=0; share_rate: float=0; sub_conversion: float=0; engagement_rate: float=0; view_to_like: float=0; view_to_sub: float=0
class Drop(BaseModel):
    t_s: float; delta: float; beat: int | None=None; segment: int | None=None; sentence: str | None=None; likely_cause: str
class RetentionAnalysis(BaseModel):
    points: list[tuple[float,float]]; drops: list[Drop]=Field(default_factory=list); completion_est: float=0; avg_pct: float=0
class Comparison(BaseModel):
    vs_mean: float=0; vs_median: float=0; vs_last5: float=0; vs_last10: float=0; vs_category: float=0; rank: int=1
class VideoReport(BaseModel):
    markdown: str; what_worked: list[str]=Field(default_factory=list); what_failed: list[str]=Field(default_factory=list); next_recommendation: str=""; virality_score: float=0
