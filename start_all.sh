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
  pkill -f "python3.*main.py" || true
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
pkill -f "python3.*main.py" 2>/dev/null || true
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
pkill -f "next.*dev" 2>/dev/null || true
sleep 1
echo "🧹 Clean slate ready."


echo "🚀 Starting Voice Agent..."
echo ""

# --- Clean pycache to ensure fresh code ---
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# --- Start the main API server ---
echo "Starting Voice Agent API server (FastAPI)..."
python3 "$SCRIPT_DIR/main.py" &
API_PID=$!

# Wait a moment and check if the server started successfully
sleep 3
if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "❌ Server failed to start. Check logs for errors."
    exit 1
fi
echo "✅ API Server is running."

# --- Start ngrok (Optional but requested) ---
echo "Starting ngrok..."
NGROK_CMD=""
if [ -f "$SCRIPT_DIR/bin/ngrok" ]; then
    NGROK_CMD="$SCRIPT_DIR/bin/ngrok"
elif command -v ngrok >/dev/null 2>&1; then
    NGROK_CMD="ngrok"
fi

if [ -n "$NGROK_CMD" ]; then
    $NGROK_CMD http 4002 > /dev/null &
    NGROK_PID=$!
    echo "✅ ngrok started on port 4002 (PID: $NGROK_PID)"
else
    echo "⚠️ ngrok not found. Skipping ngrok start."
    echo "   Run ./setup_ngrok.sh to install it if needed."
fi

# --- Start Next.js UI ---
echo "Starting Voice Agent UI (Next.js)..."
cd "$SCRIPT_DIR/ui"
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
cd "$SCRIPT_DIR"

echo ""
echo "✅ Voice Agent startup complete!"
echo ""
echo "🌐 Access your services:"
echo "   - Dashboard: http://localhost:4002"
echo "   - API Docs: http://localhost:4002/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive to hold the trap and background jobs
wait "$API_PID" "$UI_PID" 2>/dev/null || wait "$API_PID"
