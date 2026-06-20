# Start NapCat QQ (first time: shows QR, saves login state)
# Called by start-all.bat
param([switch]$NoQR)

$ErrorActionPreference = "Continue"
$Base = $PSScriptRoot
Set-Location (Split-Path $Base)

# Auto-detect the local QQ directory (matches *_localqq)
$LocalQQ = Get-ChildItem -Directory -Path (Get-Location) -Filter "*_localqq" |
    Select-Object -First 1
if (-not $LocalQQ) {
    Write-Host "[!] No *_localqq directory found. Run setup-napcat.ps1 first." -ForegroundColor Red
    exit 1
}
$LocalQQ = $LocalQQ.FullName

Write-Host "=== NapCat QQ ===" -ForegroundColor Cyan

# ---------- QR helper ----------
function Show-QR {
    param([int]$TimeoutSec = 30)
    $qrFile = Join-Path $LocalQQ "NapCat.44498.Shell\versions\9.9.26-44498\resources\app\napcat\cache\qrcode.png"

    function _open_qr {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "  QR code - scan with QQ on your phone" -ForegroundColor White
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host ""
        Start-Process $qrFile
    }

    # Record last write time — a new QR will overwrite with a newer timestamp
    $lastWrite = (Get-Item $qrFile -ErrorAction SilentlyContinue).LastWriteTime

    Write-Host "[..] Waiting for new QR code..." -ForegroundColor Yellow
    for ($i = 0; $i -lt $TimeoutSec; $i++) {
        $current = Get-Item $qrFile -ErrorAction SilentlyContinue
        if ($current -and $current.LastWriteTime -ne $lastWrite) {
            _open_qr
            return
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host ""
    Write-Host "[!] No new QR appeared. Open:" -ForegroundColor DarkYellow
    Write-Host "    $qrFile" -ForegroundColor DarkGray
}

# ---------- main ----------
$QQExe = Join-Path $LocalQQ "NapCat.44498.Shell\QQ.exe"
if (-not (Test-Path $QQExe)) {
    Write-Host "[!] QQ.exe not found. Run setup-napcat.ps1 first." -ForegroundColor Red
    exit 1
}

$QQRunning = Get-Process -Name "QQ" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*_localqq*" }

if (-not $QQRunning) {
    Write-Host "[..] Starting QQ..." -ForegroundColor Yellow
    Start-Process -FilePath $QQExe -WorkingDirectory (Split-Path $QQExe)
    if (-not $NoQR) { Show-QR }
} else {
    Write-Host "[OK] QQ already running (PID: $($QQRunning.Id))" -ForegroundColor Green
}

# Inject NapCat
$NapCatDir = Join-Path $LocalQQ "NapCat.44498.Shell\versions\9.9.26-44498\resources\app\napcat"
$env:NAPCAT_PATCH_PACKAGE = Join-Path $NapCatDir "qqnt.json"
$env:NAPCAT_LOAD_PATH = Join-Path $NapCatDir "loadNapCat.js"
$env:NAPCAT_INJECT_PATH = Join-Path $NapCatDir "NapCatWinBootHook.dll"
$env:NAPCAT_LAUNCHER_PATH = Join-Path $NapCatDir "NapCatWinBootMain.exe"
$env:NAPCAT_MAIN_PATH = Join-Path $NapCatDir "napcat.mjs"

$mjsFwd = $env:NAPCAT_MAIN_PATH -replace '\\', '/'
"(async () => {await import('file:///$mjsFwd')})()" | Out-File -FilePath $env:NAPCAT_LOAD_PATH -Encoding UTF8

Write-Host "[..] Injecting NapCat..." -ForegroundColor Yellow
Start-Process -FilePath $env:NAPCAT_LAUNCHER_PATH `
    -ArgumentList $QQExe, $env:NAPCAT_INJECT_PATH `
    -WorkingDirectory $NapCatDir

# Wait for WebSocket
Write-Host "[..] Waiting for NapCat WebSocket (port 3001)..." -ForegroundColor Yellow
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    if (netstat -ano 2>$null | Select-String "LISTENING.*3001") {
        Write-Host "[OK] NapCat ready! ws://127.0.0.1:3001" -ForegroundColor Green
        break
    }
}
Write-Host "WebUI: http://127.0.0.1:6099" -ForegroundColor DarkGray
