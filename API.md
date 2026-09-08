# API reference

## Python entry points

| Module | Key functions / classes |
|---|---|
| `app.pipeline.orchestrator.Orchestrator` | `new_production(force)`, `prepare(id)`, `collect(id)`, `finish(id)`, `resume(id)`, `watch(id)`, `collect_analytics(now)`, `learn(now)`, `report(id)`, `daily()`, `status(id)`, `list_productions()`, `metrics()`, `costs()` |
| `app.core.config` | `load_settings(project_root, config_path, env_file)`; `Settings` sections: llm, veo, generation, tts, video, captions, trends, upload, limits, analytics, intelligence, paths, brand |
| `app.trends.*` | `TrendSource.fetch(limit)`, `aggregate(signals, llm, max_candidates)` |
| `app.research` | `score_topics`, `select_topic(scores, strategy, rng)`, `deep_research(llm, topic, use_search)` |
| `app.scripting.generator.generate_script` | `(llm, topic, research, knowledge, cfg) -> Script` |
| `app.storyboard.generator.generate_storyboard`, `app.continuity.bible.build_bible` | storyboard and continuity bible |
| `app.veo.prompt_builder.build_prompt` | `(segment, bible, storyboard, prev_end_state, brand) -> VeoPrompt` |
| `app.manual_video.workflow` | `export_prompts`, `collect_manual_segments`, `inbox_for` |
| `app.audio` | `build_tts(settings)`, `narrate`, `mix_audio`, `choose_music` |
| `app.captions` | `align_words`, `build_phrases`, `render_ass`, `CaptionStyle` |
| `app.editing` | `run_ffmpeg`, `run_ffprobe`, `probe`, `normalize_segment`, `concat_segments`, `render_final`, `extract_first_frame`, `extract_last_frame`, `synth_segment` |
| `app.quality.gate.run_quality_gate`, `app.metadata.generator.generate_metadata` / `policy_check` | gate and metadata |
| `app.youtube` | `YOUTUBE_SCOPES`, `get_credentials`, `GoogleYouTubeClient.upload/video_stats/post_comment`, `YouTubeDataAPI`, `YouTubeAnalyticsAPI`, `MockYouTubeClient`, `MockAnalyticsClient` |
| `app.analytics` | `due_snapshots`, `collect_for_production`, `collect_all_due`, `analyze_retention`, `engagement_rates`, `classify_growth`, `compare`, `build_report` |
| `app.intelligence` | `extract_features`, `detect_patterns`, `update_strategy` / `load_strategy`, `Knowledge`, `answer_questions`, `learn`, `ABTest` |

## CLI

`python -m app.cli <command>`: `init-db`, `doctor`, `new [--force]`, `export-prompts ID`, `collect-clips ID`,
`finish ID`, `resume ID`, `watch ID [--poll S] [--timeout S]`, `status ID`, `list [--limit N]`, `analytics`,
`learn`, `report ID`, `daily`, `metrics`, `costs [--days N]`, `youtube-auth`.
Exit codes: 0 ok, 1 error, 2 WAITING_FOR_HUMAN_ACTION.

## HTTP API (web panel, `app/web`)

Served by `python -m app.web` on `127.0.0.1:8787`. Every mutating request needs the `X-OMS-CSRF` header with
the token from `GET /api/session`; responses carry `X-Frame-Options: DENY`, `nosniff`, `no-referrer`, a strict
CSP and no CORS. Errors are JSON `{error, message}`; a `HumanActionRequired` becomes HTTP 409 with the report.

| Method | Route | Engine call |
|---|---|---|
| GET | `/api/session`, `/api/health`, `/api/metrics`, `/api/costs?days=` | session token, `doctor`, `metrics()`, `costs()` |
| GET | `/api/events` | Server-Sent Events: `state`, `job`, `clip`, `snapshot`, `settings` |
| GET | `/api/today` | today's production, banner state, steps, timeline, last published, channel summary |
| GET/POST | `/api/productions` | library (`?q&state&category&sort`) / `new_production(force)` + `prepare` job |
| GET/DELETE | `/api/productions/{id}` | detail (step, prompts, clips, quality, metadata) / delete |
| POST | `/api/productions/{id}/prepare · collect · finish · resume` | background jobs over `prepare`, `collect`+`finish`, `finish`, `resume` |
| POST | `/api/productions/{id}/publish` `{confirm:true}` | explicit upload, only from READY |
| POST | `/api/productions/{id}/reset?keep_topic=` · `/duplicate` | new script (same topic) or new topic; new production with the same topic |
| GET | `/api/productions/{id}/prompts · script.txt · video · report` | prompts with blocks, TXT download, final MP4, performance report |
| PUT | `/api/productions/{id}/metadata` | title, description, hashtags, visibility, hour |
| POST/DELETE | `/api/productions/{id}/clips` (multipart `scene`, `file`) · `/clips/{scene}` | validated upload to `storage/manual_input/<id>/segment_0N.mp4` (server-side name, 300 MB/file, ffprobe) |
| GET | `/api/analytics/{id}` · `/api/analytics/latest` | KPIs, retention curve with drops mapped to the script, report verdict, channel comparison |
| POST | `/api/analytics/collect` · `/api/learn` | `collect_analytics()` · `learn()` (rate limited) |
| GET | `/api/intelligence` | highlights, patterns, themes, structures, scatter, recommended tests |
| GET/PUT | `/api/settings` · POST `/restore` · `/test-connection` · `/youtube/connect` · `/youtube/disconnect` · `/open-folder` | masked settings; secrets written to `.env` only |
| POST/GET | `/api/chat` · `/api/chat/history` | assistant (Gemini function calling, nine closed tools; publish/delete only return a confirmation request) |
| GET | `/api/thumbs/{id}?clip=N` | JPEG thumbnail extracted with ffmpeg into `storage/thumbs/` |

## External APIs

| API | Used for | Auth | Cost |
|---|---|---|---|
| Gemini API (`gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gemini-2.5-flash-preview-tts`) | text, vision, search grounding, TTS | AI Studio key | free tier (project without billing) |
| Veo 3.1 Lite (`veo-3.1-lite-generate-preview`) | only when `generation.mode: veo` | AI Studio key with billing | $0.05/s 720p, $0.08/s 1080p; no free tier |
| YouTube Data API v3 | upload (`videos.insert`), statistics, comments | OAuth Desktop app | free, 10,000 units/day |
| YouTube Analytics API v2 | `reports.query`: video metrics, `elapsedVideoTimeRatio` retention, `insightTrafficSourceType` | OAuth | free |
| Google Trends RSS, Google News RSS, Reddit JSON, Hacker News, Wikimedia pageviews | trend signals | none | free |
| edge-tts | alternative narration | none | free |
