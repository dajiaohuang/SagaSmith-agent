@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%backend"
set "DATABASE_URL=sqlite:///%ROOT:\=/%data/napcat_dnd.db"
uv run --no-sync python -m app.integrations.manage_qq_bindings %*
