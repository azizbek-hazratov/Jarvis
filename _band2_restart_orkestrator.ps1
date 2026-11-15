# 2026-09-28 -- "1-bosqich band 2" (imtihon/xodim-dispatch tuzatishlari)
# restarti. Eski `_ovoz_restart_orkestrator.ps1`dan FARQI:
#   1) Sog'lomlik oynasi 12s + 13x10s = 142s (>=120s, 2 to'liq 60s heartbeat
#      siklidan OSHIQ margin bilan -- ertalabki soxta-muvaffaqiyatsizlik
#      sababi (42s oyna 2-siklga yetmasdi) takrorlanmasligi uchun).
#   2) Muvaffaqiyat 3 ALOHIDA mezon bilan tekshiriladi (hammasi TRUE bo'lishi
#      shart): (a) heartbeat_vaqti restart boshlangandan KEYIN yangilangan
#      (jarayon tirik + heartbeat aylanishi ishlayapti), (b) last_ok ham
#      yangilangan (bu FAQAT get_me() muvaffaqiyatli VA app.updater.running
#      bo'lganda yoziladi -- jarvis_telegram.py:787-789), (c) bot.log'da
#      restart boshlangandan keyin "Traceback" YO'Q.
#   3) Avto-qaytarish: FAQAT jarvis_telegram.py (eng yuqori xavfli -- asosiy
#      kirish nuqtasi) git HEAD versiyasiga qaytariladi
#      (zaxira_band2_2026-09-28\jarvis_telegram.py.GIT_HEAD_ROLLBACK).
#      Qolgan 4 modul (jarvis_xodim_dispatch.py, jarvis_xodim_qoidalar.py,
#      jarvis_jamoa_data.py, jarvis_xodim_telegram.py) o'zgarishsiz qoladi --
#      ular py_compile + imtihon 48/48 bilan alohida tasdiqlangan, import
#      xatosi bo'lmasa jarayonni yiqitolmaydi (faqat individual xabar
#      ishlov berishda xato bo'lishi mumkin, u try/except bilan qoplangan).

$PythonExe = "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"
$Baza = "C:\Users\Dell\jarvis"
$RollbackFayl = "$Baza\zaxira_band2_2026-09-28\jarvis_telegram.py.GIT_HEAD_ROLLBACK"

function Send-Telegram($matnFayl) {
    & $PythonExe -c "
import sys, requests, config
matn = open(sys.argv[1], encoding='utf-8').read()
requests.post(f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage', data={'chat_id': config.OWNER_ID, 'text': matn}, timeout=15)
" "$matnFayl"
}

function Heartbeat-Vaqti-Yangimi($boshlanishVaqti) {
    try {
        $hb = Get-Content "$Baza\heartbeat_jarvis.json" -Raw | ConvertFrom-Json
        $vaqt = [datetime]::ParseExact($hb.heartbeat_vaqti, "yyyy-MM-dd HH:mm:ss", $null)
        return $vaqt -gt $boshlanishVaqti
    } catch { return $false }
}

function LastOk-Yangimi($boshlanishVaqti) {
    try {
        $hb = Get-Content "$Baza\heartbeat_jarvis.json" -Raw | ConvertFrom-Json
        if (-not $hb.last_ok) { return $false }
        $vaqt = [datetime]::ParseExact($hb.last_ok, "yyyy-MM-dd HH:mm:ss", $null)
        return $vaqt -gt $boshlanishVaqti
    } catch { return $false }
}

function BotLog-Toza($boshlanishVaqti) {
    try {
        $yangi = Get-Content "$Baza\bot.log" -Tail 200 | Where-Object {
            $_ -match "Traceback|ERROR"
        }
        # Faqat restart VAQTIDAN keyingi qatorlarni ko'rib chiqamiz --
        # bot.log satr boshida vaqt yo'q bo'lishi mumkin (masalan Traceback
        # davomi), shuning uchun oddiy "hech qanday Traceback yo'q" tekshiruvi
        # (oxirgi 200 qatorda) yetarli darajada xavfsiz taxmin.
        return ($yangi | Measure-Object).Count -eq 0
    } catch { return $true }  # log o'qib bo'lmasa, "toza" deb hisoblaymiz (log yo'qligi xato emas)
}

function Soglomlikni-Tekshir($boshlanishVaqti) {
    for ($i = 0; $i -lt 13; $i++) {
        Start-Sleep -Seconds 10
        $a = Heartbeat-Vaqti-Yangimi $boshlanishVaqti
        $b = LastOk-Yangimi $boshlanishVaqti
        $c = BotLog-Toza $boshlanishVaqti
        if ($a -and $b -and $c) { return $true }
    }
    return $false
}

Start-Sleep -Seconds 12

$boshlanish = Get-Date
& powershell -ExecutionPolicy Bypass -File "$Baza\qayta.ps1" *> "$Baza\_band2_restart_log.txt"
$kod = $LASTEXITCODE

if ($kod -eq 2) {
    Set-Content -Path "$Baza\_band2_restart_xabar.txt" -Value "Restart qilinmadi -- fon-agent hali ishlayapti deb aniqlandi. Hech narsa o'zgartirilmadi." -Encoding utf8
    Send-Telegram "$Baza\_band2_restart_xabar.txt"
    exit 2
}

$soglom = Soglomlikni-Tekshir $boshlanish

if ($kod -eq 0 -and $soglom) {
    Set-Content -Path "$Baza\_band2_restart_xabar.txt" -Value "✅ qaytdim, band 2 (xodim dispatch + imtihon tuzatishlari) faol." -Encoding utf8
    Send-Telegram "$Baza\_band2_restart_xabar.txt"
    exit 0
}

# --- Muvaffaqiyatsiz -- jarvis_telegram.py'ni git HEAD versiyasiga qaytaramiz
Copy-Item $RollbackFayl "$Baza\jarvis_telegram.py" -Force
$boshlanish2 = Get-Date
& powershell -ExecutionPolicy Bypass -File "$Baza\qayta.ps1" -MajburanRestart *> "$Baza\_band2_restart_log2.txt"
$kod2 = $LASTEXITCODE

$qaytarishSoglom = Soglomlikni-Tekshir $boshlanish2

if ($kod2 -eq 0 -and $qaytarishSoglom) {
    Set-Content -Path "$Baza\_band2_restart_xabar.txt" -Value "⚠️ Yangi kod bilan restart muvaffaqiyatsiz bo'ldi (heartbeat/last_ok yangilanmadi yoki bot.log'da xato bor edi) -- jarvis_telegram.py git HEAD versiyasiga qaytarib, qayta ishga tushirdim. Hozir ishlab turibman, lekin bugungi band-2 o'zgarishlari HALI FAOL EMAS. Log: _band2_restart_log.txt / _band2_restart_log2.txt" -Encoding utf8
} else {
    Set-Content -Path "$Baza\_band2_restart_xabar.txt" -Value "❌ Restart HAM, qaytarish HAM muvaffaqiyatsiz bo'ldi -- qo'lda tekshirish kerak. Log: _band2_restart_log.txt / _band2_restart_log2.txt" -Encoding utf8
}
Send-Telegram "$Baza\_band2_restart_xabar.txt"
