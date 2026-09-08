from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.web import settings_store
from app.web.deps import WebContext, get_ctx
from app.web.schemas import OpenFolder, SettingsUpdate, TestConnection
from app.web.security import is_within

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read(ctx: WebContext = Depends(get_ctx)) -> dict:
    return settings_store.settings_view(ctx)


@router.put("")
def update(body: SettingsUpdate, ctx: WebContext = Depends(get_ctx)) -> dict:
    result = settings_store.apply_update(ctx, body)
    ctx.bus.publish("settings", result)
    return {**result, "settings": settings_store.settings_view(ctx)}


@router.post("/restore")
def restore(ctx: WebContext = Depends(get_ctx)) -> dict:
    settings_store.restore_defaults(ctx)
    ctx.bus.publish("settings", {"restored": True})
    return {"ok": True, "settings": settings_store.settings_view(ctx)}


@router.post("/test-connection")
def test_connection(body: TestConnection, ctx: WebContext = Depends(get_ctx)) -> dict:
    if not ctx.limit("test_connection"):
        raise HTTPException(429, "muitos testes seguidos; aguarde um minuto")
    return settings_store.test_connection(ctx, body.api_key, body.model)


@router.post("/youtube/disconnect")
def youtube_disconnect(ctx: WebContext = Depends(get_ctx)) -> dict:
    token = ctx.settings.resolve(ctx.settings.youtube_token_path)
    if token.is_file():
        token.unlink()
    ctx.orchestrator._youtube = None
    return {"ok": True, "settings": settings_store.settings_view(ctx)}


@router.post("/youtube/connect")
def youtube_connect(ctx: WebContext = Depends(get_ctx)) -> dict:
    """Runs the OAuth consent in a background job: the browser window opens on this machine."""
    settings = ctx.settings

    def run():
        from app.youtube.auth import get_credentials

        get_credentials(settings.resolve(settings.youtube_client_secret_path), settings.resolve(settings.youtube_token_path))
        ctx.orchestrator._youtube = None
        return "ok"

    return {"job": ctx.jobs.submit("youtube-auth", run).as_dict()}


@router.post("/open-folder")
def open_folder(body: OpenFolder, ctx: WebContext = Depends(get_ctx)) -> dict:
    view = settings_store.settings_view(ctx)["files"]
    target = Path({"project": view["project_dir"], "inbox": view["inbox_dir"], "ffmpeg": view["ffmpeg_binary"], "exports": view["exports_dir"]}[body.key])
    if body.key == "ffmpeg":
        target = target.parent
    root = Path(view["project_dir"])
    if body.key != "ffmpeg" and not is_within(target, root):
        raise HTTPException(400, "só pastas dentro do projeto podem ser abertas")
    if not target.is_dir():
        target.mkdir(parents=True, exist_ok=True) if body.key != "ffmpeg" else None
    if not target.is_dir():
        raise HTTPException(404, "pasta não encontrada")
    if os.name == "nt":
        subprocess.Popen(["explorer", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
    return {"ok": True, "path": str(target)}
