from datetime import UTC,datetime,timedelta
from app.analytics.collector import due_snapshots
from app.analytics.engagement import engagement_rates
from app.analytics.growth import classify_growth
from app.analytics.retention import analyze_retention
from app.analytics.schemas import ChannelBaseline,GrowthClass
def test_due_growth_rates_and_drop():
 assert due_snapshots(datetime.now(UTC)-timedelta(minutes=61),datetime.now(UTC),[10])==[30,60]
 assert classify_growth(12,ChannelBaseline(views_per_hour=1))==GrowthClass.EXPLOSIVE
 assert engagement_rates({"views":100,"likes":10,"comments":2,"shares":3,"subscribers_gained":1}).engagement_rate==.15
 assert analyze_retention([{"elapsed_ratio":0,"watch_ratio":1},{"elapsed_ratio":.2,"watch_ratio":.8}]).drops
