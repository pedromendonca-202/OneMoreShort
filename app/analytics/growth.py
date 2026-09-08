from app.analytics.schemas import ChannelBaseline, GrowthClass
def classify_growth(views_per_hour: float, baseline: ChannelBaseline) -> GrowthClass:
    ratio=views_per_hour/max(baseline.views_per_hour,1e-9)
    if ratio<.1:return GrowthClass.DEAD
    if ratio<.5:return GrowthClass.SLOW
    if ratio<1.5:return GrowthClass.NORMAL
    if ratio<4:return GrowthClass.ACCELERATING
    if ratio<10:return GrowthClass.VIRAL
    return GrowthClass.EXPLOSIVE
