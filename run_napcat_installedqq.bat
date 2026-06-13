@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
set "NAPCAT_LAUNCHER="

call :find_launcher "%NAPCAT_SOURCE_DIR%"
call :find_launcher "%ROOT%tools\napcat\runtime"
call :find_launcher "%ROOT%tools\napcat\pkg"

if "%NAPCAT_LAUNCHER%"=="" (
  echo NapCat installed-QQ launcher was not found.
  echo Set NAPCAT_SOURCE_DIR to a directory containing launcher-user.bat.
  pause
  exit /b 1
)

echo Using NapCat launcher:
echo   %NAPCAT_LAUNCHER%
if /i "%~1"=="--check" exit /b 0

for %%F in ("%NAPCAT_LAUNCHER%") do cd /d "%%~dpF"
call "%NAPCAT_LAUNCHER%" %*
exit /b %errorlevel%

:find_launcher
if not "%NAPCAT_LAUNCHER%"=="" exit /b 0
if "%~1"=="" exit /b 0
if not exist "%~1" exit /b 0
for /r "%~1" %%F in (launcher-user.bat) do (
  if exist "%%~fF" (
    set "NAPCAT_LAUNCHER=%%~fF"
    exit /b 0
  )
)
exit /b 0
