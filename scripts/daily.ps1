# OneMoreShort daily run: analytics -> learn -> advance today's production.
# Called by the Windows Task Scheduler job registered with register_daily_task.ps1.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  New-Item -ItemType Directory -Force -Path (Join-Path $root 'logs') | Out-Null
  $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
  $log = Join-Path $root "logs\daily_$stamp.log"
  & .\.venv\Scripts\python.exe -m app.cli daily *>&1 | Tee-Object -FilePath $log
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
