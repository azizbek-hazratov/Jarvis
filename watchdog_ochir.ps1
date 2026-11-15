# JarvisWatchdog vazifasini o'chiradi.
#
# Sabab: bu vazifa har 3 daqiqada ishga tushib, "openclaw gateway" degan
# xizmatni tekshiradi. U sog'lom bo'lmasa, KOMPYUTERDAGI BARCHA Node.js
# protsesslarini majburan o'ldiradi (Get-Process node | Stop-Process -Force).
# Jarvisning Claude bilan gaplashadigan ichki qismi ham Node ustida
# ishlaydi - shuning uchun bot muntazam "exit code 129" bilan o'lib
# turgan edi.
#
# Bu skript vazifani NOL QILMAYDI, faqat O'CHIRADI (Disable) - fayllar
# joyida qoladi, kerak bo'lsa keyin qayta yoqish mumkin:
#   Enable-ScheduledTask -TaskName "JarvisWatchdog"
#
# Ishlatish:
#   powershell -ExecutionPolicy Bypass -File C:\Users\Dell\jarvis\watchdog_ochir.ps1

Write-Host "1/3  JarvisWatchdog vazifasini qidiryapman..."
$vazifa = Get-ScheduledTask -TaskName "JarvisWatchdog" -ErrorAction SilentlyContinue

if (-not $vazifa) {
    Write-Host "     Topilmadi - allaqachon o'chirilgan yoki mavjud emas."
} else {
    Write-Host ("     Topildi. Holati: {0}" -f $vazifa.State)
    Write-Host "2/3  O'chirilyapti (fayllar saqlanadi, keyin qayta yoqish mumkin)..."
    Disable-ScheduledTask -TaskName "JarvisWatchdog" | Out-Null
    $yangi = (Get-ScheduledTask -TaskName "JarvisWatchdog").State
    Write-Host ("     Yangi holat: {0}" -f $yangi)
}

Write-Host "3/3  Jarvisni toza qayta ishga tushiryapman..."
Write-Host ""

& powershell -ExecutionPolicy Bypass -File "C:\Users\Dell\jarvis\qayta.ps1"
