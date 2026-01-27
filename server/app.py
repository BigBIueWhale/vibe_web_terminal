#!/usr/bin/env python3
"""
Vibe Web Terminal Server

A web-based terminal service that spawns Docker containers with Vibe CLI.
Each user gets a unique session with a persistent container they can return to.
"""

import asyncio
import hashlib
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
import docker
import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# =============================================================================
# SECURITY CONFIGURATION - DO NOT CHANGE
# =============================================================================
# This server MUST only bind to localhost (127.0.0.1).
# It provides unauthenticated shell access - NEVER expose to the internet!
# =============================================================================
SERVER_HOST = "127.0.0.1"  # SECURITY: localhost only - DO NOT CHANGE TO 0.0.0.0
SERVER_PORT = 8080

# Configuration
DOCKER_IMAGE = "vibe-terminal:latest"
CONTAINER_PREFIX = "vibe-session-"
# No automatic cleanup - containers persist until PC restart
# Users can manually delete via DELETE /session/{id} or ./stop.sh
SESSION_TIMEOUT_HOURS = None  # Disabled
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes (only cleans up stopped containers)
HOST_PORT_START = 17000
HOST_PORT_END = 18000
WORKSPACE_BASE = Path("/tmp/vibe-workspaces")  # /tmp is cleared on reboot

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker client
docker_client = docker.from_env()

# Session storage (in production, use Redis or a database)
sessions: dict[str, dict] = {}
port_allocations: set[int] = set()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return secrets.token_urlsafe(16)


def is_port_in_use(port: int) -> bool:
    """Check if a port is actually in use on the system."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def allocate_port() -> int:
    """Allocate an available port for a container."""
    for port in range(HOST_PORT_START, HOST_PORT_END):
        if port not in port_allocations and not is_port_in_use(port):
            port_allocations.add(port)
            return port
    raise RuntimeError("No available ports")


def release_port(port: int):
    """Release a port allocation."""
    port_allocations.discard(port)


def get_container_name(session_id: str) -> str:
    """Get container name for a session."""
    return f"{CONTAINER_PREFIX}{session_id[:12]}"


async def create_container(session_id: str) -> dict:
    """Create a new Docker container for a session."""
    port = allocate_port()
    container_name = get_container_name(session_id)

    # Create workspace directory
    workspace_dir = WORKSPACE_BASE / session_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(workspace_dir, 0o777)

    try:
        # Remove existing container if any
        try:
            old_container = docker_client.containers.get(container_name)
            old_container.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Create new container
        container = docker_client.containers.run(
            DOCKER_IMAGE,
            name=container_name,
            detach=True,
            ports={"7681/tcp": port},
            volumes={
                str(workspace_dir): {"bind": "/home/vibe/workspace", "mode": "rw"}
            },
            # Allow container to reach host's Ollama
            extra_hosts={"host.docker.internal": "host-gateway"},
            environment={
                "TERM": "xterm-256color",
            },
            mem_limit="2g",
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
        )

        session_data = {
            "session_id": session_id,
            "container_id": container.id,
            "container_name": container_name,
            "port": port,
            "workspace": str(workspace_dir),
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
        }

        sessions[session_id] = session_data
        logger.info(f"Created container {container_name} on port {port}")

        # Wait for ttyd to start
        await asyncio.sleep(2)

        return session_data

    except Exception as e:
        release_port(port)
        logger.error(f"Failed to create container: {e}")
        raise


async def get_or_create_session(session_id: str) -> dict:
    """Get existing session or create a new one."""
    if session_id in sessions:
        session = sessions[session_id]
        session["last_accessed"] = datetime.now().isoformat()

        # Check if container is still running
        try:
            container = docker_client.containers.get(session["container_name"])
            if container.status != "running":
                logger.info(f"Container {session['container_name']} not running, recreating")
                return await create_container(session_id)
        except docker.errors.NotFound:
            logger.info(f"Container {session['container_name']} not found, recreating")
            return await create_container(session_id)

        return session
    else:
        return await create_container(session_id)


async def cleanup_old_sessions():
    """Clean up stopped/dead containers. No time-based expiry - containers persist until reboot."""
    while True:
        try:
            # Only clean up containers that have stopped/died (not time-based)
            for session_id, session in list(sessions.items()):
                try:
                    container = docker_client.containers.get(session["container_name"])
                    if container.status in ("exited", "dead"):
                        # Container stopped - clean up
                        sessions.pop(session_id, None)
                        container.remove(force=True)
                        release_port(session["port"])
                        logger.info(f"Cleaned up stopped container for session {session_id}")
                except docker.errors.NotFound:
                    # Container gone - clean up session
                    sessions.pop(session_id, None)
                    release_port(session.get("port", 0))

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)
    cleanup_task = asyncio.create_task(cleanup_old_sessions())
    logger.info("Vibe Web Terminal server started")

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("Vibe Web Terminal server stopped")


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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page - create new session."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/session/new")
async def create_new_session():
    """Create a new terminal session."""
    session_id = generate_session_id()
    try:
        session = await create_container(session_id)
        return JSONResponse({
            "session_id": session_id,
            "redirect": f"/terminal/{session_id}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/terminal/{session_id}", response_class=HTMLResponse)
async def terminal_page(request: Request, session_id: str):
    """Terminal page for a session."""
    try:
        session = await get_or_create_session(session_id)
        return templates.TemplateResponse("terminal.html", {
            "request": request,
            "session_id": session_id,
            "ttyd_port": session["port"],
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/status")
async def session_status(session_id: str):
    """Get session status."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    try:
        container = docker_client.containers.get(session["container_name"])
        return {
            "session_id": session_id,
            "status": container.status,
            "created_at": session["created_at"],
            "last_accessed": session["last_accessed"],
        }
    except docker.errors.NotFound:
        return {
            "session_id": session_id,
            "status": "not_found",
        }


@app.post("/session/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    path: Optional[str] = None
):
    """Upload a file to the session workspace.

    Args:
        session_id: The session ID
        file: The file to upload
        path: Optional relative path (for folder uploads, preserves structure)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    workspace = Path(session["workspace"])

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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/files")
async def list_files(session_id: str):
    """List files in the session workspace."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    workspace = Path(session["workspace"])

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


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its container."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions.pop(session_id)

    try:
        container = docker_client.containers.get(session["container_name"])
        container.remove(force=True)
    except docker.errors.NotFound:
        pass

    release_port(session["port"])

    # Clean up workspace
    workspace = Path(session["workspace"])
    if workspace.exists():
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)

    return {"status": "deleted"}


@app.get("/sessions")
async def list_sessions():
    """List all active sessions (admin endpoint)."""
    result = []
    for session_id, session in sessions.items():
        try:
            container = docker_client.containers.get(session["container_name"])
            status = container.status
        except docker.errors.NotFound:
            status = "not_found"

        result.append({
            "session_id": session_id,
            "status": status,
            "port": session["port"],
            "created_at": session["created_at"],
            "last_accessed": session["last_accessed"],
        })

    return {"sessions": result}


if __name__ == "__main__":
    import uvicorn
    import sys

    # ==========================================================================
    # SECURITY CHECK - Prevent accidental exposure to the internet
    # ==========================================================================
    ALLOWED_HOSTS = ("127.0.0.1", "localhost")

    if SERVER_HOST not in ALLOWED_HOSTS:
        print("=" * 70)
        print("SECURITY ERROR: Refusing to start!")
        print("=" * 70)
        print(f"SERVER_HOST is set to '{SERVER_HOST}'")
        print()
        print("This server provides UNAUTHENTICATED SHELL ACCESS.")
        print("It MUST only bind to localhost (127.0.0.1).")
        print()
        print("Binding to 0.0.0.0 or a public IP would expose shell access")
        print("to anyone on the network or internet!")
        print("=" * 70)
        sys.exit(1)

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
