from statistics import mean, median
from app.analytics.schemas import Comparison
def compare(video, channel_videos) -> Comparison:
    values=[float(getattr(v,"views",v.get("views",0))) for v in channel_videos]; current=float(getattr(video,"views",video.get("views",0)))
    if not values:return Comparison()
    m=mean(values); return Comparison(vs_mean=current/m if m else 0,vs_median=current/median(values) if median(values) else 0,
      vs_last5=current/mean(values[-5:]) if mean(values[-5:]) else 0,vs_last10=current/mean(values[-10:]) if mean(values[-10:]) else 0,
      vs_category=current/m if m else 0,rank=1+sum(v>current for v in values))
