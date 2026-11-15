# 2026-09-27: bitta qattiq kutishning o'rniga -- suhbat faol davom etayotganda
# "tinch oyna" deyarli chiqmasligi mumkin (har javobdan keyin darhol yangi
# xabar keladi). Shu sabab BIR MARTA emas, bir necha marta (oraliqda) sinab
# ko'radi, birinchi muvaffaqiyatli/haqiqiy-boshqa-sabab bilan to'xtaganda
# chiqadi.
$maxUrinish = 12
$oraliqSoniya = 6

for ($i = 1; $i -le $maxUrinish; $i++) {
    Start-Sleep -Seconds $oraliqSoniya
    powershell -ExecutionPolicy Bypass -File "C:\Users\Dell\jarvis\qayta.ps1" *> "C:\Users\Dell\jarvis\qayta_log.txt"
    $logMatni = Get-Content "C:\Users\Dell\jarvis\qayta_log.txt" -Raw -ErrorAction SilentlyContinue

    if ($logMatni -notmatch "RESTART TAQIQLANDI") {
        "[$( Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Urinish $i/$maxUrinish -- RESTART O'TDI (yoki boshqa sabab bilan to'xtadi)." | Out-File -Append "C:\Users\Dell\jarvis\_restart_qayta_urinish.log"
        exit 0
    }
    "[$( Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Urinish $i/$maxUrinish -- hali ham band, keyingisini kutmoqda." | Out-File -Append "C:\Users\Dell\jarvis\_restart_qayta_urinish.log"
}

"[$( Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $maxUrinish marta urinildi, baribir band -- to'xtatildi." | Out-File -Append "C:\Users\Dell\jarvis\_restart_qayta_urinish.log"
