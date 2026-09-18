Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$TmpDir = Join-Path $ProjectRoot (".tmp\dev_up\" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$BackendPidFile = Join-Path $TmpDir "backend.pid"
$FrontendPidFile = Join-Path $TmpDir "frontend.pid"
$BackendLog = Join-Path $TmpDir "backend.log"
$FrontendLog = Join-Path $TmpDir "frontend.log"
$BackendErrorLog = Join-Path $TmpDir "backend.error.log"
$FrontendErrorLog = Join-Path $TmpDir "frontend.error.log"

function Log($Message) {
    Write-Host "[dev_up] $Message"
}

function Assert-PortsFree {
    $connections = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object { $_.LocalPort -in 8000,5276 } |
        Where-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue })
    if ($connections.Count -gt 0) {
        $connections | Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table | Out-Host
        throw "[dev_up] Required ports are occupied. No processes were stopped. Review the listed processes before retrying."
    }
}

function Test-HttpReady($Url) {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Import-DotEnv($Path) {
    if (-not (Test-Path $Path)) {
        return
    }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            if ($key -match '^(SMTP_|EMAIL_DELIVERY_MODE$)' -or -not [Environment]::GetEnvironmentVariable($key, "Process")) {
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
}

New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

Log "checking required ports"
Assert-PortsFree
Log "ports available; logs: $TmpDir"

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "[dev_up] missing .venv. Run: powershell -ExecutionPolicy Bypass -File scripts\reset_env.ps1"
}

$pythonVersion = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "[dev_up] Python version must be >= 3.10. Found: $pythonVersion"
}
Log "Python version OK: $pythonVersion"

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    throw "[dev_up] node was not found in PATH. Install Node.js and npm first."
}
Log "Node version: $(& $node.Source --version)"

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "[dev_up] npm was not found in PATH. Install Node.js with npm first."
}
Log "npm version: $(& $npm.Source --version)"

$redisCli = @(
    (Get-Command redis-cli -ErrorAction SilentlyContinue)
    (Get-Command memurai-cli -ErrorAction SilentlyContinue)
) | Where-Object { $_ } | Select-Object -First 1
$redisServer = @(
    (Get-Command redis-server -ErrorAction SilentlyContinue)
    (Get-Command memurai -ErrorAction SilentlyContinue)
    (Get-Command memurai.exe -ErrorAction SilentlyContinue)
) | Where-Object { $_ } | Select-Object -First 1

function Test-RedisReady {
    if ($redisCli) {
        & $redisCli.Source ping 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    }
    try {
        $redisCheck = & $venvPython -c "from redis import Redis; print('PONG' if Redis(host='localhost', port=6379, db=0, socket_connect_timeout=1).ping() else '');" 2>$null
        return $LASTEXITCODE -eq 0 -and $redisCheck -contains "PONG"
    }
    catch {
        return $false
    }
}

if (-not (Test-RedisReady)) {
    if (-not $redisServer) {
        throw "[dev_up] Redis/Memurai is not responding on localhost:6379. Install Memurai or start a compatible Redis service, then rerun this script."
    }
    Log "starting Redis-compatible server"
    Start-Process -FilePath $redisServer.Source -WindowStyle Hidden
    Start-Sleep -Seconds 1
}

if (-not (Test-RedisReady)) {
    throw "[dev_up] Redis is not responding on localhost:6379"
}
Log "Redis OK"

Set-Location $ProjectRoot
$pipCommonArgs = @("--disable-pip-version-check", "--progress-bar", "off", "--timeout", "30")
if (-not $env:PIP_INDEX_URL) {
    $pipCommonArgs += @("-i", "https://pypi.tuna.tsinghua.edu.cn/simple")
}

& $venvPython -m pip install --upgrade pip @pipCommonArgs
if ($LASTEXITCODE -ne 0) {
    throw "[dev_up] pip upgrade failed"
}

& $venvPython -m pip install -r requirements.txt @pipCommonArgs
if ($LASTEXITCODE -ne 0) {
    throw "[dev_up] Python dependency installation failed"
}

Import-DotEnv (Join-Path $ProjectRoot ".env")
Import-DotEnv (Join-Path $ProjectRoot ".env.test")

$env:PYTHONPATH = "$ProjectRoot"
$env:ENV = "dev"
$env:DB_URL = "sqlite+aiosqlite:///$(($ProjectRoot.Path -replace '\\','/'))/agentforge_preview.db"
$env:REDIS_URL = "redis://localhost:6379/1"
$env:OPENROUTER_BASE_URL = if ($env:OPENROUTER_BASE_URL) { $env:OPENROUTER_BASE_URL } else { "https://openrouter.ai/api/v1" }
$env:OPENROUTER_MODEL = if ($env:OPENROUTER_MODEL) { $env:OPENROUTER_MODEL } else { "openai/gpt-4o-mini" }
$env:EMAIL_DELIVERY_MODE = if ($env:EMAIL_DELIVERY_MODE) { $env:EMAIL_DELIVERY_MODE } else { "smtp" }
$env:AUTH_DEV_BYPASS_ENABLED = if ($env:AUTH_DEV_BYPASS_ENABLED) { $env:AUTH_DEV_BYPASS_ENABLED } else { "false" }

if (-not $env:OPENROUTER_API_KEY) {
    $env:OPENROUTER_API_KEY = $env:MODEL_API_KEY
}
if (-not $env:OPENROUTER_API_KEY) {
    throw "[dev_up] missing OPENROUTER_API_KEY or MODEL_API_KEY. Set it in the current PowerShell session or create a project .env file."
}
$env:MODEL_API_KEY = if ($env:MODEL_API_KEY) { $env:MODEL_API_KEY } else { $env:OPENROUTER_API_KEY }
$env:MODEL_BASE_URL = if ($env:MODEL_BASE_URL) { $env:MODEL_BASE_URL } else { $env:OPENROUTER_BASE_URL }

Log "starting backend"
$backend = Start-Process -FilePath $venvPython -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload") -WorkingDirectory $ProjectRoot -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrorLog -PassThru -WindowStyle Hidden
$backend.Id | Set-Content $BackendPidFile

$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-HttpReady "http://127.0.0.1:8000/health") {
        $backendReady = $true
        break
    }
    if ($backend.HasExited) {
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $backendReady) {
    Log "See backend.log and backend.error.log in $TmpDir"
    throw "[dev_up] backend failed to start on port 8000"
}

Log "starting frontend"
$frontendDir = Join-Path $ProjectRoot "frontend"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Log "node_modules missing, running npm install"
    & $npm.Source install --prefix $frontendDir --cache (Join-Path $TmpDir "npm-cache")
    if ($LASTEXITCODE -ne 0) {
        throw "[dev_up] npm install failed"
    }
}

$frontendCommand = '""{0}" run dev -- --port 5276 --strictPort"' -f $npm.Source
$frontend = Start-Process -FilePath $env:ComSpec -ArgumentList @('/d', '/s', '/c', $frontendCommand) -WorkingDirectory $frontendDir -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrorLog -PassThru -WindowStyle Hidden
$frontend.Id | Set-Content $FrontendPidFile

$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($frontend.HasExited -or $backend.HasExited) { break }
    if (Test-HttpReady "http://127.0.0.1:5276") {
        $frontendReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $frontendReady) {
    throw "[dev_up] Frontend did not become ready. Logs preserved in $TmpDir; backend may still be running."
}

Log "services up: backend=http://127.0.0.1:8000 frontend=http://127.0.0.1:5276"
Log "logs: $TmpDir"
Log "process IDs: backend=$($backend.Id) frontend launcher=$($frontend.Id)"

while ($true) {
    if ($backend.HasExited) {
        Log "See backend.log and backend.error.log in $TmpDir"
        throw "[dev_up] backend process exited"
    }
    if ($frontend.HasExited) {
        Log "See frontend.log and frontend.error.log in $TmpDir"
        throw "[dev_up] frontend process exited"
    }
    Start-Sleep -Seconds 1
}
