"""TTS providers plus the settings-driven selector used by the orchestrator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.audio.tts.base import TTSProvider
from app.audio.tts.mock import MockTTS
from app.core.errors import HumanActionRequired

if TYPE_CHECKING:
    from app.core.config import Settings

__all__ = ["MockTTS", "TTSProvider", "build_tts"]


def build_tts(settings: "Settings") -> TTSProvider:
    """One narrator voice per channel. Mock mode never touches the network."""
    cfg = settings.tts
    if settings.mode == "mock" or cfg.provider == "mock":
        return MockTTS(wpm=cfg.wpm)
    if cfg.provider == "edge":
        from app.audio.tts.edge import EdgeTTS

        return EdgeTTS(cfg.edge_voice)
    if cfg.provider == "gemini":
        if not settings.google_api_key:
            raise HumanActionRequired(
                problem="GOOGLE_API_KEY is not configured; Gemini TTS narration cannot run in live mode.",
                root_cause="Gemini TTS needs a Google AI Studio API key. The free tier covers TTS when the key belongs "
                "to a project WITHOUT Cloud Billing; a billed project is charged at list price.",
                automated="Provider selection, mock narration, edge-tts fallback path.",
                remains="Create the key or switch tts.provider to edge (free, no key).",
                action="1) Open https://aistudio.google.com/apikey and create a key in a project without billing. "
                "2) Put it in .env as OMS_GOOGLE_API_KEY=... 3) Or set tts.provider: edge in config/local.yaml.",
                next_step="Re-run `python -m app.cli finish <ID>`; narration resumes from the saved script.",
            )
        from app.audio.tts.gemini_tts import GeminiTTS

        return GeminiTTS(settings.google_api_key.get_secret_value(), cfg.gemini_model, cfg.voice)
    raise ValueError(f"unknown tts provider: {cfg.provider}")
