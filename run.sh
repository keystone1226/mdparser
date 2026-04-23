#!/usr/bin/env bash
# MD Parser - macOS / Linux 실행 스크립트 (개발/대체용)
set -euo pipefail

cd "$(dirname "$0")"

PY_BIN="${PYTHON:-python3}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
    echo "[ERROR] Python 3.10+이 필요합니다." >&2
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[setup] 가상환경 생성 중..."
    "$PY_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

STAMP=".venv/.requirements.stamp"
if [ ! -f "$STAMP" ] || [ "requirements.txt" -nt "$STAMP" ]; then
    echo "[setup] 의존성 설치 중... (markitdown[all] 포함, 수 분 소요)"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    touch "$STAMP"
fi

if [ ! -f ".env" ]; then
    echo "[setup] .env 생성 (.env.example 복사) — Fabrix 키를 입력하고 재실행하세요."
    cp .env.example .env
fi

PORT="$(grep -E '^PORT=' .env | tail -n1 | cut -d= -f2 | tr -d '\r' || true)"
PORT="${PORT:-8000}"
HOST_BIND="$(grep -E '^HOST=' .env | tail -n1 | cut -d= -f2 | tr -d '\r' || true)"
HOST_BIND="${HOST_BIND:-0.0.0.0}"

URL="http://localhost:${PORT}/"
echo ""
echo "============================================================"
echo " MD Parser 시작: $URL"
echo " (종료하려면 Ctrl+C)"
echo "============================================================"
echo ""

( sleep 1.2
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true
  fi ) &

exec python -m uvicorn app.main:app --host "$HOST_BIND" --port "$PORT"
