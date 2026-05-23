$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$GuiApp = Join-Path $ProjectRoot "src\gui_app.py"

if (-not (Test-Path $Python)) {
    Write-Error "Project venv Python not found: $Python. Please install dependencies first."
}

Push-Location $ProjectRoot
try {
    $env:PYTHONNOUSERSITE = "1"
    $env:PYTHONUSERBASE = Join-Path $ProjectRoot ".cache\python-userbase"
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $ProjectRoot ".cache\pyinstaller"
    New-Item -ItemType Directory -Force -Path $env:PYTHONUSERBASE | Out-Null

    & $Python -s -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name MultiagentStudio `
        --paths src `
        --add-data "config;config" `
        $GuiApp
}
finally {
    Pop-Location
}
