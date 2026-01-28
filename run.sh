#!/bin/bash
# Vibe Web Terminal - Run Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "Setup not complete. Running setup first..."
    ./setup.sh
fi

echo ""
echo "============================================"
echo "  Vibe Web Terminal"
echo "============================================"
echo ""
echo "Server starting on: http://127.0.0.1:8081"
echo ""
echo "SECURITY: Bound to localhost only (127.0.0.1)"
echo "          NOT accessible from the network/internet"
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
