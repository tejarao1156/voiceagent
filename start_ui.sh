#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_DIR="$SCRIPT_DIR/ui"

cd "$UI_DIR"

if [[ ! -d node_modules ]]; then
  echo "Installing UI dependencies..."
  npm install
fi

echo "Starting Voice Agent UI (Next.js)..."
exec npm run dev

