"""Operator CLI smoke tests (mock mode, isolated database and storage)."""
from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from app import cli
from app.editing.synth import synth_segment

runner = CliRunner()


@pytest.fixture
def isolated(settings, monkeypatch):
    settings.veo.duration_seconds = 1
    settings.video.max_duration_s = 5
    settings.video.music_enabled = False
    settings.video.logo_watermark = False
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    return settings


def _pid(output: str) -> str:
    match = re.search(r"OMS-\d{8}-\d{4}", output)
    assert match, output
    return match.group(0)


def test_doctor_reports_manual_workflow(isolated):
    result = runner.invoke(cli.app, ["doctor"])
    assert result.exit_code == 0 and "manual" in result.output.lower()


def test_new_status_list_and_export(isolated):
    created = runner.invoke(cli.app, ["new"])
    assert created.exit_code == 0
    pid = _pid(created.output)
    status = runner.invoke(cli.app, ["status", pid])
    assert status.exit_code == 0 and "DISCOVERING" in status.output
    exported = runner.invoke(cli.app, ["export-prompts", pid])
    assert exported.exit_code == 0 and "MANUAL_VIDEO_HANDOFF" in exported.output
    listed = runner.invoke(cli.app, ["list"])
    assert listed.exit_code == 0 and pid in listed.output and "GENERATING" in listed.output


def test_new_refuses_second_production_same_day_unless_forced(isolated):
    assert runner.invoke(cli.app, ["new"]).exit_code == 0
    second = runner.invoke(cli.app, ["new"])
    assert second.exit_code != 0 and "WAITING_FOR_HUMAN_ACTION" in second.output
    forced = runner.invoke(cli.app, ["new", "--force"])
    assert forced.exit_code == 0


def test_resume_prints_human_action_then_completes(isolated):
    from app.core.storage import Storage
    from app.manual_video.workflow import inbox_for

    pid = _pid(runner.invoke(cli.app, ["new"]).output)
    waiting = runner.invoke(cli.app, ["resume", pid])
    assert waiting.exit_code != 0 and "EXACT HUMAN ACTION REQUIRED" in waiting.output
    storage = Storage(isolated.resolve(isolated.paths.storage_root))
    inbox = inbox_for(pid, storage, isolated)
    for i in range(1, 6):
        synth_segment(inbox / f"segment_{i}.mp4", 1, "black", str(i), with_audio=True)
    done = runner.invoke(cli.app, ["resume", pid])
    assert done.exit_code == 0 and "READY" in done.output
    report = runner.invoke(cli.app, ["metrics"])
    assert report.exit_code == 0 and "videos_generated" in report.output
