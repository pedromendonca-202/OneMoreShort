# Serve the panel against the demo database (screen comparison only). Never touches database/oms.db.
$root = Split-Path -Parent $PSScriptRoot
$env:OMS_PATHS__DATABASE_URL = "sqlite:///database/demo.db"
$env:OMS_PATHS__STORAGE_ROOT = "storage_demo"
$env:OMS_GOOGLE_API_KEY = "AIzaSyB-demo-key-not-real-0000000000000"
$env:OMS_YOUTUBE_TOKEN_PATH = "storage_demo/youtube_token_demo.json"
Set-Location $root
if (-not (Test-Path "database/demo.db")) { & ".\.venv\Scripts\python.exe" "scripts/seed_demo.py" --clips 4 }
if (-not (Test-Path "storage_demo/youtube_token_demo.json")) { Set-Content -Path "storage_demo/youtube_token_demo.json" -Value "{}" }
& ".\.venv\Scripts\python.exe" -m app.web
