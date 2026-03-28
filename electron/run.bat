@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting Electron app...

if not exist "node_modules" (
    echo Error: node_modules not found!
    echo Please run start.bat first to install dependencies.
    echo.
    pause
    exit /b 1
)

npx electron .

if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to start Electron app!
    pause
    exit /b 1
)
