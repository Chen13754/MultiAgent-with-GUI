@echo off
setlocal

cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"

set "EXE=%CD%\dist\MultiagentStudio\MultiagentStudio.exe"
set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "GUI_APP=%CD%\src\gui_app.py"
set "SMOKE_ARG="
set "MULTIAGENT_PROJECT_ROOT=%CD%"
set "MULTIAGENT_ENV_FILE=%CD%\.env"

if "%MULTIAGENT_GUI_SMOKE%"=="1" set "SMOKE_ARG=--smoke-test"

if not exist "%CD%\.env" (
    echo [ERROR] .env not found.
    echo Run: Copy-Item .env.template .env
    echo Then fill DEEPSEEK_API_KEY before running the GUI.
    pause
    exit /b 1
)

if exist "%EXE%" (
    echo Starting Multiagent Studio executable...
    "%EXE%" %SMOKE_ARG%
    exit /b %ERRORLEVEL%
)

if not exist "%PYTHON%" (
    echo [ERROR] Project venv Python not found:
    echo %PYTHON%
    echo Please install dependencies into .venv first.
    pause
    exit /b 1
)

if not exist "%GUI_APP%" (
    echo [ERROR] GUI entry not found:
    echo %GUI_APP%
    pause
    exit /b 1
)

echo Starting Multiagent Studio from source...
"%PYTHON%" "%GUI_APP%" %SMOKE_ARG%
exit /b %ERRORLEVEL%
