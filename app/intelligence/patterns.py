from collections import defaultdict
from app.intelligence.schemas import Insight
def detect_patterns(videos):
 if not videos:return []
 base=sum(v.retention for v in videos)/len(videos); groups=defaultdict(list)
 for v in videos:groups[("hook_type",v.hook_type)].append(v)
 return [Insight(feature=k[0],value=k[1],metric="retention",effect_vs_channel=sum(x.retention for x in g)/len(g)-base,n=len(g),confidence=min(1,len(g)/5)) for k,g in groups.items()]
