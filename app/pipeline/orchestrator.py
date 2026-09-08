"""Persistent, idempotent workflow around the manual visual-generation hand-off.

Stages (spec section 30):  DISCOVERING -> SELECTED -> RESEARCHING -> SCRIPTING -> STORYBOARDING ->
GENERATING (operator creates the five clips) -> VALIDATING -> EDITING -> QUALITY_CHECK -> READY ->
UPLOADING -> PUBLISHED -> ANALYZING -> LEARNED.  Every stage is safe to re-run: artefacts already in the
database are loaded instead of regenerated, and the LLM is only called for missing pieces.
"""
from __future__ import annotations

import random
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.audio.tts import build_tts
from app.continuity.bible import build_bible
from app.continuity.schemas import ContinuityBible
from app.core.config import Settings
from app.core.cost import record_cost
from app.core.db import get_engine, init_db, session_scope
from app.core.errors import HumanActionRequired
from app.core.ids import new_production_id
from app.core.logging import get_logger, record_event
from app.core.models import (
    AudioAsset,
    Caption,
    ContinuityBible as BibleRow,
    FinalVideo,
    HumanAction,
    Production,
    Prompt as PromptRow,
    Research as ResearchRow,
    Script as ScriptRow,
    Storyboard as StoryRow,
    Topic,
    Upload,
    VideoMetadata as MetadataRow,
)
from app.core.states import HOLD_STATES, PIPELINE_ORDER, State
from app.core.storage import Storage
from app.llm.base import LLMProvider
from app.llm.router import build_llm
from app.manual_video.workflow import ManualCollection, ManualPromptPackage, collect_manual_segments, export_prompts, inbox_for
from app.research.deep_research import deep_research
from app.research.schemas import KnowledgeContext, Research, StrategyWeights, TopicScore
from app.scripting.generator import generate_script
from app.scripting.schemas import Script
from app.storyboard.generator import generate_storyboard
from app.storyboard.schemas import Storyboard

log = get_logger(component="orchestrator")

# Stages that leave the operator with something to do; `status` surfaces them.
_MANUAL_STATES = {State.GENERATING}


class Orchestrator:
    def __init__(self, settings: Settings, *, llm: LLMProvider | None = None, youtube: Any | None = None,
                 tts: Any | None = None, clock=None):
        self.settings = settings
        self.engine = get_engine(settings.paths.database_url)
        init_db(self.engine)
        self.storage = Storage(settings.resolve(settings.paths.storage_root))
        self._llm = llm
        self._youtube = youtube
        self._tts = tts
        self.now = clock or (lambda: datetime.now(UTC))

    # ------------------------------------------------------------------ providers
    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = build_llm(self.settings)
        return self._llm

    @property
    def tts(self):
        if self._tts is None:
            self._tts = build_tts(self.settings)
        return self._tts

    @property
    def youtube(self):
        if self._youtube is None:
            if self.settings.mode == "mock":
                from app.youtube.mock import MockYouTubeClient

                self._youtube = MockYouTubeClient()
            else:
                from app.youtube.auth import get_credentials
                from app.youtube.uploader import GoogleYouTubeClient

                creds = get_credentials(self.settings.resolve(self.settings.youtube_client_secret_path),
                                        self.settings.resolve(self.settings.youtube_token_path))
                self._youtube = GoogleYouTubeClient(creds)
        return self._youtube

    # ------------------------------------------------------------------ helpers
    @contextmanager
    def _stage(self, session: Session, pid: str | None, stage: str, action: str = "run") -> Iterator[None]:
        """Record one structured event (spec section 31) with duration, status, error and LLM cost."""
        started = time.perf_counter()
        try:
            yield
        except HumanActionRequired as err:
            self._record_llm_cost(session, pid, stage)
            record_event(session, action=action, status="needs_human_action", production_id=pid, stage=stage,
                         duration_ms=int((time.perf_counter() - started) * 1000), error=err.problem)
            raise
        except Exception as err:
            self._record_llm_cost(session, pid, stage)
            record_event(session, action=action, status="failed", production_id=pid, stage=stage,
                         duration_ms=int((time.perf_counter() - started) * 1000), error=str(err))
            raise
        cost = self._record_llm_cost(session, pid, stage)
        record_event(session, action=action, status="ok", production_id=pid, stage=stage,
                     duration_ms=int((time.perf_counter() - started) * 1000), cost_usd=cost or None)

    def _record_llm_cost(self, session: Session, pid: str | None, stage: str) -> float:
        drain = getattr(self._llm, "drain_cost", None)
        cost = float(drain()) if drain else 0.0
        if cost > 0:
            record_cost(session, pid, api="llm", units=1, unit_cost=cost, usd=cost, note=stage)
        return cost

    @staticmethod
    def _advance(production: Production, target: State) -> None:
        """Move forward through the pipeline (never backwards); hold states are always reachable."""
        current = production.state
        if target in HOLD_STATES:
            production.previous_state, production.state = current, target
            return
        if current in HOLD_STATES:
            production.state = target
            return
        if PIPELINE_ORDER.index(target) > PIPELINE_ORDER.index(current):
            production.previous_state, production.state = current, target

    def _human_action(self, session: Session, production: Production, err: HumanActionRequired) -> None:
        session.add(HumanAction(production_id=production.id, **err.as_dict()))
        production.human_action = err.as_dict()
        self._advance(production, State.NEEDS_HUMAN_ACTION)

    def _get(self, session: Session, pid: str) -> Production:
        production = session.get(Production, pid)
        if production is None:
            raise ValueError(f"unknown production {pid}")
        return production

    def _selected_topic(self, production: Production) -> TopicScore | None:
        row = next((topic for topic in production.topics if topic.selected), None)
        if row is None:
            return None
        return TopicScore(topic=row.topic, category=row.category, trend_score=row.trend_score, viral_potential=row.viral_potential,
                          us_relevance=row.us_relevance, competition=row.competition, shorts_fit=row.shorts_fit,
                          originality=row.originality, risk=row.risk, final_score=row.final_score, reasons=row.reasons or [])

    # ------------------------------------------------------------------ learning inputs (filled by Phase C)
    def _strategy(self, session: Session) -> StrategyWeights:
        try:
            from app.intelligence.strategy import load_strategy

            return load_strategy(session, self.settings)
        except ImportError:  # pragma: no cover - transitional
            return StrategyWeights(exploration_ratio=self.settings.intelligence.exploration_ratio)

    def _knowledge(self, session: Session, category: str | None) -> KnowledgeContext:
        try:
            from app.intelligence.knowledge import Knowledge

            return Knowledge().context_for(category, session=session)
        except (ImportError, TypeError):  # pragma: no cover - transitional
            return KnowledgeContext()

    # ------------------------------------------------------------------ public API
    def new_production(self, *, force: bool = False) -> str:
        with session_scope(self.engine) as session:
            today = self.now().date()
            if not force:
                prefix = f"OMS-{today:%Y%m%d}-"
                made_today = session.query(Production).filter(Production.id.like(prefix + "%")).count()
                if made_today >= self.settings.limits.max_videos_per_day:
                    raise HumanActionRequired(
                        problem=f"Daily production limit reached ({made_today}/{self.settings.limits.max_videos_per_day}).",
                        root_cause="limits.max_videos_per_day caps how many productions start per calendar day.",
                        automated="Counted today's productions before creating a new one.",
                        remains="Wait for tomorrow's daily run, or raise the limit deliberately.",
                        action="Run again with --force, or set limits.max_videos_per_day in config/local.yaml.",
                        next_step="The next `daily` run creates tomorrow's production automatically.",
                    )
            pid = new_production_id(session, today)
            session.add(Production(id=pid, state=State.DISCOVERING, config_snapshot=self.settings.snapshot(), started_at=self.now()))
            record_event(session, action="new_production", status="ok", production_id=pid, stage="discover")
            return pid

    def prepare(self, pid: str) -> ManualPromptPackage:
        """Topic -> research -> script -> storyboard -> continuity bible -> five prompt files."""
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            strategy = self._strategy(session)

            with self._stage(session, pid, "discover"):
                topic = self._selected_topic(production)
                if topic is None:
                    topic = self._discover_topic(session, strategy)
                    session.add(Topic(production_id=pid, topic=topic.topic, category=topic.category, trend_score=topic.trend_score,
                                      viral_potential=topic.viral_potential, us_relevance=topic.us_relevance, competition=topic.competition,
                                      shorts_fit=topic.shorts_fit, originality=topic.originality, risk=topic.risk, selected=True,
                                      final_score=topic.final_score, reasons=topic.reasons,
                                      selection_reason="; ".join(topic.reasons[:3]) or "highest strategy-adjusted score"))
                    session.flush()
                self._advance(production, State.SELECTED)

            knowledge = self._knowledge(session, topic.category)

            with self._stage(session, pid, "research"):
                self._advance(production, State.RESEARCHING)
                if production.research is not None:
                    research = Research.model_validate(production.research.data)
                else:
                    research = deep_research(self.llm, topic.topic, use_search=self.settings.is_live and self.settings.llm.use_search_grounding)
                    session.add(ResearchRow(production_id=pid, topic=topic.topic, data=research.model_dump(),
                                            sources=[fact.source for fact in research.facts if fact.source]))
                    session.flush()

            with self._stage(session, pid, "script"):
                self._advance(production, State.SCRIPTING)
                if production.script is not None:
                    script = Script.model_validate(production.script.data)
                else:
                    script = generate_script(self.llm, topic, research, knowledge, self.settings)
                    session.add(ScriptRow(production_id=pid, data=script.model_dump(), text=script.text, hook_type=script.hook_type.value,
                                          ending_type=script.ending_type, total_words=script.total_words, est_duration_s=script.est_duration_s))
                    session.flush()

            with self._stage(session, pid, "storyboard"):
                self._advance(production, State.STORYBOARDING)
                if production.storyboard is not None:
                    storyboard = Storyboard.model_validate(production.storyboard.data)
                else:
                    storyboard = generate_storyboard(self.llm, script, self.settings)
                    session.add(StoryRow(production_id=pid, data=storyboard.model_dump(), visual_style=storyboard.visual_style))
                    session.flush()
                if production.bible is not None:
                    bible = ContinuityBible.model_validate(production.bible.data)
                else:
                    bible = build_bible(self.llm, script, storyboard)
                    session.add(BibleRow(production_id=pid, data=bible.model_dump()))
                    session.flush()

            with self._stage(session, pid, "prompts"):
                package = export_prompts(pid, storyboard, bible, self.storage, self.settings)
                if not production.prompts:
                    for index, path in enumerate(package.prompt_files, start=1):
                        text = path.read_text(encoding="utf-8")
                        prompt_text, _, negative = text.partition("\n\nNEGATIVE PROMPT:\n")
                        session.add(PromptRow(production_id=pid, segment_index=index, attempt=1, prompt=prompt_text.strip(),
                                              negative_prompt=negative.strip() or None,
                                              config={"duration_seconds": self.settings.veo.duration_seconds, "aspect_ratio": "9:16"}))
                self._advance(production, State.GENERATING)
            return package

    def _discover_topic(self, session: Session, strategy: StrategyWeights) -> TopicScore:
        manual = getattr(self.settings.trends, "manual_topic", None)
        if manual:
            return TopicScore(topic=str(manual), category="manual", trend_score=50, viral_potential=50, us_relevance=50, competition=50,
                              shorts_fit=80, originality=60, risk=10, final_score=60, reasons=["manual topic from configuration"])
        if self.settings.mode != "live":
            return TopicScore(topic="A surprising science fact", category="science", trend_score=70, viral_potential=70, us_relevance=80,
                              competition=30, shorts_fit=90, originality=80, risk=10, final_score=78, reasons=["deterministic mock discovery"])
        from app.research.scorer import score_topics
        from app.research.selector import select_topic
        from app.trends.aggregator import aggregate
        from app.trends.gtrends_rss_source import GoogleTrendsRSSSource
        from app.trends.hackernews_source import HackerNewsSource
        from app.trends.news_rss_source import GoogleNewsRSSSource
        from app.trends.reddit_source import RedditSource
        from app.trends.wikipedia_source import WikipediaTopViewedSource
        from app.trends.youtube_source import YouTubeTrendSource

        cfg = self.settings.trends
        sources: list[Any] = [
            RedditSource(cfg.reddit_subreddits, timeout_s=cfg.http_timeout_s),
            GoogleNewsRSSSource(region=cfg.region, language=cfg.language, timeout_s=cfg.http_timeout_s),
            HackerNewsSource(timeout_s=cfg.http_timeout_s),
            WikipediaTopViewedSource(timeout_s=cfg.http_timeout_s),
            GoogleTrendsRSSSource(region=cfg.region, timeout_s=cfg.http_timeout_s),
        ]
        if self.settings.google_api_key:
            sources.append(YouTubeTrendSource(self.settings.google_api_key.get_secret_value(), region=cfg.region,
                                              categories=cfg.youtube_categories, timeout_s=cfg.http_timeout_s))
        signals = [signal for source in sources for signal in source.fetch(cfg.per_source_limit)]
        clusters = aggregate(signals, llm=self.llm, max_candidates=cfg.max_candidates)
        if not clusters:
            raise RuntimeError("no usable trend signals; retry later or check network/source configuration")
        scores = score_topics(self.llm, clusters, knowledge=self._knowledge(session, None))
        seed = self.settings.veo.seed_base
        return select_topic(scores, strategy, rng=random.Random(seed))[0]

    def collect(self, pid: str) -> ManualCollection:
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            with self._stage(session, pid, "validate"):
                self._advance(production, State.VALIDATING)
                result = collect_manual_segments(pid, self.storage, session, self.settings)
                self._advance(production, State.EDITING)
            return result

    def inbox_ready(self, pid: str) -> tuple[bool, int]:
        inbox = inbox_for(pid, self.storage, self.settings)
        accepted = {ext.lower() for ext in self.settings.generation.accepted_extensions}
        files = [path for path in inbox.iterdir() if path.is_file() and path.suffix.lower() in accepted]
        return len(files) >= 5, len(files)

    def finish(self, pid: str) -> Path:
        """Narration, mix, captions, render, quality gate, metadata and (optional) upload."""
        from app.audio.mixer import mix_audio
        from app.audio.music import choose_music
        from app.audio.narration import narrate
        from app.captions.aligner import align_words, build_phrases
        from app.captions.ass_renderer import render_ass
        from app.captions.style import CaptionStyle
        from app.editing.probe import probe
        from app.editing.render import render_final
        from app.metadata.generator import generate_metadata
        from app.quality.gate import run_quality_gate

        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            if production.script is None:
                raise ValueError("production must be prepared (export-prompts) and collected before finish")
            concat = self.storage.path_for(pid, "renders", "segments_concat.mp4")
            if not concat.exists():
                raise ValueError("collect clips before finish")
            script = Script.model_validate(production.script.data)
            topic = self._selected_topic(production)
            video_cfg = self.settings.video

            with self._stage(session, pid, "narration"):
                self._advance(production, State.EDITING)
                tts = self.tts
                narration = narrate(script, tts, self.llm, self.storage, pid, video_cfg.max_duration_s,
                                    tighten_passes=self.settings.tts.tighten_passes)
                session.query(AudioAsset).filter_by(production_id=pid).delete()
                voice = getattr(tts, "voice", None)
                for item in narration.beats:
                    session.add(AudioAsset(production_id=pid, kind="narration_beat", beat_index=item.beat.index, path=str(item.path),
                                           duration_s=item.duration_s, start_s=item.start_s, voice=voice,
                                           words=[w.model_dump() for w in item.words] if item.words else None))

            with self._stage(session, pid, "mix"):
                music = None
                if video_cfg.music_enabled:
                    music = choose_music(self.settings.resolve(self.settings.paths.assets_dir) / "music")
                    if music is not None:
                        session.add(AudioAsset(production_id=pid, kind="music", path=str(music), duration_s=0,
                                               meta={"gain_db": video_cfg.music_gain_db}))
                mixed = mix_audio(concat, narration, music, self.storage.path_for(pid, "audio", "mixed.wav"), self.settings)
                session.add(AudioAsset(production_id=pid, kind="mix", path=str(mixed), duration_s=probe(mixed).duration_s, voice=voice))

            ass = None
            with self._stage(session, pid, "captions"):
                if self.settings.captions.enabled:
                    cap = self.settings.captions
                    phrases = build_phrases(align_words(narration), cap.max_words)
                    style = CaptionStyle(font=cap.font, font_size=cap.font_size, primary_color=cap.primary_color,
                                         highlight_color=cap.highlight_color, outline_color=cap.outline_color, outline=cap.outline,
                                         shadow=cap.shadow, uppercase=cap.uppercase,
                                         margin_v=int(round(video_cfg.height * (1 - cap.position_pct))))
                    ass = render_ass(phrases, style, self.storage.path_for(pid, "captions", "captions.ass"))
                    caption_row = production.caption or Caption(production_id=pid, ass_path=str(ass))
                    caption_row.ass_path, caption_row.style, caption_row.phrase_count = str(ass), style.model_dump(), len(phrases)
                    caption_row.words = [w.model_dump() for phrase in phrases for w in phrase.words]
                    session.add(caption_row)

            with self._stage(session, pid, "render"):
                logo = None
                if video_cfg.logo_watermark:
                    candidate = self.settings.resolve(video_cfg.logo_path)
                    logo = candidate if candidate.is_file() else None
                final = render_final(concat, mixed, ass, logo, self.storage.path_for(pid, "renders", "OneMoreShort_Final.mp4"),
                                     video_cfg.max_duration_s, self.storage.root, logo_width_px=video_cfg.logo_width_px,
                                     logo_opacity=video_cfg.logo_opacity)

            with self._stage(session, pid, "metadata"):
                meta = generate_metadata(self.llm, script, topic or script.title_working, self.settings)
                if self.settings.upload.add_shorts_hashtag and "#Shorts" not in meta.hashtags:
                    meta = meta.model_copy(update={"hashtags": ["#Shorts", *meta.hashtags][:6]})
                publish_at = self._publish_at() if self.settings.upload.schedule_enabled or self.settings.upload.visibility == "scheduled" else None
                meta = meta.model_copy(update={"publish_at": publish_at})
                row = production.video_metadata or MetadataRow(production_id=pid, title=meta.title, description=meta.description)
                row.title, row.description, row.tags, row.hashtags = meta.title, meta.description, meta.tags, meta.hashtags
                row.category_id, row.publish_at, row.pinned_comment, row.thumbnail_time_s = meta.category_id, publish_at, meta.pinned_comment, meta.thumbnail_time_s
                session.add(row)

            with self._stage(session, pid, "quality_gate"):
                self._advance(production, State.QUALITY_CHECK)
                report = run_quality_gate(final, list(production.segments), narration, ass, meta,
                                          [segment.continuity_score for segment in production.segments], self.llm, self.settings)
                final_row = production.final_video or FinalVideo(production_id=pid, path=str(final))
                final_row.path, final_row.probe = str(final), probe(final).model_dump()
                final_row.quality_report, final_row.passed = report.model_dump(), report.passed
                session.add(final_row)
                if not report.passed:
                    self._advance(production, State.NEEDS_REVIEW)
                    log.warning("quality_gate.failed", production_id=pid, checks=[c.name for c in report.checks if not c.passed])
                    return final
                self._advance(production, State.READY)
                production.finished_at = self.now()

            if self.settings.upload.enabled:
                self._upload(session, production, final, meta)
            return final

    def _upload(self, session: Session, production: Production, final: Path, meta) -> None:
        from app.core.states import NEVER_UPLOAD

        pid = production.id
        if production.state in NEVER_UPLOAD:
            raise ValueError(f"refusing to upload production in state {production.state.value}")
        with self._stage(session, pid, "upload"):
            self._advance(production, State.UPLOADING)
            upload_row = production.upload or Upload(production_id=pid)
            upload_row.attempts = (upload_row.attempts or 0) + 1
            upload_row.privacy = self.settings.upload.visibility
            session.add(upload_row)
            try:
                client = self.youtube
                privacy = "private" if self.settings.upload.visibility in {"draft", "scheduled"} else self.settings.upload.visibility
                result = client.upload(final, meta, privacy, meta.publish_at)
            except HumanActionRequired as err:
                upload_row.status, upload_row.error = "pending", err.problem
                self._human_action(session, production, err)
                raise
            upload_row.youtube_video_id, upload_row.url, upload_row.status = result.video_id, result.url, result.status
            upload_row.publish_at, upload_row.uploaded_at = meta.publish_at, self.now()
            upload_row.published_at = meta.publish_at or self.now()
            upload_row.error = None
            if meta.pinned_comment and self.settings.upload.post_pinned_comment and hasattr(client, "post_comment"):
                try:
                    client.post_comment(result.video_id, meta.pinned_comment)
                except Exception as err:  # a failed comment never blocks publication
                    log.warning("pinned_comment.failed", production_id=pid, error=str(err))
            self._advance(production, State.PUBLISHED)

    def _publish_at(self) -> datetime:
        cfg = self.settings.upload
        tz = ZoneInfo(cfg.timezone)
        local_now = self.now().astimezone(tz)
        candidate = local_now.replace(hour=cfg.publish_hour_local, minute=0, second=0, microsecond=0)
        if candidate <= local_now + timedelta(minutes=15):
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC)

    def resume(self, pid: str) -> str:
        """Continue from the persisted state. Returns the resulting state value."""
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            state = production.state if production.state not in HOLD_STATES else (production.previous_state or State.DISCOVERING)
        if PIPELINE_ORDER.index(state) < PIPELINE_ORDER.index(State.GENERATING):
            self.prepare(pid)
            state = State.GENERATING
        if state == State.GENERATING:
            ready, count = self.inbox_ready(pid)
            if not ready:
                inbox = inbox_for(pid, self.storage, self.settings)
                raise HumanActionRequired(
                    problem=f"Production {pid} is waiting for the five manually generated clips ({count}/5 present).",
                    root_cause="generation.mode=manual: visuals are created by the operator in Google Flow with subscription credits.",
                    automated="Topic, research, script, storyboard, continuity bible and the five prompt files.",
                    remains="Generate five portrait clips and drop them in the inbox.",
                    action=f"Follow {self.storage.path_for(pid, 'prompts', 'MANUAL_VIDEO_HANDOFF.txt')} and place segment_01..05.mp4 in {inbox}",
                    next_step=f"python -m app.cli watch {pid}  (or collect-clips + finish)",
                )
            self.collect(pid)
            state = State.EDITING
        if state in {State.VALIDATING, State.EDITING, State.QUALITY_CHECK, State.READY}:
            self.finish(pid)
        return self.status(pid)["state"]

    def watch(self, pid: str, *, poll_s: float = 15, timeout_s: float | None = None, sleep=time.sleep) -> str:
        """Block until the inbox holds five clips, then collect and finish automatically."""
        waited = 0.0
        while True:
            ready, count = self.inbox_ready(pid)
            if ready:
                break
            if timeout_s is not None and waited >= timeout_s:
                raise TimeoutError(f"inbox for {pid} still has {count}/5 clips after {waited:.0f}s")
            sleep(poll_s)
            waited += poll_s
        self.collect(pid)
        self.finish(pid)
        return self.status(pid)["state"]

    def status(self, pid: str) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            topic = next((t.topic for t in production.topics if t.selected), None)
            latest = production.snapshots[-1] if production.snapshots else None
            ready, count = self.inbox_ready(pid) if production.state in _MANUAL_STATES else (None, None)
            return {
                "id": production.id,
                "state": production.state.value,
                "topic": topic,
                "cost_usd": round(production.cost_usd or 0.0, 4),
                "segments": len(production.segments),
                "inbox_clips": count,
                "final_video": production.final_video.path if production.final_video else None,
                "quality_passed": production.final_video.passed if production.final_video else None,
                "title": production.video_metadata.title if production.video_metadata else None,
                "youtube_video_id": production.upload.youtube_video_id if production.upload else None,
                "url": production.upload.url if production.upload else None,
                "views": latest.views if latest else None,
                "snapshots": len(production.snapshots),
                "human_action": production.human_action,
                "updated_at": production.updated_at.isoformat() if production.updated_at else None,
            }

    def list_productions(self, limit: int = 20) -> list[dict[str, Any]]:
        with session_scope(self.engine) as session:
            rows = session.query(Production).order_by(Production.created_at.desc()).limit(limit).all()
            return [{"id": p.id, "state": p.state.value, "cost_usd": round(p.cost_usd or 0, 4),
                     "topic": next((t.topic for t in p.topics if t.selected), None),
                     "youtube_video_id": p.upload.youtube_video_id if p.upload else None} for p in rows]

    # ------------------------------------------------------------------ analytics + learning
    def _analytics_clients(self) -> tuple[Any, Any | None]:
        if self.settings.mode == "mock":
            from app.youtube.mock import MockAnalyticsClient

            return self.youtube, MockAnalyticsClient()
        from app.youtube.analytics_api import YouTubeAnalyticsAPI
        from app.youtube.auth import get_credentials
        from app.youtube.data_api import YouTubeDataAPI

        creds = get_credentials(self.settings.resolve(self.settings.youtube_client_secret_path),
                                self.settings.resolve(self.settings.youtube_token_path))
        return YouTubeDataAPI(credentials=creds), YouTubeAnalyticsAPI(credentials=creds)

    def collect_analytics(self, now: datetime | None = None) -> list[str]:
        """Capture every due checkpoint for every published video (spec sections 33 and 34)."""
        from app.analytics.collector import collect_all_due

        now = now or self.now()
        stats_client, analytics_client = self._analytics_clients()
        with session_scope(self.engine) as session:
            with self._stage(session, None, "analytics", action="collect"):
                return collect_all_due(session, stats_client, analytics_client, now=now, cfg=self.settings)

    def learn(self, now: datetime | None = None):
        """Refresh insights, strategy weights, knowledge base and per-video reports (spec sections 41 to 48)."""
        from app.intelligence.learn import learn

        with session_scope(self.engine) as session:
            with self._stage(session, None, "intelligence", action="learn"):
                return learn(session, self.storage, self.llm, self.settings, now=now or self.now())

    def report(self, pid: str) -> str:
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            if production.reports:
                return production.reports[-1].markdown
            if not production.snapshots:
                raise ValueError(f"{pid} has no analytics snapshots yet; run `analytics` after publishing")
        self.learn()
        with session_scope(self.engine) as session:
            production = self._get(session, pid)
            if not production.reports:
                raise ValueError(f"no report could be built for {pid}")
            return production.reports[-1].markdown

    def daily(self) -> dict[str, Any]:
        """One scheduled run: collect analytics, learn, then advance today's production as far as possible."""
        summary: dict[str, Any] = {"date": self.now().date().isoformat(), "collected": [], "learned_videos": 0,
                                   "production_id": None, "state": None, "waiting_for_clips": False, "human_action": None}
        try:
            summary["collected"] = self.collect_analytics()
        except HumanActionRequired as err:
            summary["human_action"] = err.as_dict()
        except Exception as err:  # analytics never blocks production
            log.warning("daily.analytics_failed", error=str(err))
        try:
            summary["learned_videos"] = self.learn().videos
        except Exception as err:
            log.warning("daily.learn_failed", error=str(err))

        prefix = f"OMS-{self.now():%Y%m%d}-"
        with session_scope(self.engine) as session:
            todays = session.query(Production).filter(Production.id.like(prefix + "%")).order_by(Production.id.desc()).first()
            pid = todays.id if todays else None
        if pid is None:
            try:
                pid = self.new_production()
            except HumanActionRequired as err:
                summary["human_action"] = err.as_dict()
                return summary
        summary["production_id"] = pid
        try:
            state = self.resume(pid)
        except HumanActionRequired as err:
            summary["human_action"] = err.as_dict()
            state = self.status(pid)["state"]
            summary["waiting_for_clips"] = state == State.GENERATING.value
        summary["state"] = state
        return summary

    def metrics(self) -> dict[str, Any]:
        """Operational metrics (spec section 31)."""
        from sqlalchemy import func

        from app.core.cost import spent_on_day
        from app.core.models import Event, FinalVideo, Upload

        with session_scope(self.engine) as session:
            total = session.query(Production).count()
            generated = session.query(FinalVideo).filter(FinalVideo.passed.is_(True)).count()
            attempted = session.query(Production).filter(Production.state.in_([
                State.EDITING, State.QUALITY_CHECK, State.READY, State.UPLOADING, State.PUBLISHED, State.ANALYZING,
                State.LEARNED, State.NEEDS_REVIEW, State.FAILED])).count()
            published = session.query(Upload).filter(Upload.youtube_video_id.isnot(None)).count()
            failed = session.query(Production).filter(Production.state.in_([State.FAILED, State.NEEDS_REVIEW, State.BLOCKED])).count()
            durations = [((p.finished_at - p.started_at).total_seconds()) for p in session.query(Production).all()
                         if p.finished_at and p.started_at]
            cost_total = session.query(func.sum(Production.cost_usd)).scalar() or 0.0
            api_errors = session.query(Event).filter(Event.status == "failed", Event.api.isnot(None)).count()
            upload_failures = session.query(Upload).filter(Upload.error.isnot(None)).count()
            waiting = session.query(Production).filter(Production.state == State.GENERATING).count()
            today = self.now().date()
            return {
                "productions": total,
                "videos_generated": generated,
                "videos_published": published,
                "generation_success_rate": round(generated / attempted, 3) if attempted else 0.0,
                "failure_rate": round(failed / total, 3) if total else 0.0,
                "average_generation_time_s": round(sum(durations) / len(durations), 1) if durations else None,
                "average_cost_per_video_usd": round(cost_total / generated, 4) if generated else 0.0,
                "api_errors": api_errors,
                "upload_failures": upload_failures,
                "waiting_for_clips": waiting,
                "spent_today_usd": round(spent_on_day(session, today), 4),
                "daily_budget_usd": self.settings.limits.daily_budget_usd,
            }

    def costs(self, days: int = 30) -> dict[str, Any]:
        from sqlalchemy import func

        from app.core.cost import spent_on_day
        from app.core.models import CostLedger

        with session_scope(self.engine) as session:
            since = self.now() - timedelta(days=days)
            by_api = dict(session.query(CostLedger.api, func.sum(CostLedger.usd)).filter(CostLedger.at >= since)
                          .group_by(CostLedger.api).all())
            return {"today_usd": round(spent_on_day(session, self.now().date()), 4),
                    "window_days": days, "window_usd": round(sum(by_api.values()), 4),
                    "by_api": {api: round(float(usd or 0), 4) for api, usd in by_api.items()},
                    "daily_budget_usd": self.settings.limits.daily_budget_usd}
