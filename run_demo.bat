@echo off
setlocal
cd /d "%~dp0"
if not defined APP_PORT set "APP_PORT=5002"
python app.py
pause