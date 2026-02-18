#!/usr/bin/env bash
# Start StorePredict in the background
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.store-predict.pid"
LOG_FILE="$PROJECT_DIR/.store-predict.log"
PORT="${PORT:-8080}"

cd "$PROJECT_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "StorePredict is already running (PID $(cat "$PID_FILE"))"
    exit 0
fi

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "Starting StorePredict on port $PORT..."
nohup python -m store_predict.main > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

sleep 2
if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "StorePredict started (PID $(cat "$PID_FILE"), port $PORT)"
    echo "Logs: $LOG_FILE"
else
    echo "Failed to start. Check $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
