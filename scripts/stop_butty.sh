#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8001}"

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
    
  else
    echo "✅ Port $PORT is free"
  fi
else
  echo "⚠️  lsof not available; skipping port check"
fi