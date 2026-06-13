@echo off
setlocal
set "ROOT=%~dp0"
set "UV=uv"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8010"
where %UV% >nul 2>nul
if errorlevel 1 (
  echo uv is not installed or not on PATH.
  exit /b 1
)
cd /d "%ROOT%backend"
set "DATABASE_URL=sqlite:///%ROOT:\=/%data/napcat_dnd.db"
set "DATA_DIR=%ROOT%data"
%UV% run --no-sync uvicorn app.main:app --host 127.0.0.1 --port %PORT%
