# ESKI/legacy skript (hardcoded PID 14484 -- ehtimol eskirgan). 2026-09-27:
# fon-agent xavfsizlik tekshiruvi qo'shildi, boshqa restart skriptlari bilan
# bir xil qoida (majburan uchun: -MajburanRestart).
param([switch]$MajburanRestart)

$PythonExe = "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"
$pyArgs = @("C:\Users\Dell\jarvis\_fon_ishlar_tekshiruv.py")
if ($MajburanRestart) { $pyArgs += "--majburan" }
& $PythonExe @pyArgs
if ($LASTEXITCODE -eq 2) {
    Write-Host "RESTART TO'XTATILDI -- fon-agent(lar) ishlayapti." -ForegroundColor Red
    exit 2
}

Start-Sleep -Seconds 5
Stop-Process -Id 14484 -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Set-Location "C:\Users\Dell\jarvis"
Start-Process -FilePath "C:\Users\Dell\jarvis\run_bot.cmd" -WindowStyle Hidden
