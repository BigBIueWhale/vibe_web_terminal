# Docker Swarm Scaling Plan

## Target Requirements

- **800 concurrent containers** running simultaneously
- **Ephemeral data**: All user data lives inside the container (no host bind mounts)
- **Security**: When container dies, data is gone

## Why Swarm (Not Kubernetes)

| Aspect | Docker Swarm | Kubernetes |
|--------|--------------|------------|
| Setup | `docker swarm init` | Days of configuration |
| Learning curve | Already know Docker | New concepts (pods, deployments, etc.) |
| Sufficient for 800? | Yes | Overkill |
| Operational overhead | Low | High |

Swarm is Docker-native and sufficient for this scale.

---

## Physical Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        SWARM CLUSTER                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   MANAGER NODE (1 server, 64GB RAM)                              │
│   ┌────────────────────────────────────────────────────────┐     │
│   │  • Docker daemon + Swarm manager                       │     │
│   │  • Traefik (ingress, SSL termination)                  │     │
│   │  • FastAPI                                             │     │
│   │  • Redis (session state store)                         │     │
│   │  • Private Registry (for hibernated session images)    │     │
│   │                                                        │     │
│   │  If this dies: restart it. Swarm state persists on     │     │
│   │  disk. Workers keep running existing containers.       │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                   │
│   WORKER NODES (7 servers, 64GB RAM each)                        │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│   │  Worker 1  │ │  Worker 2  │ │  Worker 3  │ │  Worker 4  │   │
│   │  ~115      │ │  ~115      │ │  ~115      │ │  ~115      │...│
│   │ containers │ │ containers │ │ containers │ │ containers │   │
│   │            │ │            │ │            │ │            │   │
│   │  If dies:  │ │  If dies:  │ │  If dies:  │ │  If dies:  │   │
│   │  sessions  │ │  sessions  │ │  sessions  │ │  sessions  │   │
│   │  on it are │ │  on it are │ │  on it are │ │  on it are │   │
│   │  gone (OK) │ │  gone (OK) │ │  gone (OK) │ │  gone (OK) │   │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                                   │
│   OVERLAY NETWORK                                                 │
│   ┌────────────────────────────────────────────────────────┐     │
│   │  vibe-network (10.0.0.0/16)                            │     │
│   │  All containers addressable by name: session-{id}:7681 │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### What Each Node Is (Physically)

- **Manager (1 node)**: The server you SSH into. Runs control plane + services. If it dies, restart it - Swarm state persists on disk, workers keep running.
- **Workers (7 nodes)**: Servers that run session containers (~115 each). If one dies, those sessions are gone (acceptable - data is ephemeral anyway).
- **Overlay network**: Virtual LAN spanning all nodes. Containers talk by name, Docker routes automatically.

---

## Failure Modes (Realistic)

| What dies | What happens | Recovery |
|-----------|--------------|----------|
| Manager node | Workers keep running. Can't create/delete sessions. | Restart manager. |
| Worker node | ~115 sessions on that node gone. | Users create new sessions. |
| Single container | That session gone. | User creates new session. |
| Redis | Session lookups fail. | Restart Redis. |
| Registry | Can't hibernate or restore. | Restart registry. |

**This is acceptable because:**
- Data is ephemeral anyway (by design)
- Manager restart recovers cluster state from disk
- Worker loss = partial outage, not total outage
- Same failure model as single-process apps (if it dies, restart it)

---

## Resource Calculations

```
800 containers × 500MB average = 400GB RAM required
7 workers × 64GB = 448GB RAM available
Headroom: 48GB (10%) for bursts
```

| Resource | Requirement |
|----------|-------------|
| Manager node | 1x 64GB RAM |
| Worker nodes | 7x 64GB RAM |
| Network | Gigabit between nodes |
| Registry storage | ~100GB for hibernated images |

### Estimated Cost

```
Cloud (AWS/GCP):
  7 × 64GB workers     ≈ $1400/month
  1 × 64GB manager     ≈ $200/month
  Total                ≈ $1600/month

On-prem:
  8 servers (64GB each) ≈ $12-20k one-time
  Power/cooling         ≈ $200-400/month
```

---

## Data Persistence Strategy

### Constraint
Data must be ephemeral (security requirement). No host bind mounts.

### Solution: Docker Commit for Hibernation

```
Container running → Idle timeout → docker commit → Image saved → Container deleted
User returns → New container from saved image → Data restored
```

**Current code (data on host - removing this):**
```python
"Binds": [f"{workspace_dir}:/home/vibe/workspace:rw"]
```

**New code (data in container layer - ephemeral):**
```python
# No Binds. Data lives only in container's writable layer.
```

**Hibernation flow:**
```python
async def hibernate_session(session_id: str):
    container = docker.containers.get(container_id)

    # Commit container state to image
    image_tag = f"registry:5000/vibe-session-{session_id}:latest"
    container.commit(repository=image_tag)

    # Push to registry (accessible from all nodes)
    docker.images.push(image_tag)

    # Delete container (frees RAM)
    container.remove(force=True)

    # Update Redis
    redis.hset(f"session:{session_id}", "state", "hibernated")

async def restore_session(session_id: str):
    image_tag = f"registry:5000/vibe-session-{session_id}:latest"

    # Create service from hibernated image
    docker.services.create(
        image=image_tag,
        name=f"session-{session_id}",
        networks=["vibe-overlay"],
    )
```

**Storage math:**
```
Base image: 2GB (shared by all, stored once)
User layers: 800 × 100MB average = 80GB
Total registry storage: ~82GB
```

---

## Key Architecture Changes

### 1. No Port Allocation (Overlay DNS Instead)

```python
# BEFORE (doesn't scale past 1000)
session.port = allocate_port()  # 17000-18000
url = f"http://127.0.0.1:{session.port}"

# AFTER (unlimited)
container_name = f"session-{session_id}"
url = f"http://{container_name}:7681"
# Swarm DNS resolves to correct node automatically
```

### 2. Session State in Redis

```python
# BEFORE (in-memory, single process)
class SessionManager:
    sessions: Dict[str, Session] = {}

# AFTER (Redis, survives restarts)
await redis.hset(f"session:{session_id}", mapping={
    "user_id": user_id,
    "state": "running",  # running | hibernated
    "created_at": datetime.now().isoformat(),
    "last_activity": datetime.now().isoformat(),
})
await redis.sadd(f"user:{user_id}:sessions", session_id)
```

### 3. Swarm Services Instead of Direct Containers

```python
# BEFORE (direct Docker API)
container = await docker.containers.run(config=config, name=name)

# AFTER (Swarm service)
client.services.create(
    image="vibe-terminal:latest",
    name=f"session-{session_id}",
    networks=["vibe-overlay"],
    constraints=["node.role==worker"],
    resources=Resources(mem_limit=2147483648),
)
```

---

## Swarm Setup (One-Time)

### On Manager Node
```bash
# Initialize swarm
docker swarm init --advertise-addr <MANAGER_IP>

# Get join token for workers
docker swarm join-token worker

# Create overlay network
docker network create --driver overlay --attachable vibe-overlay

# Deploy registry
docker service create \
    --name registry \
    --publish 5000:5000 \
    --mount type=volume,source=registry-data,destination=/var/lib/registry \
    registry:2
```

### On Each Worker Node
```bash
docker swarm join --token <TOKEN> <MANAGER_IP>:2377
```

### Verify
```bash
docker node ls       # See all nodes
docker service ls    # See running services
```

---

## Request Flow

```
User browser
    │
    ▼
Traefik (on manager, SSL termination)
    │
    ├── /terminal/* → FastAPI
    │                    │
    │                    ▼
    │               Redis lookup
    │                    │
    │                    ▼
    │               If hibernated: restore from image
    │
    └── /ttyd/{session_id}/* → session-{session_id}:7681
                                (overlay network routes to correct worker)
```

---

## Implementation Phases

### Phase 1: Redis Migration
- [ ] Add Redis to current single-node setup
- [ ] Migrate SessionManager to Redis
- [ ] Migrate SessionOwnerStore to Redis
- [ ] Test everything still works

### Phase 2: Remove Bind Mounts
- [ ] Remove workspace bind mount
- [ ] Test ephemeral data behavior
- [ ] Add UI warning about data loss

### Phase 3: Swarm Setup
- [ ] Initialize swarm on manager
- [ ] Join 2 workers (start small)
- [ ] Create overlay network
- [ ] Deploy registry

### Phase 4: Service-Based Containers
- [ ] Change container creation to Swarm services
- [ ] Remove port allocation code
- [ ] Use overlay DNS for routing
- [ ] Update Traefik for service discovery

### Phase 5: Hibernation
- [ ] Implement docker commit on idle timeout
- [ ] Implement restore from image
- [ ] Add cleanup job for old images

### Phase 6: Scale Up
- [ ] Add remaining workers
- [ ] Load test: 100 → 200 → 400 → 800 containers
- [ ] Tune based on results

---

## Idle Detection

**How do we know a session is idle?**

The terminal uses a WebSocket connection. When the user is looking at the terminal, the WebSocket is connected. When they close the tab or navigate away, the WebSocket disconnects.

```python
# Track in Redis
async def on_websocket_connect(session_id: str):
    await redis.hset(f"session:{session_id}", "websocket_connected", "true")
    await redis.hset(f"session:{session_id}", "last_activity", now())

async def on_websocket_disconnect(session_id: str):
    await redis.hset(f"session:{session_id}", "websocket_connected", "false")
    await redis.hset(f"session:{session_id}", "last_disconnect", now())

# Cleanup job checks periodically
async def check_idle_sessions():
    for session in all_sessions:
        if not session.websocket_connected:
            idle_time = now() - session.last_disconnect
            if idle_time > IDLE_TIMEOUT:
                await hibernate_session(session.id)
```

**Idle = no WebSocket connection for IDLE_TIMEOUT duration.**

---

## Configuration

```python
# Swarm
OVERLAY_NETWORK = "vibe-overlay"
REGISTRY_URL = "registry:5000"

# Sessions
MAX_SESSIONS_PER_USER = 3
IDLE_TIMEOUT_MINUTES = 120      # Hibernate after 2 hours of no WebSocket
HIBERNATED_TTL_DAYS = 7         # Delete images after 7 days

# Redis
REDIS_URL = "redis://redis:6379"
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Scale | 800 concurrent containers |
| Orchestration | Docker Swarm (1 manager, 7 workers, all 64GB) |
| Data | Ephemeral (in-container only) |
| Hibernation | Docker commit to private registry |
| Session state | Redis |
| Networking | Overlay (no port allocation) |
| Failure model | Restart what dies. Data loss acceptable. |
| Cost | ~$1600/month cloud |
