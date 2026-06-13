@echo off
setlocal
set "NAPCAT_SOURCE=%NAPCAT_SOURCE_DIR%"
if "%NAPCAT_SOURCE%"=="" if exist "%~dp0tools\napcat\runtime" set "NAPCAT_SOURCE=%~dp0tools\napcat\runtime"
if "%NAPCAT_SOURCE%"=="" (
  echo NapCat runtime not found.
  echo Set NAPCAT_SOURCE_DIR or install it under "%~dp0tools\napcat\runtime".
  exit /b 1
)
set "NAPCAT_DIR="
for /d %%D in ("%NAPCAT_SOURCE%\NapCat.*.Shell") do (
  set "NAPCAT_DIR=%%~fD"
  goto found
)
if "%NAPCAT_DIR%"=="" (
  echo NapCat shell not found under "%NAPCAT_SOURCE%".
  exit /b 1
)
:found
cd /d "%NAPCAT_DIR%"
call .\napcat.bat
