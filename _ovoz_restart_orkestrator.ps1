# 2026-09-28 -- "Ovozli buyruq" bandi restarti. Joriy javob Telegram'ga
# yetib borguncha kutadi, keyin mavjud qayta.ps1 (fon-agent tekshiruvi +
# toza kill + qayta ishga tushirish) orqali restart qiladi, sog'lomligini
# heartbeat_jarvis.json orqali tekshiradi, va NATIJASINI Azizbekka Telegram
# orqali (jarayon o'zi o'lganidan keyin ham) xabar qiladi. Muvaffaqiyatsiz
# bo'lsa -- git HEAD'ga (oxirgi commit qilingan barqaror holat) qaytarib,
# yana bir bor qayta ishga tushirishga urinadi ("avto-qaytarish").

$PythonExe = "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"
$Baza = "C:\Users\Dell\jarvis"

function Send-Telegram($matnFayl) {
    & $PythonExe -c "
import sys, requests, config
matn = open(sys.argv[1], encoding='utf-8').read()
requests.post(f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage', data={'chat_id': config.OWNER_ID, 'text': matn}, timeout=15)
" "$matnFayl"
}

function Heartbeat-Yangimi($boshlanishVaqti) {
    try {
        $hb = Get-Content "$Baza\heartbeat_jarvis.json" -Raw | ConvertFrom-Json
        $hbVaqt = [datetime]::ParseExact($hb.last_ok, "yyyy-MM-dd HH:mm:ss", $null)
        return $hbVaqt -gt $boshlanishVaqti
    } catch { return $false }
}

Start-Sleep -Seconds 12

$boshlanish = Get-Date
& powershell -ExecutionPolicy Bypass -File "$Baza\qayta.ps1" *> "$Baza\_ovoz_restart_log.txt"
$kod = $LASTEXITCODE

if ($kod -eq 2) {
    Set-Content -Path "$Baza\_ovoz_restart_xabar.txt" -Value "Restart qilinmadi -- fon-agent hali ishlayapti deb aniqlandi (qayta.ps1 o'zi ham alohida xabar yuborgan bo'lishi kerak). Hech narsa o'zgartirilmadi, hozirgi eski kod bilan ishlab turibdi." -Encoding utf8
    Send-Telegram "$Baza\_ovoz_restart_xabar.txt"
    exit 2
}

# Sog'lomlik tekshiruvi -- heartbeat qayta ishga tushishdan KEYIN yangilanganmi (30s gacha, 5 marta urinish)
$soglom = $false
for ($i = 0; $i -lt 6; $i++) {
    Start-Sleep -Seconds 5
    if (Heartbeat-Yangimi $boshlanish) { $soglom = $true; break }
}

if ($kod -eq 0 -and $soglom) {
    Set-Content -Path "$Baza\_ovoz_restart_xabar.txt" -Value "✅ qaytdim, ovoz tayyor" -Encoding utf8
    Send-Telegram "$Baza\_ovoz_restart_xabar.txt"
    exit 0
}

# --- Muvaffaqiyatsiz -- AVTO-QAYTARISH: FAQAT bugungi "ovoz->xodim" yo'naltirish
# blokini olib tashlaymiz (eng ehtimolli sabab), boshqa hech narsaga (jarvis_core.py,
# Band 1/2 kodiga) TEGMAYMIZ -- ular bugungi ishga aloqasiz, allaqachon barqaror.
Copy-Item "$Baza\zaxira_ovoz_2026-09-28\jarvis_telegram_ROLLBACK.py" "$Baza\jarvis_telegram.py" -Force
& powershell -ExecutionPolicy Bypass -File "$Baza\qayta.ps1" -MajburanRestart *> "$Baza\_ovoz_restart_log2.txt"
$kod2 = $LASTEXITCODE

$qaytarishSoglom = $false
for ($i = 0; $i -lt 6; $i++) {
    Start-Sleep -Seconds 5
    if (Heartbeat-Yangimi (Get-Date)) { $qaytarishSoglom = $true; break }
}

if ($kod2 -eq 0) {
    Set-Content -Path "$Baza\_ovoz_restart_xabar.txt" -Value "⚠️ Yangi kod (ovoz->xodim yo'naltirish) bilan restart muvaffaqiyatsiz bo'ldi (heartbeat yangilanmadi) -- shu qismni olib tashlab (boshqa hech narsaga tegmasdan), qayta ishga tushirdim. Hozir ishlab turibman, lekin ovozli buyruq band hali FAOL EMAS -- tekshirib qayta urinaman. Log: _ovoz_restart_log.txt / _ovoz_restart_log2.txt" -Encoding utf8
} else {
    Set-Content -Path "$Baza\_ovoz_restart_xabar.txt" -Value "❌ Restart HAM, qaytarish HAM muvaffaqiyatsiz bo'ldi -- qo'lda tekshirish kerak. Log: _ovoz_restart_log.txt / _ovoz_restart_log2.txt" -Encoding utf8
}
Send-Telegram "$Baza\_ovoz_restart_xabar.txt"
