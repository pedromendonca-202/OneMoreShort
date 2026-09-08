$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  & .\.venv\Scripts\python.exe -m app.cli doctor
} finally {
  Pop-Location
}
