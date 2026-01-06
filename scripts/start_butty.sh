#!/usr/bin/env bash
set -euo pipefail

# -----------------------
# Config (portable)
# -----------------------
APP_NAME="butty"
PORT="${PORT:-8001}"


# Resolve project root (script lives in ./scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKDIR="${WORKDIR:-$PROJECT_ROOT}"

PYTHON="$WORKDIR/.venv/bin/python"

# Cross-platform application data dir
if [[ "$OSTYPE" == "darwin"* ]]; then
  APP_DATA_DIR="$HOME/Library/Application Support/$APP_NAME"
else
  APP_DATA_DIR="$HOME/.local/share/$APP_NAME"
fi

# Mock mode toggle (TEST_MODE=1)
TEST_MODE="${TEST_MODE:-0}"

if [[ "$TEST_MODE" == "1" ]]; then
  DB_NAME="dbtemp.sqlite"
else
  DB_NAME="db.sqlite"
fi

DB_PATH="$APP_DATA_DIR/$DB_NAME"
LOGFILE="$APP_DATA_DIR/logs/web.log"

# -----------------------
# Python environment bootstrap
# -----------------------
echo "🔍 Preflight checks..."

if [[ ! -x "$PYTHON" ]]; then
  echo "🐍 Virtualenv not found. Bootstrapping..."

  if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found on PATH"
    exit 1
  fi

  python3 -m venv "$WORKDIR/.venv"
  # shellcheck disable=SC1091
  source "$WORKDIR/.venv/bin/activate"

  python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1

  if [[ -f "$WORKDIR/pyproject.toml" ]]; then
    echo "📦 Installing dependencies from pyproject.toml"
    pip install . >/dev/null 2>&1
  else
    echo "❌ pyproject.toml not found"
    exit 1
  fi

  deactivate
else
  echo "✅ Virtualenv found"
fi

mkdir -p "$APP_DATA_DIR"
mkdir -p "$(dirname "$LOGFILE")"

# -----------------------
# Port cleanup (best-effort)
# -----------------------
echo "🔍 Checking for process using port $PORT..."

if command -v lsof >/dev/null 2>&1; then
  PORT_PIDS="$(lsof -ti tcp:"$PORT" || true)"
  if [[ -n "$PORT_PIDS" ]]; then
    echo "🛑 Killing process(es) on port $PORT:"
    echo "$PORT_PIDS"

    # Kill each PID individually
    for pid in $PORT_PIDS; do
      kill "$pid" 2>/dev/null || true
    done

    sleep 1
  else
    echo "✅ Port $PORT is free"
  fi
else
  echo "⚠️  lsof not available; skipping port check"
fi

# -----------------------
# Start server
# -----------------------
echo "🚀 Starting $APP_NAME..."
cd "$WORKDIR"

export BUTTY_DB_PATH="$DB_PATH"
export BUTTY_PORT="$PORT"
export BUTTY_TEST_MODE="$TEST_MODE"

nohup "$PYTHON" -m apps.web.main \
  > "$LOGFILE" 2>&1 &

echo "✅ $APP_NAME started"
echo "   PID:  $!"
echo "   Port: $PORT"
echo "   Mode: $([[ "$TEST_MODE" == "1" ]] && echo "TEST" || echo "NORMAL")"
echo "   DB:   $DB_PATH"
echo "   Logs: $LOGFILE"