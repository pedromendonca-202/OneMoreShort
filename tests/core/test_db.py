from sqlalchemy import func, select

from app.core.models import CostLedger, Production, Segment, Topic
from app.core.states import State


def test_production_roundtrip(session):
    p = Production(id="OMS-20260907-0001", state=State.SELECTED, config_snapshot={"veo": {"resolution": "1080p"}})
    session.add(p)
    session.flush()
    got = session.get(Production, "OMS-20260907-0001")
    assert got.state == State.SELECTED
    assert got.config_snapshot["veo"]["resolution"] == "1080p"
    assert got.created_at is not None


def test_relationships(session):
    p = Production(id="OMS-20260907-0001", state=State.GENERATING)
    session.add(p)
    session.add(Topic(production_id=p.id, topic="Why cats knock things over", category="animals", final_score=81.5, selected=True, reasons=["high curiosity"]))
    for i in range(1, 6):
        session.add(Segment(production_id=p.id, index=i, status="pending", attempts=0))
    session.flush()
    session.expire_all()
    got = session.get(Production, p.id)
    assert len(got.segments) == 5
    assert got.topics[0].selected is True


def test_cost_ledger_sum(session):
    session.add(Production(id="OMS-20260907-0001", state=State.GENERATING))
    session.add(CostLedger(production_id="OMS-20260907-0001", api="veo", units=8, unit_cost=0.08, usd=0.64))
    session.add(CostLedger(production_id="OMS-20260907-0001", api="veo", units=8, unit_cost=0.08, usd=0.64))
    session.flush()
    total = session.execute(select(func.sum(CostLedger.usd))).scalar_one()
    assert abs(total - 1.28) < 1e-9
