from __future__ import annotations

import pytest

from app.core.errors import BudgetExceeded
from app.core.models import Production
from app.core.states import State
from app.llm.mock import MockLLM
from app.veo.generator import generate_segments
from app.veo.mock_client import MockVeoClient


def _production(session, production_id="OMS-20260907-0001"):
    session.add(Production(id=production_id, state=State.GENERATING))
    session.flush()
    return production_id


def test_mock_chain_produces_five_segments_and_last_frames(session, storage, settings, storyboard, bible):
    settings.veo.duration_seconds = 1
    settings.veo.check_continuity = True
    production_id = _production(session)
    records = generate_segments(production_id, storyboard, bible, MockVeoClient(), MockLLM(), storage, session, settings)
    assert len(records) == 5
    assert all(record.path.exists() and record.last_frame_path.exists() for record in records)
    assert [record.index for record in records] == [1, 2, 3, 4, 5]


def test_generator_resumes_after_segment_three_failure_without_regenerating_completed(session, storage, settings, storyboard, bible):
    settings.veo.duration_seconds = 1
    production_id = _production(session)
    failing = MockVeoClient(crash_segments={3})
    with pytest.raises(KeyboardInterrupt):
        generate_segments(production_id, storyboard, bible, failing, MockLLM(), storage, session, settings)
    resumed = MockVeoClient()
    records = generate_segments(production_id, storyboard, bible, resumed, MockLLM(), storage, session, settings)
    assert len(records) == 5
    assert [call.segment for call in resumed.calls] == [3, 4, 5]


def test_generator_stops_before_call_when_budget_would_be_exceeded(session, storage, settings, storyboard, bible):
    settings.veo.duration_seconds = 1
    settings.limits.daily_budget_usd = 0.01
    production_id = _production(session)
    client = MockVeoClient()
    with pytest.raises(BudgetExceeded):
        generate_segments(production_id, storyboard, bible, client, MockLLM(), storage, session, settings)
    assert client.calls == []
