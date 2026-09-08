from datetime import datetime, timezone

import pytest

from app.core.cost import Budget, estimate_llm_cost, estimate_tts_cost, estimate_veo_cost, record_cost, spent_on_day
from app.core.errors import BudgetExceeded
from app.core.models import Production
from app.core.states import State


def test_veo_cost_by_resolution():
    assert estimate_veo_cost(8, "1080p") == pytest.approx(0.64)
    assert estimate_veo_cost(8, "720p") == pytest.approx(0.40)


def test_llm_cost_known_and_unknown_model():
    assert estimate_llm_cost("gemini-3.8-flash", 1_000_000, 1_000_000) == pytest.approx(0.75 + 3.75)
    # unknown models fall back to a conservative default instead of zero
    assert estimate_llm_cost("mystery-model", 1_000_000, 0) > 0


def test_tts_cost():
    assert estimate_tts_cost("gemini-2.5-flash-preview-tts", 1_000) > 0
    assert estimate_tts_cost("edge", 1_000) == 0


def test_budget_flow(session):
    session.add(Production(id="OMS-20260907-0001", state=State.GENERATING))
    now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    record_cost(session, "OMS-20260907-0001", api="veo", units=8, unit_cost=0.08, usd=0.64, at=now)
    record_cost(session, "OMS-20260907-0001", api="veo", units=8, unit_cost=0.08, usd=0.64, at=now)
    assert spent_on_day(session, now.date()) == pytest.approx(1.28)
    budget = Budget(daily_limit_usd=2.0)
    status = budget.check(session, now.date(), upcoming_usd=0.64)
    assert status.ok and status.remaining == pytest.approx(0.72)
    with pytest.raises(BudgetExceeded):
        budget.check(session, now.date(), upcoming_usd=0.80, raise_on_exceed=True)
