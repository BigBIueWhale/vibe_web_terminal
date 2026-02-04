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
│   MANAGER NODE (1x 64GB RAM)                                     │
│   ┌────────────────────────────────────────────────────────┐     │
│   │  • Docker daemon + Swarm manager                       │     │
│   │  • Traefik (ingress, SSL termination)                  │     │
│   │  • FastAPI (stateless, can scale to multiple)          │     │
│   │  • Redis (session state store)                         │     │
│   │  • Private Registry (for hibernated session images)    │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                   │
│   WORKER NODES (5x 128GB RAM each = 640GB total)                 │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│   │  Worker 1  │ │  Worker 2  │ │  Worker 3  │ │  Worker 4  │   │
│   │  ~160      │ │  ~160      │ │  ~160      │ │  ~160      │   │
│   │ containers │ │ containers │ │ containers │ │ containers │...│
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

- **Manager**: One server (physical or VM) you SSH into to run commands. Runs the control plane.
- **Workers**: Servers that just run containers. You don't SSH into these normally.
- **Overlay network**: Virtual LAN spanning all nodes. Containers talk by name, Docker handles routing.

---

## Resource Calculations

```
800 containers × 500MB average = 400GB RAM required
5 workers × 128GB = 640GB RAM available
Headroom: 240GB (37%) for bursts and overhead
```

| Resource | Requirement |
|----------|-------------|
| Worker nodes | 5x 128GB RAM, 32+ CPU cores |
| Manager node | 1x 64GB RAM |
| Network | Gigabit between nodes minimum |
| Storage | ~100GB for hibernated images |

### Estimated Cost

```
Cloud (AWS/GCP):
  5 × 128GB workers    ≈ $2000/month
  1 × 64GB manager     ≈ $400/month
  Registry + LB        ≈ $150/month
  ─────────────────────────────────
  Total                ≈ $2500-3000/month

On-prem:
  6 servers            ≈ $15-25k one-time
  Power/cooling        ≈ $200-400/month
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

**How it works:**
```python
# Current (data on host - REMOVING THIS)
"Binds": [f"{workspace_dir}:/home/vibe/workspace:rw"]

# New (data in container layer - EPHEMERAL)
# No Binds. Data lives only in container's writable layer.
```

**Hibernation flow:**
```python
async def hibernate_session(session_id: str):
    container = docker.containers.get(container_id)

    # Commit container state to image (preserves all data)
    image_tag = f"registry:5000/vibe-session-{session_id}:latest"
    container.commit(repository=image_tag)

    # Push to private registry (accessible from all nodes)
    docker.images.push(image_tag)

    # Delete container (frees RAM)
    container.remove(force=True)

    # Update Redis
    redis.hset(f"session:{session_id}", "state", "hibernated")

async def restore_session(session_id: str):
    image_tag = f"registry:5000/vibe-session-{session_id}:latest"

    # Create service from hibernated image
    docker service create \
        --name session-{session_id} \
        --network vibe-overlay \
        {image_tag}
```

**Storage math:**
```
Base image: 2GB (shared by all, stored once)
User layers: 800 × 100MB average = 80GB
Total registry storage: ~82GB
```

---

## Key Architecture Changes

### 1. Remove Port Allocation

```python
# BEFORE (doesn't scale past 1000)
HOST_PORT_START = 17000
HOST_PORT_END = 18000
session.port = allocate_port()
url = f"http://127.0.0.1:{session.port}"

# AFTER (unlimited via overlay DNS)
container_name = f"session-{session_id}"
url = f"http://{container_name}:7681"
# Swarm DNS resolves to correct node automatically
```

### 2. Session State in Redis

```python
# BEFORE (in-memory, single process)
class SessionManager:
    sessions: Dict[str, Session] = {}

# AFTER (Redis, shared across all FastAPI instances)
async def create_session(session_id: str, user_id: str):
    await redis.hset(f"session:{session_id}", mapping={
        "user_id": user_id,
        "state": "running",  # running | hibernated | deleted
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
    })
    await redis.sadd(f"user:{user_id}:sessions", session_id)

async def get_session(session_id: str) -> dict:
    return await redis.hgetall(f"session:{session_id}")
```

### 3. Container Creation via Swarm Services

```python
# BEFORE (direct Docker API)
container = await docker.containers.run(config=config, name=name)

# AFTER (Swarm service)
import subprocess
subprocess.run([
    "docker", "service", "create",
    "--name", f"session-{session_id}",
    "--network", "vibe-overlay",
    "--constraint", "node.role==worker",
    "--limit-memory", "2g",
    "vibe-terminal:latest"
])
```

Or via Docker SDK:
```python
client.services.create(
    image="vibe-terminal:latest",
    name=f"session-{session_id}",
    networks=["vibe-overlay"],
    constraints=["node.role==worker"],
    resources=Resources(mem_limit=2147483648),
)
```

---

## Swarm Setup Commands

### Initialize Swarm (on Manager)

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER_IP>

# Save the join token for workers
docker swarm join-token worker
```

### Join Workers

```bash
# On each worker node
docker swarm join --token <TOKEN> <MANAGER_IP>:2377
```

### Create Overlay Network

```bash
docker network create \
    --driver overlay \
    --attachable \
    vibe-overlay
```

### Deploy Private Registry

```bash
docker service create \
    --name registry \
    --publish 5000:5000 \
    --constraint 'node.role==manager' \
    --mount type=volume,source=registry-data,destination=/var/lib/registry \
    registry:2
```

### Verify Setup

```bash
docker node ls          # See all nodes
docker network ls       # See overlay network
docker service ls       # See running services
```

---

## Request Flow

```
1. User browser
   │
   ▼
2. Traefik (on manager, handles SSL)
   │  Route: /terminal/{session_id}/* → FastAPI
   │  Route: /ttyd/{session_id}/* → session-{session_id}:7681
   │
   ▼
3. FastAPI (stateless)
   │  • Authenticates user
   │  • Looks up session in Redis
   │  • If hibernated: restores from image
   │  • Returns terminal page
   │
   ▼
4. WebSocket: wss://vibe.example.com/ttyd/{session_id}/ws
   │
   ▼
5. Traefik proxies to session-{session_id}:7681
   │  (Overlay network routes to correct worker node)
   │
   ▼
6. ttyd in container serves terminal
```

---

## Implementation Phases

### Phase 1: Redis Migration
- [ ] Add Redis container to current setup
- [ ] Migrate SessionManager to Redis-backed
- [ ] Migrate SessionOwnerStore to Redis
- [ ] Test with single node

### Phase 2: Remove Bind Mounts
- [ ] Remove workspace bind mount from container config
- [ ] Test ephemeral data behavior
- [ ] Add UI warning: "Data is deleted when session closes"

### Phase 3: Swarm Setup
- [ ] Set up manager node
- [ ] Set up 2 worker nodes (start small)
- [ ] Create overlay network
- [ ] Deploy private registry

### Phase 4: Service-Based Containers
- [ ] Change container creation to Swarm services
- [ ] Remove port allocation code
- [ ] Use overlay network DNS for routing
- [ ] Update Traefik config for dynamic service discovery

### Phase 5: Hibernation
- [ ] Implement docker commit on idle timeout
- [ ] Implement restore from committed image
- [ ] Add image cleanup job (delete images older than N days)

### Phase 6: Scale Testing
- [ ] Add remaining worker nodes
- [ ] Load test with 100, 200, 400, 800 containers
- [ ] Monitor RAM, network, registry storage
- [ ] Tune based on results

---

## Configuration

```python
# New configuration values for app.py

# Swarm settings
SWARM_ENABLED = True
OVERLAY_NETWORK = "vibe-overlay"
REGISTRY_URL = "registry:5000"

# Session settings
MAX_SESSIONS_PER_USER = 3
IDLE_TIMEOUT_MINUTES = 120  # Hibernate after 2 hours idle
HIBERNATED_TTL_DAYS = 7     # Delete hibernated images after 7 days

# Redis
REDIS_URL = "redis://redis:6379"
```

---

## Monitoring

Essential metrics to track:

```
# Container metrics
swarm_containers_running        # Total running across cluster
swarm_containers_per_node       # Distribution across workers
container_memory_usage          # Actual vs limit

# Session metrics
sessions_active                 # Currently connected WebSockets
sessions_hibernated             # Stored as images
sessions_created_total          # All-time counter

# Registry metrics
registry_storage_bytes          # Image storage used
registry_images_count           # Number of hibernated images

# Node metrics
node_memory_available           # Per worker
node_cpu_usage                  # Per worker
```

---

## Failure Scenarios

| Scenario | Swarm Behavior | Data Impact |
|----------|----------------|-------------|
| Worker dies | Containers gone, services rescheduled | Data lost (ephemeral) |
| Manager dies | Cluster still runs, no new operations | None |
| Container crashes | Service auto-restarts on same/different node | Data lost |
| Network partition | Containers continue, new ops may fail | None |

**Mitigation for data loss:**
- Clear UI warnings about ephemeral nature
- "Download workspace" button
- Optional: Git integration for code persistence

---

## Summary

| Aspect | Decision |
|--------|----------|
| Scale target | 800 concurrent containers |
| Orchestration | Docker Swarm |
| Data model | Ephemeral (in-container only) |
| Hibernation | Docker commit to private registry |
| Session state | Redis |
| Networking | Overlay (no port allocation) |
| Nodes | 1 manager (64GB) + 5 workers (128GB each) |
| Estimated cost | ~$2500-3000/month cloud |
