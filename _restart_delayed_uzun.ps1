# restart_delayed.ps1 bilan bir xil, faqat KENGROQ bufer (20s, 12s emas) --
# 2026-09-27, avvalgi urinish 12s'da hali ham joriy javob tugamagani sabab
# fon-ishlar.json'da o'ziga tegishli yozuv qolib, o'zini bloklagan edi.
Start-Sleep -Seconds 20
powershell -ExecutionPolicy Bypass -File "C:\Users\Dell\jarvis\qayta.ps1" *> "C:\Users\Dell\jarvis\qayta_log.txt"
