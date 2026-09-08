from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import session_scope
from app.core.models import Production
from app.core.states import State
from app.web import actions
from app.web.deps import WebContext, get_ctx
from app.web.queries import analytics_view, published_at

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/latest")
def latest(ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        rows = [r for r in session.query(Production).filter(Production.state.in_([State.PUBLISHED, State.ANALYZING, State.LEARNED])).all()
                if r.upload is not None]
        rows.sort(key=lambda r: published_at(r) or ctx.now(), reverse=True)
        return {"id": rows[0].id if rows else None}


@router.get("/analytics/{pid}")
def analytics(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        return analytics_view(ctx, session, actions.get_production(session, pid))


@router.post("/analytics/collect")
def collect(ctx: WebContext = Depends(get_ctx)) -> dict:
    if not ctx.limit("analytics"):
        raise HTTPException(429, "aguarde um pouco antes de coletar de novo")
    return {"job": ctx.jobs.submit("analytics", lambda: ctx.orchestrator.collect_analytics()).as_dict()}


@router.post("/learn")
def learn(ctx: WebContext = Depends(get_ctx)) -> dict:
    if not ctx.limit("learn"):
        raise HTTPException(429, "aguarde um pouco antes de aprender de novo")
    return {"job": ctx.jobs.submit("learn", lambda: ctx.orchestrator.learn().model_dump()).as_dict()}
