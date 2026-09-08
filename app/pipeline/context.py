from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.storage import Storage
@dataclass
class PipelineContext:
 session:Session; settings:Settings; storage:Storage; llm:object; yt:object
