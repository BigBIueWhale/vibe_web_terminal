# Vibe Web Terminal

A web-based terminal service that provides full Linux terminals with Mistral Vibe CLI pre-configured. Each user gets an isolated Docker container with their own workspace.

## Features

- **Full Terminal Experience** - Complete keyboard support, colors, TUI apps
- **Vibe CLI Ready** - Pre-configured to work with local Ollama
- **Isolated Sessions** - Each user gets their own Docker container
- **File Upload** - Upload files to your workspace via the web UI
- **Session Persistence** - Return to your session anytime using the URL
- **Persistent Sessions** - Containers persist until PC restart (workspaces in /tmp)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
└──────────────┬────────────────────┬─────────────────────┘
               │ :8080              │ :17000+
               ▼                    ▼
┌──────────────────────┐  ┌────────────────────────────────┐
│  FastAPI Server      │  │  Docker Container (per user)   │
│  (Python on HOST)    │  │  ┌──────────────────────────┐  │
│                      │  │  │ ttyd → bash              │  │
│  - Serves web UI     │  │  │ Vibe CLI installed       │  │
│  - Creates containers│  │  │ Workspace mounted        │  │
│  - Manages sessions  │  │  └──────────────────────────┘  │
│  - File upload API   │  │                                │
└──────────────────────┘  └───────────────┬────────────────┘
        │                                 │
        │ Docker API                      │ 172.17.0.1:11434
        ▼                                 ▼
┌──────────────────────────────────────────────────────────┐
│                     HOST MACHINE                         │
│  - Docker daemon                                         │
│  - Ollama (must listen on 0.0.0.0:11434)                │
│  - Workspaces at /tmp/vibe-workspaces/                  │
└──────────────────────────────────────────────────────────┘
```

**Key points:**
- FastAPI server runs on the **host** (not in Docker), manages everything
- Each user gets their own Docker container with ttyd terminal
- Containers access host's Ollama via Docker bridge IP (172.17.0.1)
- Workspaces are mounted from host into containers

## Requirements

- Docker
- Python 3.10+
- Ollama running and accessible from Docker containers (see Networking section)

## Installing Docker (Ubuntu/Debian)

If Docker is not installed, run these commands:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add yourself to the docker group (allows running docker without sudo)
sudo usermod -aG docker $USER

# Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Apply group change in current terminal (or log out and back in)
newgrp docker

# Verify Docker is working
docker run hello-world
```

## Quick Start

```bash
# Clone/copy to your server
cd /path/to/vibe-web-terminal

# Run setup (builds Docker image, installs dependencies)
./setup.sh

# Start the server
./run.sh
```

Then open http://localhost:8080 (or your server's IP on port 8080).

## Offline / Internal Network Deployment

The setup is fully offline-friendly. No CDNs or external resources are used at runtime.

### Export for transfer:

```bash
# Save Docker image to file
docker save vibe-terminal:latest | gzip > vibe-terminal-image.tar.gz

# Package everything needed
tar -czf vibe-web-terminal-bundle.tar.gz \
    --exclude='venv' \
    --exclude='.git' \
    -C /home/user/Desktop vibe-web-terminal

# Transfer both files to target machine
```

### Import on target machine:

```bash
# Load Docker image
gunzip -c vibe-terminal-image.tar.gz | docker load

# Extract project files
tar -xzf vibe-web-terminal-bundle.tar.gz

# Setup (skips Docker build since image already loaded)
cd vibe-web-terminal
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# Run
./run.sh
```

## Files

```
vibe-web-terminal/
├── setup.sh              # One-time setup script
├── run.sh                # Start the server
├── stop.sh               # Stop all containers and clean up
├── docker/
│   ├── Dockerfile        # Terminal container image
│   └── config/
│       ├── vibe-config.toml  # Vibe CLI configuration
│       └── vibe-env          # Vibe CLI environment
└── server/
    ├── app.py            # FastAPI server
    ├── requirements.txt  # Python dependencies
    └── templates/
        ├── index.html    # Landing page
        └── terminal.html # Terminal page with file upload
```

## Configuration

### Server Port

Edit `server/app.py`, change the port in the last line:
```python
uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Session Lifetime

Sessions persist until PC restart:
- Containers stay running until manually stopped or PC reboots
- Workspaces are in `/tmp/vibe-workspaces/` (cleared on reboot)
- Use `./stop.sh` to manually clean up all containers

### Ollama Server

If your Ollama is at a different address, edit `docker/config/vibe-config.toml`:
```toml
api_base = "http://YOUR_OLLAMA_IP:11434/v1"
```

### Container Resources

In `server/app.py`, modify the `create_container` function:
```python
mem_limit="2g",      # Memory limit
cpu_quota=100000,    # CPU limit (100000 = 1 CPU)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/terminal/{session_id}` | GET | Terminal page for a session |
| `/session/new` | POST | Create new session |
| `/session/{id}/status` | GET | Get session status |
| `/session/{id}/upload` | POST | Upload file to workspace |
| `/session/{id}/files` | GET | List workspace files |
| `/session/{id}` | DELETE | Delete session |
| `/sessions` | GET | List all sessions (admin) |

## Security Considerations

⚠️ **This is designed for trusted local network use.**

- Containers have limited resources but can still run arbitrary code
- The "password" for sudo is publicly known
- Consider adding authentication for production use
- Network access from containers is limited but not fully isolated

## Networking: Ollama Load Balancer Setup

Vibe CLI inside containers connects to **Ollama Load Balancer**, not directly to Ollama.

Docker containers cannot reach `127.0.0.1` on the host. They access the host via the Docker bridge IP: `172.17.0.1`.

### Required Setup

1. **Real Ollama** listens on `172.17.0.1:11434` (already the case if using the standard setup)

2. **Ollama Load Balancer** must listen on `172.17.0.1:11434` (docker0 interface):

   Modify `main.rs` in ollama_load_balancer to bind to `172.17.0.1:11434` instead of `127.0.0.1:11434`, then run:

   ```bash
   cd /home/user/Desktop/ollama_load_balancer
   ./target/release/ollama_load_balancer --server "http://172.17.0.1:11434=RTX5090 Server" --timeout 120
   ```

   **Note:** Do NOT use `0.0.0.0` - that's insecure. Only bind to docker0 (`172.17.0.1`).

3. **Containers** connect to Load Balancer at `http://172.17.0.1:11434/v1`

### Verify Connectivity

```bash
# Check Load Balancer is listening on docker0
ss -tlnp | grep 11434

# Test from a container
docker run --rm curlimages/curl curl -s http://172.17.0.1:11434/v1/models
```

## Troubleshooting

### Vibe CLI can't connect to Ollama

Check that Ollama Load Balancer is reachable:
```bash
curl http://172.17.0.1:11434/v1/models
```

### Docker permission denied

Add yourself to the docker group:
```bash
sudo usermod -aG docker $USER
# Then log out and log back in
```

### Port already in use

Change the port in `server/app.py` or stop the existing service.

### Container fails to start

Check Docker logs:
```bash
docker logs vibe-session-XXXXX
```

## License

MIT
