@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d C:\Users\Dell\jarvis
set LOG=bot_%RANDOM%.log
echo. >> %LOG%
echo [cmd] launching %DATE% %TIME% (log: %LOG%) >> %LOG%
C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe jarvis_telegram.py >> %LOG% 2>&1
echo [cmd] stopped %DATE% %TIME% >> %LOG%
