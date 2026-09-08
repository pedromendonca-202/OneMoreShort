# OneMoreShort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution chosen — the operator runs autonomously and cannot pick between options; see DECISIONS.md D-014). Steps use checkbox (`- [ ]`) syntax for tracking. Code bodies live in the repo, not duplicated here, because the plan author is also the executor in the same session; each task lists exact files, interfaces and the tests that must pass.

**Goal:** Build the autonomous Shorts factory described in `ARCHITECTURE.md`: trend research → topic selection → script → storyboard → continuity → 5 chained Veo 3.1 Lite segments → edit/narrate/caption → quality gate → YouTube upload → analytics → content intelligence → strategy feedback, runnable end-to-end in mock mode today and in live mode once credentials exist.

**Architecture:** Python package `app/` with one module per stage, all pure functions/classes taking their dependencies (LLM, Veo, TTS, YouTube, DB session) as arguments. A persistent SQLite state machine (`productions.state`) drives idempotent stages through `pipeline.Orchestrator`. External adapters each have a real and a mock implementation selected by `OMS_MODE`.

**Tech Stack:** Python 3.12, google-genai 2.22, google-api-python-client, google-auth-oauthlib, SQLAlchemy 2.0 (SQLite WAL), pydantic 2 + pydantic-settings, typer, structlog, tenacity, httpx, feedparser, edge-tts, ffmpeg 9.0.1 (winget) with imageio-ffmpeg fallback, pytest.

**Spec:** `ARCHITECTURE.md` (+ `DECISIONS.md`)

## Global Constraints

- American English content; max duration `video.max_duration_s: 40`; 5 segments × 8 s; output 1080×1920 9:16 H.264/AAC.
- Veo model `veo-3.1-lite-generate-preview`; `aspect_ratio="9:16"`, `resolution` from config (default `"1080p"`), `duration_seconds=8`, `generate_audio=True`, `person_generation="allow_adult"`.
- Never put credentials in code/logs; `.env` + `secrets/` only.
- Every external call: timeout + retry with exponential backoff + structured logging + cost ledger entry.
- Never upload productions in `BLOCKED`, `FAILED`, `NEEDS_REVIEW`, `NEEDS_HUMAN_ACTION`, `PAUSED_BUDGET`.
- Tests never call paid APIs; `OMS_MODE=mock` must run the whole pipeline.
- ffmpeg receives relative paths for filter arguments (OneDrive accented path).
- Production IDs: `OMS-YYYYMMDD-NNNN`.

---

### Task 1: Core foundation (config, ids, states, db, logging, cost, retry, storage)

**Files:** `app/__init__.py`, `app/core/{__init__,config,ids,states,db,models,logging,cost,retry,storage,errors}.py`, `config/default.yaml`, `.env.example`, `tests/conftest.py`, `tests/core/test_{config,ids,states,db,cost,retry}.py`

**Interfaces produced:**
- `Settings` (pydantic-settings) loaded by `load_settings(path: Path|None=None) -> Settings`; env prefix `OMS_`; `.env` support; nested YAML sections `llm, veo, tts, video, captions, trends, upload, limits, analytics, intelligence, paths`.
- `new_production_id(session, today: date) -> str` (sequential per day).
- `State` enum + `TRANSITIONS: dict[State, set[State]]`, `assert_transition(from, to)`.
- `get_engine(url) / get_session(engine)`, `Base.metadata.create_all`; ORM models per ARCHITECTURE §4.
- `get_logger(**bind) -> structlog logger` writing JSON lines to `logs/oms.jsonl` and console.
- `CostLedger.record(session, production_id, api, units, unit_cost, note)`, `Budget.check(session, day, limit) -> BudgetStatus`, `estimate_veo_cost(seconds, resolution) -> float`.
- `retrying(api_name, max_attempts, exceptions)` decorator (tenacity) + `CircuitBreaker(api_name, failure_threshold, reset_after_s)`.
- `Storage(root).path_for(production_id, kind, filename) -> Path` and ensures dirs.

**Tests:** settings load defaults and env override; id sequence resets per day; illegal transition raises; models round-trip in SQLite memory; budget exceeded flag; retry gives up after N attempts and breaker opens/resets.

- [ ] Write failing tests → run → implement → pass → commit `feat(core): foundation`.

### Task 2: LLM provider layer

**Files:** `app/llm/{__init__,base,mock,gemini,anthropic_provider,router}.py`, `tests/llm/test_{mock,router,gemini_parsing}.py`

**Interfaces produced:**
- `class LLMRequest(BaseModel): system: str|None; prompt: str; schema: type[BaseModel]|None; images: list[Path|bytes]; use_search: bool; temperature: float; max_output_tokens: int; role: Literal["fast","smart"]`
- `class LLMResponse(BaseModel): text: str; parsed: Any|None; usage_in: int; usage_out: int; cost_usd: float; model: str; grounding: list[dict]`
- `class LLMProvider(Protocol): def generate(self, req: LLMRequest) -> LLMResponse`
- `MockLLM(responses: dict[str, Any] | callable)` returns schema-valid fixtures by schema class name.
- `GeminiProvider(api_key, fast_model, smart_model)` using `client.models.generate_content` with `response_json_schema` for structured output, `Tool(google_search=GoogleSearch())` when `use_search` (structured output disabled in that call; a second cheap call structures the grounded text).
- `AnthropicProvider(model="claude-opus-5")` using structured outputs `output_config.format`, adaptive thinking, streaming with `get_final_message()`.
- `build_llm(settings) -> LLMProvider`; `structured(llm, req) -> BaseModel` helper with one repair retry on validation error.

**Tests:** mock returns typed object; router picks mock in mock mode; JSON repair path (` ```json` fences) parses.

- [ ] TDD cycle → commit `feat(llm): provider abstraction with Gemini/Anthropic/mock`.

### Task 3: Trend sources + aggregator

**Files:** `app/trends/{__init__,base,youtube_source,reddit_source,news_rss_source,hackernews_source,wikipedia_source,gtrends_rss_source,aggregator}.py`, `tests/trends/test_{sources,aggregator}.py`, `tests/fixtures/trends/*.json|xml`

**Interfaces produced:**
- `class TrendSignal(BaseModel): source: str; title: str; url: str|None; summary: str|None; category: str|None; metrics: dict[str,float]; published_at: datetime|None; fetched_at: datetime`
- `class TrendSource(Protocol): name: str; def fetch(self, limit: int) -> list[TrendSignal]` (each wraps httpx with timeout/retry; failures return `[]` and log).
- `aggregate(signals) -> list[TrendCluster]` where `TrendCluster(topic: str, signals: list[TrendSignal], sources: set[str], momentum: float)` (LLM-assisted clustering into candidate topics via `ClusterProposal` schema).

**Tests:** each parser handles fixture payloads and malformed input; aggregator merges duplicates across sources.

- [ ] TDD cycle → commit `feat(trends): multi-source trend discovery`.

### Task 4: Virality scoring, topic selection, deep research

**Files:** `app/research/{__init__,schemas,scorer,selector,deep_research}.py`, `tests/research/test_{scorer,selector,deep_research}.py`

**Interfaces produced:**
- `class TopicScore(BaseModel)`: fields from spec §7 (`topic, category, trend_score, viral_potential, us_relevance, competition, shorts_fit, originality, risk, final_score, reasons: list[str]`).
- `score_topics(llm, clusters, weights: ScoringWeights, knowledge: KnowledgeContext) -> list[TopicScore]` (LLM rates dimensions 0–100 with reasons; `final_score` computed deterministically by `compute_final(score, weights)`).
- `select_topic(scores, strategy: StrategyWeights, exploration_ratio: float, rng) -> tuple[TopicScore, str reason]` (hard-avoid list: risk ≥ threshold, competition saturation; exploit/explore split).
- `class Research(BaseModel): facts: list[Fact(text, source, confidence)]; context: str; angles: list[str]; hooks: list[str]; risks: list[str]; curiosity_points: list[str]; best_40s_approach: str`
- `deep_research(llm, topic) -> Research` (uses `use_search=True` when live).

**Tests:** final score math; hard avoid; exploration picks non-top with seeded rng; research fixture parses.

- [ ] TDD cycle → commit `feat(research): virality score, selector, deep research`.

### Task 5: Script + storyboard + continuity bible

**Files:** `app/scripting/{__init__,schemas,generator,hook_classifier}.py`, `app/storyboard/{__init__,schemas,generator}.py`, `app/continuity/{__init__,schemas,bible,state}.py`, `tests/{scripting,storyboard,continuity}/test_*.py`

**Interfaces produced:**
- `class Beat(BaseModel): index:int; start_s: float; end_s: float; purpose: Literal[HOOK,SETUP,ESCALATION,REVELATION,PAYOFF,ENDING]; narration: str; on_screen_note: str|None`
- `class Script(BaseModel): title_working: str; beats: list[Beat]; hook_type: HookType; ending_type: Literal[loop,cta,cliff,statement]; cta_used: bool; loop_used: bool; total_words: int; est_duration_s: float` with validator: monotonic beats, `end_s ≤ max_duration`.
- `generate_script(llm, topic, research, knowledge, cfg) -> Script`; `classify_hook(llm, first_beat_text) -> HookType`; `estimate_duration(words, wpm) -> float`.
- `class Segment(BaseModel)`: spec §13 fields (`segment, duration, purpose, visual_description, camera, lens, lighting, characters, environment, objects, action, narration, dialogue, sound_design, transition_to_next, continuity_state`) ; `Storyboard(segments: list[Segment] (len 5), visual_style: str, palette: str)`.
- `generate_storyboard(llm, script, cfg) -> Storyboard` (maps beats → 5 segments by time window).
- `class ContinuityBible(BaseModel)`: spec §15 fields; `build_bible(llm, script, storyboard) -> ContinuityBible`; `SegmentEndState(BaseModel): description: str; character_positions: str; camera: str; lighting: str; objects: str; motion: str`.

**Tests:** script validator rejects overlap/overlength; beats→segments mapping; bible has all required sections.

- [ ] TDD cycle → commit `feat(story): script, storyboard, continuity bible`.

### Task 6: ffmpeg editing toolkit (probe, synth fixtures, frames, normalize, concat)

**Files:** `app/editing/{__init__,ffmpeg,probe,frames,normalize,concat,synth}.py`, `tests/editing/test_*.py`

**Interfaces produced:**
- `resolve_ffmpeg() -> tuple[Path ffmpeg, Path ffprobe]` (env `OMS_FFMPEG` → PATH → winget package dir → imageio-ffmpeg).
- `run_ffmpeg(args: list[str], cwd: Path, timeout_s) -> CompletedProcess` (raises `FFmpegError` with stderr tail).
- `probe(path) -> MediaInfo(duration_s, width, height, fps, vcodec, acodec, has_audio, sample_rate, size_bytes)`.
- `extract_last_frame(video, out_png)`, `extract_first_frame(video, out_png)`, `extract_frame_at(video, t, out_png)`.
- `normalize_segment(src, dst, w=1080, h=1920, fps=24) -> Path`; `concat_segments(paths, dst) -> Path`; `synth_segment(dst, seconds, color, label, with_audio=True)` for mock/tests.

**Tests (real ffmpeg):** synth → probe values; last frame exists; normalize gives 1080×1920@24; concat duration ≈ sum.

- [ ] TDD cycle → commit `feat(editing): ffmpeg toolkit`.

### Task 7: Veo prompt builder, client (real + mock), segment generator, validator

**Files:** `app/veo/{__init__,schemas,prompt_builder,client,mock_client,validator,generator}.py`, `app/continuity/{observer,checker}.py`, `tests/veo/test_*.py`

**Interfaces produced:**
- `class VeoPrompt(BaseModel): segment: int; prompt: str; negative_prompt: str; first_frame: Path|None; previous_end_state: str|None; config: dict`
- `build_prompt(segment, bible, storyboard, prev_end_state: SegmentEndState|None, brand: BrandStyle) -> VeoPrompt` — sections exactly: SCENE CONTEXT, CHARACTER CONTINUITY, ENVIRONMENT, OBJECT CONTINUITY, ACTION, CAMERA, LENS, LIGHTING, COLOR, MOTION, AUDIO, DIALOGUE / NARRATION (always "none — silent characters, no voiceover"), TIMING, CONTINUITY REQUIREMENTS, NEGATIVE CONSTRAINTS; ≤ 1,024 tokens guard (trim least important sections).
- `class VeoClient(Protocol): def generate(self, prompt: VeoPrompt, out_path: Path) -> VeoResult(path, operation_id, seconds, cost_usd, raw)`.
- `GoogleVeoClient(api_key, model, resolution, poll_interval_s, timeout_s)`; `MockVeoClient(synth=True)` writes synthesized 8 s clips.
- `validate_segment(path, expect_seconds=8, tolerance=1.0, min_w=..., orientation="portrait") -> ValidationReport(ok, issues)`.
- `observe_end_state(llm, frame_png) -> SegmentEndState`; `check_continuity(llm, last_frame_n, first_frame_n1) -> ContinuityScore(score: float, issues)`.
- `generate_segments(production_id, storyboard, bible, veo, llm, storage, session, cfg) -> list[SegmentRecord]` — sequential chain, per-segment retries, budget check before each call, persists after each segment (resume-safe).

**Tests:** prompt contains all sections and forbids speech; mock chain produces 5 files + 5 last frames; validator flags short/landscape/silent clip; generator resumes after simulated crash at segment 3 without regenerating 1–2; budget stop.

- [ ] TDD cycle → commit `feat(veo): chained segment generation with continuity`.

### Task 8: Narration (TTS), mixing, captions, final render

**Files:** `app/audio/{__init__,schemas,tts/base,tts/mock,tts/gemini_tts,tts/edge,narration,mixer,music}.py`, `app/captions/{__init__,aligner,style,ass_renderer}.py`, `app/editing/render.py`, `tests/{audio,captions,editing}/test_*.py`

**Interfaces produced:**
- `class TTSResult(BaseModel): path: Path; duration_s: float; words: list[WordTiming(word, start_s, end_s)]|None; cost_usd: float`
- `class TTSProvider(Protocol): voice: str; def synthesize(self, text, out_wav) -> TTSResult`.
- `narrate(script, tts, llm, storage, production_id, max_total_s) -> NarrationPlan(beats: list[BeatAudio(beat, path, start_s, duration_s, words)], total_s)` with tighten (LLM) then `atempo` fallback.
- `mix_audio(video_in, narration: NarrationPlan, music: Path|None, out_wav, cfg) -> Path` (ducking via `sidechaincompress`, `loudnorm` I=-14 TP=-1).
- `align_words(narration) -> list[WordTiming]` (native → proportional) ; `build_phrases(words, max_words=3)`; `render_ass(phrases, style: CaptionStyle, out_ass)`.
- `render_final(concat_video, mixed_audio, ass_path, logo: Path|None, out_mp4, max_duration_s, cwd) -> Path`.

**Tests:** mock TTS durations sum; over-length triggers tighten; ASS timing monotonic; final render probe = 1080×1920, has audio, ≤ 40 s, file size > 0.

- [ ] TDD cycle → commit `feat(post): narration, mix, captions, final render`.

### Task 9: Quality gate + metadata

**Files:** `app/quality/{__init__,gate,policy}.py`, `app/metadata/{__init__,schemas,generator}.py`, `tests/{quality,metadata}/test_*.py`

**Interfaces produced:**
- `class QualityReport(BaseModel): checks: list[Check(name, passed, detail)]; passed: bool; failed_stage_hint: str|None`
- `run_quality_gate(final: Path, segments, narration, captions, metadata, continuity_scores, policy_llm, cfg) -> QualityReport`.
- `class VideoMetadata(BaseModel): title (≤100); description; hashtags (3–6, includes #Shorts); tags (≤ 500 chars total); category_id (default 24/27/28 by category); publish_at: datetime|None; pinned_comment: str|None; thumbnail_time_s: float`
- `generate_metadata(llm, script, topic, cfg) -> VideoMetadata`; `policy_check(llm, script, metadata) -> PolicyVerdict(ok, flags, reasons)`.

**Tests:** gate fails on overlength/missing audio; metadata validators; policy mock verdict propagates to `NEEDS_REVIEW`.

- [ ] TDD cycle → commit `feat(quality): quality gate and metadata`.

### Task 10: YouTube integration (auth, upload, data, analytics) + mock

**Files:** `app/youtube/{__init__,auth,uploader,data_api,analytics_api,mock,schemas}.py`, `tests/youtube/test_*.py`

**Interfaces produced:**
- `get_credentials(client_secret_path, token_path, scopes) -> Credentials` (installed-app flow; raises `HumanActionRequired` with the exact steps if the client secret is missing).
- `class YouTubeClient(Protocol): upload(video, metadata, privacy, publish_at) -> UploadResult(video_id, status); video_stats(ids) -> list[VideoStats]; analytics(video_id, start, end, metrics, dimensions, filters) -> list[dict]; retention_curve(video_id) -> list[RetentionPoint(elapsed_ratio, watch_ratio, relative)]; set_thumbnail; post_comment`.
- `GoogleYouTubeClient(creds)` (resumable upload with retries; `snippet.categoryId`, `status.privacyStatus`, `status.publishAt`, `status.selfDeclaredMadeForKids=False`).
- `MockYouTubeClient` producing deterministic ids/metrics that evolve with `age_minutes`.

**Tests:** mock upload returns id; analytics parsing from fixture rows; missing client secret → HumanActionRequired message includes PROBLEM/ROOT CAUSE/EXACT HUMAN ACTION/NEXT AUTOMATIC STEP.

- [ ] TDD cycle → commit `feat(youtube): upload, data, analytics`.

### Task 11: Analytics collection + analysis + report

**Files:** `app/analytics/{__init__,schemas,collector,growth,engagement,retention,comparison,report}.py`, `tests/analytics/test_*.py`

**Interfaces produced:**
- `SNAPSHOT_SCHEDULE_MIN = [10,30,60,180,360,720,1440,2880,10080,20160,43200]`; `due_snapshots(published_at, now, taken) -> list[int]`; `collect(session, yt, now) -> int` (takes due snapshots for every published video, pulls Analytics API metrics + retention when age ≥ 48 h).
- `classify_growth(snapshots, baseline: ChannelBaseline) -> GrowthClass`.
- `engagement_rates(stats) -> EngagementRates(like_rate, comment_rate, share_rate, sub_conversion, engagement_rate, view_to_like, view_to_sub)`.
- `analyze_retention(curve, script, storyboard) -> RetentionAnalysis(points, drops: list[Drop(t_s, delta, beat, segment, sentence, likely_cause)], completion_est, avg_pct)`.
- `compare(video, channel_videos) -> Comparison(vs_mean, vs_median, vs_last5, vs_last10, vs_category, rank)`.
- `build_report(llm, production, stats, rates, retention, comparison, growth) -> VideoReport(markdown, what_worked, what_failed, next_recommendation, virality_score)`.

**Tests:** due snapshot math; growth classes at boundaries; drop detection on synthetic curve maps to beat; rates math; report fixture.

- [ ] TDD cycle → commit `feat(analytics): collection, retention analysis, reports`.

### Task 12: Content intelligence + strategy + knowledge base + A/B

**Files:** `app/intelligence/{__init__,schemas,features,patterns,insights,strategy,knowledge,ab_testing}.py`, `tests/intelligence/test_*.py`

**Interfaces produced:**
- `extract_features(production) -> VideoFeatures` (spec §36 list).
- `detect_patterns(videos: list[VideoOutcome]) -> list[Insight(feature, value, metric, effect_vs_channel, n, confidence)]`; `answer_questions(insights) -> IntelligenceSummary` (spec §41 questions).
- `update_strategy(session, insights, cfg) -> StrategyWeights(category_weights, hook_weights, duration_pref, style_weights, exploration_ratio)`; consumed by `research.selector` and `scripting.generator` via `KnowledgeContext`.
- `Knowledge.add(kind, payload)`, `Knowledge.context_for(topic_category) -> KnowledgeContext(best_hooks, best_structures, failed_patterns, successful_prompts)`.
- `ABTest.assign(production, dimension) -> variant`, `ABTest.evaluate(session, dimension) -> ABResult`.

**Tests:** insights from synthetic outcomes favour the better hook; weights normalise and keep exploration mass; knowledge context roundtrip.

- [ ] TDD cycle → commit `feat(intelligence): learning loop`.

### Task 13: Pipeline orchestrator, stages, CLI, daily runner, resume

**Files:** `app/pipeline/{__init__,orchestrator,context,stages/__init__,stages/discover,stages/select,stages/research,stages/script,stages/storyboard,stages/generate,stages/validate,stages/edit,stages/quality,stages/metadata,stages/upload,stages/analyze,stages/learn}.py`, `app/pipeline/daily.py`, `app/cli.py`, `scripts/register_daily_task.ps1`, `tests/pipeline/test_{orchestrator,resume,e2e_mock}.py`

**Interfaces produced:**
- `class Stage(Protocol): name; from_state: State; to_state: State; def already_done(ctx) -> bool; def run(ctx) -> None`.
- `Orchestrator(deps).run(production_id, until: State|None)`; `Orchestrator.resume_all()`; `Orchestrator.new_production() -> str`.
- `PipelineContext` (session, settings, storage, llm, veo, tts, yt, production, logger, budget).
- CLI: `oms init-db`, `oms discover`, `oms produce [--id] [--until STATE]`, `oms publish ID`, `oms collect`, `oms learn`, `oms daily`, `oms resume`, `oms status [ID]`, `oms stats`, `oms youtube auth`, `oms doctor`.

**Tests:** full mock e2e → PUBLISHED with a real mp4 (ffmpeg) passing the gate; kill-and-resume test; budget pause test; failure recovery on Veo timeout (mock raises once).

- [ ] TDD cycle → commit `feat(pipeline): orchestrator, stages, CLI`.

### Task 14: Failure-injection suite + docs + first real run readiness

**Files:** `tests/failures/test_*.py` (Veo timeout, YouTube timeout, corrupted video, missing segment, invalid audio, DB unavailable, network failure, OAuth expiry, rate limit), `README.md`, `SETUP.md`, `API.md`, `PIPELINE.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `scripts/doctor.ps1`

- [ ] Write failure tests → make them pass → docs → `oms doctor` reports exact human actions → commit `docs: operations & setup`.

### Task 15: First production attempt (live where possible)

- [ ] Run `oms doctor`; if `GOOGLE_API_KEY` is absent, run the complete pipeline in mock mode to produce `storage/renders/<id>/OneMoreShort_Final.mp4`, then record `NEEDS_HUMAN_ACTION` with the exact steps for the API key and YouTube OAuth. If present, run live discovery → production with `upload.enabled` per config.

---

## Self-review

- Spec coverage: §6–§9 → T3/T4; §10–§17 → T5/T7; §18–§19 → T7; §20–§23 → T8/T9; §24–§27 → T9/T10; §28 → T10 (`HumanActionRequired`) + docs; §29–§32 → T1/T13; §33–§44 → T11; §45–§48 → T12; §49–§51 → T1/T14; §52 dashboard deferred by spec ("não priorizar"); §53 → every task + T14; §54–§55 → T13/T15; §56–§61 → cross-cutting.
- Type names are consistent across tasks (`Script`, `Storyboard`, `ContinuityBible`, `SegmentEndState`, `VeoPrompt`, `NarrationPlan`, `QualityReport`, `VideoMetadata`, `StrategyWeights`, `KnowledgeContext`).
