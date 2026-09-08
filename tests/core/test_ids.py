from datetime import date

from app.core.ids import new_production_id, parse_production_id
from app.core.models import Production
from app.core.states import State


def test_id_format_and_sequence(session):
    d = date(2026, 9, 7)
    first = new_production_id(session, d)
    assert first == "OMS-20260907-0001"
    session.add(Production(id=first, state=State.DISCOVERING))
    session.flush()
    second = new_production_id(session, d)
    assert second == "OMS-20260907-0002"


def test_sequence_resets_per_day(session):
    session.add(Production(id="OMS-20260907-0001", state=State.DISCOVERING))
    session.flush()
    assert new_production_id(session, date(2026, 9, 8)) == "OMS-20260908-0001"


def test_parse():
    d, n = parse_production_id("OMS-20260907-0042")
    assert d == date(2026, 9, 7) and n == 42
