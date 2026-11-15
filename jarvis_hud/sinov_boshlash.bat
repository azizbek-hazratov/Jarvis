@echo off
title Jarvis HUD - sinov serveri
cd /d "%~dp0"

echo Server ishga tushirilmoqda (port 8080)...
start "Jarvis HUD Server" cmd /k python -m http.server 8080

timeout /t 2 /nobreak >nul

echo Brauzer ochilmoqda...
start "" http://localhost:8080

exit
