@echo off
chcp 65001 > nul
echo ========================================================
echo   BIST 360 AI ALGO BOT & WEBHOOK SUNUCUSU BASLATILIYOR
echo ========================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python live_bot_daemon.py
pause
