from __future__ import annotations

from app.audio.schemas import NarrationPlan
from app.editing.synth import synth_segment
from app.llm.mock import MockLLM
from app.metadata.schemas import PolicyVerdict, VideoMetadata
from app.quality.gate import run_quality_gate


def metadata():
    return VideoMetadata(title="A valid title", description="A valid description.", hashtags=["#Science", "#Space", "#Shorts"], tags=["science"])


def test_quality_gate_fails_overlength_and_missing_audio(tmp_path, settings):
    settings.video.max_duration_s = 1
    silent = synth_segment(tmp_path / "silent.mp4", 1, "black", "silent", with_audio=False)
    report = run_quality_gate(silent, [], NarrationPlan(beats=[], total_s=0), None, metadata(), [], MockLLM(), settings)
    assert not report.passed
    assert any(check.name == "audio" and not check.passed for check in report.checks)


def test_policy_failure_is_propagated_as_needs_review(tmp_path, settings):
    video = synth_segment(tmp_path / "valid.mp4", 1, "black", "valid", with_audio=True)
    llm = MockLLM(handlers={"PolicyVerdict": lambda req: PolicyVerdict(ok=False, flags=["misinformation"], reasons=["unsupported claim"])})
    report = run_quality_gate(video, [], NarrationPlan(beats=[], total_s=0), None, metadata(), [], llm, settings)
    assert not report.passed and report.failed_stage_hint == "NEEDS_REVIEW"
