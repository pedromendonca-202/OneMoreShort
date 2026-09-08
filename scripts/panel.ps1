# Starts the OneMoreShort web panel (127.0.0.1:8787 only) and opens it in the default browser.
# Used by the desktop shortcut created with create_desktop_shortcut.ps1. Safe to run twice: if the
# panel is already up, it only opens the browser.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  $listening = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue
  if (-not $listening) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root 'logs') | Out-Null
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList '-m', 'app.web' `
      -WorkingDirectory $root -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $root 'logs\panel.out.log') `
      -RedirectStandardError (Join-Path $root 'logs\panel.err.log')
    $deadline = (Get-Date).AddSeconds(20)
    do {
      Start-Sleep -Milliseconds 400
      try { $ok = (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8787/api/session' -TimeoutSec 2).StatusCode -eq 200 } catch { $ok = $false }
    } while (-not $ok -and (Get-Date) -lt $deadline)
  }
  Start-Process 'http://127.0.0.1:8787/'
} finally {
  Pop-Location
}
