"""Read the configuration for the Ajustes screen (secrets masked) and write it back safely.

Non-secret values go to config/local.yaml (deep-merged over config/default.yaml); secrets go to .env
as OMS_GOOGLE_API_KEY. Panel-only preferences (title suffix, description template, watermark position,
toggles that have no engine counterpart) live under the `panel:` key of local.yaml.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from app.core.config import Settings, load_settings

ENV_KEY = "OMS_GOOGLE_API_KEY"
ENV_MODE = "OMS_MODE"
MODEL_CHOICES = [
    ("gemini-3.8-flash", "Gemini 3.8 Flash (recomendado)"),
    ("gemini-3.5-flash", "Gemini 3.5 Flash"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro (preview)"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro"),
]
SCOPE_LABELS = {
    "https://www.googleapis.com/auth/youtube.upload": "Acesso para publicar vídeos",
    "https://www.googleapis.com/auth/yt-analytics.readonly": "Ler analytics do canal",
    "https://www.googleapis.com/auth/youtube.force-ssl": "Gerenciar títulos e descrições",
    "https://www.googleapis.com/auth/youtube.readonly": "Acessar playlist e miniaturas",
}
PANEL_DEFAULTS: dict[str, Any] = {
    "title_suffix": "#OneMoreShort",
    "description_template": "👇 Curtiu o vídeo?\nSe inscreva no canal e ative o sininho!\n\n#OneMoreShort #Shorts #Curiosidades",
    "default_hashtags": "#curiosidades, #fatos, #shorts, #onemoreshort",
    "tone": "Informativo e descontraído",
    "cta": "Se inscreva para mais curiosidades!",
    "watermark": "Logo OneMoreShort (canto inferior direito)",
    "use_brand_identity": True,
    "safety_moderation": True,
}


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    return value[:6] + "*" * 22


def _local_yaml_path(root: Path) -> Path:
    return root / "config" / "local.yaml"


def read_local_yaml(root: Path) -> dict[str, Any]:
    path = _local_yaml_path(root)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_local_yaml(root: Path, data: dict[str, Any]) -> None:
    path = _local_yaml_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# Overrides written by the web panel (Ajustes). Secrets never go here; they live in .env.\n"
    path.write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=True), encoding="utf-8")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def read_env(root: Path) -> dict[str, str]:
    path = root / ".env"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env(root: Path, updates: dict[str, str | None]) -> None:
    """Update keys in .env preserving other lines; None removes the key. File mode stays private."""
    path = root / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    done: set[str] = set()
    out: list[str] = []
    for line in lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        key = match.group(1) if match else None
        if key in updates:
            done.add(key)
            if updates[key] is not None:
                out.append(f"{key}={updates[key]}")
            continue
        out.append(line)
    for key, value in updates.items():
        if key not in done and value is not None:
            out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def settings_view(ctx, *, connection: dict[str, Any] | None = None) -> dict[str, Any]:
    settings: Settings = ctx.settings
    root = settings.project_root
    panel = {**PANEL_DEFAULTS, **(read_local_yaml(root).get("panel") or {})}
    key = settings.google_api_key.get_secret_value() if settings.google_api_key else None
    token = settings.resolve(settings.youtube_token_path)
    secret = settings.resolve(settings.youtube_client_secret_path)
    from app.youtube.auth import YOUTUBE_SCOPES

    try:
        from app.editing.ffmpeg import resolve_ffmpeg

        ffmpeg_path = str(resolve_ffmpeg()[0])
    except Exception:
        ffmpeg_path = settings.paths.ffmpeg_binary or ""
    return {
        "mode": settings.mode,
        "ai": {
            "has_key": bool(key), "api_key_masked": mask_secret(key), "model": settings.llm.fast_model,
            "models": [{"value": v, "label": l} for v, l in MODEL_CHOICES] + (
                [{"value": settings.llm.fast_model, "label": settings.llm.fast_model}] if settings.llm.fast_model not in {v for v, _ in MODEL_CHOICES} else []),
            "connected": bool(key) and settings.mode == "live",
            "connection": connection or ({"ok": True, "message": "Chave salva. Clique em Testar conexão para validar."} if key
                                         else {"ok": False, "message": "Nenhuma chave salva. Cole a chave do AI Studio e salve."}),
        },
        "youtube": {
            "connected": token.is_file(), "has_client_secret": secret.is_file(),
            "account": {"name": settings.brand.name, "handle": settings.brand.channel_handle, "subscribers": None},
            "scopes": [{"scope": s, "label": SCOPE_LABELS.get(s, s), "active": token.is_file()} for s in YOUTUBE_SCOPES],
            "client_secret_path": str(settings.youtube_client_secret_path),
        },
        "publish": {
            "visibility": settings.upload.visibility if settings.upload.visibility != "draft" else "private",
            "publish_hour_local": settings.upload.publish_hour_local, "title_suffix": panel["title_suffix"],
            "description_template": panel["description_template"], "default_hashtags": panel["default_hashtags"],
            "auto_publish": settings.upload.enabled,
        },
        "brand": {"name": settings.brand.name, "tone": panel["tone"], "cta": panel["cta"], "watermark": panel["watermark"],
                  "use_brand_identity": bool(panel["use_brand_identity"]) and settings.video.logo_watermark},
        "rules": {
            "target_duration_s": int(round(settings.video.target_duration_s)), "scenes": settings.veo.segments,
            "cost_limit_usd": float(settings.limits.daily_budget_usd) if settings.limits.daily_budget_usd <= 1 else 0.10,
            "cost_limit_configured_usd": float(settings.limits.daily_budget_usd),
            "safety_moderation": bool(panel["safety_moderation"]), "avoid_sensitive": bool(settings.brand.avoid),
            "auto_captions": settings.captions.enabled,
        },
        "files": {
            "project_dir": str(root), "inbox_dir": str(settings.resolve(settings.generation.inbox_dir)),
            "ffmpeg_binary": ffmpeg_path, "exports_dir": str(settings.resolve(settings.paths.storage_root) / "renders"),
        },
    }


def apply_update(ctx, update) -> dict[str, Any]:
    """Persist an Ajustes form submission. Returns the fields that changed."""
    settings: Settings = ctx.settings
    root = settings.project_root
    local = read_local_yaml(root)
    patch: dict[str, Any] = {}
    panel_patch: dict[str, Any] = {}
    env_updates: dict[str, str | None] = {}
    changed: list[str] = []

    if update.ai is not None:
        if update.ai.clear_key:
            env_updates[ENV_KEY] = None
            changed.append("ai.api_key")
        elif update.ai.api_key:
            key = update.ai.api_key.strip()
            if not re.fullmatch(r"[A-Za-z0-9_\-]{20,120}", key):
                raise ValueError("a chave informada não tem o formato de uma chave do Google AI Studio")
            env_updates[ENV_KEY] = key
            if settings.mode == "mock":
                env_updates[ENV_MODE] = "live"
            changed.append("ai.api_key")
        if update.ai.model:
            patch.setdefault("llm", {})["fast_model"] = update.ai.model
            patch["llm"]["vision_model"] = update.ai.model
            changed.append("ai.model")
    if update.publish is not None:
        p = update.publish
        upload: dict[str, Any] = {}
        if p.visibility is not None:
            upload["visibility"] = p.visibility
            upload["schedule_enabled"] = p.visibility == "scheduled"
        if p.publish_hour_local is not None:
            upload["publish_hour_local"] = p.publish_hour_local
        if p.auto_publish is not None:
            upload["enabled"] = p.auto_publish
        if upload:
            patch["upload"] = upload
        for field in ("title_suffix", "description_template", "default_hashtags"):
            if getattr(p, field) is not None:
                panel_patch[field] = getattr(p, field)
        changed.append("publish")
    if update.brand is not None:
        b = update.brand
        if b.name:
            patch.setdefault("brand", {})["name"] = b.name
        for field in ("tone", "cta", "watermark"):
            if getattr(b, field) is not None:
                panel_patch[field] = getattr(b, field)
        if b.use_brand_identity is not None:
            panel_patch["use_brand_identity"] = b.use_brand_identity
            patch.setdefault("video", {})["logo_watermark"] = b.use_brand_identity
        changed.append("brand")
    if update.rules is not None:
        r = update.rules
        if r.target_duration_s is not None:
            patch.setdefault("video", {})["target_duration_s"] = r.target_duration_s
            patch["video"]["max_duration_s"] = max(40, r.target_duration_s) if r.target_duration_s <= 40 else r.target_duration_s
        if r.scenes is not None:
            patch.setdefault("veo", {})["segments"] = r.scenes
        if r.cost_limit_usd is not None:
            patch.setdefault("limits", {})["daily_budget_usd"] = r.cost_limit_usd
        if r.safety_moderation is not None:
            panel_patch["safety_moderation"] = r.safety_moderation
        if r.avoid_sensitive is not None:
            patch.setdefault("brand", {})["avoid"] = list(settings.brand.avoid) if r.avoid_sensitive and not settings.brand.avoid else \
                ([] if not r.avoid_sensitive else list(settings.brand.avoid))
        if r.auto_captions is not None:
            patch.setdefault("captions", {})["enabled"] = r.auto_captions
        changed.append("rules")
    if update.files is not None:
        f = update.files
        if f.inbox_dir:
            patch.setdefault("generation", {})["inbox_dir"] = f.inbox_dir
        if f.ffmpeg_binary is not None:
            patch.setdefault("paths", {})["ffmpeg_binary"] = f.ffmpeg_binary or None
        changed.append("files")

    if panel_patch:
        patch["panel"] = {**(local.get("panel") or {}), **panel_patch}
    if patch:
        write_local_yaml(root, _deep_merge(local, patch))
    if env_updates:
        write_env(root, env_updates)
    reload_settings(ctx)
    return {"changed": changed}


def restore_defaults(ctx) -> None:
    path = _local_yaml_path(ctx.settings.project_root)
    if path.exists():
        path.unlink()
    reload_settings(ctx)


def reload_settings(ctx) -> None:
    """Re-read YAML + .env and hand the new settings to the orchestrator (providers are rebuilt lazily)."""
    root = ctx.settings.project_root
    fresh = load_settings(project_root=root)
    for key in ("storage_root", "logs_dir", "database_url", "secrets_dir", "assets_dir"):
        setattr(fresh.paths, key, getattr(ctx.settings.paths, key))
    if os.environ.get("OMS_MODE") is None and (root / ".env").exists() and ENV_MODE not in read_env(root):
        fresh.mode = ctx.settings.mode if ctx.settings.mode == "mock" and not fresh.google_api_key else fresh.mode
    ctx.settings = fresh
    ctx.orchestrator.settings = fresh
    ctx.orchestrator._llm = None
    ctx.orchestrator._tts = None
    ctx.orchestrator._youtube = None


def test_connection(ctx, api_key: str | None, model: str | None) -> dict[str, Any]:
    key = (api_key or "").strip() or (ctx.settings.google_api_key.get_secret_value() if ctx.settings.google_api_key else "")
    if not key:
        return {"ok": False, "message": "Nenhuma chave para testar.", "detail": "Cole a chave do Google AI Studio e tente de novo."}
    model = model or ctx.settings.llm.fast_model
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=20_000))
        response = client.models.generate_content(model=model, contents="Reply with the single word OK.",
                                                  config=types.GenerateContentConfig(max_output_tokens=5, temperature=0))
        text = (response.text or "").strip()
        return {"ok": True, "message": "Conexão bem-sucedida!", "detail": "Sua chave está válida e respondendo.", "model": model, "sample": text[:20]}
    except Exception as err:  # the message never includes the key
        detail = re.sub(r"key=[^&\s]+", "key=***", str(err))[:200]
        return {"ok": False, "message": "Falha na conexão", "detail": detail, "model": model}
