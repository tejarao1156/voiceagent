#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Graceful Cleanup ---
cleanup() {
  echo ""
  echo "🔌 Shutting down services..."
  # Use pkill to find processes by name, which is more robust
  pkill -f "ngrok http 4002" || true
  pkill -f "python.*main.py" || true
  pkill -f "uvicorn.*main:app" || true
  echo "✅ All services stopped."
}

trap cleanup INT TERM EXIT

# --- Pre-run Check & Cleanup ---
echo "🔍 Checking for existing services..."
# Terminate any running instances before starting new ones to prevent port conflicts.
pkill -f "ngrok http 4002" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "uvicorn.*main:app" 2>/dev/null || true
sleep 1
echo "🧹 Clean slate ready."


echo "🚀 Starting Voice Agent..."
echo ""

# --- Start the main API server ---
echo "Starting Voice Agent API server (FastAPI)..."
python "$SCRIPT_DIR/main.py" &
API_PID=$!

# Wait a moment and check if the server started successfully
sleep 3
if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "❌ Server failed to start. Check logs for errors."
    exit 1
fi
echo "✅ API Server is running."

# --- Optional: Start Next.js UI (uncomment if needed) ---
# echo "Starting Voice Agent UI (Next.js)..."
# cd "$SCRIPT_DIR/ui"
# if [[ ! -d node_modules ]]; then
#   echo "Installing UI dependencies..."
#   npm install
# fi
# npm run dev &
# UI_PID=$!

echo ""
echo "✅ Voice Agent startup complete!"
echo "   Waiting for user to trigger ngrok or other tasks."
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive to hold the trap and background jobs
wait "$API_PID"

