#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
  echo "Shutting down services..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${UI_PID:-}" ]] && kill "$UI_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$UI_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting Voice Agent API..."
"$SCRIPT_DIR/start_api.sh" &
API_PID=$!

echo "Starting Voice Agent UI..."
"$SCRIPT_DIR/start_ui.sh" &
UI_PID=$!

echo "Servers are running. Press Ctrl+C to stop."
wait "$API_PID"
wait "$UI_PID"

