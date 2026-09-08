from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.db import session_scope
from app.web.deps import WebContext, get_ctx
from app.web.queries import intelligence_view

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.get("/intelligence")
def intelligence(ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        return intelligence_view(ctx, session)
