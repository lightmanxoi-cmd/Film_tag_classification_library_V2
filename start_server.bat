@echo off
chcp 65001 >nul
title Video Library Web Server

echo ================================================
echo   Video Library Web Application
echo ================================================
echo.

cd /d "%~dp0"

echo Starting server...
echo.

python web_app.py

echo.
echo Server stopped.
pause
