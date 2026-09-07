# Decision Log

Format: **ID · date · decision** — context → choice → consequences. Newest last.

---

**D-001 · 2026-09-07 · Python 3.12 as the implementation language**
Empty repo, no existing stack. Google GenAI SDK, YouTube client libraries, ffmpeg orchestration and LLM tooling are all first-class in Python. → Consequence: single `.venv`, `pip`, pytest.

**D-002 · 2026-09-07 · Veo 3.1 Lite via `google-genai` (`veo-3.1-lite-generate-preview`)**
Required by spec. Verified capabilities (docs + installed SDK 2.22): 9:16, 720p/1080p, 4/6/8 s, `image` first frame, `last_frame`, `negative_prompt`, `generate_audio`, `seed`. Not supported: reference images, Extension, 4K. → Consequence: continuity via last-frame chaining (D-005), not Extension.

**D-003 · 2026-09-07 · Gemini as default LLM, Anthropic pluggable**
User specified no LLM. Gemini shares the Veo API key, so the operator sets up one credential. `gemini-3.8-flash` for fast/cheap tasks, `gemini-3.1-pro-preview` for script/strategy. Anthropic `claude-opus-5` provider ships behind a config switch. → Consequence: `app/llm` provider protocol with structured output support for both.

**D-004 · 2026-09-07 · SQLite + SQLAlchemy 2.0, own state machine, no broker**
One video/day, single operator. A broker (Redis/Celery) adds ops burden without benefit. `Stage` interface is broker-agnostic. → Consequence: `DATABASE_URL` swap enables Postgres later; queue can be added without rewriting stages.

**D-005 · 2026-09-07 · Continuity = Bible + last-frame chaining + observed end-state + vision check**
Veo Lite has no Extension. The strongest available conditioning is a first-frame image. Adding an AI description of the *actual* last frame prevents drift between intent and result. → Consequence: 1 extra vision call per segment (cents); regeneration bounded by retries/budget.

**D-006 · 2026-09-07 · Narration via one TTS voice; Veo speech forbidden by prompt**
Veo's native dialogue voice differs per generation, violating the "never change narrator/voice/accent" rule. → Consequence: Veo supplies ambient/SFX only; TTS (Gemini TTS or edge-tts) supplies narration; mixed with ducking in post.

**D-007 · 2026-09-07 · Per-beat TTS**
Generating narration per beat lets each beat start at its timeline mark and keeps sync with the segment it belongs to. → Consequence: 6 short TTS calls per video, tighten-or-atempo loop if the total exceeds the cap.

**D-008 · 2026-09-07 · Captions as ASS burned by libass**
Precise timing, styling, and safe-area control; `drawtext` is too limited. Word timings prefer TTS-native boundaries, then transcription, then proportional estimate. → Consequence: ffmpeg invoked with relative paths (accented OneDrive path safety).

**D-009 · 2026-09-07 · Trend sources: multiple public/official feeds; Google Trends via RSS, official API optional**
The official Google Trends API is a gated alpha; `pytrends` is unofficial and brittle. → Consequence: Google Trends daily RSS (public) is a signal, not a dependency; YouTube mostPopular, Reddit JSON, Google News RSS, Hacker News, Wikimedia top-views round out the ensemble.

**D-010 · 2026-09-07 · Mock mode is a first-class operating mode**
No API credentials exist yet and Veo has no free tier. → Consequence: `OMS_MODE=mock` runs the entire pipeline with deterministic adapters and ffmpeg-synthesized segments; tests never spend money.

**D-011 · 2026-09-07 · Google AI Plus credits are not usable**
User's subscription credits (50/day, 200/month) apply to consumer apps, not the Gemini API. → Consequence: budget math uses API list prices; `GOOGLE_API_KEY` with Cloud Billing is a required human action (`NEEDS_HUMAN_ACTION`).

**D-012 · 2026-09-07 · Windows Task Scheduler for the daily run**
Simplest reliable trigger on the operator's machine; a `scripts/register_daily_task.ps1` registers `oms daily`. → Consequence: no long-running daemon in v1; `oms serve` (APScheduler) can be added later.

**D-013 · 2026-09-07 · Default resolution 1080p at $0.08/s**
Spec prefers 1080×1920. Cost $0.64/segment, $3.20/video visuals, well inside the $10/day default budget with 3 retries headroom for one segment. `veo.resolution` is configurable to 720p ($0.05/s) for cheaper iteration.
