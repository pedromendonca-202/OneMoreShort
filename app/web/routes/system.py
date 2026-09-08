"""Session, health, metrics, costs, SSE stream and thumbnails."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.web.deps import WebContext, get_ctx
from app.web.thumbs import clip_thumbnail, thumbnail_for

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/session")
def session(ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"csrf_token": ctx.csrf_token, "server": "localhost:8787", "now": ctx.now().isoformat(),
            "mode": ctx.settings.mode, "timezone": ctx.settings.timezone}


def health_items(ctx: WebContext) -> list[dict]:
    """The `doctor` command as a list the Ajustes screen can render."""
    settings = ctx.settings
    items: list[dict] = [{"key": "server", "name": "Servidor", "status": "ok", "label": "Online"}]
    try:
        with ctx.orchestrator.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        items.append({"key": "database", "name": "Banco de dados", "status": "ok", "label": "Online"})
    except Exception as err:
        items.append({"key": "database", "name": "Banco de dados", "status": "error", "label": "Indisponível", "detail": str(err)[:200]})
    try:
        from app.editing.ffmpeg import resolve_ffmpeg

        resolve_ffmpeg()
        items.append({"key": "ffmpeg", "name": "FFmpeg", "status": "ok", "label": "Disponível"})
    except Exception:
        items.append({"key": "ffmpeg", "name": "FFmpeg", "status": "error", "label": "Não encontrado"})
    token = settings.resolve(settings.youtube_token_path)
    secret = settings.resolve(settings.youtube_client_secret_path)
    if token.is_file():
        items.append({"key": "youtube", "name": "YouTube API", "status": "ok", "label": "Conectado"})
    elif secret.is_file():
        items.append({"key": "youtube", "name": "YouTube API", "status": "warn", "label": "Autorização pendente"})
    else:
        items.append({"key": "youtube", "name": "YouTube API", "status": "warn", "label": "Não configurado"})
    if settings.mode == "mock":
        items.append({"key": "gemini", "name": "Gemini / IA", "status": "warn", "label": "Modo de exemplo"})
    elif settings.google_api_key:
        items.append({"key": "gemini", "name": "Gemini / IA", "status": "ok", "label": "Conectado"})
    else:
        items.append({"key": "gemini", "name": "Gemini / IA", "status": "error", "label": "Sem chave"})
    root = settings.resolve(settings.paths.storage_root)
    try:
        usage = shutil.disk_usage(root)
        free_gb = usage.free / 1e9
        status = "ok" if free_gb > 5 else "warn"
        items.append({"key": "storage", "name": "Armazenamento", "status": status,
                      "label": "Saudável" if status == "ok" else f"{free_gb:.1f} GB livres"})
    except OSError:
        items.append({"key": "storage", "name": "Armazenamento", "status": "error", "label": "Indisponível"})
    return items


@router.get("/health")
def health(ctx: WebContext = Depends(get_ctx)) -> dict:
    items = health_items(ctx)
    missing = ctx.settings.missing_live_requirements()
    return {"items": items, "ok": all(item["status"] != "error" for item in items), "missing": missing,
            "mode": ctx.settings.mode, "generation_mode": ctx.settings.generation.mode}


@router.get("/metrics")
def metrics(ctx: WebContext = Depends(get_ctx)) -> dict:
    return ctx.orchestrator.metrics()


@router.get("/costs")
def costs(days: int = 30, ctx: WebContext = Depends(get_ctx)) -> dict:
    return ctx.orchestrator.costs(max(1, min(days, 365)))


@router.get("/events")
async def events(request: Request, ctx: WebContext = Depends(get_ctx)):
    ctx.bus.bind_loop(asyncio.get_running_loop())
    queue = ctx.bus.subscribe()

    async def stream():
        try:
            yield {"event": "hello", "data": json.dumps({"job": ctx.jobs.current.as_dict() if ctx.jobs.current else None})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": event["type"], "data": json.dumps(event, default=str)}
        finally:
            ctx.bus.unsubscribe(queue)

    return EventSourceResponse(stream(), ping=20)


@router.get("/thumbs/{production_id}")
def thumb(production_id: str, clip: int | None = None, ctx: WebContext = Depends(get_ctx)):
    path = clip_thumbnail(ctx, production_id, clip) if clip else thumbnail_for(ctx, production_id)
    if path is None:
        raise HTTPException(404, "sem miniatura")
    return FileResponse(Path(path), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=60"})
