"""Failure simulations from spec section 53: every failure must land in a documented, recoverable state."""
from __future__ import annotations

import httpx
import pytest

from app.core.errors import HumanActionRequired
from app.core.states import State
from app.editing.synth import synth_segment
from app.manual_video.workflow import inbox_for
from app.pipeline.orchestrator import Orchestrator
from app.trends.reddit_source import RedditSource


def _short(settings):
    settings.veo.duration_seconds = 1
    settings.video.max_duration_s = 5
    settings.video.music_enabled = False
    settings.video.logo_watermark = False
    return settings


def _prepared(settings):
    o = Orchestrator(settings)
    pid = o.new_production()
    o.prepare(pid)
    return o, pid, inbox_for(pid, o.storage, settings)


def _fill(inbox, count=5, skip=None, with_audio=True):
    for i in range(1, count + 1):
        if i == skip:
            continue
        synth_segment(inbox / f"segment_{i}.mp4", 1, "black", str(i), with_audio=with_audio)


def test_missing_segment_is_reported_and_recoverable(settings):
    o, pid, inbox = _prepared(_short(settings))
    _fill(inbox, skip=3)
    with pytest.raises(ValueError, match="1 through 5|five"):
        o.collect(pid)
    assert o.status(pid)["state"] in {"GENERATING", "VALIDATING"}
    synth_segment(inbox / "segment_3.mp4", 1, "black", "3", with_audio=True)
    o.collect(pid)
    assert o.status(pid)["state"] == "EDITING"


def test_corrupted_segment_is_rejected_without_losing_the_production(settings):
    o, pid, inbox = _prepared(_short(settings))
    _fill(inbox, skip=2)
    (inbox / "segment_2.mp4").write_bytes(b"\x00garbage" * 2048)
    with pytest.raises(Exception) as excinfo:
        o.collect(pid)
    assert "segment" in str(excinfo.value).lower() or "ffprobe" in str(excinfo.value).lower()
    synth_segment(inbox / "segment_2.mp4", 1, "black", "2", with_audio=True)
    o.collect(pid)
    assert o.status(pid)["state"] == "EDITING"


def test_segment_without_audio_fails_validation(settings):
    o, pid, inbox = _prepared(_short(settings))
    _fill(inbox, skip=4)
    synth_segment(inbox / "segment_4.mp4", 1, "black", "4", with_audio=False)
    with pytest.raises(ValueError, match="audio"):
        o.collect(pid)


def test_trend_source_network_failure_degrades_to_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    source = RedditSource(subreddits=["science"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert source.fetch(limit=5) == []


def test_upload_without_oauth_moves_to_needs_human_action(settings, tmp_path):
    settings = _short(settings)
    settings.upload.enabled = True
    settings.youtube_client_secret_path = str(tmp_path / "missing_client_secret.json")
    settings.youtube_token_path = str(tmp_path / "token.json")
    o, pid, inbox = _prepared(settings)  # prepared offline in mock mode (no network)
    _fill(inbox)
    o.collect(pid)
    # Simulate a live upload attempt: real OAuth is required, providers stay offline.
    settings.mode = "live"
    settings.llm.provider = "mock"
    settings.tts.provider = "mock"
    with pytest.raises(HumanActionRequired) as excinfo:
        o.finish(pid)
    assert "OAuth" in excinfo.value.problem
    status = o.status(pid)
    assert status["state"] == State.NEEDS_HUMAN_ACTION.value
    assert status["human_action"]["action"]
    assert status["final_video"], "the rendered video is preserved for resume"


def test_database_unavailable_surfaces_clearly(settings):
    settings.paths.database_url = "sqlite:///Z:/definitely/not/here/oms.db"
    with pytest.raises(Exception):
        Orchestrator(settings)
