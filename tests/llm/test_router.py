import pytest

from app.core.errors import HumanActionRequired
from app.llm.mock import MockLLM
from app.llm.router import build_llm


def test_mock_mode_returns_mock(settings):
    settings.mode = "mock"
    assert isinstance(build_llm(settings), MockLLM)


def test_live_gemini_without_key_is_human_action(settings):
    settings.mode = "live"
    settings.llm.provider = "gemini"
    settings.google_api_key = None
    with pytest.raises(HumanActionRequired) as ei:
        build_llm(settings)
    report = ei.value.report()
    assert "GOOGLE_API_KEY" in report and "EXACT HUMAN ACTION" in report


def test_live_gemini_with_key_builds_provider(settings):
    from pydantic import SecretStr

    from app.llm.gemini import GeminiProvider

    settings.mode = "live"
    settings.google_api_key = SecretStr("fake-key-for-construction-only")
    llm = build_llm(settings)
    assert isinstance(llm, GeminiProvider)
    assert llm.model_for("smart") == settings.llm.smart_model
