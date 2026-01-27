#!/bin/bash
# Vibe Web Terminal - Run Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "Setup not complete. Running setup first..."
    ./setup.sh
fi

# Get the local IP for display
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "============================================"
echo "  Vibe Web Terminal"
echo "============================================"
echo ""
echo "Server starting on:"
echo "  - Local:   http://localhost:8080"
echo "  - Network: http://${LOCAL_IP}:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with docker group permissions if not already in docker group
if groups | grep -q docker; then
    "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/server/app.py"
else
    echo "Note: Running with 'sg docker' for Docker socket access"
    sg docker -c "$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/server/app.py"
fi
