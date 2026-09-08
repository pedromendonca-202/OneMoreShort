from pathlib import Path

from app.core.config import Settings, load_settings

ROOT = Path(__file__).resolve().parents[2]


def test_defaults_come_from_yaml():
    s = load_settings(project_root=ROOT, env_file=None)
    assert isinstance(s, Settings)
    assert s.mode == "mock"
    assert s.veo.model == "veo-3.1-lite-generate-preview"
    assert s.veo.aspect_ratio == "9:16"
    assert s.veo.duration_seconds == 8
    assert s.veo.segments == 5
    assert s.video.max_duration_s == 40
    assert s.video.width == 1080 and s.video.height == 1920
    assert s.limits.daily_budget_usd == 10
    assert s.limits.max_videos_per_day == 1
    assert s.upload.enabled is False
    assert s.brand.name == "OneMoreShort"


def test_env_overrides_yaml(monkeypatch):
    monkeypatch.setenv("OMS_MODE", "live")
    monkeypatch.setenv("OMS_VEO__RESOLUTION", "720p")
    monkeypatch.setenv("OMS_LIMITS__DAILY_BUDGET_USD", "3.5")
    monkeypatch.setenv("OMS_GOOGLE_API_KEY", "not-a-real-key")
    s = load_settings(project_root=ROOT, env_file=None)
    assert s.mode == "live"
    assert s.veo.resolution == "720p"
    assert s.limits.daily_budget_usd == 3.5
    assert s.google_api_key is not None
    assert s.google_api_key.get_secret_value() == "not-a-real-key"
    # secrets must never leak through repr/str
    assert "not-a-real-key" not in repr(s)


def test_live_mode_without_key_reports_missing():
    s = load_settings(project_root=ROOT, env_file=None)
    s.mode = "live"
    missing = s.missing_live_requirements()
    assert "GOOGLE_API_KEY" in " ".join(missing)


def test_segments_times_duration_fits_max():
    s = load_settings(project_root=ROOT, env_file=None)
    assert s.veo.segments * s.veo.duration_seconds <= s.video.max_duration_s
