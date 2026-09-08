"""Policy-safe A/B testing (spec section 47): one variant per production, evaluated on outcomes."""
from __future__ import annotations

import hashlib
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.core.models import ABAssignment, Production
from app.intelligence.features import extract_features
from app.intelligence.schemas import ABResult

DEFAULT_VARIANTS: dict[str, tuple[str, ...]] = {
    "hook_style": ("curiosity", "shock", "question", "contrarian"),
    "ending_style": ("loop", "statement", "cliff"),
    "caption_style": ("bold-white-outline", "yellow-highlight"),
}


class ABTest:
    def __init__(self, variants: dict[str, tuple[str, ...]] | None = None):
        self.variants = {**DEFAULT_VARIANTS, **(variants or {})}

    def assign(self, production: Any, dimension: str, session: Session | None = None) -> str:
        options = self.variants.get(dimension, ("A", "B"))
        pid = str(getattr(production, "id", production))
        digest = int(hashlib.sha256(f"{pid}:{dimension}".encode()).hexdigest(), 16)
        variant = options[digest % len(options)]
        if session is not None:
            existing = session.query(ABAssignment).filter_by(production_id=pid, dimension=dimension).first()
            if existing is not None:
                return existing.variant
            session.add(ABAssignment(production_id=pid, dimension=dimension, variant=variant))
            session.flush()
        return variant

    def evaluate(self, session: Session, dimension: str, metric: str = "retention") -> ABResult:
        rows = session.query(ABAssignment).filter_by(dimension=dimension).all()
        scores: dict[str, list[float]] = {}
        for row in rows:
            production = session.get(Production, row.production_id)
            if production is None or not production.snapshots:
                continue
            outcome = extract_features(production)
            scores.setdefault(row.variant, []).append(float(getattr(outcome, metric, 0) or 0))
        if not scores:
            return ABResult(dimension=dimension)
        averages = {variant: mean(values) for variant, values in scores.items()}
        winner = max(averages, key=averages.get)
        n = min(len(values) for values in scores.values())
        spread = (max(averages.values()) - min(averages.values())) / max(max(averages.values()), 1e-9) if len(averages) > 1 else 0
        confidence = round(min(1.0, n / 5) * min(1.0, spread * 2), 3) if len(averages) > 1 else 0
        return ABResult(dimension=dimension, winner=winner, confidence=confidence, variants=averages)
