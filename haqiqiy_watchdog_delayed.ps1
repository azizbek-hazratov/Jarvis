# Haqiqiy (stubsiz) watchdog sinovini xavfsiz kechiktirib ishga tushiradi.
# Maqsad: joriy javob Telegram'ga yetib borguncha kutish, keyin haqiqiy
# restart (bu joriy jarvis_fon.py jarayonini o'ldiradi).
Start-Sleep -Seconds 15
& "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\Dell\jarvis\watchdog_haqiqiy_ishga_tushir.py" *> "C:\Users\Dell\jarvis\watchdog_haqiqiy_natija.txt"
