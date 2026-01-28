#!/bin/bash
# Stop the Vibe Terminal server and proxy (does NOT remove containers or data).
# To fully clean up containers and workspaces, use: ./cleanup-sessions.sh

echo "Stopping Vibe Terminal server and proxy..."
pkill -f "python3.*server/app.py" 2>/dev/null || true
pkill -f "python3.*reverse_proxy.py" 2>/dev/null || true

echo "Done. Containers are still running (persistent by design)."
echo "To remove all session containers and data: ./cleanup-sessions.sh"
