#!/usr/bin/env bash
set -e

# Ensure user-local tools (uv, npm/node) are on PATH
export PATH="$HOME/.local/bin:$PATH"

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$REPO_DIR/frontend"
DIST_DIR="$FRONTEND_DIR/dist"
PUBLIC_DIR="$FRONTEND_DIR/public"

# Generate favicon from the committed logo if not already present
if [ ! -f "$PUBLIC_DIR/favicon.ico" ] && [ -f "$PUBLIC_DIR/LensLoop.png" ] && command -v convert &>/dev/null; then
  convert "$PUBLIC_DIR/LensLoop.png" -resize 32x32 "$PUBLIC_DIR/favicon.ico" 2>/dev/null || true
fi

# Build React if dist is missing or package.json is newer
if [ ! -d "$DIST_DIR" ] \
   || [ "$FRONTEND_DIR/package.json" -nt "$DIST_DIR" ]; then
  echo "[start.sh] Building frontend…"
  cd "$FRONTEND_DIR"
  npm ci --silent
  npm run build --silent
  cd "$REPO_DIR"
fi

echo "[start.sh] Starting LensLoop on port ${PORT:-8000}…"
cd "$REPO_DIR"
exec uv run uvicorn backend.main:app \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}" \
  --log-level "${LOG_LEVEL:-info}"
