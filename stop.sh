#!/bin/bash
# Stop the Vibe Terminal server and proxy (does NOT remove containers or data).
# To fully clean up containers and workspaces, use: ./cleanup-sessions.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

stopped=0

# Kill server (matches both venv/bin/python and python3)
pids=$(pgrep -f "python.*server/app\.py" 2>/dev/null)
if [ -n "$pids" ]; then
    echo "Stopping server (PID: $pids)..."
    kill $pids 2>/dev/null
    stopped=$((stopped + 1))
fi

# Kill reverse proxy
pids=$(pgrep -f "python.*reverse_proxy\.py" 2>/dev/null)
if [ -n "$pids" ]; then
    echo "Stopping reverse proxy (PID: $pids)..."
    kill $pids 2>/dev/null
    stopped=$((stopped + 1))
fi

if [ $stopped -eq 0 ]; then
    echo "Nothing to stop — no server or proxy processes found."
else
    # Wait briefly and verify
    sleep 1
    remaining=$(pgrep -f "python.*(server/app|reverse_proxy)\.py" 2>/dev/null)
    if [ -n "$remaining" ]; then
        echo "Processes didn't stop gracefully, sending SIGKILL..."
        kill -9 $remaining 2>/dev/null
    fi
    echo "Stopped. Containers are still running (persistent by design)."
    echo "To remove all session containers and data: ./cleanup-sessions.sh"
fi
