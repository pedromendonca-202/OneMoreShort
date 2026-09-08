from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.db import session_scope
from app.web.deps import WebContext, get_ctx
from app.web.queries import today_view

router = APIRouter(prefix="/api", tags=["today"])


@router.get("/today")
def today(ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        return today_view(ctx, session)
