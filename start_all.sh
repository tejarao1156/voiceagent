#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
  echo ""
  echo "Shutting down services..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${UI_PID:-}" ]] && kill "$UI_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$UI_PID" 2>/dev/null || true
  echo "All services stopped."
}

trap cleanup INT TERM EXIT

echo "🚀 Starting Voice Agent..."
echo ""

# Start the main API server (includes all UIs on one port)
echo "Starting Voice Agent API server (FastAPI)..."
python "$SCRIPT_DIR/main.py" &
API_PID=$!

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

