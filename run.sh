#!/bin/bash
# Vibe Web Terminal - Run Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "Setup not complete. Running setup first..."
    ./setup.sh
fi

# Stop any already-running instances
"$SCRIPT_DIR/stop.sh" 2>/dev/null

PYTHON="$SCRIPT_DIR/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON=python3
fi

run_python() {
    if groups | grep -q docker; then
        "$PYTHON" "$@"
    else
        sg docker -c "\"$PYTHON\" $*"
    fi
}

# Ensure valid SSL certificates exist (auto-generate or renew)
CERT="$SCRIPT_DIR/certs/self-signed/fullchain.pem"
KEY="$SCRIPT_DIR/certs/self-signed/privkey.pem"
generate_cert() {
    mkdir -p "$SCRIPT_DIR/certs/self-signed"
    CN=$(curl -4 -s --connect-timeout 3 ifconfig.me 2>/dev/null || echo "localhost")
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$KEY" -out "$CERT" \
        -days 3650 -nodes -subj "/CN=$CN" 2>/dev/null
    echo "  SSL certificate generated (CN=$CN, valid 10 years)"
}
if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
    echo "  No SSL certificates found, generating..."
    generate_cert
elif ! openssl x509 -checkend 0 -noout -in "$CERT" 2>/dev/null; then
    echo "  SSL certificate expired, regenerating..."
    generate_cert
fi

# Start server in background
run_python "$SCRIPT_DIR/server/app.py" &
SERVER_PID=$!

# Start reverse proxy
PROXY_PID=""
"$PYTHON" "$SCRIPT_DIR/reverse_proxy.py" \
    --cert "$CERT" --key "$KEY" &
PROXY_PID=$!

# Ctrl+C stops everything
cleanup() {
    echo ""
    echo "Stopping..."
    kill $SERVER_PID 2>/dev/null
    [ -n "$PROXY_PID" ] && kill $PROXY_PID 2>/dev/null
    wait 2>/dev/null
    echo "Stopped."
    exit 0
}
trap cleanup INT TERM

echo ""
echo "============================================"
echo "  Vibe Web Terminal"
echo "============================================"
echo ""
echo "  Server:  http://127.0.0.1:8081"
echo "  Proxy:   https://0.0.0.0:8443"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Wait for either process to exit
wait -n $SERVER_PID $PROXY_PID 2>/dev/null
cleanup
