from app.intelligence.knowledge import Knowledge
from app.intelligence.patterns import detect_patterns
from app.intelligence.schemas import VideoOutcome
def test_insights_and_knowledge():
 insights=detect_patterns([VideoOutcome(hook_type="shock",retention=.9),VideoOutcome(hook_type="question",retention=.3)])
 assert max(insights,key=lambda x:x.effect_vs_channel).value=="shock"
 k=Knowledge();k.add("best_hooks","shock");assert k.context_for("science").best_hooks==["shock"]
