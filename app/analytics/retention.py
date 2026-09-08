from __future__ import annotations
from app.analytics.schemas import Drop, RetentionAnalysis
def analyze_retention(curve, script=None, storyboard=None, threshold=.08) -> RetentionAnalysis:
    def value(point, key):
        return point.get(key) if isinstance(point, dict) else getattr(point, key)
    points=[(float(value(p,"elapsed_ratio")),float(value(p,"watch_ratio"))) for p in curve]
    drops=[]
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        if y0-y1>=threshold:
            t=x1*40; beat=next((b.index for b in getattr(script,"beats",[]) if b.start_s<=t<b.end_s),None)
            drops.append(Drop(t_s=t,delta=y0-y1,beat=beat,segment=min(5,max(1,int(t//8)+1)),likely_cause="retention drop at transition or pacing change"))
    return RetentionAnalysis(points=points,drops=drops,completion_est=points[-1][1] if points else 0,avg_pct=sum(y for _,y in points)/len(points) if points else 0)
