@echo off
setlocal
cd /d "%~dp0"
if not defined APP_PORT set "APP_PORT=5002"
if not defined APP_ADVERTISE_HOST for /f "delims=" %%I in ('tailscale ip -4 2^>nul') do set "APP_ADVERTISE_HOST=%%I"
python app.py
pause