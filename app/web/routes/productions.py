"""Productions: library, detail, pipeline actions, prompts, clip upload, video, metadata, report."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from app.core.db import session_scope
from app.web import actions
from app.web.deps import WebContext, get_ctx
from app.web.queries import inbox_clips, library_view, production_detail
from app.web.schemas import Confirm, MetadataEdit, NewProduction
from app.web.security import UPLOAD_MAX_FILE_BYTES, UPLOAD_MAX_TOTAL_BYTES, safe_clip_path

router = APIRouter(prefix="/api/productions", tags=["productions"])


def _detail(ctx: WebContext, pid: str) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        return production_detail(ctx, session, actions.get_production(session, pid))


@router.get("")
def list_productions(q: str = "", state: str = "", category: str = "", sort: str = "recent", limit: int = 200,
                     ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        return library_view(ctx, session, q=q[:80], state=state, category=category, sort=sort, limit=max(1, min(limit, 500)))


@router.post("")
def new_production(body: NewProduction, ctx: WebContext = Depends(get_ctx)) -> dict:
    pid, job = actions.start_production(ctx, force=body.force, prepare=body.prepare)
    return {"id": pid, "job": job.as_dict() if job else None}


@router.get("/{pid}")
def detail(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return _detail(ctx, pid)


@router.delete("/{pid}")
def delete(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    actions.delete_production(ctx, pid)
    return {"ok": True}


@router.post("/{pid}/prepare")
def prepare(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"job": actions.prepare(ctx, pid).as_dict()}


@router.post("/{pid}/collect")
def collect(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"job": actions.collect_and_finish(ctx, pid).as_dict()}


@router.post("/{pid}/finish")
def finish(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"job": actions.finish_only(ctx, pid).as_dict()}


@router.post("/{pid}/resume")
def resume(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"job": actions.resume(ctx, pid).as_dict()}


@router.post("/{pid}/publish")
def publish(pid: str, body: Confirm, ctx: WebContext = Depends(get_ctx)) -> dict:
    if not body.confirm:
        raise HTTPException(400, "a publicação exige confirmação explícita")
    return {"job": actions.publish(ctx, pid).as_dict()}


@router.post("/{pid}/reset")
def reset(pid: str, keep_topic: bool = True, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"job": actions.reset_production(ctx, pid, keep_topic=keep_topic).as_dict()}


@router.post("/{pid}/duplicate")
def duplicate(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    new_id, job = actions.duplicate_production(ctx, pid)
    return {"id": new_id, "job": job.as_dict()}


@router.get("/{pid}/prompts")
def prompts(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    return {"prompts": _detail(ctx, pid)["prompts"]}


@router.get("/{pid}/script.txt")
def script_txt(pid: str, ctx: WebContext = Depends(get_ctx)) -> PlainTextResponse:
    data = _detail(ctx, pid)
    lines = [f"ONE MORE SHORT - {pid}", f"Topic: {data.get('topic') or ''}", ""]
    if data.get("script"):
        lines += ["SCRIPT", ""]
        for beat in data["script"]["beats"]:
            lines.append(f"[{beat['start_s']:.0f}s-{beat['end_s']:.0f}s] ({beat['purpose']}) {beat['narration']}")
        lines.append("")
    for prompt in data["prompts"]:
        lines += [f"===== SCENE {prompt['scene']} ({prompt['start_s']}s-{prompt['end_s']}s) =====", prompt["text"], ""]
    return PlainTextResponse("\n".join(lines), headers={"Content-Disposition": f'attachment; filename="{pid}-roteiro.txt"'})


@router.get("/{pid}/video")
def video(pid: str, ctx: WebContext = Depends(get_ctx)):
    data = _detail(ctx, pid)
    if not data.get("final_video"):
        raise HTTPException(404, "vídeo final ainda não existe")
    return FileResponse(data["final_video"]["path"], media_type="video/mp4")


@router.get("/{pid}/report")
def report(pid: str, ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        production = actions.get_production(session, pid)
        if not production.reports:
            raise HTTPException(404, "ainda não há relatório para esta produção")
        latest = production.reports[-1]
        return {"markdown": latest.markdown, "verdict": latest.verdict, "virality_score": latest.virality_score,
                "created_at": latest.created_at.isoformat() if latest.created_at else None}


@router.put("/{pid}/metadata")
def metadata(pid: str, body: MetadataEdit, ctx: WebContext = Depends(get_ctx)) -> dict:
    return actions.edit_metadata(ctx, pid, title=body.title, description=body.description, hashtags=body.hashtags,
                                 visibility=body.visibility, publish_hour_local=body.publish_hour_local)


@router.delete("/{pid}/clips/{scene}")
def delete_clip(pid: str, scene: int, ctx: WebContext = Depends(get_ctx)) -> dict:
    actions.delete_clip(ctx, pid, scene)
    return {"ok": True}


@router.post("/{pid}/clips")
async def upload_clip(pid: str, request: Request, scene: int = Form(...), file: UploadFile = File(...),
                      ctx: WebContext = Depends(get_ctx)) -> dict:
    """Store one clip for one scene. The client file name is ignored; validation is by ffprobe."""
    with session_scope(ctx.orchestrator.engine) as session:
        production = actions.get_production(session, pid)
        state = production.state.value
        present = sum(1 for c in inbox_clips(ctx, production) if c["present"] and c["scene"] != scene)
    if state not in {"GENERATING", "NEEDS_HUMAN_ACTION", "FAILED"}:
        raise HTTPException(409, f"a produção não está aguardando clipes (estado {state})")
    if present >= 5:
        raise HTTPException(409, "a produção já tem cinco clipes")
    declared = request.headers.get("content-length")
    if declared and int(declared) > UPLOAD_MAX_FILE_BYTES + 64 * 1024:
        raise HTTPException(413, "arquivo acima do limite de 300 MB")
    inbox = ctx.orchestrator.storage.dir_for(pid, "manual_input")
    try:
        target = safe_clip_path(inbox, scene)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err
    used = sum(p.stat().st_size for p in inbox.iterdir() if p.is_file())
    fd, tmp_name = tempfile.mkstemp(prefix=".upload-", suffix=".part", dir=inbox)
    tmp = Path(tmp_name)
    written = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > UPLOAD_MAX_FILE_BYTES:
                    raise HTTPException(413, "arquivo acima do limite de 300 MB")
                if used + written > UPLOAD_MAX_TOTAL_BYTES:
                    raise HTTPException(413, "limite total de 1,2 GB por produção atingido")
                out.write(chunk)
        if written == 0:
            raise HTTPException(400, "arquivo vazio")
        from app.veo.validator import validate_segment

        expected = float(ctx.settings.veo.duration_seconds)
        try:
            report = validate_segment(tmp, expect_seconds=expected, tolerance=max(0.25, min(1, expected * .2)))
        except Exception as err:
            raise HTTPException(422, f"o arquivo não é um vídeo legível: {str(err)[:160]}") from err
        if not report.ok:
            raise HTTPException(422, "clipe recusado: " + "; ".join(report.issues))
        for old in inbox.iterdir():  # one file per scene: remove any previous upload for this scene
            if old.is_file() and old != tmp and (old == target or _scene_of(old.stem) == scene):
                old.unlink(missing_ok=True)
        shutil.move(str(tmp), str(target))
    finally:
        tmp.unlink(missing_ok=True)
    thumb = ctx.orchestrator.storage.root / "thumbs" / f"{pid}_clip{scene}.jpg"
    thumb.unlink(missing_ok=True)
    ctx.bus.publish("clip", {"production_id": pid, "scene": scene})
    with session_scope(ctx.orchestrator.engine) as session:
        clips = inbox_clips(ctx, actions.get_production(session, pid))
    return next(c for c in clips if c["scene"] == scene)


def _scene_of(stem: str) -> int | None:
    from app.web.queries import _NUMBERED

    match = _NUMBERED.search(stem)
    return int(match.group(1)) if match else None
