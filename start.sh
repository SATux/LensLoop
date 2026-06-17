#!/usr/bin/env bash
set -e

# Ensure user-local tools (uv, npm/node) are on PATH
export PATH="$HOME/.local/bin:$PATH"

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$REPO_DIR/frontend"
DIST_DIR="$FRONTEND_DIR/dist"
PUBLIC_DIR="$FRONTEND_DIR/public"

# Copy logo and generate favicon if not already done
mkdir -p "$PUBLIC_DIR"
if [ -f "$REPO_DIR/LensLoop.png" ]; then
  cp -f "$REPO_DIR/LensLoop.png" "$PUBLIC_DIR/LensLoop.png"
  if [ ! -f "$PUBLIC_DIR/favicon.ico" ] && command -v convert &>/dev/null; then
    convert "$REPO_DIR/LensLoop.png" -resize 32x32 "$PUBLIC_DIR/favicon.ico" 2>/dev/null || true
  fi
fi

# Build React if dist is missing, package.json is newer, or public assets changed
if [ ! -d "$DIST_DIR" ] \
   || [ "$FRONTEND_DIR/package.json" -nt "$DIST_DIR" ] \
   || [ "$PUBLIC_DIR/LensLoop.png" -nt "$DIST_DIR" ]; then
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
