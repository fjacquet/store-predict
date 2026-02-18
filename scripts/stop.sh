#!/usr/bin/env bash
# Stop StorePredict background process
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.store-predict.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. StorePredict is not running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping StorePredict (PID $PID)..."
    kill "$PID"
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$PID"
    fi
    echo "Stopped."
else
    echo "Process $PID not running (stale PID file)."
fi

rm -f "$PID_FILE"
