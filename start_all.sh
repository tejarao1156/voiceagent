#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if port 4002 is already in use
if lsof -Pi :4002 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 4002 is already in use. Stopping existing processes..."
    lsof -ti :4002 | xargs kill -9 2>/dev/null || true
    ps aux | grep -E "(python.*main.py|uvicorn)" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "✅ Port freed"
fi

cleanup() {
  echo ""
  echo "Shutting down services..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${UI_PID:-}" ]] && kill "$UI_PID" 2>/dev/null || true
  [[ -n "${API_PID:-}" ]] && wait "$API_PID" 2>/dev/null || true
  [[ -n "${UI_PID:-}" ]] && wait "$UI_PID" 2>/dev/null || true
  echo "All services stopped."
}

trap cleanup INT TERM EXIT

echo "🚀 Starting Voice Agent..."
echo ""

# Start the main API server (includes all UIs on one port)
echo "Starting Voice Agent API server (FastAPI)..."
python "$SCRIPT_DIR/main.py" &
API_PID=$!

# Wait a moment to check if server started successfully
sleep 3
if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "❌ Server failed to start. Check logs for errors."
    exit 1
fi

# Optional: Start Next.js UI if you want it (comment out if not needed)
# echo "Starting Voice Agent UI (Next.js)..."
# cd "$SCRIPT_DIR/ui"
# if [[ ! -d node_modules ]]; then
#   echo "Installing UI dependencies..."
#   npm install
# fi
# npm run dev &
# UI_PID=$!

echo ""
echo "✅ Voice Agent is running!"
echo ""
echo "📋 Available endpoints:"
echo "   🏠 Landing Page:  http://localhost:4002/"
echo "   🎧 Chat UI:      http://localhost:4002/chat"
echo "   📞 Dashboard:     http://localhost:4002/dashboard"
echo "   📚 API Docs:      http://localhost:4002/docs"
echo ""
echo "Press Ctrl+C to stop all services."
wait "$API_PID"

