from app.analytics.schemas import EngagementRates
def engagement_rates(stats) -> EngagementRates:
    views=max(1,float(getattr(stats,"views",0) if not isinstance(stats,dict) else stats.get("views",0)))
    get=lambda key: float(getattr(stats,key,0) if not isinstance(stats,dict) else stats.get(key,0))
    likes,comments,shares,subs=get("likes"),get("comments"),get("shares"),get("subscribers_gained")
    return EngagementRates(like_rate=likes/views,comment_rate=comments/views,share_rate=shares/views,sub_conversion=subs/views,
                           engagement_rate=(likes+comments+shares)/views,view_to_like=views/max(likes,1),view_to_sub=views/max(subs,1))
