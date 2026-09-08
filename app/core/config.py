"""Configuration: YAML defaults (config/default.yaml, optional config/local.yaml) overridden by environment (.env / OMS_*)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LLMConfig(BaseModel):
    provider: Literal["gemini", "anthropic", "mock"] = "gemini"
    fast_model: str = "gemini-3.8-flash"
    smart_model: str = "gemini-3.1-pro-preview"
    vision_model: str = "gemini-3.8-flash"
    anthropic_model: str = "claude-opus-5"
    temperature: float = 0.7
    max_output_tokens: int = 8192
    timeout_s: int = 180
    use_search_grounding: bool = True


class VeoConfig(BaseModel):
    model: str = "veo-3.1-lite-generate-preview"
    resolution: Literal["720p", "1080p"] = "1080p"
    aspect_ratio: Literal["9:16", "16:9"] = "9:16"
    duration_seconds: int = 8
    segments: int = 5
    generate_audio: bool = True
    person_generation: str = "allow_adult"
    poll_interval_s: int = 10
    timeout_s: int = 900
    continuity_strategy: Literal["chain_last_frame", "keyframe_interpolation", "prompt_only"] = "chain_last_frame"
    continuity_min_score: float = 0.6
    observe_end_state: bool = True
    check_continuity: bool = True
    seed_base: int | None = None


class TTSConfig(BaseModel):
    provider: Literal["gemini", "edge", "mock"] = "gemini"
    voice: str = "Charon"
    edge_voice: str = "en-US-GuyNeural"
    gemini_model: str = "gemini-2.5-flash-preview-tts"
    style_instruction: str = "Speak like an energetic, confident American narrator for a fast-paced YouTube Short. Clear diction, natural pauses, no filler."
    wpm: int = 165
    max_atempo: float = 1.08
    tighten_passes: int = 2


class VideoConfig(BaseModel):
    max_duration_s: float = 40
    target_duration_s: float = 38
    width: int = 1080
    height: int = 1920
    fps: int = 24
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"
    logo_watermark: bool = True
    logo_path: str = "assets/logo_youtube.png"
    logo_opacity: float = 0.75
    logo_width_px: int = 140
    music_enabled: bool = True
    music_gain_db: float = -18
    veo_audio_gain_db: float = -8
    narration_gain_db: float = 0
    loudness_lufs: float = -14
    true_peak_dbtp: float = -1


class CaptionsConfig(BaseModel):
    enabled: bool = True
    font: str = "Impact"
    font_size: int = 72
    max_words: int = 3
    position_pct: float = 0.62
    primary_color: str = "&H00FFFFFF"
    highlight_color: str = "&H0000E5FF"
    outline_color: str = "&H00000000"
    outline: int = 5
    shadow: int = 2
    uppercase: bool = True
    margin_h_px: int = 80


class TrendsConfig(BaseModel):
    region: str = "US"
    language: str = "en"
    sources: list[str] = Field(default_factory=lambda: ["youtube", "reddit", "news_rss", "hackernews", "wikipedia", "gtrends_rss"])
    per_source_limit: int = 25
    max_candidates: int = 12
    reddit_subreddits: list[str] = Field(default_factory=lambda: ["todayilearned", "interestingasfuck", "Damnthatsinteresting", "science", "technology", "mildlyinteresting", "explainlikeimfive"])
    youtube_categories: list[str] = Field(default_factory=lambda: ["0", "28", "27", "24", "22"])
    http_timeout_s: int = 20


class UploadConfig(BaseModel):
    enabled: bool = False
    visibility: Literal["draft", "private", "unlisted", "scheduled", "public"] = "private"
    schedule_enabled: bool = False
    timezone: str = "America/Sao_Paulo"
    publish_hour_local: int = 18
    made_for_kids: bool = False
    default_category_id: str = "24"
    add_shorts_hashtag: bool = True
    post_pinned_comment: bool = False


class LimitsConfig(BaseModel):
    daily_budget_usd: float = 10
    max_video_generation_retries: int = 3
    max_api_retries: int = 5
    max_videos_per_day: int = 1
    max_stage_attempts: int = 3
    max_script_regenerations: int = 2


class AnalyticsConfig(BaseModel):
    snapshot_schedule_min: list[int] = Field(default_factory=lambda: [10, 30, 60, 180, 360, 720, 1440, 2880, 10080, 20160, 43200])
    deep_metrics_after_hours: int = 48
    retention_drop_threshold: float = 0.08
    growth_baseline_min_videos: int = 3


class IntelligenceConfig(BaseModel):
    exploration_ratio: float = 0.30
    min_samples: int = 3
    recency_window: int = 20
    ab_testing_enabled: bool = True
    ab_dimensions: list[str] = Field(default_factory=lambda: ["hook_style", "ending_style", "caption_style"])


class PathsConfig(BaseModel):
    storage_root: str = "storage"
    logs_dir: str = "logs"
    database_url: str = "sqlite:///database/oms.db"
    secrets_dir: str = "secrets"
    assets_dir: str = "assets"
    ffmpeg_binary: str | None = None


class BrandConfig(BaseModel):
    name: str = "OneMoreShort"
    tagline: str = "One more. Always one more."
    channel_handle: str = "@OneMoreShort"
    visual_style: str = "bold, cinematic, high-contrast, modern, energetic, internet-native, clean"
    palette: str = "deep blacks, vivid red accents, crisp whites; occasional neon cyan/magenta highlights"
    narrator_persona: str = "confident, curious, fast-talking American narrator; friendly, sharp, never condescending"
    audience: str = "United States, 16-40, mobile-first, curious, skims fast"
    content_pillars: list[str] = Field(default_factory=lambda: ["surprising facts", "how things work", "tech & science", "history twists", "nature & animals", "money & everyday life", "internet culture"])
    avoid: list[str] = Field(default_factory=lambda: ["politics", "religion", "medical advice", "graphic violence", "gambling", "adult content", "tragedies in progress", "unverified rumors", "copyrighted footage"])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OMS_", env_nested_delimiter="__", extra="ignore", case_sensitive=False)

    mode: Literal["mock", "live"] = "mock"
    google_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    google_trends_api_key: SecretStr | None = None
    youtube_client_secret_path: str = "secrets/youtube_client_secret.json"
    youtube_token_path: str = "secrets/youtube_token.json"
    youtube_channel_id: str | None = None
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"

    llm: LLMConfig = Field(default_factory=LLMConfig)
    veo: VeoConfig = Field(default_factory=VeoConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    captions: CaptionsConfig = Field(default_factory=CaptionsConfig)
    trends: TrendsConfig = Field(default_factory=TrendsConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    intelligence: IntelligenceConfig = Field(default_factory=IntelligenceConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    brand: BrandConfig = Field(default_factory=BrandConfig)
    project_root: Path = PROJECT_ROOT

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings) -> tuple[PydanticBaseSettingsSource, ...]:  # noqa: D417
        # Environment beats .env beats YAML (init kwargs) beats defaults.
        return (env_settings, dotenv_settings, init_settings, file_secret_settings)

    # --- helpers -------------------------------------------------------
    def resolve(self, p: str | Path) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (self.project_root / path)

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    def missing_live_requirements(self) -> list[str]:
        missing: list[str] = []
        needs_google = self.llm.provider == "gemini" or self.tts.provider == "gemini" or True  # Veo always needs it
        if needs_google and not self.google_api_key:
            missing.append("GOOGLE_API_KEY (Google AI Studio key with Cloud Billing enabled; required for Veo/Gemini)")
        if self.llm.provider == "anthropic" and not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY (required because llm.provider=anthropic)")
        if self.upload.enabled and not self.resolve(self.youtube_client_secret_path).exists():
            missing.append(f"YouTube OAuth client secret at {self.youtube_client_secret_path} (required because upload.enabled=true)")
        return missing

    def snapshot(self) -> dict[str, Any]:
        """Config snapshot safe to persist (secrets excluded)."""
        data = self.model_dump(mode="json", exclude={"google_api_key", "anthropic_api_key", "google_trends_api_key", "project_root"})
        return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_yaml_config(project_root: Path, config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or (project_root / "config" / "default.yaml")
    data: dict[str, Any] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    local = project_root / "config" / "local.yaml"
    if config_path is None and local.exists():
        data = _deep_merge(data, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return data


def load_settings(project_root: Path | None = None, config_path: Path | None = None, env_file: str | Path | None = ".env") -> Settings:
    root = Path(project_root) if project_root else PROJECT_ROOT
    yaml_data = load_yaml_config(root, config_path)
    yaml_data["project_root"] = root
    env_path = None if env_file is None else (root / env_file if not Path(env_file).is_absolute() else Path(env_file))
    return Settings(_env_file=env_path, **yaml_data)  # type: ignore[call-arg]
