$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$GuiApp = Join-Path $ProjectRoot "src\web_gui_app.py"

if (-not (Test-Path $Python)) {
    Write-Error "Project venv Python not found: $Python. Please install dependencies first."
}

$env:PYTHONIOENCODING = "utf-8"
chcp 65001 > $null

Push-Location $ProjectRoot
try {
    & $Python $GuiApp
}
finally {
    Pop-Location
}
