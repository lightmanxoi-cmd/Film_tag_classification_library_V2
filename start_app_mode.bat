@echo off
chcp 65001 >nul
title Video Library - App Mode

set URL=http://localhost:5000

echo ================================================
echo   Video Library - App Mode Launcher
echo ================================================
echo.

if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    echo Starting with Microsoft Edge...
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=%URL% --start-maximized
) else if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    echo Starting with Microsoft Edge...
    start "" "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --app=%URL% --start-maximized
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    echo Starting with Google Chrome...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=%URL% --start-maximized
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    echo Starting with Google Chrome...
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --app=%URL% --start-maximized
) else (
    echo Error: Neither Edge nor Chrome found!
    echo Please install Microsoft Edge or Google Chrome.
    pause
    exit /b 1
)

echo.
echo App launched successfully!
timeout /t 2 >nul
