$logFile = "C:\Users\Dell\jarvis\sinov\ai_expert_autoheal_natija.txt"
"" | Out-File -FilePath $logFile -Encoding utf8
$boshlanish = Get-Date
$topildi = $false
while ((New-TimeSpan -Start $boshlanish -End (Get-Date)).TotalSeconds -lt 480) {
    $p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -match 'ai_expert_bot' }
    $vaqt = Get-Date -Format 'HH:mm:ss'
    if ($p) {
        "[$vaqt] TOPILDI - yangi jarayon PID $($p.ProcessId), CreationDate $($p.CreationDate)" | Out-File -FilePath $logFile -Append -Encoding utf8
        $topildi = $true
        break
    } else {
        "[$vaqt] hali yo'q..." | Out-File -FilePath $logFile -Append -Encoding utf8
    }
    Start-Sleep -Seconds 15
}
if (-not $topildi) {
    "[$(Get-Date -Format 'HH:mm:ss')] XATO: 480s ichida jarayon qayta paydo bo'lmadi." | Out-File -FilePath $logFile -Append -Encoding utf8
}
