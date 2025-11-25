#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# --- Graceful Cleanup ---
cleanup() {
  echo ""
  echo "🔌 Shutting down services..."
  # Use pkill to find processes by name, which is more robust
  pkill -f "ngrok http 4002" || true
  pkill -f "python.*main.py" || true
  pkill -f "uvicorn.*main:app" || true
  pkill -f "node.*server.js" || true
  pkill -f "next.*dev" || true
  echo "✅ All services stopped."
}

trap cleanup INT TERM EXIT

# --- Pre-run Check & Cleanup ---
echo "🔍 Checking for existing services..."
# Terminate any running instances before starting new ones to prevent port conflicts.
pkill -f "ngrok http 4002" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
pkill -f "next.*dev" 2>/dev/null || true
sleep 1
echo "🧹 Clean slate ready."


echo "🚀 Starting Voice Agent..."
echo ""

# --- Start the main API server ---
echo "Starting Voice Agent API server (FastAPI)..."
python "$PROJECT_ROOT/main.py" &
API_PID=$!

# Wait a moment and check if the server started successfully
sleep 3
if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "❌ Server failed to start. Check logs for errors."
    exit 1
fi
echo "✅ API Server is running."

# --- Start Next.js UI ---
echo "Starting Voice Agent UI (Next.js)..."
cd "$PROJECT_ROOT/ui"
if [[ ! -d node_modules ]]; then
  echo "Installing UI dependencies..."
  npm install
fi
npm run dev &
UI_PID=$!
sleep 2
if ! kill -0 "$UI_PID" 2>/dev/null; then
    echo "⚠️ UI server may have failed to start. Check logs for errors."
else
    echo "✅ UI Server is running internally (proxied through port 4002)"
fi
cd "$PROJECT_ROOT"

echo ""
echo "✅ Voice Agent startup complete!"
echo ""
echo "🌐 Access your services:"
echo "   - API & Dashboard: http://localhost:4002"
echo "   - Demo UI: http://localhost:4002/demo"
echo "   - SaaS Dashboard: http://localhost:4002/saas-dashboard"
echo "   - API Docs: http://localhost:4002/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive to hold the trap and background jobs
wait "$API_PID" "$UI_PID" 2>/dev/null || wait "$API_PID"

