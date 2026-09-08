# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `manual video inbox needs exactly five video files` | Fewer or more than five clips, or unnumbered names | Use `segment_01.mp4` ... `segment_05.mp4` in `storage/manual_input/ID/` |
| `manual segment N failed validation: audio stream is missing` | Flow export without audio | Re-export with audio, or generate again |
| `expected portrait video` | Clip exported 16:9 | Set 9:16 in Flow before generating |
| `duration ... outside 8.00 +- 1.60s` | Clip is not about 8 s | Regenerate with 8-second length |
| `ffmpeg failed` with garbled characters | ffmpeg output decoding | Fixed: output is decoded as UTF-8; report the full message if it recurs |
| Captions not visible | `captions.enabled: false` or font missing | Enable captions; `captions.font` must exist in `C:\Windows\Fonts` (Impact, Arial Black, Bahnschrift) |
| `GOOGLE_API_KEY is not configured` | Live mode without a key | Create the key in a project without billing; `.env` `OMS_GOOGLE_API_KEY` |
| Unexpected Google charges | Key belongs to a billed project | Create a new project without billing for the AI Studio key |
| `YouTube OAuth client secret is missing` | No Desktop-app client JSON | See SETUP.md section 4, then `youtube-auth` |
| `quotaExceeded` / RateLimited | YouTube quota (10,000 units/day) | Wait for the daily reset; uploads cost 1,600 units |
| Analytics snapshot has no retention/watch time | Analytics API latency | Deep metrics are fetched after `deep_metrics_after_hours` (48 h) |
| `Daily production limit reached` | `limits.max_videos_per_day` | `new --force` or raise the limit in `config/local.yaml` |
| Production stuck in NEEDS_REVIEW | Quality gate failed (see `status ID` -> quality report) | Fix the cause (usually clips or policy), then `finish ID` again |
| Reddit or Wikipedia source returns 403 | Public feed blocked the client | Other sources still feed discovery; nothing to do |
| SQLite `database is locked` | OneDrive syncing `database/oms.db` | Pause OneDrive sync for the project folder or move `paths.database_url` outside OneDrive |

Diagnostics: `python -m app.cli doctor`, `status ID`, `metrics`, `logs/oms.jsonl`.
