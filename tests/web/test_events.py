from __future__ import annotations

from app.core.errors import HumanActionRequired
from app.web.events import EventBus, JobRunner
from tests.web.conftest import wait_job


def test_job_runner_publishes_lifecycle_and_result():
    bus = EventBus()
    runner = JobRunner(bus)
    job = runner.submit("noop", lambda: 42, production_id="OMS-20260908-0001")
    wait_job(None, job)
    assert job.status == "done" and job.result == 42
    statuses = [e["data"]["status"] for e in bus.history if e["type"] == "job"]
    assert statuses[0] == "queued" and statuses[-1] == "done"
    assert any(e["type"] == "state" for e in bus.history)


def test_job_runner_reports_human_action_without_traceback():
    bus = EventBus()
    runner = JobRunner(bus)

    def boom():
        raise HumanActionRequired(problem="p", root_cause="r", automated="a", remains="w", action="do", next_step="n")

    job = runner.submit("boom", boom)
    wait_job(None, job)
    assert job.status == "human_action"
    assert job.human_action["action"] == "do"


def test_job_runner_reports_failure():
    bus = EventBus()
    job = JobRunner(bus).submit("fail", lambda: 1 / 0)
    wait_job(None, job)
    assert job.status == "failed" and "division" in job.error


def test_stage_hook_updates_current_job(orchestrator):
    bus = EventBus()
    runner = JobRunner(bus, orchestrator)
    pid = orchestrator.new_production()
    job = runner.submit("prepare", lambda: orchestrator.prepare(pid), production_id=pid)
    wait_job(None, job)
    assert job.status == "done"
    stages = [e["data"]["stage"] for e in bus.history if e["type"] == "job" and e["data"].get("stage")]
    assert "script" in stages and "prompts" in stages
    assert orchestrator.status(pid)["state"] == "GENERATING"
