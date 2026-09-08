"""Shared pytest fixtures for OneMoreShort."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Tests must never pick up the operator's real credentials or .env."""
    for key in list(os.environ):
        if key.startswith("OMS_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OMS_MODE", "mock")
    yield


@pytest.fixture
def settings(tmp_path):
    from app.core.config import load_settings

    s = load_settings(project_root=PROJECT_ROOT, env_file=None)
    s.paths.storage_root = str(tmp_path / "storage")
    s.paths.logs_dir = str(tmp_path / "logs")
    s.paths.database_url = "sqlite:///" + (tmp_path / "test.db").as_posix()
    s.paths.secrets_dir = str(tmp_path / "secrets")
    return s


@pytest.fixture
def engine(settings):
    from app.core.db import get_engine, init_db

    eng = get_engine(settings.paths.database_url)
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    from app.core.db import session_scope

    with session_scope(engine) as s:
        yield s


@pytest.fixture
def storage(settings):
    from app.core.storage import Storage

    return Storage(Path(settings.paths.storage_root))
