"""End-to-end through the API in mock mode: new -> prepare -> upload 5 clips -> collect+finish -> READY."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from tests.web.conftest import wait_job


def _prepare(client, ctx):
    data = client.post("/api/productions", json={"force": False}).json()
    pid = data["id"]
    wait_job(ctx, ctx.jobs.get(data["job"]["id"]))
    return pid


def test_today_is_idle_first_run_free_in_mock_mode(client):
    data = client.get("/api/today").json()
    assert data["production"] is None
    assert data["banner"]["kind"] == "idle"
    assert [s["status"] for s in data["steps"]] == ["pending"] * 6
    assert data["last_published"] == []
    assert data["channel"]["published"] == 0


def test_new_production_prepares_and_today_waits_for_clips(client, ctx):
    pid = _prepare(client, ctx)
    data = client.get("/api/today").json()
    assert data["production"]["id"] == pid
    assert data["banner"]["kind"] == "waiting_clips"
    assert data["banner"]["title"] == "Gerar os 5 clipes no Google Flow"
    assert [s["status"] for s in data["steps"]] == ["done", "done", "done", "current", "pending", "pending"]
    assert data["badge"] == {"variant": "amber", "label": "Aguardando clipes"}
    titles = [t["title"] for t in data["timeline"]]
    assert titles[:3] == ["Roteiro escrito", "Storyboard montado", "5 prompts gerados"]
    assert data["timeline"][-1]["counter"] == "0/5"
    assert data["theme"]["score"] == 78
    assert data["first_prompt"].startswith("SEGMENT 1 OF 5")


def test_detail_has_five_prompts_with_blocks_and_five_clip_slots(client, ctx):
    pid = _prepare(client, ctx)
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["step"] == 3
    assert [s["status"] for s in detail["steps"]] == ["done", "done", "current", "pending", "pending"]
    assert len(detail["prompts"]) == 5
    first = detail["prompts"][0]
    labels = [b["label"] for b in first["blocks"]]
    assert labels[0] == "SCENE CONTEXT" and "CAMERA" in labels and labels[-1] == "NEGATIVE"
    assert first["start_s"] == 0 and first["end_s"] == 8
    assert [c["present"] for c in detail["clips"]] == [False] * 5
    assert detail["can_publish"] is False
    txt = client.get(f"/api/productions/{pid}/script.txt")
    assert txt.status_code == 200 and "SCENE 5" in txt.text


def _clip_bytes(tmp_path: Path, seconds: float, name: str) -> bytes:
    from app.editing.synth import synth_segment

    return synth_segment(tmp_path / name, seconds, "blue", name).read_bytes()


def test_upload_rejects_bad_scene_and_non_video(client, ctx, tmp_path):
    pid = _prepare(client, ctx)
    bad = client.post(f"/api/productions/{pid}/clips", data={"scene": 7}, files={"file": ("x.mp4", b"abc", "video/mp4")})
    assert bad.status_code == 400
    junk = client.post(f"/api/productions/{pid}/clips", data={"scene": 1}, files={"file": ("../../evil.mp4", b"not a video", "video/mp4")})
    assert junk.status_code == 422
    inbox = ctx.orchestrator.storage.dir_for(pid, "manual_input")
    assert list(inbox.iterdir()) == []


def test_upload_five_clips_then_finish_reaches_ready(client, ctx, tmp_path):
    pid = _prepare(client, ctx)
    ok_clip = _clip_bytes(tmp_path, 8.0, "ok.mp4")
    long_clip = _clip_bytes(tmp_path, 8.6, "long.mp4")
    for scene in range(1, 6):
        payload = long_clip if scene == 3 else ok_clip
        response = client.post(f"/api/productions/{pid}/clips", data={"scene": scene},
                               files={"file": (f"whatever name {scene}.mp4", io.BytesIO(payload), "video/mp4")})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scene"] == scene and body["present"] is True
    inbox = ctx.orchestrator.storage.dir_for(pid, "manual_input")
    assert sorted(p.name for p in inbox.iterdir()) == [f"segment_0{i}.mp4" for i in range(1, 6)]
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["clips_received"] == 5
    assert detail["clips"][2]["status"] == "warn" and "cena 3" in detail["clips"][2]["warning"]
    assert detail["clips"][0]["status"] == "ok"
    assert client.get(f"/api/thumbs/{pid}?clip=1").status_code == 200

    # replacing a clip keeps exactly one file per scene
    response = client.post(f"/api/productions/{pid}/clips", data={"scene": 3}, files={"file": ("new.mp4", io.BytesIO(ok_clip), "video/mp4")})
    assert response.status_code == 200 and response.json()["status"] == "ok"
    assert len(list(inbox.iterdir())) == 5

    job = client.post(f"/api/productions/{pid}/collect").json()["job"]
    wait_job(ctx, ctx.jobs.get(job["id"]), timeout=300)
    assert ctx.jobs.get(job["id"]).status == "done", ctx.jobs.get(job["id"]).error
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["state"] == "READY" and detail["can_publish"] is True and detail["step"] == 5
    assert detail["final_video"]["url"].endswith("/video")
    assert detail["quality"]["passed"] is True
    assert client.get(f"/api/productions/{pid}/video").status_code == 200
    assert client.get(f"/api/thumbs/{pid}").status_code == 200
    today = client.get("/api/today").json()
    assert today["banner"]["kind"] == "ready_to_publish"

    # publishing needs explicit confirmation and then goes through the (mock) uploader
    assert client.post(f"/api/productions/{pid}/publish", json={"confirm": False}).status_code == 400
    job = client.post(f"/api/productions/{pid}/publish", json={"confirm": True}).json()["job"]
    wait_job(ctx, ctx.jobs.get(job["id"]))
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["state"] == "PUBLISHED" and detail["upload"]["youtube_video_id"].startswith("mock-")
    assert client.post(f"/api/productions/{pid}/publish", json={"confirm": True}).status_code == 400


def test_library_lists_and_filters(client, ctx):
    pid = _prepare(client, ctx)
    data = client.get("/api/productions").json()
    assert data["items"][0]["id"] == pid and data["items"][0]["status"] == "in_production"
    assert data["stats"]["in_production"]["value"] == 1
    assert client.get("/api/productions?state=published").json()["items"] == []
    assert client.get("/api/productions?q=zzz-nope").json()["items"] == []


def test_reset_keeps_topic_and_regenerates_prompts(client, ctx):
    pid = _prepare(client, ctx)
    job = client.post(f"/api/productions/{pid}/reset?keep_topic=true").json()["job"]
    wait_job(ctx, ctx.jobs.get(job["id"]))
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["state"] == "GENERATING" and len(detail["prompts"]) == 5 and detail["topic"]


def test_duplicate_and_delete(client, ctx):
    pid = _prepare(client, ctx)
    data = client.post(f"/api/productions/{pid}/duplicate").json()
    wait_job(ctx, ctx.jobs.get(data["job"]["id"]))
    new_id = data["id"]
    assert new_id != pid
    detail = client.get(f"/api/productions/{new_id}").json()
    assert detail["topic"] == client.get(f"/api/productions/{pid}").json()["topic"]
    assert client.delete(f"/api/productions/{new_id}").status_code == 200
    assert client.get(f"/api/productions/{new_id}").status_code == 400


def test_metadata_edit_before_publish(client, ctx):
    pid = _prepare(client, ctx)
    response = client.put(f"/api/productions/{pid}/metadata", json={"title": "New title", "description": "desc", "hashtags": ["facts"],
                                                                     "visibility": "unlisted"})
    assert response.status_code == 200
    detail = client.get(f"/api/productions/{pid}").json()
    assert detail["metadata"]["title"] == "New title" and detail["metadata"]["hashtags"] == ["#Shorts", "#facts"]
