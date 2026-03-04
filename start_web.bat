@echo off
title Video Web Server

echo ====================================================
echo        Video Tag Library - Video Web Server
echo ====================================================
echo.
echo Starting video web server...
echo.
echo URL: http://localhost:5000
echo Default Password: 13245768
echo.
echo Press Ctrl+C to stop the server
echo ====================================================
echo.

cd /d "%~dp0"

python web_app.py

pause
