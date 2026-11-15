# Jarvis'ni to'g'ri qayta ishga tushirish
#
# Ishlatish:
#   powershell -ExecutionPolicy Bypass -File C:\Users\Dell\jarvis\qayta.ps1
#   (majburan, fon-agent tekshiruvisiz):
#   powershell -ExecutionPolicy Bypass -File C:\Users\Dell\jarvis\qayta.ps1 -MajburanRestart

param([switch]$MajburanRestart)

$PythonExe = "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

Write-Host "0/4  Fon-ishlar tekshiruvi (aktiv fon-agent bormi)..."
$pyArgs = @("C:\Users\Dell\jarvis\_fon_ishlar_tekshiruv.py")
if ($MajburanRestart) { $pyArgs += "--majburan" }
& $PythonExe @pyArgs
if ($LASTEXITCODE -eq 2) {
    Write-Host "     RESTART TO'XTATILDI -- fon-agent(lar) ishlayapti (yuqoridagi xabar Azizbekka yuborildi)." -ForegroundColor Red
    exit 2
}

Write-Host "1/4  Fondagi vazifa to'xtatilyapti..."
Stop-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "2/4  Qolgan jarvis protsesslari o'ldirilyapti..."
$protsesslar = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
        $_.CommandLine -like '*jarvis*'
    }

if ($protsesslar) {
    foreach ($p in $protsesslar) {
        Write-Host ("     PID {0} - {1}" -f $p.ProcessId, $p.Name)
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "     (ishlab turgan protsess yo'q)"
}
Start-Sleep -Seconds 3

Write-Host "3/4  Tekshiruv..."
$qoldiq = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
        $_.CommandLine -like '*jarvis*'
    }

if ($qoldiq) {
    Write-Host "     OGOHLANTIRISH: hali ham ishlayapti:" -ForegroundColor Yellow
    foreach ($p in $qoldiq) { Write-Host ("     PID {0}" -f $p.ProcessId) }
    Write-Host "     Skriptni yana bir marta ishga tushiring." -ForegroundColor Yellow
    exit 1
}
Write-Host "     Toza."

Write-Host "4/4  Jarvis qaytadan ishga tushirilyapti..."

$vazifa = Get-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue

if ($vazifa) {
    Start-ScheduledTask -TaskName "Jarvis"
    Start-Sleep -Seconds 5
    $holat = (Get-ScheduledTask -TaskName "Jarvis").State
    Write-Host ("     Fon vazifasi orqali. Holat: {0}" -f $holat)
} else {
    Write-Host "     Fon vazifasi o'rnatilmagan - to'g'ridan-to'g'ri ishga tushirilyapti."
    Start-Process -FilePath "C:\Users\Dell\jarvis\run_bot.cmd" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    $yangi = Get-CimInstance Win32_Process |
        Where-Object {
            ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
            $_.CommandLine -like '*jarvis*'
        }
    if ($yangi) {
        foreach ($p in $yangi) { Write-Host ("     Ishga tushdi. PID {0}" -f $p.ProcessId) }
    } else {
        Write-Host "     XATO: bot ishga tushmadi. bot.log ni tekshiring." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Log: C:\Users\Dell\jarvis\bot.log"
Write-Host ""
Write-Host "Endi Telegram'da sinab koring." -ForegroundColor Green
