# Pipeline

## States

```
DISCOVERING -> SELECTED -> RESEARCHING -> SCRIPTING -> STORYBOARDING -> GENERATING
-> VALIDATING -> EDITING -> QUALITY_CHECK -> READY -> UPLOADING -> PUBLISHED -> ANALYZING -> LEARNED
hold states: NEEDS_HUMAN_ACTION, NEEDS_REVIEW, FAILED, RETRYING, BLOCKED, PAUSED_BUDGET
```

Every command is idempotent: artefacts already stored (topic, research, script, storyboard, bible, prompts,
segments, render, metadata) are loaded instead of regenerated. `resume ID` continues from the persisted state.

## Stage by stage

| Command | Stages | Details |
|---|---|---|
| `new` | DISCOVERING | Allocates `OMS-YYYYMMDD-NNNN`, snapshots the config, enforces `max_videos_per_day` |
| `export-prompts` | SELECTED ... GENERATING | Trend signals (YouTube mostPopular, Reddit, Google News RSS, Hacker News, Wikipedia top views, Google Trends RSS) -> LLM clustering -> virality score -> strategy-weighted selection with exploration -> deep research with search grounding -> timed script (hook/setup/escalation/revelation/payoff/ending, max 40 s) -> five-segment storyboard -> continuity bible -> five prompts with the 15 required blocks -> hand-off file |
| operator | GENERATING | Generates the five clips in Flow (see hand-off), drops them in the inbox |
| `collect-clips` | VALIDATING -> EDITING | ffprobe validation (duration, portrait, H.264, audio), normalise to 1080x1920/24 fps, first/last frames, concat |
| `finish` | EDITING -> QUALITY_CHECK -> READY (-> UPLOADING -> PUBLISHED) | Per-beat narration with one voice (tighten or bounded atempo if over length), ducked mix (ambience + optional music + narration, loudnorm -14 LUFS, 48 kHz), word-timed ASS captions in the safe area, H.264 render with optional logo, quality gate (duration, resolution, fps, codecs, audio, segments, captions, continuity, policy), LLM metadata (title, description, hashtags incl. #Shorts, tags, category, pinned comment), scheduled `publishAt` when enabled, resumable upload |
| `analytics` | PUBLISHED -> ANALYZING | Checkpoints at 10 m, 30 m, 1 h, 3 h, 6 h, 12 h, 24 h, 48 h, 7 d, 14 d, 30 d; Data API counters immediately, Analytics API (engaged views, watch time, average view duration and percentage, shares, subscribers, traffic sources, retention curve) after 48 h |
| `learn` | ANALYZING -> LEARNED | Feature vector per video, pattern detection across hook, category, ending, duration, pacing, style, narrator, captions; strategy weights; knowledge base; per-video report; LEARNED after `learn_after_hours` |

## Continuity (the five clips must look like one shot)

- The storyboard plans each segment's end state; the bible fixes characters, wardrobe, environment,
  lighting, palette, camera, lens, movement, objects, voice and temporal state.
- Prompt N+1 embeds the planned end state of N with "Continue EXACTLY ... Do NOT restart the scene".
- In manual mode the operator chains clips in Flow with Extend or the previous clip's last frame; the
  pipeline extracts first/last frames of every delivered clip for review and vision checks.
- Narration is one TTS voice for the whole video; Veo/Flow audio is ambience only (speech and on-screen
  text are forbidden by the prompt and the negative prompt).

## Analytics and learning

- Missed checkpoints collapse into one snapshot labelled with the latest due slot; numbers are never
  back-dated.
- Retention analysis resamples the curve, detects drops above `retention_drop_threshold` and maps each drop
  to the script beat and segment.
- Derived rates: like, comment, share, subscriber conversion, engagement, view-to-like, view-to-subscriber.
- Growth classes (dead, slow, normal, accelerating, viral, explosive) compare views/hour with the channel
  baseline.
- Each video is compared with the channel mean, median, last 5, last 10 and same category.
- Strategy weights (category, hook, style, preferred duration) multiply the virality score of new
  candidates; `exploration_ratio` keeps 30% experimentation.
- The knowledge base (best hooks, best structures, failed patterns, successful prompts/topics) is injected
  into scoring and script generation on every new production.
