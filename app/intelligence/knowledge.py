"""Internal knowledge base (spec section 48): what worked, what failed, reused by every new production."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.models import KnowledgeEntry, Production
from app.intelligence.schemas import Insight, VideoOutcome
from app.research.schemas import KnowledgeContext

_CONTEXT_KINDS = ("best_hooks", "best_structures", "failed_patterns", "successful_prompts")


def _describe(insight: Insight, label: str | None = None) -> str:
    sign = "+" if insight.effect_vs_channel >= 0 else "-"
    return f"{label or insight.value} ({sign}{abs(insight.effect_vs_channel):.0%} {insight.metric} vs channel, n={insight.n})"


class Knowledge:
    def __init__(self) -> None:
        self.entries: list[tuple[str, Any]] = []

    def add(self, kind: str, payload: Any) -> None:
        self.entries.append((kind, payload))

    # ------------------------------------------------------------------ persistence
    def rebuild(self, session: Session, insights: list[Insight], outcomes: list[VideoOutcome],
                productions: list[Production] | None = None, *, top_n: int = 5) -> int:
        """Replace the persisted knowledge base from the latest insights and outcomes."""
        session.query(KnowledgeEntry).delete()
        rows: list[KnowledgeEntry] = []
        retention = [i for i in insights if i.metric == "retention"]
        by_feature = lambda feature, positive: sorted(  # noqa: E731
            (i for i in retention if i.feature == feature and (i.effect_vs_channel >= 0) == positive),
            key=lambda i: abs(i.effect_vs_channel) * i.confidence, reverse=True)
        for insight in by_feature("hook_type", True)[:top_n]:
            rows.append(KnowledgeEntry(kind="best_hooks", title=_describe(insight), payload=insight.model_dump(), score=insight.effect_vs_channel))
        for feature in ("ending_type", "pacing_bucket", "duration_bucket", "narrative_structure"):
            for insight in by_feature(feature, True)[:2]:
                rows.append(KnowledgeEntry(kind="best_structures", title=_describe(insight, f"{feature}={insight.value}"),
                                           payload=insight.model_dump(), score=insight.effect_vs_channel))
        for feature in ("hook_type", "category", "ending_type", "pacing_bucket", "duration_bucket", "visual_style"):
            for insight in by_feature(feature, False)[:2]:
                if insight.effect_vs_channel < -0.05:
                    rows.append(KnowledgeEntry(kind="failed_patterns", title=_describe(insight, f"{feature}={insight.value}"),
                                               payload=insight.model_dump(), score=insight.effect_vs_channel))
        drop_times = [t for outcome in outcomes for t in outcome.drop_offs]
        if drop_times:
            buckets: dict[int, int] = {}
            for t in drop_times:
                buckets[int(t // 8) + 1] = buckets.get(int(t // 8) + 1, 0) + 1
            worst_segment = max(buckets, key=buckets.get)
            rows.append(KnowledgeEntry(kind="failed_patterns", title=f"Common drop-off in segment {worst_segment} ({buckets[worst_segment]} videos)",
                                       payload={"segment": worst_segment, "count": buckets[worst_segment]}, score=-0.1))
        ranked = sorted(outcomes, key=lambda o: (o.retention, o.views), reverse=True)
        prompt_lookup = {p.id: p for p in (productions or [])}
        for outcome in ranked[:top_n]:
            if outcome.retention <= 0 and outcome.views <= 0:
                continue
            rows.append(KnowledgeEntry(kind="successful_topics", production_id=outcome.production_id or None,
                                       title=f"{outcome.topic or outcome.title} [{outcome.category}] retention {outcome.retention:.0%}, {int(outcome.views):,} views",
                                       payload=outcome.model_dump(), score=outcome.retention))
            production = prompt_lookup.get(outcome.production_id)
            if production is not None and production.prompts:
                first = production.prompts[0]
                rows.append(KnowledgeEntry(kind="successful_prompts", production_id=outcome.production_id,
                                           title=f"{outcome.title or outcome.topic}: {first.prompt[:160]}",
                                           payload={"prompt": first.prompt, "negative_prompt": first.negative_prompt}, score=outcome.retention))
            elif production is not None and production.script is not None:
                rows.append(KnowledgeEntry(kind="successful_scripts", production_id=outcome.production_id, title=outcome.title or outcome.topic,
                                           payload={"hook": (production.script.data or {}).get("beats", [{}])[0].get("narration", "")},
                                           score=outcome.retention))
        for insight in sorted(insights, key=lambda i: abs(i.effect_vs_channel) * i.confidence, reverse=True)[:40]:
            rows.append(KnowledgeEntry(kind="insight", title=_describe(insight, f"{insight.feature}={insight.value}"),
                                       payload=insight.model_dump(), score=insight.effect_vs_channel, tags=[insight.feature, insight.metric]))
        session.add_all(rows)
        session.flush()
        return len(rows)

    # ------------------------------------------------------------------ retrieval
    def context_for(self, topic_category: str | None, session: Session | None = None) -> KnowledgeContext:
        if session is None:
            grouped = {k: [p for kind, p in self.entries if kind == k] for k in _CONTEXT_KINDS}
            return KnowledgeContext(**grouped)
        grouped: dict[str, list[str]] = {k: [] for k in _CONTEXT_KINDS}
        rows = session.query(KnowledgeEntry).order_by(KnowledgeEntry.score.desc().nullslast()).all()
        for row in rows:
            if row.kind in grouped and len(grouped[row.kind]) < 6:
                grouped[row.kind].append(row.title)
            elif row.kind == "successful_topics" and len(grouped["best_structures"]) < 8:
                payload = row.payload or {}
                if topic_category and payload.get("category") == topic_category:
                    grouped["best_structures"].append(f"top {topic_category} video: {row.title}")
        failed = [row.title for row in rows if row.kind == "failed_patterns"]
        grouped["failed_patterns"] = sorted(set(grouped["failed_patterns"] + failed), key=failed.index)[:8]
        return KnowledgeContext(**grouped)
