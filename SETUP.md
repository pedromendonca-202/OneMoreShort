# Setup

## 1. Environment (already done on this machine)

- Python 3.12 virtualenv at `.venv` with everything in `requirements.txt`
- ffmpeg 9 (winget `Gyan.FFmpeg`); auto-detected from PATH, the winget folder or `OMS_FFMPEG`
- `python -m app.cli init-db` creates `database/oms.db`

Verify: `.\.venv\Scripts\python.exe -m app.cli doctor`

Mock mode (`OMS_MODE=mock`, the default) needs no credentials and produces synthetic media, so the whole
pipeline and the test suite run offline.

## 2. Free-tier brain: Google AI Studio key WITHOUT billing

Live mode uses Gemini for research, script, storyboard, continuity, vision checks, metadata, policy review
and reports. All of that is inside the Gemini API free tier, but only if the key belongs to a Google Cloud
project that has **no billing account linked**.

1. Open https://aistudio.google.com/apikey.
2. Create the key in a **new project** (do not pick the project that has the free-trial billing account).
3. Put it in `.env` as `OMS_GOOGLE_API_KEY=...` and set `OMS_MODE=live`.
4. Run `doctor` again.

Why this matters: a key from a billed project is charged at list price, and Google's documentation states
that the $300 trial credit cannot pay for the Gemini API in AI Studio. Keep the two projects separate.

## 3. Visuals: Google Flow with your subscription credits

`generation.mode: manual` (default). For each production the pipeline writes
`storage/prompts/<ID>/MANUAL_VIDEO_HANDOFF.txt` plus `manual_prompt_01..05.txt`.
Check once in Flow that your plan offers: portrait 9:16, 8-second clips, and either "Extend" or
"Frames to video" (start image). Those two features are what keep the five clips continuous.
Drop the clips in `storage/manual_input/<ID>/segment_01.mp4 ... segment_05.mp4` (720p or 1080p, MP4).

## 4. YouTube (free within quota)

1. Google Cloud Console, any project: enable **YouTube Data API v3** and **YouTube Analytics API**.
2. OAuth consent screen: External, add your Google account as a test user.
3. Credentials -> Create OAuth client ID -> **Desktop app** -> download JSON.
4. Save it as `secrets/youtube_client_secret.json` (path configurable via `OMS_YOUTUBE_CLIENT_SECRET_PATH`).
5. Run `python -m app.cli youtube-auth` once; the browser consent covers upload, read-only and analytics.
6. Set `upload.enabled: true` and the desired `upload.visibility` in `config/local.yaml` (or `.env`).

Quota: the default 10,000 units/day allows about six uploads (1,600 units each) plus thousands of reads.

## 5. Narration voice

Default `tts.provider: gemini` (free tier, voice `Charon`). Alternative with no key: `tts.provider: edge`
(`en-US-GuyNeural`, also free). Mock mode always uses a silent placeholder voice.

## 6. Optional

- Anthropic instead of Gemini for text: `llm.provider: anthropic` + `OMS_ANTHROPIC_API_KEY`.
- Music: drop a licensed track in `assets/music/` (`video.music_enabled: true`).
- Logo watermark: `assets/logo_youtube.png` (configurable size and opacity under `video`).
- Overrides live in `config/local.yaml` (git-ignored) or `OMS_<SECTION>__<KEY>` variables.
