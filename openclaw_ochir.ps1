# OpenClaw gateway xizmatini o'chiradi (Jarvisga tegmaydi).
#
# Sabab: bu - Jarvisdan butunlay boshqa, alohida fon xizmati. O'zining
# Telegram boti bor va xabar kelganda "claude" nomli terminal oynasini
# ochib qo'yadi - aynan shu ekranga chiqib turgan bo'sh oyna shundan.
#
# Bu skript node.exe protsesslarini FAQAT buyruq qatorida "openclaw"
# so'zi bo'lganlarini o'ldiradi - Jarvisning o'z ichki Node protsessiga
# tegmaydi.
#
# Ishlatish:
#   powershell -ExecutionPolicy Bypass -File C:\Users\Dell\jarvis\openclaw_ochir.ps1

Write-Host "1/3  'OpenClaw Gateway' vazifasini qidiryapman..."
$vazifalar = Get-ScheduledTask -ErrorAction SilentlyContinue |
    Where-Object { $_.TaskName -like "*OpenClaw*" -or $_.TaskName -like "*openclaw*" }

if ($vazifalar) {
    foreach ($v in $vazifalar) {
        Write-Host ("     Topildi: {0} (holati: {1})" -f $v.TaskName, $v.State)
        Disable-ScheduledTask -TaskName $v.TaskName -TaskPath $v.TaskPath | Out-Null
        Write-Host ("     O'chirildi: {0}" -f $v.TaskName)
    }
} else {
    Write-Host "     Vazifa topilmadi (ehtimol boshqa nom bilan yoki umuman ro'yxatdan o'tmagan)."
}

Write-Host "2/3  openclaw gateway protsessini o'ldiryapman (faqat shu, Jarvisga tegmayman)..."
$protsesslar = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq 'node.exe' -and $_.CommandLine -like '*openclaw*'
    }

if ($protsesslar) {
    foreach ($p in $protsesslar) {
        Write-Host ("     PID {0} o'ldirilyapti" -f $p.ProcessId)
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "     Ishlab turgan openclaw protsessi topilmadi."
}

Write-Host "3/3  Jarvis omon qolganini tekshiryapman..."
Start-Sleep -Seconds 2
$jarvis_holati = (Get-ScheduledTask -TaskName "Jarvis" -ErrorAction SilentlyContinue).State
Write-Host ("     Jarvis vazifasi holati: {0}" -f $jarvis_holati)

Write-Host ""
Write-Host "Tayyor. Endi 'claude' nomli bo'sh terminal oynalari ekranga chiqmasligi kerak." -ForegroundColor Green
