#!/bin/bash
# Vibe Web Terminal - Run Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# Default Configuration
# =============================================================================

CERT="$SCRIPT_DIR/certs/self-signed/fullchain.pem"
KEY="$SCRIPT_DIR/certs/self-signed/privkey.pem"
PORT=8443
UPSTREAM_HOST=127.0.0.1
UPSTREAM_PORT=8081
NO_SSL=false
AUTO_CERT=true  # Pass --auto-cert to rust_proxy by default

# =============================================================================
# Usage
# =============================================================================

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Vibe Web Terminal - Start the server and SSL reverse proxy

Options:
  --cert PATH           Path to SSL certificate (default: certs/self-signed/fullchain.pem)
  --key PATH            Path to SSL private key (default: certs/self-signed/privkey.pem)
  --port PORT           HTTPS port (default: 8443, or 8080 with --no-ssl)
  --upstream-host HOST  Backend server host (default: 127.0.0.1)
  --upstream-port PORT  Backend server port (default: 8081)
  --no-ssl              Run without SSL (development only)
  --no-auto-cert        Use existing certificates instead of auto-generating
                        Required when using externally signed certificates
  -h, --help            Show this help message

Examples:
  # Default (auto-generates and hot-reloads self-signed certs)
  ./run.sh

  # Use externally signed certificates (no auto-generation)
  ./run.sh --cert /etc/ssl/my-domain/fullchain.pem \\
           --key /etc/ssl/my-domain/privkey.pem \\
           --no-auto-cert

  # Development mode (no SSL)
  ./run.sh --no-ssl

  # Custom ports
  ./run.sh --port 443 --upstream-port 8080
EOF
    exit 0
}

# =============================================================================
# Argument Parsing
# =============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cert)
            CERT="$2"
            shift 2
            ;;
        --key)
            KEY="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --upstream-host)
            UPSTREAM_HOST="$2"
            shift 2
            ;;
        --upstream-port)
            UPSTREAM_PORT="$2"
            shift 2
            ;;
        --no-ssl)
            NO_SSL=true
            shift
            ;;
        --no-auto-cert)
            AUTO_CERT=false
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# =============================================================================
# Setup Checks
# =============================================================================

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

# =============================================================================
# Build Rust Proxy (if needed)
# =============================================================================

RUST_PROXY="$SCRIPT_DIR/rust_proxy/target/release/rust_proxy"
if [ ! -f "$RUST_PROXY" ]; then
    echo "Building Rust proxy..."
    cd "$SCRIPT_DIR/rust_proxy" && cargo build --release
    cd "$SCRIPT_DIR"
fi

# =============================================================================
# Start Services
# =============================================================================

# Start backend server
run_python "$SCRIPT_DIR/server/app.py" &
SERVER_PID=$!

# Start reverse proxy
if [ "$NO_SSL" = true ]; then
    # Use port 8080 for no-ssl unless explicitly set
    if [ "$PORT" = "8443" ]; then
        PORT=8080
    fi
    "$RUST_PROXY" --no-ssl --port "$PORT" --upstream-host "$UPSTREAM_HOST" --upstream-port "$UPSTREAM_PORT" &
elif [ "$AUTO_CERT" = true ]; then
    # Auto-generate and hot-reload certificates (default)
    "$RUST_PROXY" --auto-cert --cert "$CERT" --key "$KEY" --port "$PORT" --upstream-host "$UPSTREAM_HOST" --upstream-port "$UPSTREAM_PORT" &
else
    # Use existing certificates (--no-auto-cert specified)
    if [ ! -f "$CERT" ]; then
        echo "Error: Certificate not found: $CERT"
        echo "Provide a valid certificate or remove --no-auto-cert to auto-generate"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    if [ ! -f "$KEY" ]; then
        echo "Error: Private key not found: $KEY"
        echo "Provide a valid key or remove --no-auto-cert to auto-generate"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    "$RUST_PROXY" --cert "$CERT" --key "$KEY" --port "$PORT" --upstream-host "$UPSTREAM_HOST" --upstream-port "$UPSTREAM_PORT" &
fi
PROXY_PID=$!

# Ctrl+C stops everything
cleanup() {
    echo ""
    echo "Stopping..."
    kill $SERVER_PID 2>/dev/null
    kill $PROXY_PID 2>/dev/null
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
echo "  Server:  http://$UPSTREAM_HOST:$UPSTREAM_PORT"
if [ "$NO_SSL" = true ]; then
    echo "  Proxy:   http://0.0.0.0:$PORT"
else
    echo "  Proxy:   https://0.0.0.0:$PORT"
fi
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Wait for either process to exit
wait -n $SERVER_PID $PROXY_PID 2>/dev/null
cleanup
