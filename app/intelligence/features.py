from app.intelligence.schemas import VideoOutcome
def extract_features(production) -> VideoOutcome:
 topic=getattr(production,"selected_topic",None)
 return VideoOutcome(category=getattr(topic,"category","general") or "general")
