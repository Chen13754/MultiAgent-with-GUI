param(
    [switch]$Wait
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Executable = Join-Path $ProjectRoot "dist\MultiagentStudio\MultiagentStudio.exe"
$BuildInfo = Join-Path $ProjectRoot "dist\MultiagentStudio\build-info.json"

if (-not (Test-Path -LiteralPath $Executable)) {
    throw "找不到当前桌面包：$Executable。请先运行 .\build-gui.ps1。"
}

if (Test-Path -LiteralPath $BuildInfo) {
    $info = Get-Content -Raw -Encoding utf8 $BuildInfo | ConvertFrom-Json
    Write-Host ("启动 Multiagent Studio v{0} ({1})" -f $info.version, $info.commit)
}

$process = Start-Process -FilePath $Executable -WorkingDirectory (Split-Path $Executable) -PassThru
if ($Wait) {
    $process.WaitForExit()
    exit $process.ExitCode
}
