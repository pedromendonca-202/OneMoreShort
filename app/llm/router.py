"""Select the LLM provider from settings; raise a precise human-action report when credentials are missing."""
from __future__ import annotations

from app.core.config import Settings
from app.core.errors import HumanActionRequired
from app.llm.base import LLMProvider
from app.llm.mock import MockLLM


def google_key_action(settings: Settings, purpose: str) -> HumanActionRequired:
    return HumanActionRequired(
        problem=f"GOOGLE_API_KEY is not configured; {purpose} cannot run in live mode.",
        root_cause="Gemini/Veo API access requires a Google AI Studio API key with Cloud Billing enabled. "
        "Google AI Plus/Pro subscription credits apply only to the consumer apps, not to the API.",
        automated="Configuration loading, mock mode, provider wiring, budget guard.",
        remains="Create the key and enable billing on its Google Cloud project.",
        action="1) Open https://aistudio.google.com/apikey and create an API key. 2) In the linked Google Cloud project "
        "enable billing (Veo has no free tier). 3) Put the key in .env as OMS_GOOGLE_API_KEY=... 4) Set OMS_MODE=live. "
        "5) Run `oms doctor` to verify.",
        next_step="The pipeline resumes automatically at the stage that needed the key (`oms resume`).",
    )


def build_llm(settings: Settings) -> LLMProvider:
    cfg = settings.llm
    if settings.mode == "mock" or cfg.provider == "mock":
        return MockLLM()
    if cfg.provider == "gemini":
        if not settings.google_api_key:
            raise google_key_action(settings, "the Gemini LLM provider")
        from app.llm.gemini import GeminiProvider

        return GeminiProvider(
            api_key=settings.google_api_key.get_secret_value(),
            fast_model=cfg.fast_model,
            smart_model=cfg.smart_model,
            vision_model=cfg.vision_model,
            timeout_s=cfg.timeout_s,
            max_attempts=settings.limits.max_api_retries,
            default_temperature=cfg.temperature,
            max_output_tokens=cfg.max_output_tokens,
        )
    if cfg.provider == "anthropic":
        if not settings.anthropic_api_key:
            raise HumanActionRequired(
                problem="ANTHROPIC_API_KEY is not configured but llm.provider=anthropic.",
                root_cause="The Anthropic provider needs an API key (or `ant auth login`).",
                automated="Provider wiring and mock mode.",
                remains="Provide the key or switch llm.provider to gemini.",
                action="Set OMS_ANTHROPIC_API_KEY in .env, or set llm.provider: gemini in config/local.yaml.",
                next_step="`oms resume` continues from the stage that needed the LLM.",
            )
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=cfg.anthropic_model,
            timeout_s=cfg.timeout_s,
            max_attempts=settings.limits.max_api_retries,
            max_output_tokens=max(cfg.max_output_tokens, 4096),
        )
    raise ValueError(f"unknown llm provider: {cfg.provider}")
