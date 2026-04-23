@echo off
setlocal enabledelayedexpansion

REM =========================================================
REM MD Parser - Windows 원클릭 실행 스크립트
REM   - venv 자동 생성
REM   - requirements 자동 설치 (해시 변경 시 재설치)
REM   - .env.example 복사 (.env 없을 때)
REM   - 브라우저 자동 열기
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
        echo [ERROR] Python 3.10 이상이 필요합니다. https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if not exist ".venv" (
    echo [setup] 가상환경 생성 중...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv 생성 실패
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
    echo [setup] 의존성 설치 중... ^(markitdown[all] 포함, 수 분 소요^)
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 의존성 설치 실패
        pause
        exit /b 1
    )
    echo. > "%STAMP%"
)

if not exist ".env" (
    echo [setup] .env 생성 ^(.env.example 복사^) — Fabrix 키를 입력하고 재실행하세요.
    copy /y ".env.example" ".env" >nul
)

set "PORT=8000"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="PORT" set "PORT=%%B"
)

echo.
echo ============================================================
echo  MD Parser 시작: http://localhost:%PORT%
echo  (종료하려면 이 창에서 Ctrl+C)
echo ============================================================
echo.

start "" http://localhost:%PORT%/

python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

endlocal
