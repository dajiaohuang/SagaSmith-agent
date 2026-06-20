@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

:: ============================================================
::  dnd-dm-agent quick start
::  NapCat QQ (saved login) + nanobot gateway (GPU)
::  Double-click to run. Saved login required.
:: ============================================================

echo ============================================
echo   dnd-dm-agent ^(Quick Start^)
echo ============================================

:: ---------- NapCat QQ (quick mode) ----------
set LOCALQQ=%cd%\localqq
if exist "%LOCALQQ%\start-quick.ps1" (
    :: Check if local QQ is already running
    set QQRUNNING=0
    tasklist /FI "IMAGENAME eq QQ.exe" 2>nul | find /i "QQ.exe" >nul 2>&1
    if !errorlevel!==0 (
        for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq QQ.exe" /FO CSV /NH 2^>nul') do (
            wmic process where "ProcessId=%%~a" get ExecutablePath 2>nul | find /i "localqq" >nul 2>&1
            if !errorlevel!==0 set QQRUNNING=1
        )
    )

    if !QQRUNNING!==1 (
        echo [OK] NapCat QQ already running
    ) else (
        echo [..] Quick-starting NapCat QQ ^(saved login^)...
        start "NapCat-QQ" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALQQ%\start-quick.ps1"
        echo [OK] NapCat launched ^(window minimized^)
    )
) else (
    echo [!] NapCat not installed - run scripts\setup-napcat.ps1 first
    echo     Starting without QQ...
)

:: ---------- nanobot gateway ----------
set GWRUNNING=0
netstat -an 2>nul | findstr /C:":18765" >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":18765" ^| findstr /C:"LISTENING"') do (
        set GWRUNNING=1
    )
)

if !GWRUNNING!==1 (
    echo [OK] Gateway already running
    goto done
)

echo [..] Starting nanobot gateway ^(GPU mode^)...
start "nanobot-gateway" cmd /k "cd /d %cd% && set DND_EMBEDDING_DEVICE=cuda && nanobot gateway"
echo [OK] Gateway started

:: ---------- done ----------
:done
echo.
echo ============================================
echo   Running - press Ctrl+C to stop
echo ============================================
echo   WebUI:  http://127.0.0.1:18765
echo   NapCat: http://127.0.0.1:6099
echo ============================================
pause >nul
