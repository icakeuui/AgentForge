Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "[reset_env] project root: $ProjectRoot"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "[reset_env] python was not found in PATH. Install Python 3.10+ and enable 'Add python.exe to PATH'."
}

$versionOutput = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "[reset_env] Python version must be >= 3.10. Found: $versionOutput"
}
Write-Host "[reset_env] Python version OK: $versionOutput"

$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "[reset_env] removing existing .venv"
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

Write-Host "[reset_env] creating .venv"
& $python.Source -m venv .venv
if ($LASTEXITCODE -ne 0) {
    throw "[reset_env] failed to create .venv"
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "[reset_env] expected venv python not found at $venvPython"
}

& $venvPython -V
Write-Host "[reset_env] upgrading pip"
$pipCommonArgs = @("--disable-pip-version-check", "--progress-bar", "off", "--timeout", "30")
if (-not $env:PIP_INDEX_URL) {
    $pipCommonArgs += @("-i", "https://pypi.tuna.tsinghua.edu.cn/simple")
}

& $venvPython -m pip install --upgrade pip @pipCommonArgs
if ($LASTEXITCODE -ne 0) {
    throw "[reset_env] pip upgrade failed"
}

Write-Host "[reset_env] installing backend requirements"
& $venvPython -m pip install -r requirements.txt @pipCommonArgs
if ($LASTEXITCODE -ne 0) {
    throw "[reset_env] Python dependency installation failed"
}

Write-Host "[reset_env] done"
