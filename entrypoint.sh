#!/bin/bash
set -e

echo "[travel-app] Running database migrations..."
cd /app/backend
alembic upgrade head

echo "[travel-app] Starting FastAPI backend on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "[travel-app] Starting Next.js frontend on port 3000..."
cd /app/frontend
export PORT=${PORT:-3000}
export HOSTNAME=${HOSTNAME:-0.0.0.0}
export NODE_ENV=production
export BACKEND_URL=${BACKEND_URL:-http://127.0.0.1:8000}
node server.js &
FRONTEND_PID=$!

terminate() {
  echo "[travel-app] Received shutdown signal. Stopping services..."
  kill -TERM "$BACKEND_PID" 2>/dev/null || true
  kill -TERM "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}

trap terminate SIGTERM SIGINT SIGHUP

wait -n "$BACKEND_PID" "$FRONTEND_PID"
EXIT_CODE=$?
echo "[travel-app] A service stopped unexpectedly (exit code: $EXIT_CODE). Terminating remaining processes..."
terminate
