"""Fixtures for the web panel tests: a mock-mode orchestrator behind a FastAPI TestClient."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

FIXED_NOW = datetime(2026, 9, 8, 11, 28, tzinfo=UTC)  # 08:28 in America/Sao_Paulo


@pytest.fixture
def orchestrator(settings):
    from app.pipeline.orchestrator import Orchestrator

    return Orchestrator(settings, clock=lambda: FIXED_NOW)


@pytest.fixture
def ctx(settings, orchestrator):
    from app.web.server import build_context

    return build_context(settings, orchestrator)


@pytest.fixture
def app(ctx):
    from app.web.server import create_app

    return create_app(ctx=ctx)


@pytest.fixture
def client(app, ctx):
    with TestClient(app) as test_client:
        test_client.headers["X-OMS-CSRF"] = ctx.csrf_token
        yield test_client


@pytest.fixture
def anon_client(app):
    with TestClient(app) as test_client:
        yield test_client


def wait_job(ctx, job, timeout: float = 120) -> None:
    import time

    deadline = time.time() + timeout
    while job.status in {"queued", "running"}:
        if time.time() > deadline:
            raise TimeoutError(f"job {job.name} still {job.status}")
        time.sleep(0.05)
