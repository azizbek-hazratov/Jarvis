# Faqat asosiy Jarvis Telegram botini (jarvis_fon.py / jarvis_telegram.py)
# xavfsiz qayta ishga tushiradi. Userbot Monitor (userbot_fon.py) ga TEGMAYDI.
#
# Javob Telegram'ga yetib borishi uchun avval biroz kutadi.
#
# Majburan (fon-agent tekshiruvisiz): -MajburanRestart bilan chaqiring.

param([switch]$MajburanRestart)

Start-Sleep -Seconds 12

$PythonExe = "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"
"0/3 Fon-ishlar tekshiruvi..." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
$pyArgs = @("C:\Users\Dell\jarvis\_fon_ishlar_tekshiruv.py")
if ($MajburanRestart) { $pyArgs += "--majburan" }
$tekshiruvChiqishi = & $PythonExe @pyArgs 2>&1
$tekshiruvChiqishi | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
if ($LASTEXITCODE -eq 2) {
    "RESTART TO'XTATILDI -- fon-agent(lar) ishlayapti." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
    exit 2
}

"1/3 Jarvis vazifasi to'xtatilyapti..." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
Stop-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

"2/3 Qolgan asosiy bot protsesslari o'ldirilyapti..." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
$protsesslar = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
        ($_.CommandLine -like '*jarvis_fon.py*' -or $_.CommandLine -like '*jarvis_telegram.py*')
    }
foreach ($p in $protsesslar) {
    ("   PID {0} - {1}" -f $p.ProcessId, $p.Name) | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

"3/3 Jarvis qaytadan ishga tushirilyapti..." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
Start-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
$holat = (Get-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue).State
("Holat: {0}" -f $holat) | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"

$yangi = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
        $_.CommandLine -like '*jarvis_fon.py*'
    }
if ($yangi) {
    foreach ($p in $yangi) { ("Ishga tushdi. PID {0}" -f $p.ProcessId) | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt" }
} else {
    "XATO: bot ishga tushmadi." | Out-File -Append "C:\Users\Dell\jarvis\qayta_asosiy_log.txt"
}
