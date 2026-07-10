$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Project venv Python not found: $Python. Please install dependencies first."
}

$env:PYTHONNOUSERSITE = "1"
$env:PYTHONUSERBASE = Join-Path $ProjectRoot ".cache\python-userbase"
$env:PYINSTALLER_CONFIG_DIR = Join-Path $ProjectRoot ".cache\pyinstaller"
$env:PNPM_STORE_DIR = Join-Path $ProjectRoot ".cache\pnpm-store"

Push-Location $ProjectRoot
try {
    & $Python -s .\scripts\build_gui.py
}
finally {
    Pop-Location
}
