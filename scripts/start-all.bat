@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

:: ============================================================
::  dnd-dm-agent startup batch
::  Usage:
::    start-all.bat                  full start (QR login)
::    start-all.bat /Quick           skip QR (saved login)
::    start-all.bat /NoQQ            skip NapCat QQ entirely
::    start-all.bat /CpuOnly         CPU mode for embeddings
::    start-all.bat /RestartGateway  kill + restart gateway
:: ============================================================

set NOQQ=0
set QUICK=0
set CPUONLY=0
set RESTART=0

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="/NoQQ" set NOQQ=1
if /i "%~1"=="/Quick" set QUICK=1
if /i "%~1"=="/CpuOnly" set CPUONLY=1
if /i "%~1"=="/RestartGateway" set RESTART=1
if /i "%~1"=="-NoQQ" set NOQQ=1
if /i "%~1"=="-Quick" set QUICK=1
if /i "%~1"=="-CpuOnly" set CPUONLY=1
if /i "%~1"=="-RestartGateway" set RESTART=1
shift
goto parse_args
:args_done

echo ============================================
echo   dnd-dm-agent
echo ============================================

:: ---------- NapCat QQ ----------
if %NOQQ%==1 (
    echo [--] Skipping NapCat QQ (NoQQ)
    goto gateway
)

set LOCALQQ=%cd%\localqq
if not exist "%LOCALQQ%\start.bat" (
    echo [!] NapCat not set up. Run: scripts\setup-napcat.ps1
    echo     Or skip QQ with: start-all.bat /NoQQ
    exit /b 1
)

:: Check if QQ from localqq is already running
set QQRUNNING=0
tasklist /FI "IMAGENAME eq QQ.exe" 2>nul | find /i "QQ.exe" >nul 2>&1
if %errorlevel%==0 (
    :: QQ is running, check if it's the localqq version
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq QQ.exe" /FO CSV /NH 2^>nul') do (
        wmic process where "ProcessId=%%~a" get ExecutablePath 2>nul | find /i "localqq" >nul 2>&1
        if !errorlevel!==0 set QQRUNNING=1
    )
)

if %QQRUNNING%==1 (
    echo [OK] NapCat QQ already running
    goto gateway
)

if %QUICK%==1 (
    echo [..] Quick-starting NapCat QQ ^(saved login^)...
    start "NapCat-QQ-Quick" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALQQ%\start-quick.ps1"
) else (
    echo [..] Starting NapCat QQ ^(QR login may be needed^)...
    start "NapCat-QQ" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALQQ%\start.ps1"
)
echo [OK] NapCat launched ^(window minimized^)

:: ---------- nanobot gateway ----------
:gateway

if %RESTART%==1 (
    echo [..] Stopping any existing gateway...
    tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /i "python.exe" >nul 2>&1
    if !errorlevel!==0 taskkill /F /IM python.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: Check if gateway is already running (look for python processes, not perfect but practical)
set GWRUNNING=0
netstat -an 2>nul | findstr /C:":18765" >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":18765" ^| findstr /C:"LISTENING"') do (
        set GWPID=%%a
        set GWRUNNING=1
    )
)

if %GWRUNNING%==1 (
    echo [OK] Gateway already running ^(PID: !GWPID!^)
    goto done
)

:: Launch gateway in a new window
if %CPUONLY%==1 (
    echo [..] Starting nanobot gateway ^(CPU mode^)...
    start "nanobot-gateway" cmd /k "cd /d %cd% && set DND_EMBEDDING_DEVICE= && nanobot gateway"
) else (
    echo [..] Starting nanobot gateway ^(GPU mode - BGE-M3 on CUDA^)...
    start "nanobot-gateway" cmd /k "cd /d %cd% && set DND_EMBEDDING_DEVICE=cuda && nanobot gateway"
)
echo [OK] Gateway started

:: ---------- done ----------
:done
echo.
echo ============================================
echo   Running
echo ============================================
echo   WebUI:  http://127.0.0.1:18765
echo   Health: http://127.0.0.1:18790/health
if %NOQQ%==0 echo   NapCat: http://127.0.0.1:6099
echo.
echo   Press Ctrl+C to stop, or close windows.
echo ============================================

:: Keep window open so user can see URLs
pause >nul
