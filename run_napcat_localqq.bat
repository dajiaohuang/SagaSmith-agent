@echo off
setlocal
set "NAPCAT_SOURCE=%NAPCAT_SOURCE_DIR%"
if "%NAPCAT_SOURCE%"=="" if exist "%~dp0tools\napcat\runtime" set "NAPCAT_SOURCE=%~dp0tools\napcat\runtime"
if "%NAPCAT_SOURCE%"=="" if exist "%~dp0tools\napcat\pkg" set "NAPCAT_SOURCE=%~dp0tools\napcat\pkg"
if "%NAPCAT_SOURCE%"=="" (
  echo NapCat runtime not found.
  echo Set NAPCAT_SOURCE_DIR or install it under "%~dp0tools\napcat\runtime".
  exit /b 1
)
set "NAPCAT_LAUNCHER="
for /r "%NAPCAT_SOURCE%" %%F in (napcat.bat) do (
  if exist "%%~fF" (
    set "NAPCAT_LAUNCHER=%%~fF"
    goto found
  )
)
if "%NAPCAT_LAUNCHER%"=="" (
  echo NapCat shell not found under "%NAPCAT_SOURCE%".
  exit /b 1
)
:found
echo Using NapCat shell:
echo   %NAPCAT_LAUNCHER%
if /i "%~1"=="--check" exit /b 0
for %%F in ("%NAPCAT_LAUNCHER%") do cd /d "%%~dpF"
call "%NAPCAT_LAUNCHER%" %*
