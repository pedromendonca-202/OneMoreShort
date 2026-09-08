from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def project(settings, tmp_path, monkeypatch):
    """Redirect config/local.yaml and .env writes to a temporary project root."""
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config" / "default.yaml").write_text((Path(settings.project_root) / "config" / "default.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    settings.project_root = root
    return root


def test_settings_view_never_contains_the_key(client, ctx, project):
    from pydantic import SecretStr

    ctx.settings.google_api_key = SecretStr("AIzaSyB-super-secret-key-1234567890")
    body = client.get("/api/settings")
    assert body.status_code == 200
    text = body.text
    assert "super-secret" not in text
    data = body.json()
    assert data["ai"]["has_key"] is True
    assert data["ai"]["api_key_masked"].startswith("AIzaSy") and "*" in data["ai"]["api_key_masked"]
    assert data["youtube"]["connected"] is False
    assert data["rules"]["target_duration_s"] == 38 and data["rules"]["scenes"] == 5
    assert data["files"]["inbox_dir"].endswith("manual_input")


def test_put_writes_secret_to_env_and_rest_to_local_yaml(client, ctx, project):
    response = client.put("/api/settings", json={
        "ai": {"api_key": "AIzaSyB_test_key_abcdefghijklmnopqrstu", "model": "gemini-2.5-flash"},
        "publish": {"visibility": "unlisted", "publish_hour_local": 12, "title_suffix": "#OMS", "auto_publish": True},
        "brand": {"name": "OneMoreShort", "cta": "Subscribe!"},
        "rules": {"target_duration_s": 40, "scenes": 5, "auto_captions": False},
    })
    assert response.status_code == 200, response.text
    env = (project / ".env").read_text(encoding="utf-8")
    assert "OMS_GOOGLE_API_KEY=AIzaSyB_test_key_abcdefghijklmnopqrstu" in env
    assert "OMS_MODE=live" in env
    local = yaml.safe_load((project / "config" / "local.yaml").read_text(encoding="utf-8"))
    assert local["upload"]["visibility"] == "unlisted" and local["upload"]["enabled"] is True
    assert local["llm"]["fast_model"] == "gemini-2.5-flash"
    assert local["panel"]["title_suffix"] == "#OMS" and local["panel"]["cta"] == "Subscribe!"
    assert local["captions"]["enabled"] is False
    assert "google_api_key" not in json.dumps(local).lower()
    view = response.json()["settings"]
    assert view["publish"]["visibility"] == "unlisted" and view["ai"]["model"] == "gemini-2.5-flash"
    assert "test_key" not in response.text
    assert ctx.settings.upload.visibility == "unlisted"


def test_invalid_key_is_rejected(client, project):
    response = client.put("/api/settings", json={"ai": {"api_key": "short"}})
    assert response.status_code == 400


def test_restore_defaults_removes_local_yaml(client, ctx, project):
    client.put("/api/settings", json={"rules": {"scenes": 7}})
    assert (project / "config" / "local.yaml").exists()
    response = client.post("/api/settings/restore")
    assert response.status_code == 200
    assert not (project / "config" / "local.yaml").exists()
    assert response.json()["settings"]["rules"]["scenes"] == 5


def test_test_connection_without_key(client, project):
    data = client.post("/api/settings/test-connection", json={}).json()
    assert data["ok"] is False


def test_health_lists_services(client):
    data = client.get("/api/health").json()
    keys = [item["key"] for item in data["items"]]
    assert keys == ["server", "database", "ffmpeg", "youtube", "gemini", "storage"]
    assert data["items"][0]["status"] == "ok"


def test_open_folder_refuses_paths_outside_project(client, ctx, project, monkeypatch):
    ctx.settings.generation.inbox_dir = str(Path("/") / "outside")
    response = client.post("/api/settings/open-folder", json={"key": "inbox"})
    assert response.status_code == 400
