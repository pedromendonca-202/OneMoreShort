from pydantic import BaseModel,Field
class VideoOutcome(BaseModel):
    hook_type:str="curiosity"; category:str="general"; views:float=0; retention:float=0; engagement:float=0
class Insight(BaseModel):
    feature:str; value:str; metric:str; effect_vs_channel:float; n:int; confidence:float
class IntelligenceSummary(BaseModel):
    insights:list[Insight]=Field(default_factory=list)
class ABResult(BaseModel):
    dimension:str; winner:str|None=None; confidence:float=0
