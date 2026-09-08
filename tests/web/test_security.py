from __future__ import annotations

from pathlib import Path

import pytest

from app.web.security import RateLimiter, safe_clip_path


def test_security_headers_on_every_response(anon_client):
    response = anon_client.get("/api/session")
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in response.headers


def test_session_returns_csrf_token(anon_client, ctx):
    data = anon_client.get("/api/session").json()
    assert data["csrf_token"] == ctx.csrf_token
    assert data["server"] == "localhost:8787"


def test_mutation_without_csrf_is_rejected(anon_client):
    response = anon_client.post("/api/productions", json={"force": False})
    assert response.status_code == 403
    assert response.json()["error"] == "csrf"


def test_mutation_with_wrong_csrf_is_rejected(anon_client):
    response = anon_client.post("/api/productions", json={"force": False}, headers={"X-OMS-CSRF": "nope"})
    assert response.status_code == 403


def test_mutation_with_csrf_is_accepted(client):
    response = client.post("/api/productions", json={"force": False})
    assert response.status_code == 200


def test_spa_fallback_serves_index_but_not_for_api(anon_client):
    assert anon_client.get("/biblioteca").status_code == 200
    assert "text/html" in anon_client.get("/biblioteca").headers["content-type"]
    assert anon_client.get("/api/does-not-exist").status_code == 404


def test_rate_limiter_blocks_after_limit():
    clock = [0.0]
    limiter = RateLimiter(3, 60, clock=lambda: clock[0])
    assert [limiter.check("k") for _ in range(4)] == [True, True, True, False]
    clock[0] = 61
    assert limiter.check("k") is True


def test_safe_clip_path_is_server_named_and_inside_inbox(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    assert safe_clip_path(inbox, 3) == (inbox / "segment_03.mp4").resolve()
    with pytest.raises(ValueError):
        safe_clip_path(inbox, 0)
    with pytest.raises(ValueError):
        safe_clip_path(inbox, 6)
