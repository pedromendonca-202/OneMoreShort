from app.research.schemas import KnowledgeContext
class Knowledge:
 def __init__(self):self.entries=[]
 def add(self,kind,payload):self.entries.append((kind,payload))
 def context_for(self,topic_category):
  grouped={k:[p for kind,p in self.entries if kind==k] for k in ("best_hooks","best_structures","failed_patterns","successful_prompts")}
  return KnowledgeContext(**grouped)
