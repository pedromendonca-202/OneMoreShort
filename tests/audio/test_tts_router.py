from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.audio.tts import build_tts
from app.audio.tts.edge import EdgeTTS
from app.audio.tts.gemini_tts import GeminiTTS
from app.audio.tts.mock import MockTTS
from app.core.errors import HumanActionRequired


def test_mock_mode_always_uses_mock_tts(settings):
    settings.tts.provider = "gemini"
    assert isinstance(build_tts(settings), MockTTS)


def test_live_edge_uses_configured_voice(settings):
    settings.mode = "live"
    settings.tts.provider = "edge"
    settings.tts.edge_voice = "en-US-AndrewNeural"
    tts = build_tts(settings)
    assert isinstance(tts, EdgeTTS) and tts.voice == "en-US-AndrewNeural"


def test_live_gemini_without_key_is_a_human_action(settings):
    settings.mode = "live"
    settings.tts.provider = "gemini"
    settings.google_api_key = None
    with pytest.raises(HumanActionRequired) as err:
        build_tts(settings)
    assert "GOOGLE_API_KEY" in err.value.report()


def test_live_gemini_with_key_builds_gemini_tts(settings):
    settings.mode = "live"
    settings.tts.provider = "gemini"
    settings.tts.voice = "Kore"
    settings.google_api_key = SecretStr("AIza-test")
    tts = build_tts(settings)
    assert isinstance(tts, GeminiTTS) and tts.voice == "Kore" and tts.model == settings.tts.gemini_model
