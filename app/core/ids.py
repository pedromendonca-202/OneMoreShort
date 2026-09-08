"""Production identifiers: OMS-YYYYMMDD-NNNN (sequence resets daily)."""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import Production

PREFIX = "OMS"
_ID_RE = re.compile(r"^OMS-(\d{8})-(\d{4,})$")


def new_production_id(session: Session, today: date | None = None) -> str:
    day = (today or date.today()).strftime("%Y%m%d")
    prefix = f"{PREFIX}-{day}-"
    max_id = session.execute(select(func.max(Production.id)).where(Production.id.like(prefix + "%"))).scalar()
    n = int(max_id.rsplit("-", 1)[1]) + 1 if max_id else 1
    return f"{prefix}{n:04d}"


def parse_production_id(pid: str) -> tuple[date, int]:
    m = _ID_RE.match(pid)
    if not m:
        raise ValueError(f"invalid production id: {pid}")
    d = m.group(1)
    return date(int(d[:4]), int(d[4:6]), int(d[6:8])), int(m.group(2))
