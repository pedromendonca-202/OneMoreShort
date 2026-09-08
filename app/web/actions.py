"""State-changing operations the panel offers on top of the Orchestrator.

Long operations are submitted to the JobRunner; the few edits that are panel-specific (reset a
production to pick another topic, edit metadata before publishing, delete a production) live here so
the routes and the chat tools share one implementation.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.core.db import session_scope
from app.core.logging import record_event
from app.core.models import ContinuityBible as BibleRow, Production, Prompt as PromptRow, Research as ResearchRow, \
    Script as ScriptRow, Storyboard as StoryRow, Topic, VideoMetadata as MetadataRow
from app.core.states import NEVER_UPLOAD, State
from app.web.events import Job


def get_production(session, pid: str) -> Production:
    production = session.get(Production, pid)
    if production is None:
        raise ValueError(f"produção desconhecida: {pid}")
    return production


def start_production(ctx, *, force: bool = False, prepare: bool = True) -> tuple[str, Job | None]:
    pid = ctx.orchestrator.new_production(force=force)
    ctx.bus.publish("state", {"production_id": pid})
    job = ctx.jobs.submit("prepare", lambda: ctx.orchestrator.prepare(pid), production_id=pid) if prepare else None
    return pid, job


def prepare(ctx, pid: str) -> Job:
    return ctx.jobs.submit("prepare", lambda: ctx.orchestrator.prepare(pid), production_id=pid)


def collect_and_finish(ctx, pid: str) -> Job:
    def run():
        ctx.orchestrator.collect(pid)
        return str(ctx.orchestrator.finish(pid))

    return ctx.jobs.submit("finish", run, production_id=pid)


def finish_only(ctx, pid: str) -> Job:
    return ctx.jobs.submit("finish", lambda: str(ctx.orchestrator.finish(pid)), production_id=pid)


def resume(ctx, pid: str) -> Job:
    return ctx.jobs.submit("resume", lambda: ctx.orchestrator.resume(pid), production_id=pid)


def publish(ctx, pid: str) -> Job:
    """Explicit publication: only from READY, only with a stored final video and metadata."""
    from app.metadata.schemas import VideoMetadata

    with session_scope(ctx.orchestrator.engine) as session:
        production = get_production(session, pid)
        if production.state in NEVER_UPLOAD or production.state != State.READY:
            raise ValueError(f"não é possível publicar no estado {production.state.value}")
        if production.final_video is None or not Path(production.final_video.path).is_file():
            raise ValueError("o vídeo final não existe; monte o vídeo antes de publicar")
        if production.video_metadata is None:
            raise ValueError("título e descrição ainda não foram gerados")
        row = production.video_metadata
        final = Path(production.final_video.path)
        meta = VideoMetadata(title=row.title, description=row.description, hashtags=row.hashtags or ["#Shorts"], tags=row.tags or [],
                             category_id=row.category_id, publish_at=row.publish_at, pinned_comment=row.pinned_comment,
                             thumbnail_time_s=row.thumbnail_time_s or 1)

    def run():
        with session_scope(ctx.orchestrator.engine) as session:
            production = get_production(session, pid)
            ctx.orchestrator._upload(session, production, final, meta)
        return ctx.orchestrator.status(pid)["state"]

    return ctx.jobs.submit("publish", run, production_id=pid)


def edit_metadata(ctx, pid: str, *, title: str, description: str, hashtags: list[str], visibility: str,
                  publish_hour_local: int | None) -> dict[str, Any]:
    from datetime import UTC, timedelta
    from zoneinfo import ZoneInfo

    tags = [h if h.startswith("#") else f"#{h}" for h in (h.strip() for h in hashtags) if h]
    if "#Shorts" not in tags:
        tags = ["#Shorts", *tags]
    with session_scope(ctx.orchestrator.engine) as session:
        production = get_production(session, pid)
        row = production.video_metadata or MetadataRow(production_id=pid, title=title, description=description)
        row.title, row.description, row.hashtags = title.strip()[:100], description.strip(), tags[:6]
        row.publish_at = None
        if visibility == "scheduled":
            tz = ZoneInfo(ctx.settings.upload.timezone)
            local = ctx.now().astimezone(tz)
            hour = publish_hour_local if publish_hour_local is not None else ctx.settings.upload.publish_hour_local
            candidate = local.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate <= local + timedelta(minutes=15):
                candidate += timedelta(days=1)
            row.publish_at = candidate.astimezone(UTC)
        session.add(row)
        production.config_snapshot = {**(production.config_snapshot or {}), "publish_visibility": visibility}
        record_event(session, action="metadata.edit", status="ok", production_id=pid, stage="metadata")
    ctx.settings.upload.visibility = visibility  # the uploader reads the privacy from settings
    ctx.bus.publish("state", {"production_id": pid})
    return {"title": title, "visibility": visibility}


def reset_production(ctx, pid: str, *, keep_topic: bool) -> Job:
    """Drop the generated artefacts so `prepare` runs again (new topic, or the same topic with a new script)."""
    with session_scope(ctx.orchestrator.engine) as session:
        production = get_production(session, pid)
        if production.state not in {State.DISCOVERING, State.SELECTED, State.RESEARCHING, State.SCRIPTING, State.STORYBOARDING,
                                    State.GENERATING, State.NEEDS_HUMAN_ACTION, State.FAILED}:
            raise ValueError("só é possível refazer antes dos clipes serem validados")
        session.query(PromptRow).filter_by(production_id=pid).delete()
        session.query(BibleRow).filter_by(production_id=pid).delete()
        session.query(StoryRow).filter_by(production_id=pid).delete()
        session.query(ScriptRow).filter_by(production_id=pid).delete()
        if not keep_topic:
            session.query(ResearchRow).filter_by(production_id=pid).delete()
            session.query(Topic).filter_by(production_id=pid).delete()
        production.state, production.previous_state = (State.SELECTED if keep_topic else State.DISCOVERING), production.state
        production.human_action, production.error = None, None
        record_event(session, action="reset", status="ok", production_id=pid, stage="script" if keep_topic else "discover",
                     detail={"keep_topic": keep_topic})
    prompts_dir = ctx.orchestrator.storage.dir_for(pid, "prompts")
    for file in prompts_dir.glob("manual_prompt_*.txt"):
        file.unlink(missing_ok=True)
    ctx.bus.publish("state", {"production_id": pid})
    return ctx.jobs.submit("prepare", lambda: ctx.orchestrator.prepare(pid), production_id=pid)


def duplicate_production(ctx, pid: str) -> tuple[str, Job]:
    """New production reusing the selected topic; research, script and prompts are regenerated."""
    with session_scope(ctx.orchestrator.engine) as session:
        source = get_production(session, pid)
        topic = source.selected_topic
        if topic is None:
            raise ValueError("a produção de origem não tem tema escolhido")
        copy = {k: getattr(topic, k) for k in ("topic", "category", "trend_score", "viral_potential", "us_relevance", "competition",
                                                 "shorts_fit", "originality", "risk", "final_score", "reasons")}
    new_id = ctx.orchestrator.new_production(force=True)
    with session_scope(ctx.orchestrator.engine) as session:
        session.add(Topic(production_id=new_id, selected=True, selection_reason=f"duplicado de {pid}", **copy))
        record_event(session, action="duplicate", status="ok", production_id=new_id, stage="discover", detail={"source": pid})
    ctx.bus.publish("state", {"production_id": new_id})
    return new_id, ctx.jobs.submit("prepare", lambda: ctx.orchestrator.prepare(new_id), production_id=new_id)


def delete_production(ctx, pid: str, *, remove_files: bool = True) -> None:
    with session_scope(ctx.orchestrator.engine) as session:
        production = get_production(session, pid)
        if production.state in {State.UPLOADING}:
            raise ValueError("aguarde o upload terminar antes de apagar")
        session.delete(production)
        record_event(session, action="delete", status="ok", production_id=pid)
    if remove_files:
        storage = ctx.orchestrator.storage
        for kind in ("manual_input", "prompts", "segments", "frames", "audio", "captions", "renders", "reports"):
            folder = storage.root / kind / pid
            if folder.is_dir():
                shutil.rmtree(folder, ignore_errors=True)
        thumb = storage.root / "thumbs" / f"{pid}.jpg"
        thumb.unlink(missing_ok=True)
        for clip_thumb in (storage.root / "thumbs").glob(f"{pid}_clip*.jpg"):
            clip_thumb.unlink(missing_ok=True)
    ctx.bus.publish("state", {"production_id": pid, "deleted": True})


def delete_clip(ctx, pid: str, scene: int) -> None:
    from app.web.queries import inbox_clips

    with session_scope(ctx.orchestrator.engine) as session:
        production = get_production(session, pid)
        if production.state not in {State.GENERATING, State.NEEDS_HUMAN_ACTION, State.FAILED}:
            raise ValueError("os clipes já foram validados; não é possível remover")
        clips = inbox_clips(ctx, production)
    clip = next((c for c in clips if c["scene"] == scene), None)
    if clip is None or not clip.get("file"):
        raise ValueError("cena sem arquivo")
    inbox = ctx.orchestrator.storage.dir_for(pid, "manual_input")
    target = (inbox / clip["file"]).resolve()
    if target.parent != inbox.resolve():
        raise ValueError("caminho inválido")
    target.unlink(missing_ok=True)
    ctx.bus.publish("clip", {"production_id": pid, "scene": scene, "removed": True})
