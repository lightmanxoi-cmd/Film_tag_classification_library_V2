@echo off
chcp 65001 >nul
title Video Library - Electron App

echo ================================================
echo   Video Library - Electron Desktop App
echo ================================================
echo.

cd /d "%~dp0"

echo Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed!
    echo Please download and install from: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js found:
node -v
echo.

echo Setting up environment for China mirror...
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
set ELECTRON_CUSTOM_DIR={{ version }}
set npm_config_registry=https://registry.npmmirror.com
set npm_config_electron_mirror=https://npmmirror.com/mirrors/electron/
set npm_config_electron_builder_binaries_mirror=https://npmmirror.com/mirrors/electron-builder-binaries/
echo Environment variables set.
echo.

echo Cleaning old files...
if exist "node_modules" (
    echo Removing node_modules...
    rmdir /s /q node_modules 2>nul
    timeout /t 2 >nul
)
if exist "package-lock.json" (
    del package-lock.json 2>nul
)
echo Cleaned.
echo.

echo Clearing npm cache...
call npm cache clean --force
echo.

echo Installing dependencies...
echo (This may take 3-5 minutes, please wait...)
echo.
call npm install --registry=https://registry.npmmirror.com
if errorlevel 1 (
    echo.
    echo ================================================
    echo Error: Failed to install dependencies!
    echo.
    echo Possible solutions:
    echo 1. Close all other programs and try again
    echo 2. Check if antivirus is blocking the download
    echo 3. Try using VPN
    echo ================================================
    pause
    exit /b 1
)
echo.

echo Starting Electron app...
echo.

call npx electron .
if errorlevel 1 (
    echo.
    echo Error: Failed to start Electron app!
    pause
)
