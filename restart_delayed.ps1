# Jarvis Telegram botini bir oz kutib, keyin qayta ishga tushiradi.
# Maqsad: joriy javob Telegram'ga yetib borguncha kutish, keyin restart.
Start-Sleep -Seconds 12
powershell -ExecutionPolicy Bypass -File "C:\Users\Dell\jarvis\qayta.ps1" *> "C:\Users\Dell\jarvis\qayta_log.txt"
