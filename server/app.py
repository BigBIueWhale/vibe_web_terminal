#!/usr/bin/env python3
"""
Vibe Web Terminal Server

A web-based terminal service that spawns Docker containers with Vibe CLI.
Each user gets a unique session with a persistent container they can return to.
"""

import asyncio
import io
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import aiofiles
import aiodocker
import aiodocker.exceptions
import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketState

try:
    from server.auth import create_auth_manager
except ImportError:
    from auth import create_auth_manager

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# Without auth.yaml: binds to localhost only (unauthenticated, safe for local).
# With auth.yaml:    authentication required; safe to expose via reverse proxy.
# =============================================================================
SERVER_HOST = "127.0.0.1"  # Overridden to 0.0.0.0 when auth is enabled
SERVER_PORT = 8081

# Configuration
DOCKER_IMAGE = "vibe-terminal:latest"
CONTAINER_PREFIX = "vibe-session-"
MAX_SESSIONS_PER_USER = 3
# No automatic cleanup - containers persist until user deletes them
SESSION_TIMEOUT_HOURS = None  # Disabled
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes (only cleans up dead containers)
HOST_PORT_START = 17000
HOST_PORT_END = 18000

# Data directory: persistent storage within the project (survives reboots)
DATA_DIR = Path(__file__).parent.parent / "data"
WORKSPACE_BASE = DATA_DIR / "workspaces"
OWNER_STORE_PATH = DATA_DIR / "session_owners.json"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Docker client (initialized in lifespan)
docker_client: aiodocker.Docker | None = None


def is_container_not_found(e: Exception) -> bool:
    """Check if exception indicates container not found."""
    return isinstance(e, aiodocker.exceptions.DockerError) and e.status == 404


# =============================================================================
# SESSION STATE MACHINE
# =============================================================================


class SessionState(Enum):
    """State machine for session lifecycle."""
    CREATING = auto()  # Container being created
    READY = auto()     # Accepting connections
    DELETING = auto()  # Being cleaned up


class SessionError(Exception):
    """Exception for session-related errors."""
    pass


@dataclass
class Session:
    """
    Represents a terminal session with state machine and reference counting.

    State transitions:
        CREATING -> READY -> DELETING -> (removed)
    """
    session_id: str
    container_id: str | None = None
    container_name: str | None = None
    port: int | None = None
    workspace: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)

    _state: SessionState = SessionState.CREATING
    _ref_count: int = 0  # Active WebSocket connections
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def can_delete(self) -> bool:
        """Check if session can be deleted (READY state and no active refs)."""
        return self._state == SessionState.READY and self._ref_count == 0

    def acquire_ref(self) -> None:
        """Increment ref_count. Raises if not READY."""
        if self._state != SessionState.READY:
            raise SessionError(f"Session not ready: {self._state}")
        self._ref_count += 1

    def release_ref(self) -> None:
        """Decrement ref_count."""
        if self._ref_count > 0:
            self._ref_count -= 1


class SessionManager:
    """
    Manages sessions with proper concurrency control.

    Lock ordering (to prevent deadlocks):
        1. _global_lock (global)
        2. session._lock (per-session)
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._global_lock = asyncio.Lock()  # For creation/deletion
        self._port_allocations: set[int] = set()

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is actually in use on the system."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return False
            except OSError:
                return True

    def _allocate_port(self) -> int:
        """Allocate an available port for a container."""
        for port in range(HOST_PORT_START, HOST_PORT_END):
            if port not in self._port_allocations and not self._is_port_in_use(port):
                self._port_allocations.add(port)
                return port
        raise RuntimeError("No available ports")

    def _release_port(self, port: int) -> None:
        """Release a port allocation."""
        self._port_allocations.discard(port)

    async def get_or_create_session(self, session_id: str) -> Session:
        """
        Get existing or create new session (prevents duplicates).

        Uses double-check locking pattern for efficiency.
        """
        # Fast path: existing READY session
        session = self._sessions.get(session_id)
        if session and session._state == SessionState.READY:
            async with session._lock:
                session.last_accessed = datetime.now()
                # Verify container is still running
                try:
                    container = await docker_client.containers.get(session.container_name)
                    info = await container.show()
                    if info["State"]["Status"] == "running":
                        return session
                except aiodocker.exceptions.DockerError:
                    pass
                # Container not running, need to recreate
                session._state = SessionState.DELETING

        # Slow path: need global lock
        async with self._global_lock:
            # Double-check pattern
            session = self._sessions.get(session_id)
            if session and session._state == SessionState.READY:
                return session

            # Clean up old session if exists
            if session:
                self._sessions.pop(session_id, None)
                if session.port:
                    self._release_port(session.port)

            # Create new session with port allocation (atomic)
            session = Session(session_id=session_id)
            self._sessions[session_id] = session
            port = self._allocate_port()
            session.port = port

        # Create container (outside global lock, but session is in CREATING state)
        try:
            await self._create_container(session)
            async with session._lock:
                session._state = SessionState.READY
            return session
        except Exception as e:
            # Cleanup on failure
            async with self._global_lock:
                self._sessions.pop(session_id, None)
                if session.port:
                    self._release_port(session.port)
            raise

    async def _create_container(self, session: Session) -> None:
        """Create a Docker container for the session."""
        container_name = get_container_name(session.session_id)
        session.container_name = container_name

        # Create workspace directory
        workspace_dir = WORKSPACE_BASE / session.session_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(workspace_dir, 0o777)
        session.workspace = str(workspace_dir)

        # Remove existing container if any
        try:
            old_container = await docker_client.containers.get(container_name)
            await old_container.delete(force=True)
        except aiodocker.exceptions.DockerError as e:
            if not is_container_not_found(e):
                raise

        # Create container on default bridge (iptables handles isolation)
        config = {
            "Image": DOCKER_IMAGE,
            "Env": ["TERM=xterm-256color"],
            "HostConfig": {
                "PortBindings": {
                    "7681/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(session.port)}]
                },
                "Binds": [f"{workspace_dir}:/home/vibe/workspace:rw"],
                "ExtraHosts": ["host.docker.internal:host-gateway"],
                "Memory": 2147483648,  # 2GB
                "CpuPeriod": 100000,
                "CpuQuota": 100000,  # 1 CPU
                "RestartPolicy": {"Name": "unless-stopped"},
            },
        }

        container = await docker_client.containers.run(config=config, name=container_name)
        session.container_id = container.id

        logger.info(f"Created container {container_name} on port {session.port}")

        # Wait for ttyd to start
        await asyncio.sleep(2)

    async def acquire_session_ref(self, session_id: str) -> Session:
        """Acquire reference for WebSocket (atomic ref_count increment)."""
        session = self._sessions.get(session_id)
        if not session:
            raise SessionError("Session not found")
        async with session._lock:
            session.acquire_ref()
            session.last_accessed = datetime.now()
        return session

    async def release_session_ref(self, session: Session) -> None:
        """Release reference when WebSocket disconnects."""
        async with session._lock:
            session.release_ref()

    async def delete_session(self, session_id: str, force: bool = False) -> bool:
        """
        Delete session. If force=True, bypass ref_count check.

        Returns True if deleted, False if not found or has active connections.
        """
        async with self._global_lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            async with session._lock:
                if not force and not session.can_delete():
                    return False
                session._state = SessionState.DELETING
                self._sessions.pop(session_id)
                if session.port:
                    self._release_port(session.port)

        # Cleanup outside lock
        await self._cleanup_container(session)
        return True

    async def _cleanup_container(self, session: Session) -> None:
        """Clean up container and workspace for a session."""
        # Remove container
        if session.container_name:
            try:
                container = await docker_client.containers.get(session.container_name)
                await container.delete(force=True)
            except aiodocker.exceptions.DockerError:
                pass

        # Clean up workspace
        if session.workspace:
            workspace = Path(session.workspace)
            if workspace.exists():
                import shutil
                shutil.rmtree(workspace, ignore_errors=True)

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID without creating it."""
        return self._sessions.get(session_id)

    def get_session_port(self, session_id: str) -> int | None:
        """Get the ttyd port for a session, or None if not found."""
        session = self._sessions.get(session_id)
        if session and session._state == SessionState.READY:
            return session.port
        return None

    async def recover_existing_sessions(self) -> None:
        """Discover and re-register containers from previous server runs.

        Running containers are recovered as READY sessions.
        Stopped containers are restarted (they persist across reboots).
        Containers that fail to restart are removed.
        """
        try:
            containers = await docker_client.containers.list(
                all=True, filters={"name": [CONTAINER_PREFIX]}
            )
        except Exception as e:
            logger.error(f"Failed to list existing containers: {e}")
            return

        for container in containers:
            try:
                info = await container.show()
                name = info["Name"].lstrip("/")
                status = info["State"]["Status"]

                # Extract session ID and workspace path from bind mount
                session_id = None
                workspace_path = None
                binds = info.get("HostConfig", {}).get("Binds", [])
                for bind in binds:
                    parts = bind.split(":")
                    if len(parts) >= 2 and "/home/vibe/workspace" in parts[1]:
                        workspace_path = parts[0]
                        session_id = Path(parts[0]).name
                        break

                if not session_id:
                    logger.warning(f"Cannot determine session ID for container {name}, removing")
                    await container.delete(force=True)
                    continue

                # Restart stopped/exited containers instead of removing them
                if status != "running":
                    logger.info(f"Restarting stopped container {name} (status: {status})")
                    try:
                        await container.start()
                        await asyncio.sleep(2)
                        info = await container.show()
                        status = info["State"]["Status"]
                        if status != "running":
                            logger.warning(f"Container {name} failed to restart (status: {status}), removing")
                            await container.delete(force=True)
                            continue
                        logger.info(f"Container {name} restarted successfully")
                    except Exception as e:
                        logger.error(f"Failed to restart container {name}: {e}, removing")
                        await container.delete(force=True)
                        continue

                # Extract port from PortBindings
                port = None
                port_bindings = info.get("HostConfig", {}).get("PortBindings", {})
                for _key, bindings in port_bindings.items():
                    if bindings:
                        port = int(bindings[0]["HostPort"])
                        break

                if not port:
                    logger.warning(f"Cannot determine port for container {name}, removing")
                    await container.delete(force=True)
                    continue

                created_str = info.get("Created", "")
                try:
                    created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    created_at = datetime.now()

                session = Session(
                    session_id=session_id,
                    container_id=container.id,
                    container_name=name,
                    port=port,
                    workspace=workspace_path,
                    created_at=created_at,
                    last_accessed=datetime.now(),
                )
                session._state = SessionState.READY

                self._sessions[session_id] = session
                self._port_allocations.add(port)

                logger.info(f"Recovered session {session_id} (container {name}, port {port})")

            except Exception as e:
                logger.error(f"Failed to recover container: {e}")

        if self._sessions:
            logger.info(f"Recovered {len(self._sessions)} session(s) from previous run")

    def list_sessions(self) -> list[Session]:
        """Get all sessions."""
        return list(self._sessions.values())


# =============================================================================
# SESSION OWNERSHIP
# =============================================================================
# Persists which user owns which session. Stored in data/session_owners.json.
# When auth is disabled, all sessions belong to "__anonymous__".
# =============================================================================


class SessionOwnerStore:
    """Persists session-to-user ownership mapping on disk."""

    def __init__(self, path: Path):
        self._path = path
        self._owners: dict[str, str] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._owners = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._owners = {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(self._owners, f, indent=2)
        tmp_path.replace(self._path)

    def assign(self, session_id: str, username: str):
        """Record that username owns session_id."""
        self._owners[session_id] = username
        self._save()

    def remove(self, session_id: str):
        """Remove ownership record."""
        if session_id in self._owners:
            del self._owners[session_id]
            self._save()

    def get_owner(self, session_id: str) -> str | None:
        """Get the username that owns a session, or None."""
        return self._owners.get(session_id)

    def get_user_sessions(self, username: str) -> list[str]:
        """Get all session IDs owned by a user."""
        return [sid for sid, owner in self._owners.items() if owner == username]

    def count_user_sessions(self, username: str) -> int:
        """Count sessions owned by a user."""
        return sum(1 for owner in self._owners.values() if owner == username)

    def all_session_ids(self) -> set[str]:
        """Get all tracked session IDs."""
        return set(self._owners.keys())


# Global instances
session_manager = SessionManager()
owner_store: SessionOwnerStore | None = None  # Initialized in lifespan
_user_create_locks: dict[str, asyncio.Lock] = {}  # Per-user locks for session creation


def generate_session_id() -> str:
    """Generate a cryptographically secure session ID (512 bits of entropy)."""
    return secrets.token_urlsafe(64)


def get_container_name(session_id: str) -> str:
    """Get container name for a session."""
    return f"{CONTAINER_PREFIX}{session_id[:12]}"


def get_current_user(request: Request) -> str:
    """Get the authenticated username from the request, or '__anonymous__'."""
    return getattr(request.state, "username", "__anonymous__")


def verify_session_ownership(request: Request, session_id: str):
    """Verify the current user owns the session. Raises HTTPException if not."""
    username = get_current_user(request)
    session_owner = owner_store.get_owner(session_id)
    if session_owner is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_owner != username:
        raise HTTPException(status_code=403, detail="Access denied")


async def cleanup_old_sessions():
    """Clean up dead containers and orphaned owner store entries."""
    while True:
        try:
            # Clean up containers that have died
            for session in session_manager.list_sessions():
                if session._state != SessionState.READY:
                    continue
                try:
                    container = await docker_client.containers.get(session.container_name)
                    info = await container.show()
                    if info["State"]["Status"] in ("exited", "dead"):
                        # Try to restart
                        try:
                            await container.start()
                            logger.info(f"Restarted dead container for session {session.session_id}")
                        except Exception:
                            # Can't restart - clean up
                            await session_manager.delete_session(session.session_id, force=True)
                            if owner_store:
                                owner_store.remove(session.session_id)
                            logger.info(f"Cleaned up dead container for session {session.session_id}")
                except aiodocker.exceptions.DockerError as e:
                    if is_container_not_found(e):
                        await session_manager.delete_session(session.session_id, force=True)
                        if owner_store:
                            owner_store.remove(session.session_id)

            # Clean up orphaned owner store entries (owner store has ID but no session)
            if owner_store:
                for sid in list(owner_store.all_session_ids()):
                    if session_manager.get_session(sid) is None:
                        # Session not in manager - check if container exists
                        container_name = get_container_name(sid)
                        try:
                            await docker_client.containers.get(container_name)
                            # Container exists but not in session manager - will be
                            # recovered on next startup. Leave owner entry alone.
                        except aiodocker.exceptions.DockerError:
                            # Container truly gone - remove owner entry
                            owner_store.remove(sid)
                            logger.info(f"Removed orphaned owner entry for session {sid[:12]}")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _http_client, docker_client, owner_store
    # Startup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)
    owner_store = SessionOwnerStore(OWNER_STORE_PATH)
    docker_client = aiodocker.Docker()
    await session_manager.recover_existing_sessions()
    cleanup_task = asyncio.create_task(cleanup_old_sessions())
    logger.info("Vibe Web Terminal server started")

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    if docker_client is not None:
        await docker_client.close()
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    logger.info("Vibe Web Terminal server stopped")


# Forward declaration for HTTP client (used by proxy)
_http_client: Optional[httpx.AsyncClient] = None


# FastAPI app
app = FastAPI(
    title="Vibe Web Terminal",
    description="Web-based terminal with Vibe CLI in Docker containers",
    lifespan=lifespan,
)

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# =============================================================================
# AUTHENTICATION
# =============================================================================
# Enabled when auth.yaml exists.  When disabled, all routes are open
# (localhost-only mode).
# =============================================================================

auth_manager = create_auth_manager()

# Paths that never require authentication
_AUTH_EXEMPT = {"/login", "/logout"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Gate every request behind login when authentication is enabled."""
    if not auth_manager:
        # No auth — single anonymous user
        request.state.username = "__anonymous__"
        return await call_next(request)

    path = request.url.path

    # Allow auth-exempt paths and static assets (needed for login page CSS/JS)
    if path in _AUTH_EXEMPT or path.startswith("/static/"):
        return await call_next(request)

    # Check session cookie
    token = request.cookies.get("vibe_session")
    username = auth_manager.validate_session(token) if token else None

    if username:
        request.state.username = username
        return await call_next(request)

    # Not authenticated — reject
    # WebSocket upgrades get 401 (can't redirect)
    if "upgrade" in request.headers.get("connection", "").lower():
        return Response(status_code=401, content="Unauthorized")

    # Regular HTTP — redirect to login with return URL
    next_url = request.url.path
    if request.url.query:
        next_url += f"?{request.url.query}"
    return RedirectResponse(f"/login?next={next_url}", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    """Show the login form."""
    # If auth is disabled, just redirect to index
    if not auth_manager:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
        "username": "",
        "next_url": next,
    })


@app.post("/login")
async def login_submit(request: Request):
    """Process login form submission."""
    if not auth_manager:
        return RedirectResponse("/", status_code=302)

    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    next_url = form.get("next", "/")

    if auth_manager.authenticate(username, password):
        token = auth_manager.create_session(username)
        response = RedirectResponse(next_url or "/", status_code=302)
        response.set_cookie(
            key="vibe_session",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/",
            max_age=int(auth_manager._timeout.total_seconds()),
        )
        return response

    # Authentication failed
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid username or password.",
        "username": username,
        "next_url": next_url,
    }, status_code=401)


@app.get("/logout")
async def logout(request: Request):
    """Destroy session and redirect to login."""
    token = request.cookies.get("vibe_session")
    if token and auth_manager:
        auth_manager.destroy_session(token)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("vibe_session", path="/")
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page - create new session."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/session/new")
async def create_new_session(request: Request):
    """Create a new terminal session for the current user."""
    username = get_current_user(request)

    if username not in _user_create_locks:
        _user_create_locks[username] = asyncio.Lock()
    async with _user_create_locks[username]:
        # Prune gone sessions before counting (owner_store may have stale entries)
        for sid in owner_store.get_user_sessions(username):
            session = session_manager.get_session(sid)
            if not session:
                owner_store.remove(sid)
                continue
            try:
                container = await docker_client.containers.get(session.container_name)
                info = await container.show()
                if info["State"]["Status"] in ("exited", "dead"):
                    owner_store.remove(sid)
            except aiodocker.exceptions.DockerError:
                owner_store.remove(sid)

        # Enforce max sessions per user
        count = owner_store.count_user_sessions(username)
        if count >= MAX_SESSIONS_PER_USER:
            raise HTTPException(
                status_code=429,
                detail=f"Maximum {MAX_SESSIONS_PER_USER} sessions reached. Delete a session first."
            )

        session_id = generate_session_id()
        try:
            await session_manager.get_or_create_session(session_id)
            owner_store.assign(session_id, username)
            return JSONResponse({
                "session_id": session_id,
                "redirect": f"/terminal/{session_id}"
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/terminal/{session_id}", response_class=HTMLResponse)
async def terminal_page(request: Request, session_id: str):
    """Terminal page for a session. Refuses if session doesn't exist or isn't owned."""
    # Check ownership — refuses non-existent and non-owned sessions
    verify_session_ownership(request, session_id)

    try:
        session = await session_manager.get_or_create_session(session_id)
        return templates.TemplateResponse("terminal.html", {
            "request": request,
            "session_id": session_id,
            "ttyd_port": session.port,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/status")
async def session_status(request: Request, session_id: str):
    """Get session status."""
    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        container = await docker_client.containers.get(session.container_name)
        info = await container.show()
        return {
            "session_id": session_id,
            "status": info["State"]["Status"],
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
        }
    except aiodocker.exceptions.DockerError as e:
        if is_container_not_found(e):
            return {
                "session_id": session_id,
                "status": "not_found",
            }
        raise


@app.post("/session/{session_id}/upload")
async def upload_file(
    request: Request,
    session_id: str,
    file: UploadFile = File(...),
    path: Optional[str] = Form(None)
):
    """Upload a file to the session workspace.

    Args:
        session_id: The session ID
        file: The file to upload
        path: Optional relative path (for folder uploads, preserves structure)
    """
    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Path(session.workspace)

    # Use provided path or fall back to filename
    relative_path = path or file.filename

    # Sanitize path - remove any attempts to escape workspace
    relative_path = relative_path.lstrip("/").lstrip("\\")
    if ".." in relative_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Get just the filename for validation
    filename = Path(relative_path).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = workspace / relative_path

    try:
        # Create parent directories if needed (for folder uploads)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Ensure all parent directories are writable by container user
        for parent in filepath.parents:
            if parent.is_relative_to(workspace):
                os.chmod(parent, 0o777)

        # Stream file to disk in chunks for large files
        async with aiofiles.open(filepath, "wb") as f:
            total_size = 0
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                total_size += len(chunk)

        # Set proper permissions (777 so scripts are executable and container can write)
        os.chmod(filepath, 0o777)

        return {
            "filename": filename,
            "path": relative_path,
            "size": total_size,
            "full_path": f"/home/vibe/workspace/{relative_path}"
        }
    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/files")
async def list_files(request: Request, session_id: str):
    """List files in the session workspace."""
    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Path(session.workspace)

    files = []
    for item in workspace.iterdir():
        stat = item.stat()
        files.append({
            "name": item.name,
            "size": stat.st_size,
            "is_dir": item.is_dir(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return {"files": files}


@app.get("/session/{session_id}/browse")
async def browse_files(request: Request, session_id: str, path: str = ""):
    """Browse files in the session workspace with subdirectory support."""
    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Path(session.workspace)

    # Sanitize and resolve the path
    clean_path = path.strip("/").replace("..", "")
    target_dir = workspace / clean_path if clean_path else workspace

    # Security: ensure path is within workspace
    try:
        target_dir = target_dir.resolve()
        if not str(target_dir).startswith(str(workspace.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    files = []
    try:
        for item in sorted(target_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "size": stat.st_size if not item.is_dir() else get_dir_size(item),
                    "is_dir": item.is_dir(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except (PermissionError, OSError):
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {
        "path": clean_path,
        "files": files,
        "parent": str(Path(clean_path).parent) if clean_path else None
    }


def get_dir_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
    return total


@app.get("/session/{session_id}/download")
async def download_file(request: Request, session_id: str, path: str):
    """Download a single file from the session workspace."""
    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Path(session.workspace)

    # Sanitize and resolve the path
    clean_path = path.strip("/").replace("..", "")
    if not clean_path:
        raise HTTPException(status_code=400, detail="Path required")

    target_file = (workspace / clean_path).resolve()

    # Security: ensure path is within workspace
    if not str(target_file).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if target_file.is_dir():
        raise HTTPException(status_code=400, detail="Use download-archive for directories")

    return FileResponse(
        path=target_file,
        filename=target_file.name,
        media_type="application/octet-stream"
    )


@app.get("/session/{session_id}/download-archive")
async def download_archive(request: Request, session_id: str, path: str = ""):
    """Download a directory as a 7z archive (preserves Unix file permissions)."""
    import py7zr

    verify_session_ownership(request, session_id)

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Path(session.workspace)

    # Sanitize and resolve the path
    clean_path = path.strip("/").replace("..", "")
    target_dir = (workspace / clean_path).resolve() if clean_path else workspace.resolve()

    # Security: ensure path is within workspace
    if not str(target_dir).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    # Create 7z archive in memory
    archive_buffer = io.BytesIO()
    archive_name = target_dir.name if clean_path else f"workspace-{session_id[:8]}"

    with py7zr.SevenZipFile(archive_buffer, "w") as szf:
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                try:
                    arcname = str(file_path.relative_to(target_dir))
                    szf.write(file_path, arcname)
                except (PermissionError, OSError) as e:
                    logger.warning(f"Skipping file {file_path}: {e}")

    archive_buffer.seek(0)

    return StreamingResponse(
        archive_buffer,
        media_type="application/x-7z-compressed",
        headers={"Content-Disposition": f'attachment; filename="{archive_name}.7z"'}
    )


@app.delete("/session/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Delete a session and its container. Only the owner can delete."""
    verify_session_ownership(request, session_id)

    # Force-delete regardless of active connections
    session = session_manager.get_session(session_id)
    if session:
        await session_manager.delete_session(session_id, force=True)

    owner_store.remove(session_id)
    return {"status": "deleted"}


@app.get("/my/sessions")
async def my_sessions(request: Request):
    """List the current user's sessions with live status."""
    username = get_current_user(request)
    session_ids = owner_store.get_user_sessions(username)

    result = []
    prune_ids = []

    for sid in session_ids:
        info = {
            "id": sid,
            "label": sid[:8],
            "status": "gone",
            "created_at": None,
        }

        session = session_manager.get_session(sid)
        if session:
            try:
                container = await docker_client.containers.get(session.container_name)
                container_info = await container.show()
                info["status"] = container_info["State"]["Status"]
                info["created_at"] = session.created_at.isoformat()
            except aiodocker.exceptions.DockerError:
                info["status"] = "gone"

        if info["status"] == "gone":
            prune_ids.append(sid)
            continue

        result.append(info)

    # Auto-prune gone sessions from owner store
    for sid in prune_ids:
        owner_store.remove(sid)

    # Sort: running first, then by created_at descending
    result.sort(key=lambda s: (
        0 if s["status"] == "running" else 1,
        s.get("created_at") or "",
    ))

    return {
        "sessions": result,
        "max_sessions": MAX_SESSIONS_PER_USER,
    }


@app.get("/sessions")
async def list_sessions():
    """List all active sessions (admin endpoint).

    Session IDs are deliberately omitted to prevent enumeration attacks.
    """
    result = []
    for session in session_manager.list_sessions():
        try:
            container = await docker_client.containers.get(session.container_name)
            info = await container.show()
            status = info["State"]["Status"]
        except aiodocker.exceptions.DockerError as e:
            if is_container_not_found(e):
                status = "not_found"
            else:
                status = "error"

        result.append({
            "status": status,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "ref_count": session._ref_count,
            "state": session._state.name,
        })

    return {"count": len(result), "sessions": result}


# =============================================================================
# WEBSOCKET AND HTTP PROXY FOR TTYD
# =============================================================================
# All browser connections now go through port 8080 - no direct port access needed
# This provides a single entry point and better security
# =============================================================================

async def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


def get_session_port(session_id: str) -> Optional[int]:
    """Get the ttyd port for a session, or None if not found."""
    return session_manager.get_session_port(session_id)


@app.websocket("/ttyd/{session_id}/ws")
async def websocket_proxy(websocket: WebSocket, session_id: str):
    """
    WebSocket proxy for ttyd terminal connections.

    Includes authentication and ownership checks.
    """
    # Auth check (HTTP middleware doesn't cover WebSocket connections)
    if auth_manager:
        token = websocket.cookies.get("vibe_session")
        ws_username = auth_manager.validate_session(token) if token else None
        if not ws_username:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    else:
        ws_username = "__anonymous__"

    # Ownership check
    if owner_store:
        session_owner = owner_store.get_owner(session_id)
        if session_owner is None or session_owner != ws_username:
            await websocket.close(code=4003, reason="Access denied")
            return

    # Acquire session reference (prevents deletion while we're connected)
    try:
        session = await session_manager.acquire_session_ref(session_id)
    except SessionError:
        await websocket.close(code=4004, reason="Session not found")
        return

    try:
        port = session.port  # Safe - we hold reference
        # Accept with 'tty' subprotocol - required by ttyd
        await websocket.accept(subprotocol="tty")
        logger.info(f"WebSocket proxy started for session {session_id[:12]} -> port {port}")

        # Connect to ttyd's WebSocket
        ttyd_ws = None
        try:
            import websockets
            ttyd_url = f"ws://127.0.0.1:{port}/ws"

            async with websockets.connect(
                ttyd_url,
                subprotocols=["tty"],  # Required by ttyd
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=20,   # Wait 20 seconds for pong
                close_timeout=5,   # 5 second close timeout
            ) as ttyd_ws:

                async def forward_to_ttyd():
                    """Forward messages from browser to ttyd."""
                    try:
                        while True:
                            if websocket.client_state != WebSocketState.CONNECTED:
                                break
                            data = await websocket.receive()
                            if data["type"] == "websocket.receive":
                                if "bytes" in data:
                                    await ttyd_ws.send(data["bytes"])
                                elif "text" in data:
                                    await ttyd_ws.send(data["text"])
                            elif data["type"] == "websocket.disconnect":
                                break
                    except WebSocketDisconnect:
                        pass
                    except Exception as e:
                        logger.debug(f"Forward to ttyd ended: {e}")

                async def forward_to_browser():
                    """Forward messages from ttyd to browser."""
                    try:
                        async for message in ttyd_ws:
                            if websocket.client_state != WebSocketState.CONNECTED:
                                break
                            if isinstance(message, bytes):
                                await websocket.send_bytes(message)
                            else:
                                await websocket.send_text(message)
                    except Exception as e:
                        logger.debug(f"Forward to browser ended: {e}")

                # Run both directions concurrently
                await asyncio.gather(
                    forward_to_ttyd(),
                    forward_to_browser(),
                    return_exceptions=True
                )

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"ttyd WebSocket closed for session {session_id[:12]}: {e}")
        except Exception as e:
            logger.error(f"WebSocket proxy error for session {session_id[:12]}: {e}")
        finally:
            # Clean up WebSocket
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
            logger.info(f"WebSocket proxy ended for session {session_id[:12]}")
    finally:
        # Always release the session reference
        await session_manager.release_session_ref(session)


@app.get("/ttyd/{session_id}/{path:path}")
@app.get("/ttyd/{session_id}")
async def http_proxy(request: Request, session_id: str, path: str = ""):
    """
    HTTP proxy for ttyd static content (HTML, JS, CSS).

    Proxies HTTP requests to ttyd, enabling all traffic through port 8080.
    """
    port = get_session_port(session_id)
    if port is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build the target URL
    target_url = f"http://127.0.0.1:{port}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    try:
        client = await get_http_client()

        # Forward the request with appropriate headers
        headers = {}
        for key, value in request.headers.items():
            # Skip hop-by-hop headers
            if key.lower() not in ('host', 'connection', 'keep-alive', 'transfer-encoding',
                                   'upgrade', 'proxy-connection', 'proxy-authenticate',
                                   'proxy-authorization', 'te', 'trailers'):
                headers[key] = value

        response = await client.get(target_url, headers=headers)

        # Build response headers
        response_headers = {}
        for key, value in response.headers.items():
            if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding',
                                   'connection'):
                response_headers[key] = value

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type')
        )

    except httpx.RequestError as e:
        logger.error(f"HTTP proxy error for session {session_id[:12]}: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to terminal service")


if __name__ == "__main__":
    import uvicorn
    import sys

    try:
        from server.auth import is_auth_enabled
    except ImportError:
        from auth import is_auth_enabled

    # ==========================================================================
    # SECURITY CHECK
    # ==========================================================================
    # Without auth.yaml: localhost only (unauthenticated).
    # With auth.yaml:    any bind address is allowed (authentication enforced).
    # ==========================================================================
    if is_auth_enabled():
        logger.info("auth.yaml found — authentication enabled")
    else:
        ALLOWED_HOSTS = ("127.0.0.1", "localhost")
        if SERVER_HOST not in ALLOWED_HOSTS:
            print("=" * 70)
            print("SECURITY ERROR: Refusing to start!")
            print("=" * 70)
            print(f"SERVER_HOST is set to '{SERVER_HOST}'")
            print()
            print("Authentication is NOT configured (no auth.yaml).")
            print("Without authentication, the server MUST bind to localhost.")
            print()
            print("To enable authentication:")
            print("  cp auth.yaml.example auth.yaml")
            print("  python3 edit_user.py add admin")
            print("=" * 70)
            sys.exit(1)

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, access_log=False)
