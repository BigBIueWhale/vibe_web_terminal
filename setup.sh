#!/bin/bash
# Vibe Web Terminal - Complete Setup Script
# This script sets up everything needed to run the web terminal service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Vibe Web Terminal - Setup Script"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (we shouldn't be)
if [ "$EUID" -eq 0 ]; then
    log_warn "Running as root. Some steps may need adjustment."
fi

# Step 1: Check Docker
log_info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    echo ""
    echo "To install Docker, run these commands:"
    echo ""
    echo "  # Install Docker"
    echo "  curl -fsSL https://get.docker.com | sudo sh"
    echo ""
    echo "  # Add yourself to docker group"
    echo "  sudo usermod -aG docker \$USER"
    echo ""
    echo "  # Enable and start Docker"
    echo "  sudo systemctl enable docker"
    echo "  sudo systemctl start docker"
    echo ""
    echo "  # Apply group change (or log out and back in)"
    echo "  newgrp docker"
    echo ""
    echo "Then run this setup script again."
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running or you don't have permission."
    echo ""
    echo "Try these commands:"
    echo ""
    echo "  # Start Docker service"
    echo "  sudo systemctl start docker"
    echo ""
    echo "  # If permission denied, add yourself to docker group:"
    echo "  sudo usermod -aG docker \$USER"
    echo "  newgrp docker"
    echo ""
    echo "Then run this setup script again."
    exit 1
fi
log_info "Docker is available."

# Step 2: Check Python
log_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed."
    exit 1
fi
log_info "Python 3 is available: $(python3 --version)"

# Step 3: Create virtual environment
log_info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_info "Virtual environment created."
else
    log_info "Virtual environment already exists."
fi

# Activate and install dependencies
source venv/bin/activate
log_info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r server/requirements.txt
log_info "Dependencies installed."

# Step 4: Build Docker image (or skip if already exists)
if docker image inspect vibe-terminal:latest &> /dev/null; then
    log_info "Docker image vibe-terminal:latest already exists, skipping build."
    log_info "(Delete it with 'docker rmi vibe-terminal:latest' to force rebuild)"
else
    log_info "Building Docker image (this may take a few minutes)..."
    cd docker
    docker build -t vibe-terminal:latest .
    cd ..
    log_info "Docker image built successfully."
fi

# Step 5: Create workspace directory
log_info "Creating workspace directory..."
mkdir -p /tmp/vibe-workspaces
chmod 777 /tmp/vibe-workspaces
log_info "Workspace directory created at /tmp/vibe-workspaces"

# Step 6: Test Ollama connectivity
log_info "Testing Ollama Load Balancer connectivity..."
if curl -s --connect-timeout 5 http://172.17.0.1:11434/v1/models > /dev/null 2>&1; then
    log_info "Ollama Load Balancer is reachable at 172.17.0.1:11434"
else
    log_warn "Cannot reach Ollama at 172.17.0.1:11434"
    log_warn "Make sure Ollama Load Balancer is running."
    log_warn "Vibe CLI inside containers may not work without it."
fi

# Step 7: Create run script if not exists
if [ ! -f "run.sh" ]; then
    log_info "Creating run script..."
    cat > run.sh << 'RUNEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
echo "Starting Vibe Web Terminal on http://127.0.0.1:8080"
echo "Press Ctrl+C to stop"
python server/app.py
RUNEOF
    chmod +x run.sh
fi

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "To start the server:"
echo "  ./run.sh"
echo ""
echo "Then open: http://localhost:8080"
echo ""
echo "SECURITY: Server binds to localhost only (127.0.0.1)"
echo "          NOT accessible from the network/internet"
echo ""
echo "Make sure Ollama Load Balancer is running at 172.17.0.1:11434"
echo "for Vibe CLI to work inside the containers."
echo ""
