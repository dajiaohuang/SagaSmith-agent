# Setup NapCat QQ for dnd-dm-agent
# Downloads NapCat + portable QQ, configures OneBot WebSocket, creates startup script.
# Run from repo root: .\scripts\setup-napcat.ps1

param(
    [string]$LocalQQDir = "localqq",
    [string]$NapCatVersion = "v4.18.6",
    [int]$WsPort = 3001,
    [int]$WebUIPort = 6099
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Get-Item .).FullName
$LocalQQPath = Join-Path $RepoRoot $LocalQQDir

Write-Host "=== dnd-dm-agent NapCat QQ Setup ===" -ForegroundColor Cyan
Write-Host "Target: $LocalQQPath"
Write-Host "NapCat: $NapCatVersion"
Write-Host ""

# --------------- Step 1: Download ---------------
$TempDir = Join-Path $env:TEMP "napcat-setup"
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

$NodeZip = Join-Path $TempDir "NapCat.Node.zip"
$OneKeyZip = Join-Path $TempDir "NapCat.OneKey.zip"
$BaseUrl = "https://github.com/NapNeko/NapCatQQ/releases/download/$NapCatVersion"

if (-not (Test-Path $NodeZip)) {
    Write-Host "[1/4] Downloading NapCat Node version..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "$BaseUrl/NapCat.Shell.Windows.Node.zip" -OutFile $NodeZip
}

if (-not (Test-Path $OneKeyZip)) {
    Write-Host "[2/4] Downloading NapCat OneKey (portable QQ)..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "$BaseUrl/NapCat.Shell.Windows.OneKey.zip" -OutFile $OneKeyZip
}

# --------------- Step 2: Extract ---------------
Write-Host "[3/4] Extracting..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $LocalQQPath -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $LocalQQPath | Out-Null

# Extract Node version (NapCat runtime)
Expand-Archive -Path $NodeZip -DestinationPath $LocalQQPath -Force

# Extract OneKey (portable QQ)
$OneKeyExtract = Join-Path $TempDir "onekey"
Remove-Item -Recurse -Force $OneKeyExtract -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $OneKeyExtract | Out-Null
Expand-Archive -Path $OneKeyZip -DestinationPath $OneKeyExtract -Force

# Use 7z to extract QQ
Push-Location $OneKeyExtract
$SevenZip = Join-Path $OneKeyExtract "7z.exe"
& $SevenZip x NapCatInstaller.exe -y | Out-Null
& $SevenZip x QQ.exe "-oQQApp" -y | Out-Null
Pop-Location

# Move QQ runtime into place
$QQSource = Join-Path $OneKeyExtract "QQApp\Files"
$QQDest = Join-Path $LocalQQPath "NapCat.44498.Shell"
if (Test-Path $QQDest) { Remove-Item -Recurse -Force $QQDest }
Move-Item -Path $QQSource -Destination $QQDest -Force

# Copy NapCat into QQ's resources
$NapCatSrc = Join-Path $LocalQQPath "napcat"
$NapCatDest = Join-Path $QQDest "versions\9.9.26-44498\resources\app\napcat"
if (Test-Path $NapCatDest) { Remove-Item -Recurse -Force $NapCatDest }
Copy-Item -Recurse -Path $NapCatSrc -Destination $NapCatDest

# Cleanup
Remove-Item -Recurse -Force $OneKeyExtract -ErrorAction SilentlyContinue

# --------------- Step 3: Configure ---------------
Write-Host "[4/4] Configuring OneBot WebSocket..." -ForegroundColor Yellow

$ConfigDir = Join-Path $NapCatDest "config"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$OneBotConfig = @{
    network = @{
        httpServers = @(
            @{
                name = "localWebUI"
                enable = $true
                port = $WebUIPort
                host = "127.0.0.1"
                enableCors = $true
                enableWebsocket = $true
                messagePostFormat = "array"
                token = ""
                debug = $false
            }
        )
        httpClients = @()
        websocketServers = @(
            @{
                name = "nanobot"
                enable = $true
                host = "127.0.0.1"
                port = $WsPort
                messagePostFormat = "array"
                reportSelfMessage = $false
                enableForcePushEvent = $true
                token = ""
                debug = $false
                heartInterval = 30000
            }
        )
        websocketClients = @()
    }
    musicSignUrl = ""
    enableLocalFile2Url = $false
    parseMultMsg = $true
}

$OneBotConfig | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $ConfigDir "onebot11.json") -Encoding UTF8

# --------------- Copy start scripts ---------------
$ScriptsSrc = Join-Path $RepoRoot "scripts"
@"
@echo off
powershell -File "%~dp0start.ps1" %*
"@ | Set-Content -Path (Join-Path $LocalQQPath "start.bat") -Encoding ASCII

@"
@echo off
powershell -File "%~dp0start-quick.ps1" %*
"@ | Set-Content -Path (Join-Path $LocalQQPath "quick.bat") -Encoding ASCII

# --------------- Done ---------------
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "QQ runtime: $QQDest"
Write-Host "NapCat config: $ConfigDir\onebot11.json"
Write-Host "WebSocket: ws://127.0.0.1:${WsPort}"
Write-Host "WebUI: http://127.0.0.1:${WebUIPort}"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Enable napcat in ~/.nanobot/config.json (see README.md)"
Write-Host "  2. Start: .\localqq\start.bat"
Write-Host "  3. Scan QR to login QQ"
Write-Host "  4. Start gateway: `$env:DND_EMBEDDING_DEVICE='cuda'; nanobot gateway"
