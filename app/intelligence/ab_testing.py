from app.intelligence.schemas import ABResult
class ABTest:
 def assign(self,production,dimension): return "A" if hash(f"{getattr(production,'id','')}{dimension}")%2==0 else "B"
 def evaluate(self,session,dimension): return ABResult(dimension=dimension)
