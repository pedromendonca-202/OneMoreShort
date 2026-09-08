from app.research.schemas import StrategyWeights
def update_strategy(session, insights, cfg):
 weights={}
 for i in insights:
  if i.feature=="category":weights[i.value]=max(.1,1+i.effect_vs_channel)
 return StrategyWeights(category_weights=weights,exploration_ratio=getattr(getattr(cfg,"intelligence",cfg),"exploration_ratio",.3))
