@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM =========================================================
REM MD Parser - Windows one-click launcher
REM   - auto-create venv
REM   - auto-install requirements (re-run when requirements.txt changes)
REM   - copy .env.example to .env if missing
REM   - open browser
REM =========================================================

cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo [ERROR] Python 3.10+ is required. Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if not exist ".venv" (
    echo [setup] Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

set "STAMP=.venv\.requirements.stamp"
set "NEEDS_INSTALL=0"
if not exist "%STAMP%" set "NEEDS_INSTALL=1"
if exist "%STAMP%" (
    for %%A in (requirements.txt) do set "REQ_TIME=%%~tA"
    for %%A in (%STAMP%) do set "STAMP_TIME=%%~tA"
    if "!REQ_TIME!" gtr "!STAMP_TIME!" set "NEEDS_INSTALL=1"
)

if "%NEEDS_INSTALL%"=="1" (
    echo [setup] Installing dependencies ^(markitdown[all] included, may take several minutes^)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
    echo. > "%STAMP%"
)

if not exist ".env" (
    echo [setup] Created .env from .env.example. Fill in Fabrix keys and re-run for LLM features.
    copy /y ".env.example" ".env" >nul
)

set "PORT=8000"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="PORT" set "PORT=%%B"
)

echo.
echo ============================================================
echo  MD Parser running at: http://localhost:%PORT%
echo  (Press Ctrl+C in this window to stop)
echo ============================================================
echo.

start "" http://localhost:%PORT%/

python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

endlocal
