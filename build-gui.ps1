$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$GuiApp = Join-Path $ProjectRoot "src\gui_app.py"
$BuiltAppDir = Join-Path $ProjectRoot "dist\MultiagentStudio"
$BuiltExe = Join-Path $BuiltAppDir "MultiagentStudio.exe"
$BuiltInternal = Join-Path $BuiltAppDir "_internal"
$RootExe = Join-Path $ProjectRoot "MultiagentStudio.exe"
$RootInternal = Join-Path $ProjectRoot "_internal"

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
        --windowed `
        --name MultiagentStudio `
        --paths src `
        --add-data "config;config" `
        $GuiApp

    if (-not (Test-Path $BuiltExe)) {
        Write-Error "Build completed but executable was not found: $BuiltExe"
    }
    if (-not (Test-Path $BuiltInternal)) {
        Write-Error "Build completed but runtime directory was not found: $BuiltInternal"
    }

    Copy-Item -LiteralPath $BuiltExe -Destination $RootExe -Force
    if (Test-Path $RootInternal) {
        Remove-Item -LiteralPath $RootInternal -Recurse -Force
    }
    Copy-Item -LiteralPath $BuiltInternal -Destination $RootInternal -Recurse -Force

    Write-Host "Root executable ready: $RootExe"
}
finally {
    Pop-Location
}
