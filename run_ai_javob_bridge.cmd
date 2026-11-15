@echo off
cd /d "C:\Users\Dell\jarvis"

:loop
echo [%date% %time%] AI Javob Bridge ishga tushmoqda >> ai_javob_bridge_task.log
"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe" ai_javob_bridge.py >> ai_javob_bridge_task.log 2>&1
echo [%date% %time%] Server to'xtadi (kod: %ERRORLEVEL%), 3 soniyadan keyin qayta ishga tushadi >> ai_javob_bridge_task.log
timeout /t 3 /nobreak >nul
goto :loop
