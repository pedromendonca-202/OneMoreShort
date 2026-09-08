# OneMoreShort — Architecture

> Autonomous AI Shorts factory: research → select → script → storyboard → continuity → Veo 3.1 Lite (5 chained segments) → edit → narrate → caption → quality gate → publish → analytics → content intelligence → better next video.

Status: **v1 design, 2026-09-07**. Decisions are logged in `DECISIONS.md`.

---

## 1. Current architecture (audit, 2026-09-07)

| Item | Finding |
|---|---|
| Repository | Empty. Two brand logos (`logo/*.png`, YouTube-red and TikTok-color variants), empty `video1/`. No code, no git, no config, no credentials. |
| Runtime | Windows 11 Pro, Python 3.12.10, Node 24.18, Docker 29.6, Git 2.55. |
| Media tooling | ffmpeg was **absent**; installed `Gyan.FFmpeg 9.0.1` via winget (full build: libx264, aac, libass `subtitles`, `loudnorm`, `sidechaincompress`). |
| Credentials | None for Google / Gemini / Veo / YouTube in the environment. User has **Google AI Plus** (consumer credits: 50/day + 200/month). Those credits apply to the Gemini app and Flow only, **not** to the Gemini API; Veo API usage is billed separately through an AI Studio key with Cloud Billing, and Veo has no free tier. |
| Constraints | Project folder lives inside OneDrive with an accented path (`Área de Trabalho`). SQLite in a synced folder can hit lock conflicts; ffmpeg subtitle filters choke on colons/accents in absolute paths. Both are handled (see §11). |
| Reusable code | None. Everything below is new. |

---

## 2. Target architecture

```
                 ┌──────────────────────────── CLI (typer) ────────────────────────────┐
                 │  oms discover | produce | publish | collect | learn | daily | resume │
                 └───────────────────────────────┬──────────────────────────────────────┘
                                                 │
                     ┌───────────────────────────▼────────────────────────────┐
                     │              pipeline.Orchestrator                       │
                     │   persistent state machine · idempotent stages · retry   │
                     └──┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┘
   trends/research      │     │     │     │     │     │     │     │     │
   ┌────────────┐  scripting  │ continuity  │  audio  │  quality  │  analytics
   │ sources:   │      │  storyboard │    veo    │ captions│ metadata │ intelligence
   │ youtube    │      ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼
   │ reddit     │  ┌────────────────────────────────────────────────────────────┐
   │ gnews rss  │  │  core: config · db (SQLAlchemy) · ids · logging · cost     │
   │ hackernews │  │        retry/backoff · circuit breaker · storage paths      │
   │ wikipedia  │  └────────────────────────────────────────────────────────────┘
   │ gtrends rss│         │                │                 │
   └────────────┘   ┌─────▼─────┐   ┌──────▼──────┐   ┌──────▼──────┐
                    │ llm       │   │ veo client  │   │ youtube     │
                    │ gemini    │   │ google-genai│   │ data v3     │
                    │ anthropic │   │ mock        │   │ analytics v2│
                    │ mock      │   └─────────────┘   │ oauth       │
                    └───────────┘                     └─────────────┘
```

### 2.1 Stack decisions

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Best fit for Google GenAI SDK, YouTube client libs, ffmpeg orchestration, and LLM tooling. |
| Video model | `veo-3.1-lite-generate-preview` via `google-genai` | Required by spec. Supports 9:16, 720p/1080p, 8 s, first/last-frame conditioning, native audio. Does **not** support reference images, Extension, or 4K. |
| LLM | Provider abstraction. Default **Gemini** (`gemini-3.8-flash` for fast tasks, `gemini-3.1-pro-preview` for script/strategy). **Anthropic** (`claude-opus-5`) pluggable. **Mock** for tests. | Gemini shares the Veo API key → one credential to set up. Anthropic remains a config switch. |
| Trend sources | YouTube Data API v3 (mostPopular, search), Reddit public JSON, Google News RSS, Hacker News API, Wikimedia top-viewed pages, Google Trends RSS (daily trends), optional Google Trends API (gated alpha) | No single point of failure; all public/official. |
| TTS | Provider abstraction: Gemini TTS (`gemini-2.5-flash-preview-tts`), `edge-tts` (free, returns word boundaries), Mock | Single narrator voice across the whole video. Veo native speech is disabled by prompt so voice never changes. |
| Storage | SQLite via SQLAlchemy 2.0; files under `storage/` | Zero-ops single operator. `DATABASE_URL` swap to Postgres later without code changes. |
| Job system | Own persistent state machine in SQLite (no Redis/Celery) | One video/day does not justify a broker. Interface (`Stage`) is broker-agnostic so a queue can be added later. |
| Editing | ffmpeg subprocess (winget build; `imageio-ffmpeg` static binary as fallback) | Deterministic, scriptable, libass captions, loudnorm. |
| Captions | ASS subtitles burned with libass | Precise word/phrase timing, styled, safe-area aware. |
| Scheduling | `oms daily` command + Windows Task Scheduler registration script | Simplest reliable daily trigger on this machine. |
| Tests | pytest with mocks; ffmpeg-synthesized fixtures | No paid API calls in tests. |

---

## 3. Module map

```
app/
├── core/          config.py (pydantic-settings + YAML), db.py, models.py (ORM), ids.py (OMS-YYYYMMDD-NNNN),
│                  logging.py (structlog JSON), cost.py (ledger + budget), retry.py (backoff + circuit breaker),
│                  storage.py (paths), errors.py, states.py (state enums + transitions)
├── llm/           base.py (LLMProvider protocol, structured output), gemini.py, anthropic_provider.py, mock.py, router.py
├── trends/        base.py (TrendSource, TrendSignal), youtube_source.py, reddit_source.py, news_rss_source.py,
│                  hackernews_source.py, wikipedia_source.py, gtrends_rss_source.py, aggregator.py
├── research/      scorer.py (Virality Score), selector.py (explore/exploit + intelligence weights), deep_research.py
├── scripting/     generator.py (timeline beats), hook_classifier.py, schemas.py
├── storyboard/    generator.py, schemas.py (5 segments, transitions, continuity_state)
├── continuity/    bible.py (Continuity Bible), state.py (end-state carryover), observer.py (vision end-state), checker.py
├── veo/           prompt_builder.py, client.py (real), mock_client.py, generator.py (segment jobs), validator.py (ffprobe)
├── audio/         tts/{base,gemini_tts,edge,mock}.py, narration.py (per-beat), mixer.py (ducking, loudnorm), music.py
├── captions/      aligner.py (word timings: native → transcribe → proportional), ass_renderer.py, style.py
├── editing/       ffmpeg.py (binary resolution, probe, run), normalize.py, concat.py, render.py (final mux), frames.py
├── quality/       gate.py (checks), policy.py (LLM policy/originality check)
├── metadata/      generator.py (title, description, hashtags, tags, category, pinned comment, publish time)
├── youtube/       auth.py (OAuth installed app), uploader.py, data_api.py, analytics_api.py, mock.py
├── analytics/     collector.py (snapshot schedule), retention.py (curve + drop detection + segment attribution),
│                  growth.py (velocity classes), engagement.py (derived rates), comparison.py, report.py
├── intelligence/  features.py (video feature vector), patterns.py, insights.py, strategy.py (weights + exploration),
│                  knowledge.py (KB), ab_testing.py
├── pipeline/      orchestrator.py, stages/*.py (one file per stage), daily.py, resume.py
└── cli.py
```

Every module exposes plain functions/classes with typed Pydantic inputs/outputs and takes its dependencies (LLM, Veo client, YouTube client, DB session) as arguments so it can be tested in isolation.

---

## 4. Data model (SQLite)

```
productions            OMS-YYYYMMDD-NNNN · state · retry_count · error · timings · cost_usd · config_snapshot
topics                 candidate topics with score breakdown (trend, viral, us_relevance, competition, shorts_fit,
                       originality, risk, final) · selected flag · reason
trend_signals          raw signals per source (title, url, metrics, fetched_at)
research               facts, angles, hooks, risks, sources (JSON)
scripts                full text · beats[] (start, end, purpose, narration, hook_type) · duration estimate
storyboards            segments[] (5) with camera/lens/lighting/action/transition/continuity_state
continuity_bibles      characters, wardrobe, environment, lighting, palette, camera, voice, temporal state
prompts                per segment: veo prompt text, negative prompt, config, previous_end_state, first_frame path
segments               per segment: status, veo operation id, file path, probe (duration/res/fps/codec/audio),
                       last_frame path, observed_end_state, attempts, cost
audio_assets           narration per beat, mixed track, music/sfx used, loudness
captions               ass path, word timings JSON, style
final_videos           path, probe, quality report JSON, passed
video_metadata         title, description, tags, hashtags, category, publish_at, pinned_comment
uploads                youtube_video_id, privacy, publish_at, status, error, attempts
analytics_snapshots    youtube_video_id, captured_at, age_minutes, views, likes, comments, shares, subs, ...
retention_curves       youtube_video_id, captured_at, points[] (elapsed_ratio → watch_ratio, relative)
video_reports          per video markdown + structured verdict (what worked / failed / next recommendation)
insights               feature · metric · effect vs channel · confidence · sample size
strategy_weights       category/hook/format weights with exploration ratio, updated_at
knowledge_entries      successful/failed prompts, scripts, structures, hooks (searchable text + JSON)
cost_ledger            production_id, api, units, unit_cost, usd, ts
events                 structured event log mirror (job_id, stage, action, status, duration, error, retry)
```

Relationships follow `Topic → Research → Script → Storyboard → ContinuityBible → Prompts → Segments → FinalVideo → Upload → Analytics → Report → Insights → StrategyWeights`, all keyed by `production_id`.

---

## 5. State machine

```
DISCOVERING → SELECTED → RESEARCHING → SCRIPTING → STORYBOARDING → GENERATING → VALIDATING
→ EDITING → QUALITY_CHECK → READY → UPLOADING → PUBLISHED → ANALYZING → LEARNED
```
Error/hold states: `FAILED`, `RETRYING`, `BLOCKED`, `NEEDS_HUMAN_ACTION`, `PAUSED_BUDGET`.

Rules
- A stage runs only if its artifact does not already exist for the production (idempotent). `oms resume` restarts any non-terminal production at its current state.
- Each stage has `max_attempts` (config). Exhaustion → `FAILED` with structured error. Budget exceeded → `PAUSED_BUDGET`.
- `NEEDS_HUMAN_ACTION` records `PROBLEM / ROOT CAUSE / WHAT WAS AUTOMATED / WHAT REMAINS / EXACT HUMAN ACTION / NEXT AUTOMATIC STEP` and never publishes.
- `BLOCKED`, `FAILED`, `NEEDS_REVIEW` productions are never uploaded.

---

## 6. Continuity strategy (highest priority)

Veo Lite cannot Extend, so the video is stitched from 5 independent 8 s generations. Continuity is enforced in four layers:

1. **Continuity Bible** — generated once from script + storyboard; injected verbatim into every prompt (characters, wardrobe, hair, accessories, environment, objects, lighting, palette, camera, lens, movement, voice, style, temporal state).
2. **Last-frame chaining** — after segment *N* is validated, ffmpeg extracts its final frame; it becomes the `image` (first frame) of segment *N+1*. This is the strongest signal Veo Lite accepts.
3. **Observed end-state** — Gemini vision describes the *actual* last frame (positions, gaze, door angle, camera height…). The next prompt says "Continue EXACTLY from this state" using the observed description plus the storyboard's intended `continuity_state`. Intent and reality are reconciled rather than assumed.
4. **Continuity check** — after generation, a vision model compares last frame of *N* with first frame of *N+1* and scores continuity; below threshold → regenerate *N+1* (bounded by budget/retries).

Prompts never restart actions. Negative constraints forbid: scene resets, new characters, wardrobe/lighting/camera changes, on-screen text, subtitles, speech/voiceover (narration is added in post so the voice is always one voice).

Optional strategy `keyframe_interpolation` (disabled by default): pre-generate boundary keyframes with an image model and use `last_frame` conditioning. Interface exists; not needed for v1.

---

## 7. Audio strategy

- Veo generates ambient sound and SFX only (prompted; speech forbidden).
- Narration: one TTS voice, generated **per beat** so each beat lands at its timeline start; total is checked against the 40 s cap. Over-length → LLM tightens the beat text (max 2 passes) then `atempo` ≤ 1.08.
- Mix: Veo audio ducked under narration (sidechain), optional royalty-free music from `assets/music/` ducked further, then `loudnorm` to −14 LUFS, −1 dBTP.
- No music is bundled (licensing). Pipeline works without it.

## 8. Captions

Word timings come from the first available: TTS native word boundaries (edge-tts) → Gemini transcription with timestamps → proportional estimate within each beat's measured duration. Rendered as ASS phrases of 2–4 words, bold sans (Impact / Segoe UI Bold), white with dark outline, positioned at ~62 % height (inside 9:16 safe area, above Shorts UI). Burned with libass.

## 9. Quality gate

Duration ≤ `max_duration_s`, 1080×1920, 24–30 fps, H.264 + AAC, audio present with narration RMS above floor, all 5 segments validated, continuity score ≥ threshold, captions present and within duration, metadata complete (title ≤ 100 chars, description, hashtags, tags), LLM policy check (misinformation, danger, copyright, ad-suitability), originality self-check. Fail → regenerate affected stage → revalidate, until limits.

## 10. Analytics & learning

- **Snapshots** (YouTube Data API, near-real-time): 10 m, 30 m, 1 h, 3 h, 6 h, 12 h, 24 h, 48 h, 7 d, 14 d, 30 d → growth class (Dead / Slow / Normal / Accelerating / Viral / Explosive) from velocity vs channel baseline.
- **Deep metrics** (YouTube Analytics API, ~48 h latency): engagedViews, averageViewDuration, averageViewPercentage, likes, comments, shares, subscribersGained, traffic sources (SHORTS), and the **retention curve** (`elapsedVideoTimeRatio` × `audienceWatchRatio`, `relativeRetentionPerformance`). Curve is mapped to the timeline → beats and segments → drop attribution (which beat/sentence/visual/transition).
- **Three success levels**: retention, engagement, conversion. Derived rates: like/comment/share rate, subscriber conversion, view-to-like.
- **Comparison**: vs channel mean/median, last 5/10, same category, same hook type, top/bottom performers.
- **Content Intelligence**: feature vector per video (topic, category, hook type, structure, duration, scenes, visual style, voice, pacing wpm, caption style, ending type, loop, CTA) → effect sizes → `insights` → `strategy_weights` (70/30 exploit/explore, configurable) → consumed by the topic selector and by the script generator's system prompt (knowledge base of what worked/failed). Per-video markdown report stored in `storage/reports/` and DB.
- **A/B testing**: variant slots for hook/ending/caption style, one variant per publication, results compared over rolling windows. Never duplicate uploads.

## 11. Reliability, cost, security, observability

- Every external call: timeout, `tenacity` exponential backoff with jitter, rate-limit aware (429/RESOURCE_EXHAUSTED), circuit breaker per API, structured error capture.
- `CostLedger` + `Budget`: Veo Lite at $0.05/s (720p) or $0.08/s (1080p) → $3.20 for 5×8 s at 1080p; LLM/TTS cents. Daily budget default $10; per-segment retries ≤ 3; `PAUSED_BUDGET` when exceeded.
- Secrets only via `.env` / env vars; `secrets/` (OAuth tokens) is gitignored. No keys in code or logs.
- Logs: structlog JSON to `logs/oms.jsonl` + console; fields `timestamp, job_id, stage, action, duration_ms, status, error, retry_count, api, cost_usd`. Metrics computed from `events` + `cost_ledger` (`oms stats`).
- OneDrive: `storage_root` and `DATABASE_URL` are configurable; default stays in-project with WAL mode. Docs recommend excluding `storage/` and `database/` from sync.
- ffmpeg is invoked with `cwd` set to the working directory and relative paths for filter arguments (accent/colon safe).

## 12. Human-action boundaries

| Step | Human action | Automated after |
|---|---|---|
| Gemini/Veo API key | Create AI Studio key, enable Cloud Billing, set `GOOGLE_API_KEY` | Everything else |
| YouTube OAuth | Create GCP OAuth client (Desktop), enable YouTube Data v3 + Analytics v2, run `oms youtube auth` once | Token refresh, uploads, analytics |
| Monetization | YPP application, identity, tax, AdSense | Eligibility tracking, status reporting |
| Music | Drop licensed tracks in `assets/music/` (optional) | Selection and mixing |

## 13. Operating modes

`OMS_MODE=mock` runs the whole pipeline with deterministic fake LLM/Veo/TTS/YouTube adapters and ffmpeg-synthesized segments — used by tests and for validating the pipeline before any money is spent. `OMS_MODE=live` uses real APIs; `upload.enabled=false` keeps live generation local until publishing is switched on.

---

## 12. Manual visual generation mode (default since 2026-09-08)

`generation.mode: manual` replaces the Veo API call with an explicit, validated hand-off:

```
export-prompts ──► storage/prompts/<ID>/manual_prompt_01..05.txt + MANUAL_VIDEO_HANDOFF.txt
      │                    (operator generates the clips in Google Flow with subscription credits,
      │                     chaining them with Extend or the previous clip's last frame)
      ▼
storage/manual_input/<ID>/segment_01..05.mp4 ──► collect-clips (validate, normalise, frames, concat)
      ▼
finish (narration, mix, captions, render, quality gate, metadata, upload) ──► analytics ──► learn
```

`watch <ID>` polls the inbox and runs the rest automatically; `daily` chains analytics, learning and
today's production, stopping with a WAITING_FOR_HUMAN_ACTION report only while the clips are missing.
Cost of a video in this mode: 0 USD on the Veo API; Gemini text/vision/TTS stay inside the free tier when
the key belongs to a project without billing. The Veo client (`app/veo`) remains available behind
`generation.mode: veo` for a future paid setup.
