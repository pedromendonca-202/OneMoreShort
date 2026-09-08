# Registers (or updates) the Windows Task Scheduler job that runs `python -m app.cli daily`.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 [-Time "09:00"] [-AnalyticsEveryHours 3]
param(
  [string]$Time = "09:00",
  [int]$AnalyticsEveryHours = 3,
  [string]$TaskName = "OneMoreShort Daily"
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$daily = Join-Path $root 'scripts\daily.ps1'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "venv python not found at $python" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$daily`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "OneMoreShort: analytics, learning and today's production" -Force | Out-Null
Write-Host "Registered '$TaskName' daily at $Time"

# Analytics checkpoints (10 min, 30 min, 1 h, 3 h ...) need more than one run per day.
$analyticsName = "$TaskName - Analytics"
$analyticsAction = New-ScheduledTaskAction -Execute $python -Argument "-m app.cli analytics" -WorkingDirectory $root
$analyticsTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours $AnalyticsEveryHours) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $analyticsName -Action $analyticsAction -Trigger $analyticsTrigger -Settings $settings -Description "OneMoreShort: capture analytics checkpoints" -Force | Out-Null
Write-Host "Registered '$analyticsName' every $AnalyticsEveryHours h"
