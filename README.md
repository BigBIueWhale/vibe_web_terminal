# Vibe Web Terminal

A web-based terminal service that provides full Linux terminals with Mistral Vibe CLI pre-configured. Each user gets an isolated Docker container with their own workspace.

## Features

- **Full Terminal Experience** - Complete keyboard support, colors, TUI apps
- **Vibe CLI Ready** - Pre-configured to work with local Ollama
- **Isolated Sessions** - Each user gets their own Docker container
- **File Upload** - Upload files to your workspace via the web UI
- **File Download** - Download files/folders as 7z archives (preserves Unix permissions)
- **Session Management** - Track, switch, and delete sessions from the browser
- **Session Persistence** - Containers persist until PC restart (workspaces in /tmp)
- **Authentication** - Optional username/password and LDAP login for internet-facing deployments
- **SSL Reverse Proxy** - Built-in Python reverse proxy with self-signed certificates

## Architecture

### Local Development (default)

```
Browser --> localhost:8081 --> FastAPI Server --> Docker Containers
                                                 (one per user)
```

### Production (internet-facing)

```
Internet --> reverse_proxy.py :8443 (SSL) --> localhost:8081 (FastAPI)
                                                   |
                                                   v
                                            Docker Containers
```

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
cd /path/to/vibe-web-terminal

# One-time setup (builds Docker image, installs all dependencies)
# NOTE: Building the Docker image requires internet access
./setup.sh

# After changing docker/config files, rebuild the image:
./setup.sh --force-build

# Start everything (server + SSL reverse proxy)
./run.sh

# Stop everything
./stop.sh
```

`run.sh` automatically generates self-signed SSL certificates if missing or expired, starts the backend server on `http://127.0.0.1:8081`, and the SSL reverse proxy on `https://0.0.0.0:8443`. Press Ctrl+C to stop both.

To use a different HTTPS port (e.g., 443 to bypass strict corporate firewalls):
```bash
./run.sh --port 443
```

---

## Production Deployment (Internet-Facing)

To expose Vibe Web Terminal to the internet you need authentication.
SSL is handled automatically by `run.sh` (self-signed certificates).

### Step 1: Enable Authentication

#### 1a. Create the config file

```bash
cp auth.yaml.example auth.yaml
```

#### 1b. Add your first user

```bash
python3 edit_user.py add admin
# Password: ********
# Confirm password: ********
# User 'admin' added successfully.
```

#### 1c. Manage users

```bash
# List all users
python3 edit_user.py list

# Change a password
python3 edit_user.py passwd admin

# Remove a user
python3 edit_user.py remove olduser
```

#### How auth.yaml looks

When you add users via `edit_user.py`, the file looks like this:

```yaml
session_timeout_hours: 24

users:
  admin:
    password_hash: $2b$12$LJ3m5E3rKlGxX9qN7vD.K.abcdefghijklmnopqrstuv
    created_at: '2025-01-29T12:00:00'
  alice:
    password_hash: $2b$12$Mn8p2Q4rSlHzY1wO8vF.A.abcdefghijklmnopqrstuv
    created_at: '2025-01-29T13:30:00'

ldap:
  enabled: false
  server_url: ldap://ldap.example.com:389
  # ... (see auth.yaml.example for all options)
```

Passwords are bcrypt-hashed with random salt (12 rounds). Never edit hashes by hand — always use `edit_user.py`.

**Behaviour:**
- When `auth.yaml` exists: all routes require login.
- When `auth.yaml` does not exist: no authentication (localhost-only mode, original behaviour).
- `auth.yaml` is in `.gitignore` — it is never committed.

#### 1d. LDAP / Active Directory (optional)

In addition to local users, you can authenticate against an LDAP server. Local users are checked first; if no match, LDAP is tried.

Edit `auth.yaml` and set `ldap.enabled: true`:

```yaml
ldap:
  enabled: true

  # Connection
  server_url: "ldap://ldap.example.com:389"    # or ldaps://host:636
  use_starttls: false                           # upgrade plain to TLS
  tls_verify: true                              # verify server certificate
  timeout: 10                                   # seconds

  # Service account (for searching users)
  bind_dn: "cn=readonly,dc=example,dc=com"
  bind_password: "readonly_password"

  # User search
  search_base: "ou=people,dc=example,dc=com"
  search_filter: "(uid={username})"             # {username} is replaced
  display_name_attr: "cn"

  # Group-based access control (optional)
  # Leave required_group_dn empty to allow all LDAP users
  required_group_dn: "cn=vibe-users,ou=groups,dc=example,dc=com"
  group_search_base: "ou=groups,dc=example,dc=com"
  group_search_filter: "(&(objectClass=groupOfNames)(member={user_dn}))"
```

**Active Directory example:**

```yaml
ldap:
  enabled: true
  server_url: "ldaps://dc01.corp.example.com:636"
  tls_verify: true
  bind_dn: "CN=svc-vibe,OU=ServiceAccounts,DC=corp,DC=example,DC=com"
  bind_password: "service_account_password"
  search_base: "DC=corp,DC=example,DC=com"
  search_filter: "(sAMAccountName={username})"
  display_name_attr: "displayName"
  required_group_dn: "CN=Vibe-Users,OU=Groups,DC=corp,DC=example,DC=com"
  group_search_base: "DC=corp,DC=example,DC=com"
  group_search_filter: "(&(objectClass=group)(member={user_dn}))"
```

Install the LDAP library:

```bash
pip install ldap3
```

### Step 2: Start Everything

```bash
./run.sh
```

This single command:
1. Auto-generates self-signed SSL certificates if missing or expired (10-year validity)
2. Starts the backend server on `http://127.0.0.1:8081`
3. Starts the SSL reverse proxy on `https://0.0.0.0:8443`

Your site is live at `https://<your-public-ip>:8443`. Browsers will show a
certificate warning (self-signed) — click "Advanced" > "Proceed" to continue.

To stop: press Ctrl+C, or from another terminal run `./stop.sh`.

### Step 3 (optional): systemd Service

Create `/etc/systemd/system/vibe-terminal.service`:

```ini
[Unit]
Description=Vibe Web Terminal
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/vibe-web-terminal
ExecStart=/path/to/vibe-web-terminal/run.sh
ExecStop=/path/to/vibe-web-terminal/stop.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable vibe-terminal
sudo systemctl start vibe-terminal
```

---

## Offline / Internal Network Deployment

The setup is fully offline-friendly once the Docker image is built. No CDNs or external resources are used at runtime.

**Online vs Offline:**
- **Building the Docker image** (`./setup.sh --force-build`) requires internet access to download base images and packages
- **Running the service** (`./run.sh`) works fully offline once the image is built
- For air-gapped networks, build the image on an internet-connected machine and transfer it (see below)

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

# Setup (skips Docker build since image already loaded) and run
cd vibe-web-terminal
./setup.sh
./run.sh
```

## Files

```
vibe-web-terminal/
├── setup.sh                # One-time setup (Docker image, all dependencies)
├── run.sh                  # Start server + proxy (auto-generates SSL certs)
├── stop.sh                 # Stop server + proxy
├── edit_user.py            # CLI tool to manage local users
├── auth.yaml.example       # Example auth configuration (committed)
├── auth.yaml               # Actual auth config (gitignored)
├── reverse_proxy.py        # SSL reverse proxy for production
├── proxy_requirements.txt  # Dependencies for reverse proxy
├── docker/
│   ├── Dockerfile          # Terminal container image
│   └── config/
│       ├── start-session.sh    # tmux session startup
│       ├── vibe-config.toml    # Vibe CLI configuration
│       └── vibe-env            # Vibe CLI environment
└── server/
    ├── app.py              # FastAPI server
    ├── auth.py             # Authentication module
    ├── requirements.txt    # Python dependencies
    ├── static/
    │   └── sessions.js     # Client-side session management
    └── templates/
        ├── index.html      # Landing page with session list
        ├── terminal.html   # Terminal page with file browser
        └── login.html      # Login page (when auth enabled)
```

## Configuration

### Server Port

Edit `server/app.py`, change `SERVER_PORT`:
```python
SERVER_PORT = 8081
```

### Session Lifetime

Sessions persist until PC restart:
- Containers stay running until manually stopped or PC reboots
- Workspaces are in `/tmp/vibe-workspaces/` (cleared on reboot)
- Use `./stop.sh` to stop the server and proxy (containers keep running)
- Use `./cleanup-sessions.sh` to remove all containers and data

### Ollama Server

If your Ollama is at a different address, edit `docker/config/vibe-config.toml`:
```toml
api_base = "http://YOUR_OLLAMA_IP:11434/v1"
```

### Container Resources

In `server/app.py`, modify the container config in `_create_container`:
```python
"Memory": 2147483648,   # 2GB
"CpuQuota": 100000,     # 1 CPU
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/login` | GET/POST | Login page (when auth enabled) |
| `/logout` | GET | Destroy session and redirect to login |
| `/terminal/{session_id}` | GET | Terminal page for a session |
| `/session/new` | POST | Create new session |
| `/session/{id}/status` | GET | Get session status |
| `/session/{id}/upload` | POST | Upload file to workspace |
| `/session/{id}/browse` | GET | Browse workspace files |
| `/session/{id}/download` | GET | Download a single file |
| `/session/{id}/download-archive` | GET | Download directory as .7z |
| `/session/{id}` | DELETE | Delete session |
| `/sessions` | GET | List all sessions (admin) |
| `/sessions/status` | POST | Batch status check for client session list |

## Security Considerations

### Without `auth.yaml` (local mode)

- Server binds to `localhost` (127.0.0.1) only
- Not accessible from the network or internet
- No authentication required
- Server **refuses to start** if configured to bind to `0.0.0.0`

### With `auth.yaml` (production mode)

- All routes require login (username/password)
- Session cookies are `HttpOnly`, `Secure`, `SameSite=Strict`
- Passwords stored as bcrypt hashes with random salt
- LDAP authentication supported for enterprise environments
- Use the SSL reverse proxy for encrypted connections

### General

- Containers have limited resources (2GB RAM, 1 CPU) but can run arbitrary code
- The container sudo password is "password" (publicly known)
- Network access from containers is limited but not fully isolated
- Session IDs use 512 bits of cryptographic entropy

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

Run `./stop.sh` to stop existing instances, or change the port in `server/app.py`.

### Container fails to start

Check Docker logs:
```bash
docker logs vibe-session-XXXXX
```

### Login not working

- Check `auth.yaml` exists and has users: `python3 edit_user.py list`
- Verify password: remove and re-add the user with `edit_user.py`
- For LDAP issues, check server logs for detailed error messages
- Ensure `ldap3` is installed if using LDAP: `pip install ldap3`

## License

MIT
