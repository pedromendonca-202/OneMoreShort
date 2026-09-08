# Creates "OneMoreShort.lnk" on the desktop pointing to panel.ps1 (hidden PowerShell window).
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$link = Join-Path $desktop 'OneMoreShort.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = 'powershell.exe'
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\scripts\panel.ps1`""
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = "$root\assets\logo_youtube.ico,0"
if (-not (Test-Path "$root\assets\logo_youtube.ico")) { $shortcut.IconLocation = 'shell32.dll,138' }
$shortcut.Description = 'Painel OneMoreShort (localhost:8787)'
$shortcut.Save()
Write-Host "Atalho criado: $link"
