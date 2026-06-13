@echo off
setlocal
set "ROOT=%~dp0"
set "ARCHIVE=%ROOT%tools\napcat\NapCat.Shell.Windows.OneKey.zip"
set "TARGET=%ROOT%tools\napcat\runtime"
if not exist "%ARCHIVE%" (
  echo Missing NapCat archive: "%ARCHIVE%"
  exit /b 1
)
if not exist "%TARGET%" mkdir "%TARGET%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ARCHIVE%' -DestinationPath '%TARGET%' -Force"
if errorlevel 1 exit /b 1
echo NapCat installer extracted to "%TARGET%".
echo Run "%TARGET%\NapCatInstaller.exe" to install or update the local NapCat shell.

