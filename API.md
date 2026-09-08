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

## External APIs

| API | Used for | Auth | Cost |
|---|---|---|---|
| Gemini API (`gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gemini-2.5-flash-preview-tts`) | text, vision, search grounding, TTS | AI Studio key | free tier (project without billing) |
| Veo 3.1 Lite (`veo-3.1-lite-generate-preview`) | only when `generation.mode: veo` | AI Studio key with billing | $0.05/s 720p, $0.08/s 1080p; no free tier |
| YouTube Data API v3 | upload (`videos.insert`), statistics, comments | OAuth Desktop app | free, 10,000 units/day |
| YouTube Analytics API v2 | `reports.query`: video metrics, `elapsedVideoTimeRatio` retention, `insightTrafficSourceType` | OAuth | free |
| Google Trends RSS, Google News RSS, Reddit JSON, Hacker News, Wikimedia pageviews | trend signals | none | free |
| edge-tts | alternative narration | none | free |
