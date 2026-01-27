# Vibe Web Terminal

A web-based terminal service that provides full Linux terminals with Mistral Vibe CLI pre-configured. Each user gets an isolated Docker container with their own workspace.

## Features

- **Full Terminal Experience** - Complete keyboard support, colors, TUI apps
- **Vibe CLI Ready** - Pre-configured to work with local Ollama
- **Isolated Sessions** - Each user gets their own Docker container
- **File Upload** - Upload files to your workspace via the web UI
- **Session Persistence** - Return to your session anytime using the URL
- **Auto Cleanup** - Old sessions are automatically cleaned up after 24 hours

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
│                   (xterm.js/ttyd)                       │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/WebSocket
                      ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Server (:8080)                     │
│         - Session Management                            │
│         - File Upload API                               │
│         - Container Orchestration                       │
└─────────────────────┬───────────────────────────────────┘
                      │ Docker API
                      ▼
┌─────────────────────────────────────────────────────────┐
│           Docker Containers (per session)               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Ubuntu 24.04 + ttyd                             │   │
│  │  - Vibe CLI installed                            │   │
│  │  - Connected to host Ollama (172.17.0.1:11434)   │   │
│  │  - Workspace at /home/vibe/workspace             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Requirements

- Docker
- Python 3.10+
- Ollama Load Balancer running at 172.17.0.1:11434

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

### Session Timeout

In `server/app.py`:
```python
SESSION_TIMEOUT_HOURS = 24  # Change to desired hours
```

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
