# Removes the scheduled jobs created by register_daily_task.ps1.
param([string]$TaskName = "OneMoreShort Daily")
$ErrorActionPreference = 'SilentlyContinue'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Unregister-ScheduledTask -TaskName "$TaskName - Analytics" -Confirm:$false
Write-Host "Removed '$TaskName' and '$TaskName - Analytics' (if they existed)"
