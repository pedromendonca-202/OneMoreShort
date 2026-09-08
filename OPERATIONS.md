# Operations

## Daily routine

`python -m app.cli daily` does, in order: capture due analytics checkpoints, refresh intelligence, then
create or advance today's production. While the five clips are missing it prints a WAITING_FOR_HUMAN_ACTION
block and exits with code 2; once the clips are in the inbox the next `daily` (or `watch ID`) finishes,
publishes and starts analytics.

Register it on Windows (runs at 09:00 plus analytics every 3 h):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -Time "09:00" -AnalyticsEveryHours 3
powershell -ExecutionPolicy Bypass -File scripts\unregister_daily_task.ps1   # to remove
```

Logs: `logs/oms.jsonl` (structured events with production id, stage, action, duration, status, error, retry
count, API and cost) and `logs/daily_*.log` per scheduled run.

## Web panel

`scripts\panel.ps1` starts `python -m app.web` (bound to **127.0.0.1:8787 only**; never exposed to the
network) and opens the browser; `scripts\create_desktop_shortcut.ps1` creates the desktop icon. Logs go to
`logs/panel.out.log` and `logs/panel.err.log`. The panel and the CLI share the same database, so both can be
used interchangeably; the scheduled `daily` task keeps running with the panel closed.

Per video in the panel: **Hoje** shows the single next action → **Estúdio** step 2 copies the five prompts →
generate the clips in Flow → drag the five files onto step 3 (validated with ffprobe on arrival; a clip
outside 7-9 s is refused, one slightly off shows a warning) → "Continuar para revisão" runs validation,
narration, captions, render and the quality gate → step 4 shows the preview and the gate → step 5 edits
title/description/hashtags and publishes with an explicit confirmation. **Conversa** does the same through
the assistant (publishing and deleting always open a confirmation dialog). **Ajustes** writes the Gemini key
to `.env` (never to YAML) and everything else to `config/local.yaml`; the key is only ever shown masked.

Demo data for the visual comparison with `design/*.png`: `scripts\demo.ps1` serves a separate
`database/demo.db` + `storage_demo/` (created by `scripts/seed_demo.py`) and never touches `database/oms.db`.

## Operator checklist per video

1. `daily` (or `new` + `export-prompts ID`).
2. Open `storage/prompts/ID/MANUAL_VIDEO_HANDOFF.txt`; generate the five clips in Flow; drop them in
   `storage/manual_input/ID/`.
3. `watch ID` (or `resume ID`). Check `storage/renders/ID/OneMoreShort_Final.mp4` if `upload.enabled` is off.
4. Analytics and learning run by themselves; `report ID` after 48 h, `learn` output answers the standing
   content-intelligence questions.

## Human-action protocol

Whenever an official step needs a person the CLI prints:

```
WAITING_FOR_HUMAN_ACTION
PROBLEM / ROOT CAUSE / WHAT WAS AUTOMATED / WHAT REMAINS / EXACT HUMAN ACTION REQUIRED / NEXT AUTOMATIC STEP
```

and the production moves to NEEDS_HUMAN_ACTION with the report stored (`status ID`). Known cases: missing
clips, missing OAuth client, missing API key in live mode, daily production limit.

## Budget and safety

- `limits.daily_budget_usd` (default 10) is enforced on paid APIs; manual mode spends 0 on video.
- Never publish from NEEDS_REVIEW, FAILED, BLOCKED or NEEDS_HUMAN_ACTION; the uploader refuses.
- Start with `upload.visibility: private` or `unlisted`, review the first renders, then switch to `public`
  or `scheduled` (`publish_hour_local`, `timezone`).

## First real production: current status (2026-09-08)

- WHAT WAS AUTOMATED: full pipeline, verified end to end in mock mode (119 offline tests, final MP4
  1080x1920 H.264/AAC 48 kHz, 40.0 s); manual Flow hand-off; analytics, reports and learning loop.
- WHAT REMAINS (only you can do these):
  1. Google AI Studio key in a project **without** billing -> `.env` `OMS_GOOGLE_API_KEY`, `OMS_MODE=live`.
  2. YouTube OAuth Desktop client -> `secrets/youtube_client_secret.json` -> `python -m app.cli youtube-auth`.
  3. Confirm in Flow: 9:16, 8-second clips, Extend or start-image available on your plan.
- NEXT AUTOMATIC STEP: `python -m app.cli daily` creates the first live production and writes the hand-off;
  after you drop the five clips, `watch ID` publishes it and analytics begins.
