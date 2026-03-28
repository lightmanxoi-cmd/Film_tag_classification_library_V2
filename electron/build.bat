@echo off
chcp 65001 >nul
title Video Library - Build

echo ================================================
echo   Video Library - Build Executable
echo ================================================
echo.

cd /d "%~dp0"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo.
        echo Error: Failed to install dependencies!
        pause
        exit /b 1
    )
    echo.
)

echo Building executable...
echo.

call npm run build

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Build completed successfully!
echo   Output: dist\ folder
echo ================================================
echo.
pause
