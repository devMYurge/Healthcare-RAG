#!/usr/bin/env bash
set -euo pipefail

# Non-interactive development start script
# Creates ./.venv, installs Python deps, starts backend and frontend in background

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PIDS_FILE="$ROOT_DIR/.pids"

echo "Using project root: $ROOT_DIR"

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo "Creating virtualenv at ./.venv"
  python3 -m venv ./.venv
fi

echo "Activating virtualenv"
# shellcheck disable=SC1091
source ./.venv/bin/activate

echo "Installing Python dependencies (requirements.txt)"
pip install --upgrade pip
pip install -r requirements.txt

# Start backend
echo "Starting backend (uvicorn)"
./.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "backend:$BACKEND_PID" >> "$PIDS_FILE"

# Start frontend
echo "Starting frontend (Vite)"
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "frontend:$FRONTEND_PID" >> "$PIDS_FILE"

cd "$ROOT_DIR"

echo "Started backend (pid $BACKEND_PID) and frontend (pid $FRONTEND_PID)"
echo "PIDs written to $PIDS_FILE"
echo "To stop run: make stop" 

trap 'echo "Stopping services..."; if [ -f "$PIDS_FILE" ]; then cat "$PIDS_FILE" | cut -d: -f2 | xargs -r kill; rm -f "$PIDS_FILE"; fi; exit' INT TERM

# Wait for child processes to exit
wait
