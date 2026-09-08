"""Read models for the panel: pure projections of the database into what each screen renders.

Nothing here changes state. Everything returns plain dicts (JSON-ready) so the routes stay thin.
"""
from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.models import Event, Insight as InsightRow, Production, StrategyWeightsRow
from app.core.states import HOLD_STATES, PIPELINE_ORDER, State

VIDEO_LENGTH_S = 40.0
_NUMBERED = re.compile(r"(?:segment|clip|video|cena)[ _-]*0*([1-5])(?:\D|$)", re.IGNORECASE)

STATE_LABELS: dict[str, str] = {
    "DISCOVERING": "Escolhendo tema", "SELECTED": "Tema escolhido", "RESEARCHING": "Pesquisando",
    "SCRIPTING": "Escrevendo roteiro", "STORYBOARDING": "Montando storyboard", "GENERATING": "Aguardando clipes",
    "VALIDATING": "Validando clipes", "EDITING": "Em edição", "QUALITY_CHECK": "Verificando qualidade",
    "READY": "Pronto para publicar", "UPLOADING": "Publicando", "PUBLISHED": "Publicado", "ANALYZING": "Publicado",
    "LEARNED": "Publicado", "FAILED": "Falha", "RETRYING": "Tentando de novo", "BLOCKED": "Bloqueado",
    "NEEDS_HUMAN_ACTION": "Ação necessária", "NEEDS_REVIEW": "Revisão necessária", "PAUSED_BUDGET": "Orçamento pausado",
}

PURPOSE_LABELS: dict[str, str] = {
    "hook": "O gancho", "setup": "O contexto", "escalation": "A escalada", "revelation": "A revelação",
    "payoff": "O benefício", "ending": "O encerramento",
}
SCENE_DEFAULT_LABELS = ["O impacto visual", "A transformação", "O contexto", "O benefício", "O encerramento"]

CATEGORY_LABELS: dict[str, str] = {
    "science": "ciência", "curiosities": "curiosidades", "curiosity": "curiosidades", "health": "saúde",
    "technology": "tecnologia", "tech": "tecnologia", "psychology": "psicologia", "world": "mundo", "space": "espaço",
    "history": "história", "culture": "cultura", "nature": "natureza", "money": "dinheiro", "illusions": "ilusões",
    "manual": "manual", "general": "geral",
}

HOOK_LABELS = {"curiosity": "Curiosidade", "question": "Pergunta", "shock": "Choque", "contrarian": "Contrarian",
               "story": "História", "visual": "Revelação visual", "mystery": "Mistério"}
ENDING_LABELS = {"loop": "Fecho em loop", "cta": "Chamada para ação", "cliff": "Suspense", "statement": "Afirmação", "question": "Pergunta direta"}
PURPOSE_STRUCT = {"hook": "Gancho", "setup": "Contexto", "escalation": "Escalada", "revelation": "Revelação",
                  "payoff": "Payoff", "ending": "Fecho"}
METRIC_LABELS = {"retention": "retenção", "completion": "conclusão", "views": "views", "engagement": "engajamento",
                 "share_rate": "compartilhamentos", "sub_conversion": "inscritos"}
FEATURE_LABELS = {"hook_type": "Gancho", "category": "Tema", "ending_type": "Final", "duration_bucket": "Duração",
                  "pacing_bucket": "Ritmo", "visual_style": "Estilo visual", "narrator": "Narração",
                  "caption_style": "Legendas", "narrative_structure": "Estrutura"}


# ----------------------------------------------------------------------------- helpers
def aware(value: datetime | None) -> datetime | None:
    return None if value is None else (value if value.tzinfo else value.replace(tzinfo=UTC))


def category_label(category: str | None) -> str:
    if not category:
        return "geral"
    return CATEGORY_LABELS.get(category.lower(), category.lower())


def production_title(production: Production) -> str:
    if production.video_metadata and production.video_metadata.title:
        return production.video_metadata.title
    if production.script and (production.script.data or {}).get("title_working"):
        return production.script.data["title_working"]
    topic = production.selected_topic
    return topic.topic if topic else production.id


def latest_snapshot(production: Production):
    return production.snapshots[-1] if production.snapshots else None


def retention_of(production: Production) -> float | None:
    """Average percentage viewed as a 0-1 ratio, from the deep snapshot or the retention curve."""
    snap = latest_snapshot(production)
    if snap is not None and snap.avg_view_pct is not None:
        return float(snap.avg_view_pct) / 100
    if production.retention_curves:
        analysis = production.retention_curves[-1].analysis or {}
        if analysis.get("avg_pct"):
            return float(analysis["avg_pct"])
    return None


def views_of(production: Production) -> int | None:
    snap = latest_snapshot(production)
    return int(snap.views) if snap is not None else None


def published_at(production: Production) -> datetime | None:
    if production.upload is None:
        return None
    return aware(production.upload.published_at or production.upload.uploaded_at)


def duration_of(production: Production) -> float | None:
    if production.final_video and production.final_video.probe:
        return float(production.final_video.probe.get("duration_s") or 0) or None
    if production.script:
        return float(production.script.est_duration_s or 0) or None
    return None


def status_kind(state: State) -> str:
    if state in {State.PUBLISHED, State.ANALYZING, State.LEARNED}:
        return "published"
    if state in {State.FAILED, State.BLOCKED, State.NEEDS_REVIEW}:
        return "failed"
    if state in {State.DISCOVERING, State.SELECTED, State.RESEARCHING, State.SCRIPTING, State.STORYBOARDING}:
        return "draft"
    return "in_production"


STATUS_KIND_LABELS = {"published": "Publicado", "in_production": "Em produção", "failed": "Falha", "draft": "Rascunho"}


def fmt_clock(duration_s: float | None) -> str:
    if not duration_s:
        return "--:--"
    total = int(round(duration_s))
    return f"{total // 60:02d}:{total % 60:02d}"


def is_measured(production: Production) -> bool:
    return production.upload is not None and bool(production.snapshots)


def to_local(value: datetime | None, tz: str) -> datetime | None:
    value = aware(value)
    return value.astimezone(ZoneInfo(tz)) if value else None


def relative_day(value: datetime | None, now: datetime, tz: str) -> str:
    if value is None:
        return "—"
    local, today = to_local(value, tz), now.astimezone(ZoneInfo(tz)).date()
    days = (today - local.date()).days
    if days <= 0:
        return "Hoje"
    if days == 1:
        return "Ontem"
    return f"{days} dias atrás"


def fmt_date_pt(value: datetime | None, tz: str, *, short: bool = False) -> str:
    local = to_local(value, tz)
    if local is None:
        return "—"
    months = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]
    long_months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
                   "novembro", "dezembro"]
    if short:
        return f"{local.day} de {months[local.month - 1]} de {local.year}"
    return f"{local.day} de {long_months[local.month - 1]} de {local.year}"


def prompt_blocks(prompt: str, negative: str | None) -> list[dict[str, str]]:
    """Split the stored prompt into labelled blocks ("SCENE CONTEXT", "CAMERA", ..., "NEGATIVE")."""
    body = prompt
    if "\n---" in body or body.startswith("SEGMENT "):
        parts = re.split(r"\n-{10,}\n", body, maxsplit=1)
        body = parts[1] if len(parts) == 2 else body
    blocks: list[dict[str, str]] = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        label, sep, text = chunk.partition(":\n")
        if sep and label.isupper() and len(label) < 40:
            blocks.append({"label": label.strip(), "text": " ".join(text.split())})
        elif blocks:
            blocks[-1]["text"] += " " + " ".join(chunk.split())
        else:
            blocks.append({"label": "PROMPT", "text": " ".join(chunk.split())})
    negative_text = negative or next((b["text"] for b in blocks if b["label"] == "NEGATIVE CONSTRAINTS"), None)
    blocks = [b for b in blocks if b["label"] != "NEGATIVE CONSTRAINTS"]
    if negative_text:
        blocks.append({"label": "NEGATIVE", "text": " ".join(negative_text.split())})
    return blocks


def scene_label(production: Production, index: int) -> str:
    story = (production.storyboard.data if production.storyboard else {}) or {}
    segments = story.get("segments") or []
    if index - 1 < len(segments):
        purpose = str(segments[index - 1].get("purpose", "")).strip()
        key = purpose.lower().split()[0] if purpose else ""
        if key in PURPOSE_LABELS:
            return PURPOSE_LABELS[key]
        if purpose:
            return purpose[:40]
    return SCENE_DEFAULT_LABELS[index - 1] if index - 1 < len(SCENE_DEFAULT_LABELS) else f"Cena {index}"


# ----------------------------------------------------------------------------- production views
def studio_step(production: Production) -> int:
    """1 Roteiro · 2 Prompts · 3 Clipes · 4 Revisão · 5 Publicar."""
    state = production.state
    if state in {State.PUBLISHED, State.ANALYZING, State.LEARNED, State.UPLOADING}:
        return 5
    if state == State.READY or state == State.NEEDS_REVIEW:
        return 4 if state == State.NEEDS_REVIEW else 5
    if state in {State.VALIDATING, State.EDITING, State.QUALITY_CHECK}:
        return 4
    if state == State.GENERATING:
        return 3
    if production.prompts:
        return 3
    if production.script is not None:
        return 2
    return 1


def studio_steps(production: Production) -> list[dict[str, Any]]:
    current = studio_step(production)
    names = ["Roteiro", "Prompts", "Clipes", "Revisão", "Publicar"]
    done_flags = [
        production.script is not None,
        bool(production.prompts),
        production.state not in {State.GENERATING} and PIPELINE_ORDER.index(_pipeline_state(production)) >= PIPELINE_ORDER.index(State.EDITING),
        PIPELINE_ORDER.index(_pipeline_state(production)) >= PIPELINE_ORDER.index(State.READY) and production.state != State.NEEDS_REVIEW,
        PIPELINE_ORDER.index(_pipeline_state(production)) >= PIPELINE_ORDER.index(State.PUBLISHED),
    ]
    steps = []
    for number, (name, done) in enumerate(zip(names, done_flags), start=1):
        status = "done" if done else ("current" if number == current else "pending")
        steps.append({"number": number, "name": name, "status": status,
                      "label": {"done": "Concluído", "current": "Em andamento", "pending": "Pendente"}[status]})
    return steps


def _pipeline_state(production: Production) -> State:
    if production.state in HOLD_STATES:
        return production.previous_state or State.DISCOVERING
    return production.state


def today_steps(production: Production | None) -> list[dict[str, Any]]:
    names = ["Tendências", "Roteiro", "Prompts", "Clipes", "Edição", "Publicação"]
    if production is None:
        return [{"number": i, "name": n, "status": "pending", "label": "Pendente"} for i, n in enumerate(names, 1)]
    state = _pipeline_state(production)
    idx = PIPELINE_ORDER.index(state)
    done = [
        production.selected_topic is not None,
        production.script is not None,
        bool(production.prompts),
        idx >= PIPELINE_ORDER.index(State.EDITING),
        idx >= PIPELINE_ORDER.index(State.READY) and production.state != State.NEEDS_REVIEW,
        idx >= PIPELINE_ORDER.index(State.PUBLISHED),
    ]
    current = next((i for i, d in enumerate(done) if not d), None)
    steps = []
    for i, name in enumerate(names):
        status = "done" if done[i] else ("current" if i == current else "pending")
        steps.append({"number": i + 1, "name": name, "status": status,
                      "label": {"done": "Concluído", "current": "Em andamento", "pending": "Pendente"}[status]})
    return steps


def inbox_clips(ctx, production: Production) -> list[dict[str, Any]]:
    """Five slots; each one reflects the file present in the inbox (or the validated segment row)."""
    inbox = ctx.orchestrator.storage.dir_for(production.id, "manual_input")
    accepted = {ext.lower() for ext in ctx.settings.generation.accepted_extensions}
    files = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in accepted)
    by_scene: dict[int, Path] = {}
    unnumbered: list[Path] = []
    for path in files:
        match = _NUMBERED.search(path.stem)
        if match and int(match.group(1)) not in by_scene:
            by_scene[int(match.group(1))] = path
        else:
            unnumbered.append(path)
    for scene in range(1, 6):
        if scene not in by_scene and unnumbered:
            by_scene[scene] = unnumbered.pop(0)
    expected = float(ctx.settings.veo.duration_seconds)
    rows = {row.index: row for row in production.segments}
    clips = []
    for scene in range(1, 6):
        path = by_scene.get(scene)
        clip: dict[str, Any] = {"scene": scene, "name": f"Cena {scene}", "present": path is not None, "status": "missing",
                                "status_label": "Aguardando envio", "duration_s": None, "size_bytes": None, "warning": None,
                                "thumb_url": None, "file": None}
        if path is None:
            clips.append(clip)
            continue
        clip["file"] = path.name
        clip["size_bytes"] = path.stat().st_size
        row = rows.get(scene)
        probe_data = row.probe if row is not None and row.probe and row.file_path == str(path) else None
        if probe_data is None:
            probe_data = _probe_cached(ctx, path)
        duration = float(probe_data.get("duration_s") or 0) if probe_data else None
        clip["duration_s"] = duration
        clip["thumb_url"] = f"/api/thumbs/{production.id}?clip={scene}"
        if probe_data is None:
            clip["status"], clip["status_label"] = "warn", "Não foi possível ler o arquivo"
            clip["warning"] = f"Não foi possível ler a cena {scene}. Substitua o arquivo."
        elif duration is not None and abs(duration - expected) > 0.25:
            clip["status"], clip["status_label"] = "warn", "Atenção"
            verb = "cortada no fim" if duration > expected else "esticada com o último quadro"
            shown = f"{duration:.1f}".replace(".", ",")
            clip["warning"] = (f"Atenção na cena {scene} — Duração {shown}s, {'acima' if duration > expected else 'abaixo'} "
                               f"dos {expected:g}s esperados. Vai ser {verb}.")
        else:
            clip["status"], clip["status_label"] = "ok", "Validado"
        clips.append(clip)
    return clips


_PROBE_CACHE: dict[tuple[str, float], dict[str, Any] | None] = {}


def _probe_cached(ctx, path: Path) -> dict[str, Any] | None:
    key = (str(path), path.stat().st_mtime)
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    try:
        from app.editing.probe import probe

        data = probe(path).model_dump()
    except Exception:
        data = None
    _PROBE_CACHE[key] = data
    del_keys = list(_PROBE_CACHE)[:-200]
    for old in del_keys:
        _PROBE_CACHE.pop(old, None)
    return data


def production_detail(ctx, session: Session, production: Production) -> dict[str, Any]:
    tz = ctx.settings.timezone
    topic = production.selected_topic
    script = (production.script.data if production.script else None) or None
    prompts = []
    for row in production.prompts:
        idx = row.segment_index
        prompts.append({
            "scene": idx, "start_s": (idx - 1) * 8, "end_s": idx * 8, "label": scene_label(production, idx),
            "blocks": prompt_blocks(row.prompt, row.negative_prompt),
            "text": _full_prompt_text(row.prompt, row.negative_prompt),
            "thumb_url": f"/api/thumbs/{production.id}?clip={idx}",
        })
    clips = inbox_clips(ctx, production)
    received = sum(1 for c in clips if c["present"])
    final = production.final_video
    quality = None
    if final and final.quality_report:
        quality = {"passed": bool(final.passed), "checks": [
            {"name": c.get("name"), "label": QUALITY_LABELS.get(c.get("name"), c.get("name")), "passed": bool(c.get("passed")),
             "detail": c.get("detail")} for c in final.quality_report.get("checks", [])]}
    meta = production.video_metadata
    upload = production.upload
    job = ctx.jobs.active_for(production.id)
    return {
        "id": production.id,
        "state": production.state.value,
        "state_label": STATE_LABELS.get(production.state.value, production.state.value),
        "status_kind": status_kind(production.state),
        "step": studio_step(production),
        "steps": studio_steps(production),
        "title": production_title(production),
        "topic": topic.topic if topic else None,
        "category": category_label(topic.category if topic else None),
        "score": int(round(topic.final_score)) if topic else None,
        "reason": topic.selection_reason if topic else None,
        "script": {
            "title_working": script.get("title_working") if script else None,
            "hook_type": script.get("hook_type") if script else None,
            "hook_label": HOOK_LABELS.get(str(script.get("hook_type")), script.get("hook_type")) if script else None,
            "ending_type": script.get("ending_type") if script else None,
            "ending_label": ENDING_LABELS.get(str(script.get("ending_type")), script.get("ending_type")) if script else None,
            "est_duration_s": script.get("est_duration_s") if script else None,
            "total_words": script.get("total_words") if script else None,
            "beats": [{"index": b.get("index"), "start_s": b.get("start_s"), "end_s": b.get("end_s"), "purpose": b.get("purpose"),
                       "purpose_label": PURPOSE_STRUCT.get(str(b.get("purpose")), b.get("purpose")), "narration": b.get("narration"),
                       "on_screen_note": b.get("on_screen_note")} for b in (script.get("beats") or [])] if script else [],
        } if script else None,
        "prompts": prompts,
        "clips": clips,
        "clips_received": received,
        "duration_total_s": float(ctx.settings.veo.duration_seconds) * 5,
        "format": "9:16",
        "scenes": 5,
        "scene_seconds": float(ctx.settings.veo.duration_seconds),
        "final_video": {"url": f"/api/productions/{production.id}/video", "duration_s": (final.probe or {}).get("duration_s") if final else None,
                        "path": final.path, "quality": quality} if final and Path(final.path).is_file() else None,
        "quality": quality,
        "metadata": {"title": meta.title, "description": meta.description, "hashtags": meta.hashtags or [], "tags": meta.tags or [],
                     "publish_at": meta.publish_at.isoformat() if meta.publish_at else None} if meta else None,
        "upload": {"youtube_video_id": upload.youtube_video_id, "url": upload.url, "status": upload.status, "privacy": upload.privacy,
                   "published_at": aware(upload.published_at).isoformat() if upload.published_at else None,
                   "error": upload.error} if upload else None,
        "upload_enabled": ctx.settings.upload.enabled,
        "visibility": ctx.settings.upload.visibility,
        "publish_hour_local": ctx.settings.upload.publish_hour_local,
        "human_action": production.human_action,
        "error": production.error,
        "thumb_url": f"/api/thumbs/{production.id}",
        "created_at": aware(production.created_at).isoformat() if production.created_at else None,
        "created_label": fmt_date_pt(production.created_at, tz, short=True),
        "cost_usd": round(production.cost_usd or 0, 4),
        "job": job.as_dict() if job else None,
        "can_publish": production.state == State.READY,
    }


QUALITY_LABELS = {"duration": "Duração dentro do limite", "resolution": "Resolução 1080×1920", "fps": "Taxa de quadros",
                  "codecs": "Codecs H.264 / AAC", "audio": "Áudio e narração", "segments": "5 cenas validadas",
                  "captions": "Legendas geradas", "continuity": "Continuidade entre cenas", "policy": "Política de conteúdo"}


def _full_prompt_text(prompt: str, negative: str | None) -> str:
    text = prompt.strip()
    if negative and "NEGATIVE PROMPT" not in text:
        text += "\n\nNEGATIVE PROMPT:\n" + negative.strip()
    return text


# ----------------------------------------------------------------------------- today
def todays_production(session: Session, now: datetime, tz: str) -> Production | None:
    local_day = now.astimezone(ZoneInfo(tz)).date()
    prefix = f"OMS-{local_day:%Y%m%d}-"
    row = session.query(Production).filter(Production.id.like(prefix + "%")).order_by(Production.id.desc()).first()
    if row is not None:
        return row
    # Fall back to the most recent production that still needs the operator (yesterday's clips, for example).
    open_states = [s for s in State if s not in {State.PUBLISHED, State.ANALYZING, State.LEARNED}]
    return (session.query(Production).filter(Production.state.in_(open_states))
            .order_by(Production.created_at.desc()).first())


def timeline_for(session: Session, production: Production, tz: str, clips_received: int) -> list[dict[str, Any]]:
    events = (session.query(Event).filter(Event.production_id == production.id, Event.status == "ok")
              .order_by(Event.at.asc()).all())
    seen: dict[str, Event] = {}
    for event in events:
        if event.stage:
            seen[event.stage] = event
    items: list[dict[str, Any]] = []

    def add(stage: str, title: str, text: str) -> None:
        event = seen.get(stage)
        if event is not None:
            local = to_local(event.at, tz)
            items.append({"title": title, "text": text, "time": local.strftime("%H:%M") if local else "", "done": True})

    add("script", "Roteiro escrito", f"Roteiro de {int(round(production.script.est_duration_s)) if production.script else 40}s pronto e revisado.")
    add("storyboard", "Storyboard montado", "5 cenas definidas com direção visual.")
    add("prompts", "5 prompts gerados", "Prompts otimizados para o Google Flow.")
    state = _pipeline_state(production)
    idx = PIPELINE_ORDER.index(state)
    if idx >= PIPELINE_ORDER.index(State.EDITING) or "validate" in seen:
        add("validate", "5 clipes validados", "Clipes normalizados para 1080×1920 e concatenados.")
    elif production.prompts:
        items.append({"title": f"{clips_received} de 5 clipes recebidos", "text": "Gere os clipes no Flow e faça o upload aqui.",
                      "time": "", "done": False, "counter": f"{clips_received}/5"})
    add("render", "Vídeo renderizado", "Narração, legendas e mixagem concluídas.")
    add("quality_gate", "Qualidade verificada", "Vídeo aprovado no quality gate." if production.final_video and production.final_video.passed
        else "Quality gate executado.")
    add("upload", "Publicado no YouTube", "Vídeo enviado e agendado.")
    return items


def banner_for(ctx, session: Session, production: Production | None, clips_received: int) -> dict[str, Any]:
    settings = ctx.settings
    job = ctx.jobs.active_for(production.id if production else None)
    if job is not None and job.status in {"queued", "running"}:
        return {"kind": "processing", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Processando", "lead": job.stage_label or "Preparando",
                "text": "O sistema está trabalhando. Esta tela atualiza sozinha.", "job": job.as_dict(),
                "actions": [{"id": "open_studio", "label": "Abrir o Estúdio", "variant": "secondary", "href": f"/estudio/{production.id}" if production else "/estudio"}]}
    missing = settings.missing_live_requirements()
    if production is None:
        if missing:
            return _first_run_banner(missing)
        return {"kind": "idle", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Tudo em dia", "lead": "Próxima ação",
                "text": "Nenhuma produção foi criada hoje. Comece agora ou aguarde a execução agendada das 09:00.",
                "actions": [{"id": "start_day", "label": "Começar o dia", "variant": "primary", "icon": "play"}]}
    state = production.state
    pid = production.id
    if state == State.NEEDS_HUMAN_ACTION and production.human_action:
        return {"kind": "human_action", "eyebrow": "AÇÃO NECESSÁRIA", "title": "O sistema precisa de você", "lead": "Próxima ação",
                "text": production.human_action.get("problem", ""), "report": production.human_action,
                "actions": [{"id": "resume", "label": "Tentar de novo", "variant": "primary", "icon": "refresh-cw"},
                            {"id": "open_settings", "label": "Abrir Ajustes", "variant": "secondary", "href": "/ajustes"}]}
    if state in {State.FAILED, State.BLOCKED, State.PAUSED_BUDGET, State.RETRYING}:
        return {"kind": "failed", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Algo falhou", "lead": "Próxima ação",
                "text": production.error or "A última etapa falhou. Tente de novo; o sistema continua de onde parou.",
                "actions": [{"id": "resume", "label": "Tentar de novo", "variant": "primary", "icon": "refresh-cw"},
                            {"id": "open_studio", "label": "Abrir o Estúdio", "variant": "secondary", "href": f"/estudio/{pid}"}]}
    if state in {State.DISCOVERING, State.SELECTED, State.RESEARCHING, State.SCRIPTING, State.STORYBOARDING}:
        return {"kind": "idle", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Preparar o roteiro e os prompts", "lead": "Próxima ação",
                "text": "A produção foi criada, mas o roteiro ainda não foi gerado.",
                "actions": [{"id": "prepare", "label": "Continuar preparação", "variant": "primary", "icon": "play"}]}
    if state == State.GENERATING:
        return {"kind": "waiting_clips", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Gerar os 5 clipes no Google Flow", "lead": "Próxima ação",
                "text": "Os prompts estão prontos. Copie um por vez, gere no Flow e volte aqui para subir os arquivos."
                if clips_received == 0 else f"{clips_received} de 5 clipes recebidos. Suba os que faltam para continuar.",
                "actions": [{"id": "open_studio", "label": "Abrir o Estúdio", "variant": "primary", "icon": "clapperboard", "href": f"/estudio/{pid}"},
                            {"id": "copy_prompt_1", "label": "Copiar prompt 1", "variant": "secondary", "icon": "copy"}]}
    if state in {State.VALIDATING, State.EDITING, State.QUALITY_CHECK}:
        return {"kind": "idle", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Montar o vídeo final", "lead": "Próxima ação",
                "text": "Os clipes foram recebidos. Narração, legendas e renderização são automáticas.",
                "actions": [{"id": "finish", "label": "Montar o vídeo", "variant": "primary", "icon": "play"},
                            {"id": "open_studio", "label": "Abrir o Estúdio", "variant": "secondary", "href": f"/estudio/{pid}"}]}
    if state == State.NEEDS_REVIEW:
        return {"kind": "review", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Revisar o vídeo final", "lead": "Próxima ação",
                "text": "O quality gate encontrou pontos de atenção. Assista à prévia e decida.",
                "actions": [{"id": "open_review", "label": "Abrir revisão", "variant": "primary", "icon": "eye", "href": f"/estudio/{pid}?step=4"}]}
    if state == State.READY:
        return {"kind": "ready_to_publish", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Publicar no YouTube", "lead": "Próxima ação",
                "text": "Vídeo aprovado. Confira título e descrição e publique.",
                "actions": [{"id": "open_publish", "label": "Abrir publicação", "variant": "primary", "icon": "upload", "href": f"/estudio/{pid}?step=5"}]}
    if state == State.UPLOADING:
        return {"kind": "processing", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Publicando", "lead": "Enviando para o YouTube",
                "text": "O upload está em andamento.", "actions": []}
    return {"kind": "published", "eyebrow": "PRODUÇÃO DE HOJE", "title": "Vídeo publicado", "lead": "Tudo em dia",
            "text": "O vídeo de hoje já está no ar. As métricas chegam sozinhas nas próximas horas.",
            "actions": [{"id": "open_performance", "label": "Ver desempenho", "variant": "primary", "icon": "bar-chart-3", "href": f"/desempenho/{pid}"},
                        {"id": "start_day", "label": "Nova produção", "variant": "secondary", "icon": "plus"}]}


def _first_run_banner(missing: list[str]) -> dict[str, Any]:
    return {"kind": "first_run", "eyebrow": "PRIMEIRA EXECUÇÃO", "title": "Configurar o sistema", "lead": "Antes de começar",
            "text": "Falta configurar credenciais para rodar de verdade.", "missing": missing,
            "actions": [{"id": "open_settings", "label": "Abrir Ajustes", "variant": "primary", "icon": "settings", "href": "/ajustes"}]}


def last_published(session: Session, now: datetime, tz: str, limit: int = 3) -> list[dict[str, Any]]:
    rows = (session.query(Production).filter(Production.state.in_([State.PUBLISHED, State.ANALYZING, State.LEARNED]))
            .all())
    rows = [r for r in rows if r.upload is not None]
    rows.sort(key=lambda r: published_at(r) or aware(r.created_at) or now, reverse=True)
    out = []
    for row in rows[:limit]:
        retention = retention_of(row)
        out.append({"id": row.id, "title": production_title(row), "date_label": relative_day(published_at(row), now, tz),
                    "views": views_of(row) or 0, "retention": round(retention * 100) if retention is not None else None,
                    "thumb_url": f"/api/thumbs/{row.id}", "url": row.upload.url})
    return out


def channel_summary(session: Session, now: datetime, days: int = 30) -> dict[str, Any]:
    rows = [r for r in session.query(Production).all() if r.upload is not None and published_at(r)]
    start, prev_start = now - timedelta(days=days), now - timedelta(days=2 * days)
    current = [r for r in rows if published_at(r) >= start]
    previous = [r for r in rows if prev_start <= published_at(r) < start]

    def stats(group: list[Production]) -> tuple[int, float, float | None]:
        views = [views_of(r) or 0 for r in group]
        rets = [retention_of(r) for r in group if retention_of(r) is not None]
        return len(group), (mean(views) if views else 0.0), (mean(rets) if rets else None)

    n1, v1, r1 = stats(current)
    n0, v0, r0 = stats(previous)

    def delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or b == 0:
            return None
        return round((a - b) / b * 100)

    series: list[int] = []
    for day in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=day)).date()
        series.append(sum((views_of(r) or 0) for r in rows if published_at(r).date() == day_start))
    cumulative, total = [], 0
    for value in series:
        total += value
        cumulative.append(total)
    return {"published": n1, "published_delta": delta(n1, n0), "avg_views": round(v1), "avg_views_delta": delta(v1, v0),
            "avg_retention": round(r1 * 100) if r1 is not None else None,
            "avg_retention_delta": (round((r1 - r0) * 100) if r1 is not None and r0 is not None else None),
            "series": cumulative, "window_days": days}


def today_view(ctx, session: Session) -> dict[str, Any]:
    now, tz = ctx.now(), ctx.settings.timezone
    production = todays_production(session, now, tz)
    clips = inbox_clips(ctx, production) if production is not None else []
    received = sum(1 for c in clips if c["present"])
    theme = None
    if production is not None and production.selected_topic is not None:
        topic = production.selected_topic
        theme = {"title": production_title(production), "topic": topic.topic, "category": category_label(topic.category),
                 "score": int(round(topic.final_score)), "reason": topic.selection_reason or "",
                 "thumb_url": f"/api/thumbs/{production.id}"}
    badge = None
    if production is not None:
        kind = {"GENERATING": ("amber", "Aguardando clipes"), "READY": ("green", "Pronto para publicar"),
                "NEEDS_REVIEW": ("amber", "Revisão necessária"), "NEEDS_HUMAN_ACTION": ("red", "Ação necessária"),
                "FAILED": ("red", "Falha"), "PUBLISHED": ("green", "Publicado"), "ANALYZING": ("green", "Publicado"),
                "LEARNED": ("green", "Publicado")}.get(production.state.value)
        badge = {"variant": kind[0], "label": kind[1]} if kind else {"variant": "grey", "label": STATE_LABELS.get(production.state.value, production.state.value)}
    local_now = now.astimezone(ZoneInfo(tz))
    job = ctx.jobs.active_for(production.id if production else None)
    return {
        "date": local_now.date().isoformat(),
        "production": {"id": production.id, "state": production.state.value, "state_label": STATE_LABELS.get(production.state.value, ""),
                       "step": studio_step(production), "clips_received": received} if production else None,
        "banner": banner_for(ctx, session, production, received),
        "steps": today_steps(production),
        "theme": theme,
        "timeline": timeline_for(session, production, tz, received) if production else [],
        "badge": badge,
        "last_published": last_published(session, now, tz),
        "channel": channel_summary(session, now),
        "job": job.as_dict() if job else None,
        "first_prompt": _full_prompt_text(production.prompts[0].prompt, production.prompts[0].negative_prompt) if production and production.prompts else None,
    }


# ----------------------------------------------------------------------------- library
def library_view(ctx, session: Session, *, q: str = "", state: str = "", category: str = "", sort: str = "recent",
                 limit: int = 200) -> dict[str, Any]:
    now, tz = ctx.now(), ctx.settings.timezone
    rows = session.query(Production).order_by(Production.created_at.desc()).all()
    items = []
    for row in rows:
        kind = status_kind(row.state)
        topic = row.selected_topic
        cat = category_label(topic.category if topic else None)
        title = production_title(row)
        if q and q.lower() not in f"{title} {row.id} {cat}".lower():
            continue
        if state and state != kind:
            continue
        if category and category != cat:
            continue
        retention = retention_of(row)
        when = published_at(row) or aware(row.created_at)
        items.append({"id": row.id, "title": title, "status": kind, "status_label": STATUS_KIND_LABELS[kind], "state": row.state.value,
                      "state_label": STATE_LABELS.get(row.state.value, row.state.value), "category": cat,
                      "date": when.isoformat() if when else None, "date_label": fmt_date_pt(when, tz, short=True),
                      "views": views_of(row), "retention": round(retention * 100) if retention is not None else None,
                      "duration": fmt_clock(duration_of(row)), "duration_s": duration_of(row), "thumb_url": f"/api/thumbs/{row.id}",
                      "description": (row.video_metadata.description if row.video_metadata else None) or (topic.selection_reason if topic else ""),
                      "likes": latest_snapshot(row).likes if latest_snapshot(row) else None,
                      "published_label": (f"{fmt_date_pt(published_at(row), tz)} às {to_local(published_at(row), tz):%H:%M}" if published_at(row) else None),
                      "url": row.upload.url if row.upload else None, "score": int(round(topic.final_score)) if topic else None,
                      "_sort_views": views_of(row) or 0, "_sort_ret": retention or 0})
    if sort == "views":
        items.sort(key=lambda i: i["_sort_views"], reverse=True)
    elif sort == "retention":
        items.sort(key=lambda i: i["_sort_ret"], reverse=True)
    elif sort == "oldest":
        items.reverse()
    for item in items:
        item.pop("_sort_views", None)
        item.pop("_sort_ret", None)
    return {"items": items[:limit], "stats": library_stats(rows, now), "categories": sorted({i["category"] for i in items})}


def library_stats(rows: list[Production], now: datetime) -> dict[str, Any]:
    kinds = {kind: [r for r in rows if status_kind(r.state) == kind] for kind in STATUS_KIND_LABELS}
    rets = [retention_of(r) for r in rows if retention_of(r) is not None]
    start = now - timedelta(days=30)

    def delta_count(group: list[Production]) -> int | None:
        recent = sum(1 for r in group if aware(r.created_at) and aware(r.created_at) >= start)
        older = len(group) - recent
        if older == 0:
            return None if recent == 0 else 100
        return round(recent / older * 100)

    def weekly(group: list[Production]) -> list[int]:
        out = []
        for week in range(5, -1, -1):
            lo, hi = now - timedelta(days=7 * (week + 1)), now - timedelta(days=7 * week)
            out.append(sum(1 for r in group if aware(r.created_at) and lo <= aware(r.created_at) < hi))
        return out

    prev_rets = [retention_of(r) for r in rows if retention_of(r) is not None and published_at(r) and published_at(r) < start]
    return {
        "published": {"value": len(kinds["published"]), "delta": delta_count(kinds["published"]), "series": weekly(kinds["published"])},
        "in_production": {"value": len(kinds["in_production"]), "delta": delta_count(kinds["in_production"]), "series": weekly(kinds["in_production"])},
        "drafts": {"value": len(kinds["draft"]), "delta": delta_count(kinds["draft"]), "series": weekly(kinds["draft"])},
        "avg_retention": {"value": round(mean(rets) * 100) if rets else None,
                          "delta": (round((mean(rets) - mean(prev_rets)) * 100) if rets and prev_rets else None),
                          "series": [round(x * 100) for x in rets[-6:]]},
    }


# ----------------------------------------------------------------------------- analytics
def _curve_points(production: Production, duration: float) -> list[tuple[float, float]]:
    if not production.retention_curves:
        return []
    points = production.retention_curves[-1].points or []
    out = []
    for p in points:
        ratio = float(p.get("elapsed_ratio", 0)) if isinstance(p, dict) else float(p[0])
        watch = float(p.get("watch_ratio", 0)) if isinstance(p, dict) else float(p[1])
        out.append((round(ratio * duration, 2), round(min(1.0, watch) * 100, 1)))
    return out


def _resample(points: list[tuple[float, float]], xs: list[float]) -> list[float]:
    if not points:
        return [0.0 for _ in xs]
    out = []
    for x in xs:
        before = [p for p in points if p[0] <= x]
        after = [p for p in points if p[0] >= x]
        if not before:
            out.append(after[0][1])
        elif not after:
            out.append(before[-1][1])
        else:
            (x0, y0), (x1, y1) = before[-1], after[0]
            out.append(y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return out


def analytics_view(ctx, session: Session, production: Production) -> dict[str, Any]:
    now, tz = ctx.now(), ctx.settings.timezone
    snap = latest_snapshot(production)
    if snap is None:
        return {"id": production.id, "title": production_title(production), "available": False,
                "reason": "Sem analytics ainda. As primeiras métricas chegam 10 minutos depois da publicação; a curva de retenção, em até 48 horas.",
                "state": production.state.value, "published": production.upload is not None}
    duration = duration_of(production) or VIDEO_LENGTH_S
    others = [r for r in session.query(Production).all() if r.id != production.id and is_measured(r)]
    views = int(snap.views or 0)
    retention = retention_of(production)
    likes, subs = int(snap.likes or 0), int(snap.subscribers_gained or 0)
    other_views = [views_of(r) or 0 for r in others]
    other_ret = [retention_of(r) for r in others if retention_of(r) is not None]
    other_like = [((latest_snapshot(r).likes or 0) / max(1, views_of(r) or 0)) for r in others if views_of(r)]
    other_sub = [((latest_snapshot(r).subscribers_gained or 0) / max(1, views_of(r) or 0)) for r in others if views_of(r)]
    ch_views = mean(other_views) if other_views else None
    ch_ret = mean(other_ret) if other_ret else None
    ch_like = mean(other_like) if other_like else None
    ch_sub = mean(other_sub) if other_sub else None
    like_rate = likes / views if views else 0
    sub_rate = subs / views if views else 0

    def pct_delta(a: float | None, b: float | None) -> int | None:
        return None if a is None or b in (None, 0) else round((a - b) / b * 100)

    kpis = [
        {"key": "views", "label": "Views", "value": views, "format": "int", "delta": pct_delta(views, ch_views), "delta_unit": "%",
         "compare": f"vs. média do canal ({round(ch_views):,})".replace(",", ".") if ch_views else "sem base de comparação ainda"},
        {"key": "retention", "label": "Retenção", "value": round(retention * 100) if retention is not None else None, "format": "pct",
         "delta": (round((retention - ch_ret) * 100) if retention is not None and ch_ret is not None else None), "delta_unit": "pontos",
         "compare": f"vs. média do canal ({round(ch_ret * 100)}%)" if ch_ret is not None else "sem base de comparação ainda"},
        {"key": "likes", "label": "Curtidas", "value": likes, "format": "int", "share": f"{like_rate * 100:.1f}%".replace(".", ","),
         "delta": pct_delta(like_rate, ch_like), "delta_unit": "%",
         "compare": f"vs. média do canal ({ch_like * 100:.1f}%)".replace(".", ",") if ch_like is not None else "sem base de comparação ainda"},
        {"key": "subscribers", "label": "Inscritos", "value": subs, "format": "int", "share": f"{sub_rate * 100:.1f}%".replace(".", ","),
         "delta": pct_delta(sub_rate, ch_sub), "delta_unit": "%",
         "compare": f"vs. média do canal ({ch_sub * 100:.1f}%)".replace(".", ",") if ch_sub is not None else "sem base de comparação ainda"},
    ]
    points = _curve_points(production, duration)
    analysis = (production.retention_curves[-1].analysis if production.retention_curves else {}) or {}
    script = (production.script.data if production.script else {}) or {}
    beats = script.get("beats") or []
    drops = sorted((analysis.get("drops") or []), key=lambda d: float(d.get("delta", 0)), reverse=True)
    annotations = []
    if points and len(points) > 1:
        t, v = points[1]
        annotations.append({"t": t, "value": v, "label": f"{v:.0f}%", "sub": f"Aos {t:.0f}s", "note": "(grande queda inicial)" if points[0][1] - v >= 5 else "(retenção inicial)", "kind": "small"})
    major_beat = None
    for i, drop in enumerate(drops[:3]):
        t = float(drop.get("t_s", 0))
        value = _resample(points, [t])[0] if points else 0
        beat = next((b for b in beats if float(b.get("start_s", 0)) <= t < float(b.get("end_s", 0))), None)
        sentence = _sentence_at(beat, t) if beat else None
        scene = int(drop.get("segment") or (int(t // 8) + 1))
        ann = {"t": t, "value": round(value, 1), "label": f"queda de {float(drop.get('delta', 0)) * 100:.0f}% aos {t:.0f}s", "kind": "major" if i == 0 else "small",
               "scene": scene, "beat": beat.get("index") if beat else None, "sentence": sentence,
               "sub": f"cena {scene}, na frase" if sentence and i == 0 else f"Aos {t:.0f}s"}
        if i == 0:
            major_beat = beat.get("index") if beat else None
        else:
            ann["label"] = f"{value:.0f}%"
        annotations.append(ann)
    # Milestones keep the chart readable when the analysis found fewer than three drops.
    for frac in (0.4, 0.8):
        if not points or len([a for a in annotations if a.get("kind") == "small"]) >= 4:
            break
        t = round(duration * frac)
        if all(abs(t - float(a["t"])) > duration * 0.15 for a in annotations):
            value = _resample(points, [t])[0]
            annotations.append({"t": t, "value": round(value, 1), "label": f"{value:.0f}%", "sub": f"Aos {t:.0f}s", "kind": "small"})
    if points:
        t, v = points[-1]
        annotations.append({"t": t, "value": v, "label": f"{v:.0f}%", "sub": f"Aos {t:.0f}s", "note": "(final do vídeo)", "kind": "small"})
    annotations.sort(key=lambda a: float(a["t"]))
    script_timeline = []
    for beat in beats:
        start, end = float(beat.get("start_s", 0)), float(beat.get("end_s", 0))
        narration = str(beat.get("narration", ""))
        script_timeline.append({"index": beat.get("index"), "range": f"{_mmss(start)} – {_mmss(max(start, end - 1))}", "start_s": start, "end_s": end,
                                "title": f"Cena {beat.get('index')}", "text": narration if len(narration) <= 60 else narration[:57].rstrip() + "...",
                                "purpose": PURPOSE_STRUCT.get(str(beat.get("purpose")), beat.get("purpose")),
                                "highlight": beat.get("index") == major_beat})
    report = production.reports[-1] if production.reports else None
    verdict = (report.verdict if report else None) or {}
    worked = [_split_outcome(x) for x in verdict.get("what_worked", [])]
    failed = [_split_outcome(x) for x in verdict.get("what_failed", [])]
    recommendation = verdict.get("next_recommendation") or ""
    rec_items = [_split_outcome(x) for x in re.split(r";\s*|\.\s+(?=[A-ZÁÉÍÓÚ])", recommendation.replace("Use: ", "")) if x.strip()]
    xs = [i * duration / 10 for i in range(11)]
    other_curves = [_resample(_curve_points(r, duration_of(r) or duration), xs) for r in others if r.retention_curves]
    channel_curve = [mean(col) for col in zip(*other_curves)] if other_curves else []
    video_curve = _resample(points, xs) if points else []
    gain = None
    if channel_curve and video_curve and channel_curve[-1] > 0:
        gain = round((video_curve[-1] - channel_curve[-1]) / channel_curve[-1] * 100)
    growth = verdict.get("growth")
    return {
        "id": production.id, "title": production_title(production), "available": True,
        "published_label": _published_label(published_at(production), now, tz), "duration": fmt_clock(duration), "duration_s": duration,
        "thumb_url": f"/api/thumbs/{production.id}", "url": production.upload.url if production.upload else None,
        "kpis": kpis,
        "curve": {"points": [{"t": t, "value": v} for t, v in points], "annotations": annotations, "duration_s": duration},
        "script_timeline": script_timeline,
        "worked": worked, "failed": failed, "recommendation": rec_items,
        "comparison": {"xs": [round(x, 1) for x in xs], "video": [round(v, 1) for v in video_curve], "channel": [round(v, 1) for v in channel_curve],
                       "gain": gain, "video_end": round(video_curve[-1]) if video_curve else None, "channel_end": round(channel_curve[-1]) if channel_curve else None},
        "virality_score": report.virality_score if report else None, "growth": growth,
        "report_markdown": report.markdown if report else None,
        "captured_at": aware(snap.captured_at).isoformat() if snap.captured_at else None,
    }


def _mmss(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def _published_label(when: datetime | None, now: datetime, tz: str) -> str:
    if when is None:
        return "não publicado"
    local = to_local(when, tz)
    rel = relative_day(when, now, tz).lower()
    return f"publicado {rel} · {local:%Hh%M}"


def _sentence_at(beat: dict[str, Any], t: float) -> str | None:
    narration = str(beat.get("narration", "")).strip()
    if not narration:
        return None
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()]
    if not sentences:
        return narration
    start, end = float(beat.get("start_s", 0)), float(beat.get("end_s", 0))
    frac = 0 if end <= start else min(0.999, max(0.0, (t - start) / (end - start)))
    return sentences[int(frac * len(sentences))]


def _split_outcome(text: str) -> dict[str, str]:
    text = str(text).strip()
    if ":" in text:
        title, _, detail = text.partition(":")
        return {"title": title.strip(), "text": detail.strip()}
    if "(" in text and text.endswith(")"):
        title, _, detail = text.partition("(")
        return {"title": title.strip(), "text": detail.rstrip(")").strip()}
    return {"title": text, "text": ""}


# ----------------------------------------------------------------------------- intelligence
STRUCTURE_DESCRIPTIONS = {
    "hook-setup-escalation-revelation-payoff-ending": "Começa com algo surpreendente, explica o contexto e finaliza com um insight forte.",
    "hook-setup-revelation-payoff-ending": "Apresenta um mito comum, revela a verdade e finaliza com algo inesperado.",
    "hook-escalation-revelation-ending": "Faz uma pergunta intrigante, mostra um experimento visual e entrega a resposta.",
}


def intelligence_view(ctx, session: Session) -> dict[str, Any]:
    now, tz = ctx.now(), ctx.settings.timezone
    insights = session.query(InsightRow).all()
    productions = [p for p in session.query(Production).all() if is_measured(p)]
    outcomes = [p.features for p in productions if p.features]
    sample = len(outcomes)
    minimum = int(ctx.settings.intelligence.min_samples)
    updated = max((aware(i.created_at) for i in insights), default=None)
    if not insights or sample < 1:
        return {"available": False, "sample": sample, "min_samples": minimum, "updated_at": updated.isoformat() if updated else None,
                "reason": "Ainda não há vídeos publicados com métricas suficientes. Publique e colete analytics para o canal começar a aprender."}
    base_ret = mean(o.get("retention", 0) or 0 for o in outcomes) if outcomes else 0

    def best(feature: str, metric: str, positive: bool = True):
        items = [i for i in insights if i.feature == feature and i.metric == metric]
        if not items:
            items = [i for i in insights if i.feature == feature and i.metric == "retention"]
        if not items:
            return None
        return max(items, key=lambda i: i.effect * i.confidence) if positive else min(items, key=lambda i: i.effect * i.confidence)

    hook, theme, dur, ending = best("hook_type", "retention"), best("category", "sub_conversion"), best("duration_bucket", "completion"), best("ending_type", "sub_conversion")
    highlights = [
        {"key": "hooks", "icon": "magnet", "color": "red", "title": "Ganchos que mais retêm",
         "value": f"{hook.effect * base_ret * 100:+.0f} pts" if hook else "—", "compare": "vs. média do canal",
         "text": f"{HOOK_LABELS.get(hook.value, hook.value)} nos 3 primeiros segundos." if hook else "Sem dados suficientes.", "n": hook.n if hook else 0},
        {"key": "themes", "icon": "users", "color": "purple", "title": "Temas que mais rendem inscritos",
         "value": f"{1 + theme.effect:.1f}x".replace(".", ",") if theme else "—", "compare": "vs. média do canal",
         "text": f"{category_label(theme.value).capitalize()} gera mais inscritos." if theme else "Sem dados suficientes.", "n": theme.n if theme else 0},
        {"key": "duration", "icon": "clock", "color": "blue", "title": "Duração ideal",
         "value": _bucket_label(dur.value) if dur else "—", "compare": f"{dur.effect * 100:+.0f}% taxa de conclusão" if dur else "",
         "text": "Vídeos nessa faixa performam melhor no geral." if dur else "Sem dados suficientes.", "n": dur.n if dur else 0},
        {"key": "endings", "icon": "trophy", "color": "amber", "title": "Finais que mais convertem",
         "value": f"{1 + ending.effect:.1f}x".replace(".", ",") if ending else "—", "compare": "vs. média do canal",
         "text": f"{ENDING_LABELS.get(ending.value, ending.value)} gera mais inscrições." if ending else "Sem dados suficientes.", "n": ending.n if ending else 0},
    ]
    ranked = sorted((i for i in insights if i.metric in {"retention", "completion", "sub_conversion", "views"} and i.effect > 0),
                    key=lambda i: (i.confidence, abs(i.effect)), reverse=True)
    patterns = []
    for i in ranked[:5]:
        value_label = {"hook_type": HOOK_LABELS, "ending_type": ENDING_LABELS}.get(i.feature, {}).get(i.value) or \
            (category_label(i.value) if i.feature == "category" else _bucket_label(i.value) if i.feature == "duration_bucket" else i.value)
        metric = METRIC_LABELS.get(i.metric, i.metric)
        gain = f"{i.effect * base_ret * 100:+.0f} pts" if i.metric == "retention" and base_ret else f"{i.effect * 100:+.0f}%"
        extra = i.detail or {}  # the learning loop may store a human phrasing of the pattern
        patterns.append({"feature": i.feature, "value": i.value, "title": extra.get("title") or f"{FEATURE_LABELS.get(i.feature, i.feature)} {value_label} tem",
                         "gain": extra.get("gain") or gain, "suffix": extra.get("suffix", f"de {metric}"),
                         "tags": extra.get("tags") or [FEATURE_LABELS.get(i.feature, i.feature), metric.capitalize()],
                         "confidence": round(i.confidence * 100), "n": i.n})
    by_cat: dict[str, list[dict]] = {}
    for o in outcomes:
        by_cat.setdefault(category_label(o.get("category")), []).append(o)
    themes = []
    for cat, group in sorted(by_cat.items(), key=lambda kv: mean(o.get("retention", 0) or 0 for o in kv[1]), reverse=True):
        ret = mean(o.get("retention", 0) or 0 for o in group)
        subs = mean((o.get("sub_conversion", 0) or 0) * 1000 for o in group)
        themes.append({"category": cat, "retention": round(ret * 100), "subs_per_1k": round(subs, 1), "n": len(group)})
    by_struct: dict[str, list[dict]] = {}
    for o in outcomes:
        if o.get("narrative_structure"):
            by_struct.setdefault(o["narrative_structure"], []).append(o)
    structures = []
    for key, group in sorted(by_struct.items(), key=lambda kv: mean(o.get("retention", 0) or 0 for o in kv[1]), reverse=True)[:3]:
        ret = mean(o.get("retention", 0) or 0 for o in group)
        parts = [PURPOSE_STRUCT.get(p, p) for p in key.split("-")]
        structures.append({"key": key, "name": " → ".join(parts), "description": STRUCTURE_DESCRIPTIONS.get(key, "Estrutura observada nos vídeos do canal."),
                           "result": f"{(ret - base_ret) * 100:+.0f}% retenção" if base_ret else f"{ret * 100:.0f}% retenção", "n": len(group)})
    strategy = session.query(StrategyWeightsRow).order_by(StrategyWeightsRow.id.desc()).first()
    pref = float((strategy.weights or {}).get("duration_pref") or 0) if strategy else 0
    if pref:
        highlights[2]["value"] = f"{pref - 2.5:.0f}s – {pref + 2.5:.0f}s"
    scatter = {"points": [{"duration": o.get("duration_s", 0), "retention": round((o.get("retention", 0) or 0) * 100), "views": o.get("views", 0),
                           "category": category_label(o.get("category")), "id": o.get("production_id"), "title": o.get("title")} for o in outcomes],
               "ideal": {"min": pref - 2.5, "max": pref + 2.5, "label": f"Zona ideal ({pref - 2.5:.0f}s – {pref + 2.5:.0f}s)"} if pref else None,
               "categories": sorted({category_label(o.get("category")) for o in outcomes})}
    tests = _recommended_tests(session, ctx, insights, base_ret)
    return {"available": True, "sample": sample, "min_samples": minimum, "updated_at": updated.isoformat() if updated else None,
            "updated_label": f"{fmt_date_pt(updated, tz)} às {to_local(updated, tz):%H:%M}" if updated else "—",
            "highlights": highlights, "patterns": patterns, "themes": themes, "structures": structures, "scatter": scatter, "tests": tests}


def _bucket_label(value: str) -> str:
    return {"<25s": "< 25s", "25-32s": "25s – 32s", "32-40s": "32s – 40s"}.get(value, value)


def _recommended_tests(session: Session, ctx, insights: list[InsightRow], base_ret: float) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    try:
        from app.intelligence.ab_testing import ABTest

        ab = ABTest()
        for dimension in ctx.settings.intelligence.ab_dimensions:
            result = ab.evaluate(session, dimension)
            if result.winner:
                metric = "retenção"
                label = {"hook_style": HOOK_LABELS, "ending_style": ENDING_LABELS}.get(dimension, {}).get(result.winner, result.winner)
                spread = max(result.variants.values()) - min(result.variants.values()) if len(result.variants) > 1 else 0
                tests.append({"title": f"{FEATURE_LABELS.get(dimension.replace('_style', '_type'), dimension)} {label}",
                              "hypothesis": f"manter {label.lower()} melhora a {metric}.", "impact": f"{spread * 100:+.0f}% {metric}",
                              "confidence": round(result.confidence * 100), "dimension": dimension, "variant": result.winner})
    except Exception:
        pass
    positives = sorted((i for i in insights if i.effect > 0 and i.metric in {"retention", "completion", "sub_conversion"}),
                       key=lambda i: i.effect * i.confidence, reverse=True)
    for i in positives:
        if len(tests) >= 3:
            break
        metric = METRIC_LABELS.get(i.metric, i.metric)
        label = {"hook_type": HOOK_LABELS, "ending_type": ENDING_LABELS}.get(i.feature, {}).get(i.value) or \
            (category_label(i.value) if i.feature == "category" else _bucket_label(i.value) if i.feature == "duration_bucket" else i.value)
        if any(t.get("variant") == i.value for t in tests):
            continue
        tests.append({"title": f"{FEATURE_LABELS.get(i.feature, i.feature)} {label}", "hypothesis": f"aumentar a {metric} com {label.lower()}.",
                      "impact": f"{i.effect * 100:+.0f}% {metric}", "confidence": round(i.confidence * 100), "dimension": i.feature, "variant": i.value})
    for n, test in enumerate(tests[:3], start=1):
        test["number"] = n
    return tests[:3]


# ----------------------------------------------------------------------------- activity (Conversa)
ACTIVITY_LABELS = {
    "script": ("Criou roteiro", "green"), "prompts": ("Gerou novos prompts", "green"), "upload": ("Publicou no YouTube", "blue"),
    "render": ("Finalizou edição", "green"), "analytics": ("Coletou analytics", "green"), "intelligence": ("Aprendeu com os dados", "green"),
    "validate": ("Validou os clipes", "green"), "quality_gate": ("Verificou a qualidade", "green"),
}


def recent_activity(session: Session, now: datetime, tz: str, limit: int = 6) -> list[dict[str, Any]]:
    rows = (session.query(Event).filter(Event.status.in_(["ok", "needs_human_action", "failed"]))
            .order_by(Event.at.desc()).limit(120).all())
    titles: dict[str, str] = {}
    out = []
    for event in rows:
        if event.action.startswith("chat.tool"):
            detail = event.detail or {}
            label, color = detail.get("label", event.action), "green" if event.status == "ok" else "red"
            subject = detail.get("subject", "")
        elif event.stage in ACTIVITY_LABELS and event.status == "ok":
            label, color = ACTIVITY_LABELS[event.stage]
            if event.production_id and event.production_id not in titles:
                production = session.get(Production, event.production_id)
                titles[event.production_id] = f"“{production_title(production)}”" if production else ""
            subject = titles.get(event.production_id or "", "")
        elif event.status == "failed" and event.stage:
            label, color, subject = f"Falhou em {STAGE_LABELS_PT.get(event.stage, event.stage)}", "red", (event.error or "")[:60]
        else:
            continue
        local = to_local(event.at, tz)
        same_day = local.date() == now.astimezone(ZoneInfo(tz)).date() if local else False
        out.append({"time": local.strftime("%H:%M") if local else "", "day": "" if same_day else relative_day(event.at, now, tz),
                    "label": label, "subject": subject, "color": color, "production_id": event.production_id})
        if len(out) >= limit:
            break
    return out


STAGE_LABELS_PT = {"discover": "tema", "research": "pesquisa", "script": "roteiro", "storyboard": "storyboard", "prompts": "prompts",
                   "validate": "validação", "narration": "narração", "mix": "mixagem", "captions": "legendas", "render": "renderização",
                   "metadata": "metadados", "quality_gate": "quality gate", "upload": "upload", "analytics": "analytics", "intelligence": "aprendizado"}
