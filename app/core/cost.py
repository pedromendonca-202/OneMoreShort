"""Cost estimation, ledger and daily budget enforcement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BudgetExceeded
from app.core.models import CostLedger, Production

# Veo 3.1 Lite list price per generated second (audio included). Verified 2026-09-07 on ai.google.dev pricing.
VEO_PRICE_PER_SECOND: dict[str, float] = {"720p": 0.05, "1080p": 0.08}

# USD per 1M tokens (input, output). Verified where noted; others are conservative estimates.
LLM_PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.5-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 1.50),   # estimate
    "gemini-3.1-pro-preview": (2.00, 12.00),  # estimate
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}
DEFAULT_LLM_PRICE = (5.00, 25.00)

# Gemini TTS: $0.50/1M text tokens + $10/1M audio tokens. Approximated per 1,000 characters of input.
TTS_PRICE_PER_1K_CHARS: dict[str, float] = {
    "gemini-2.5-flash-preview-tts": 0.015,
    "gemini-3.1-flash-tts-preview": 0.030,
    "gemini-2.5-pro-preview-tts": 0.030,
    "edge": 0.0,
    "mock": 0.0,
}
GROUNDED_SEARCH_QUERY_USD = 0.035


def estimate_veo_cost(seconds: float, resolution: str) -> float:
    return round(seconds * VEO_PRICE_PER_SECOND.get(resolution, VEO_PRICE_PER_SECOND["1080p"]), 6)


def estimate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = LLM_PRICES.get(model, DEFAULT_LLM_PRICE)
    return round(input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out, 6)


def estimate_tts_cost(model: str, chars: int) -> float:
    return round(chars / 1000 * TTS_PRICE_PER_1K_CHARS.get(model, 0.03), 6)


def record_cost(
    session: Session,
    production_id: str | None,
    *,
    api: str,
    units: float,
    unit_cost: float,
    usd: float,
    note: str | None = None,
    at: datetime | None = None,
) -> CostLedger:
    row = CostLedger(production_id=production_id, api=api, units=units, unit_cost=unit_cost, usd=usd, note=note)
    if at is not None:
        row.at = at
    session.add(row)
    if production_id:
        prod = session.get(Production, production_id)
        if prod is not None:
            prod.cost_usd = (prod.cost_usd or 0.0) + usd
    session.flush()
    return row


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def spent_on_day(session: Session, day: date) -> float:
    start, end = _day_bounds(day)
    total = session.execute(select(func.sum(CostLedger.usd)).where(CostLedger.at >= start, CostLedger.at < end)).scalar()
    return float(total or 0.0)


@dataclass
class BudgetStatus:
    ok: bool
    spent: float
    limit: float
    upcoming: float

    @property
    def remaining(self) -> float:
        """Budget still available before the upcoming spend is applied."""
        return round(self.limit - self.spent, 6)


class Budget:
    def __init__(self, daily_limit_usd: float):
        self.daily_limit_usd = daily_limit_usd

    def check(self, session: Session, day: date | None = None, upcoming_usd: float = 0.0, raise_on_exceed: bool = False) -> BudgetStatus:
        day = day or datetime.now(timezone.utc).date()
        spent = spent_on_day(session, day)
        ok = spent + upcoming_usd <= self.daily_limit_usd + 1e-9
        status = BudgetStatus(ok=ok, spent=spent, limit=self.daily_limit_usd, upcoming=upcoming_usd)
        if not ok and raise_on_exceed:
            raise BudgetExceeded(spent, self.daily_limit_usd, upcoming_usd)
        return status
