@echo off
title Jarvis HUD - bridge server (Jarvis "miyasi" bilan bog'lovchi)
cd /d "%~dp0"

echo Jarvis HUD bridge ishga tushirilmoqda (port 8090)...
echo Bu oyna Jarvis'ga savol-javob uchun kerak - yopmang.
echo.

rem -u = Python chiqishini (print, log) BUFERLASHTIRMAYDI — shu bo'lmasa,
rem konsolda hech qanday qator (hatto Werkzeug so'rov logi ham) darhol
rem ko'rinmasligi mumkin edi (sinovda aynan shu kuzatildi).
python -u jarvis_hud_bridge.py

pause
