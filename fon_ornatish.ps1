# Jarvis background task installer
# Run:
#   powershell -ExecutionPolicy Bypass -File C:\Users\Dell\jarvis\fon_ornatish.ps1

$ErrorActionPreference = "Stop"

$dir = "C:\Users\Dell\jarvis"
$taskName = "Jarvis"

$py = (Get-Command python).Source -replace 'python\.exe$', 'pythonw.exe'
if (-not (Test-Path $py)) {
    throw "pythonw.exe not found: $py"
}
Write-Host "Python: $py"

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$dir\jarvis_fon.py`"" -WorkingDirectory $dir

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Jarvis Telegram bot" | Out-Null

Write-Host "Task created: $taskName"

Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3

$state = (Get-ScheduledTask -TaskName $taskName).State
Write-Host "State: $state"
Write-Host ""
Write-Host "Done. Jarvis will start automatically at logon."
Write-Host "Log file: $dir\bot.log"
