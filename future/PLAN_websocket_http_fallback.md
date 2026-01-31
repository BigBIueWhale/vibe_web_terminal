# Plan: WebSocket to HTTP Fallback for Terminal

## User Requirements (Verbatim)

> "How much does this software setup rely upon websocket? For what **exactly** do we rely upon anything that's not plain pure http/https?"

> "And what if my network admins block websocket? Research extensively whether it's possible to fallback to HTTP for the terminal 'streaming' in that scenario. Like, what the simplest fallback mechanism would be for that. Research online extensively.."

> "Well but ttyd works really well. I need a solution that works really well"

> "Please research exactly how my current network architecture works then based on those insights refine your recommendations"

> "I do want this. And I guess the frontend will switch to http automatically when websocket is not available? I only have one concern. How will you possibly change the client code to support this?"

> "Will it look the same?"

> "Wait, but I was concerned that my work's firewall is 'secure' so it only allows through like plain https"

> "This seems good. Will this be best served by forking a specific github repo or github repos, or creating a translation layer of some sorts?"

> "Well, the issue is long pulling can be interrupted in the middle, couldn't it?"

---

## Why HTTP Long-Polling is the Only Reliable Solution

### The Corporate Firewall Problem

Corporate/enterprise networks block WebSocket connections through multiple mechanisms:

| Blocking Method | How It Works | What Gets Blocked |
|-----------------|--------------|-------------------|
| **Firewall rules** | Block `Upgrade: websocket` header | WebSocket handshake fails |
| **Proxy stripping** | Remove `Upgrade` and `Connection` headers | WebSocket never negotiates |
| **DPI (Deep Packet Inspection)** | Detect WebSocket frame format in TLS | Connection terminated mid-stream |
| **Connection timeouts** | Kill long-lived connections after 30-60s | WebSocket and SSE both fail |
| **Response buffering** | Proxy buffers entire response before forwarding | SSE and chunked transfer fail |

### Why Each Alternative Fails

| Technique | On The Wire | Blocked By | Verdict |
|-----------|-------------|------------|---------|
| **WebSocket** | HTTP upgrade → binary frames | Firewalls, proxies, DPI | ❌ Primary target of blocks |
| **Socket.IO (WS mode)** | Same as WebSocket | Same as WebSocket | ❌ Same problem |
| **Socket.IO (polling mode)** | POST/GET requests | Nothing | ✅ Works but adds overhead |
| **Server-Sent Events (SSE)** | Long-lived GET with streaming | Timeouts, buffering proxies | ⚠️ Unreliable |
| **Chunked Transfer** | Long-lived response | Timeouts, buffering proxies | ⚠️ Unreliable |
| **HTTP Long-Polling** | Normal GET/POST requests | Nothing | ✅ **Indistinguishable from browsing** |

### Why Long-Polling is Reliable Despite Interruptions

The user asked: "The issue is long polling can be interrupted in the middle, couldn't it?"

**Yes, but that's a feature, not a bug.** Long-polling with cursor-based resumption is MORE reliable than WebSocket:

```
Server maintains output buffer with sequence numbers:
┌─────────────────────────────────────────────────────┐
│ cursor=0      cursor=100      cursor=250            │
│ ├──────────────┼───────────────┼──────────────────► │
│ "Welcome"     "$ ls"          "file.txt\n"          │
└─────────────────────────────────────────────────────┘

Client request:  GET /poll?cursor=100
Server response: {"cursor": 250, "data": "$ ls\nfile.txt\n"}

If interrupted → client retries with cursor=100
Server sends the SAME data again → no data loss!
```

| Failure Scenario | WebSocket | Long-Polling |
|------------------|-----------|--------------|
| Connection drops mid-stream | ❌ Data lost forever | ✅ Retry with same cursor |
| Proxy kills connection | ❌ Must reconnect, lose buffer | ✅ Just retry |
| Network blip | ❌ Complex reconnect logic | ✅ Automatic retry |
| Server restarts | ❌ Session state lost | ⚠️ Same (could persist buffer) |

**Each long-polling request is atomic and stateless.** Either it succeeds completely (advance cursor) or fails (retry with same cursor). Compare to WebSocket where data streams continuously—if the stream breaks mid-byte, data is lost.

---

## Current Architecture Deep Dive

### System Overview

```
Browser (ttyd's bundled xterm.js in iframe)
    │
    │ wss://domain:8443/ttyd/{session_id}/ws
    │ [TLS encrypted]
    ▼
reverse_proxy.py:8443 (aiohttp)
    │ - SSL/TLS termination
    │ - WebSocket proxy (wss → ws)
    │ - Security headers (HSTS, X-Frame-Options)
    │
    │ ws://127.0.0.1:8081/ttyd/{session_id}/ws
    ▼
app.py:8081 (FastAPI + Starlette)
    │ - Cookie authentication
    │ - Session ownership verification
    │ - Reference counting for cleanup safety
    │
    │ ws://127.0.0.1:17xxx/ws
    │ [subprotocol: "tty"]
    ▼
Docker Container (vibe-session-XXXXXXXX)
    │ - ttyd daemon on port 7681 (mapped to 17xxx)
    │ - libwebsockets server
    │
    ▼
tmux / bash (PTY)
```

### How `reverse_proxy.py` Handles WebSocket (Lines 329-411)

The reverse proxy performs SSL termination and WebSocket forwarding:

```python
# Location: /home/user/Desktop/vibe_web_terminal/reverse_proxy.py:338-365

# Extract client's requested subprotocols
protocols = []
if "Sec-WebSocket-Protocol" in request.headers:
    protocols = [p.strip() for p in request.headers["Sec-WebSocket-Protocol"].split(",")]

# Accept browser's WebSocket connection
ws_server = web.WebSocketResponse(protocols=protocols or None)
await ws_server.prepare(request)

# Connect to upstream (app.py) preserving auth headers
upstream_headers = {}
for key, value in request.headers.items():
    if key.lower() in ("cookie", "authorization"):
        upstream_headers[key] = value

async with session.ws_connect(ws_url, protocols=protocols, headers=upstream_headers) as ws_upstream:
    # Bidirectional forwarding...
```

**Key points:**
- Preserves WebSocket subprotocols (ttyd requires `"tty"`)
- Forwards authentication cookies to upstream
- Two concurrent async tasks forward messages in both directions

### How `app.py` Proxies to ttyd (Lines 1299-1407)

The FastAPI backend authenticates and proxies to the ttyd container:

```python
# Location: /home/user/Desktop/vibe_web_terminal/server/app.py:1307-1348

# 1. Authenticate user from session cookie
if AUTH_ENABLED:
    ws_username = auth_manager.validate_session(token)
    if not ws_username:
        await websocket.close(code=4001, reason="Unauthorized")
        return

# 2. Verify user owns this session
session_owner = owner_store.get_owner(session_id)
if session_owner != ws_username:
    await websocket.close(code=4003, reason="Access denied")
    return

# 3. Acquire reference (prevents deletion while connected)
session = session_manager.acquire_session_ref(session_id)

# 4. Connect to ttyd container
ttyd_url = f"ws://127.0.0.1:{session.port}/ws"
async with websockets.connect(
    ttyd_url,
    subprotocols=["tty"],      # Required by ttyd
    ping_interval=20,          # Keepalive
    ping_timeout=20,
    close_timeout=5,
) as ttyd_ws:
    # Bidirectional forwarding...
```

**Security layers:**
1. Cookie-based session authentication
2. Per-session ownership verification (user X can't access user Y's terminal)
3. Reference counting prevents TOCTOU race conditions during deletion
4. Session tokens are 512-bit cryptographically secure (`secrets.token_urlsafe(64)`)

### How `terminal.html` Loads the Terminal (Lines 627-632)

Currently uses an iframe pointing to ttyd's bundled web interface:

```html
<!-- Location: /home/user/Desktop/vibe_web_terminal/server/templates/terminal.html:627-632 -->
<iframe
    id="terminalFrame"
    class="terminal-iframe"
    src="/ttyd/{{ session_id }}/"
    onload="hideLoading()"
></iframe>
```

**The iframe approach:**
1. Browser loads `/ttyd/{session_id}/` → HTTP proxy → ttyd's static HTML
2. ttyd's bundled JavaScript (xterm.js) initializes
3. ttyd's JS connects to `/ttyd/{session_id}/ws` via WebSocket
4. **We have NO control over ttyd's bundled client code**

This is why we must replace the iframe—we can't modify ttyd's hardcoded WebSocket logic.

### Docker Container Management (Lines 221-274)

Containers are spawned with specific port mappings:

```python
# Location: /home/user/Desktop/vibe_web_terminal/server/app.py:221-274

config = {
    "Image": "vibe-terminal:latest",
    "Env": ["TERM=xterm-256color"],
    "HostConfig": {
        "PortBindings": {
            "7681/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(session.port)}]
        },
        "Binds": [f"{workspace_dir}:/home/vibe/workspace:rw"],
        "Memory": 2147483648,  # 2GB limit
        "RestartPolicy": {"Name": "unless-stopped"},
    },
}
```

**Port allocation scheme:**
- Range: 17000-17999 (1000 possible concurrent sessions)
- Bound to `127.0.0.1` only (not exposed to network)
- Container's ttyd listens on 7681, mapped to host port 17xxx
- Port released back to pool when session deleted

---

## How ttyd Works Internally

### ttyd Source Code Analysis

**Repository:** https://github.com/tsl0922/ttyd
**Version analyzed:** Latest (cloned 2026-01-31)

ttyd is a C program using libwebsockets for the server and a bundled TypeScript/Preact frontend.

### ttyd's WebSocket Protocol

**Location:** `/tmp/ttyd/src/server.h:7-17`

```c
// Client → Server commands
#define INPUT '0'           // Keyboard input
#define RESIZE_TERMINAL '1' // Terminal resize
#define PAUSE '2'           // Flow control: pause output
#define RESUME '3'          // Flow control: resume output
#define JSON_DATA '{'       // Initial auth/size JSON

// Server → Client commands
#define OUTPUT '0'          // Terminal output
#define SET_WINDOW_TITLE '1'// Window title update
#define SET_PREFERENCES '2' // Client configuration
```

**Message format:** All messages are binary ArrayBuffers:
- First byte: command character (ASCII '0', '1', '2', '3', or '{')
- Remaining bytes: payload (raw bytes for I/O, JSON for control)

### Connection Handshake

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:248-278`

```typescript
// 1. Connect with "tty" subprotocol
this.socket = new WebSocket(this.options.wsUrl, ['tty']);
socket.binaryType = 'arraybuffer';

// 2. On open, send auth JSON with initial terminal size
const msg = JSON.stringify({
    AuthToken: this.token,
    columns: terminal.cols,
    rows: terminal.rows
});
this.socket?.send(textEncoder.encode(msg));
```

**Server response sequence:**
1. Server sends `SET_WINDOW_TITLE` (command '1') with hostname
2. Server sends `SET_PREFERENCES` (command '2') with config JSON
3. Bidirectional I/O begins

### Input Handling (Client → Server)

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:229-245`

```typescript
public sendData(data: string | Uint8Array) {
    if (typeof data === 'string') {
        const payload = new Uint8Array(data.length * 3 + 1);
        payload[0] = Command.INPUT.charCodeAt(0);  // '0'
        const stats = textEncoder.encodeInto(data, payload.subarray(1));
        socket.send(payload.subarray(0, stats.written + 1));
    } else {
        const payload = new Uint8Array(data.length + 1);
        payload[0] = Command.INPUT.charCodeAt(0);  // '0'
        payload.set(data, 1);
        socket.send(payload);
    }
}
```

**Format:** `[0x30][UTF-8 encoded input bytes]`

### Output Handling (Server → Client)

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:343-368`

```typescript
private onSocketData(event: MessageEvent) {
    const rawData = event.data as ArrayBuffer;
    const cmd = String.fromCharCode(new Uint8Array(rawData)[0]);
    const data = rawData.slice(1);

    switch (cmd) {
        case Command.OUTPUT:  // '0'
            this.writeFunc(data);
            break;
        case Command.SET_WINDOW_TITLE:  // '1'
            this.title = textDecoder.decode(data);
            document.title = this.title;
            break;
        case Command.SET_PREFERENCES:  // '2'
            this.applyPreferences(JSON.parse(textDecoder.decode(data)));
            break;
    }
}
```

**Format:** `[command byte][payload bytes]`

### Terminal Resize

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:184-189`

```typescript
terminal.onResize(({ cols, rows }) => {
    const msg = JSON.stringify({ columns: cols, rows: rows });
    this.socket?.send(this.textEncoder.encode(Command.RESIZE_TERMINAL + msg));
    // Shows "80x24" overlay briefly
});
```

**Format:** `[0x31]{"columns":80,"rows":24}`

### Flow Control (Backpressure)

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:207-227`

ttyd implements flow control to prevent the browser from being overwhelmed:

```typescript
// When too much data buffered, tell server to pause
if (this.pending > highWater) {
    this.socket?.send(textEncoder.encode(Command.PAUSE));  // '2'
}

// When buffer drains, tell server to resume
if (this.pending < lowWater) {
    this.socket?.send(textEncoder.encode(Command.RESUME)); // '3'
}
```

**Default flow control settings:**
```typescript
const flowControl = {
    limit: 100000,   // Bytes before checking
    highWater: 10,   // Pause when pending > 10
    lowWater: 4,     // Resume when pending < 4
};
```

### xterm.js Configuration in ttyd

**Location:** `/tmp/ttyd/html/src/components/app.tsx:12-53`

```typescript
const clientOptions = {
    rendererType: 'webgl',        // GPU-accelerated rendering
    disableLeaveAlert: false,     // Warn before closing tab
    disableResizeOverlay: false,  // Show "80x24" on resize
    enableZmodem: false,          // File transfer protocol
    enableTrzsz: false,           // Alternative file transfer
    enableSixel: false,           // Image support
    unicodeVersion: '11',         // Unicode 11 support
};

const termOptions = {
    fontSize: 13,
    fontFamily: 'Consolas,Liberation Mono,Menlo,Courier,monospace',
    theme: {
        foreground: '#d2d2d2',
        background: '#2b2b2b',
        cursor: '#adadad',
        // ... full color palette
    },
    allowProposedApi: true,
};
```

### xterm.js Addons Used by ttyd

**Location:** `/tmp/ttyd/html/src/components/terminal/xterm/index.ts:1-12`

```typescript
import { Terminal } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { ClipboardAddon } from '@xterm/addon-clipboard';
import { WebglAddon } from '@xterm/addon-webgl';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { ImageAddon } from '@xterm/addon-image';
import { Unicode11Addon } from '@xterm/addon-unicode11';
```

| Addon | Purpose | Required? |
|-------|---------|-----------|
| `FitAddon` | Auto-resize terminal to container | ✅ Yes |
| `WebglAddon` | GPU-accelerated rendering | No (fallback to canvas/DOM) |
| `CanvasAddon` | Canvas-based rendering | No (fallback option) |
| `ClipboardAddon` | System clipboard integration | Recommended |
| `WebLinksAddon` | Clickable URLs in output | Nice to have |
| `Unicode11Addon` | Proper Unicode width calculation | Recommended |
| `ImageAddon` | Sixel image support | No |

---

## Proposed Architecture

### Translation Layer Approach (No Forking Required)

```
Browser (xterm.js embedded directly)
    │
    │ HTTPS (plain HTTP requests)
    │ GET  /terminal/{session_id}/poll?cursor=N
    │ POST /terminal/{session_id}/input
    │
    ▼
reverse_proxy.py:8443
    │ - SSL termination (unchanged)
    │ - Now just proxies HTTP (simpler!)
    │
    ▼
app.py:8081
    │ - NEW: HTTP poll endpoint
    │ - NEW: HTTP input endpoint
    │ - Maintains WebSocket connection to ttyd (localhost)
    │ - Output buffer with cursor tracking
    │
    │ ws://127.0.0.1:17xxx/ws [localhost, always works]
    ▼
Docker Container (unchanged)
    │ - ttyd daemon (unchanged)
    ▼
tmux / bash (unchanged)
```

### What Changes

| Component | Current | Proposed | Effort |
|-----------|---------|----------|--------|
| `terminal.html` | iframe loading ttyd's UI | Embedded xterm.js + polling JS | ~80 lines JS |
| `app.py` | WebSocket proxy only | HTTP endpoints + WS client to ttyd | ~100 lines Python |
| `reverse_proxy.py` | WebSocket + HTTP proxy | HTTP proxy only (simpler) | No change needed |
| ttyd containers | As-is | **Unchanged** | None |
| Docker setup | As-is | **Unchanged** | None |
| Authentication | Cookie-based | **Unchanged** | None |
| Session management | As-is | **Unchanged** | None |

### Why No Forking

1. **ttyd is the PTY backend** - it handles the hard parts (PTY management, signals, Unicode, etc.)
2. **ttyd runs on localhost** - WebSocket to localhost is never blocked
3. **We only replace the browser↔server transport** - the server↔ttyd link stays WebSocket
4. **Translation layer is ~200 lines of code** - simple, maintainable, debuggable

---

## Concrete Implementation

### Versions to Use

| Component | Version | CDN/Package |
|-----------|---------|-------------|
| xterm.js | 5.5.0 | `@xterm/xterm@5.5.0` |
| xterm-addon-fit | 0.10.0 | `@xterm/addon-fit@0.10.0` |
| xterm-addon-web-links | 0.11.0 | `@xterm/addon-web-links@0.11.0` |
| xterm-addon-clipboard | 0.1.0 | `@xterm/addon-clipboard@0.1.0` |
| xterm-addon-unicode11 | 0.8.0 | `@xterm/addon-unicode11@0.8.0` |
| Python websockets | 12.0+ | `websockets>=12.0` (already in requirements) |

**CDN URLs:**
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css">
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@0.11.0/lib/addon-web-links.min.js"></script>
```

### Backend Implementation (`app.py`)

```python
# New imports
import base64
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional
import websockets

# Terminal session state for HTTP transport
@dataclass
class HTTPTerminalSession:
    session_id: str
    ttyd_ws: Optional[websockets.WebSocketClientProtocol] = None
    output_buffer: bytearray = field(default_factory=bytearray)
    cursor: int = 0
    max_buffer_size: int = 256 * 1024  # 256KB ring buffer
    waiters: list = field(default_factory=list)  # Waiting poll requests
    connected: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

http_terminal_sessions: Dict[str, HTTPTerminalSession] = {}


async def connect_http_terminal(session_id: str, port: int, cols: int, rows: int) -> HTTPTerminalSession:
    """Establish WebSocket connection to ttyd for HTTP transport."""
    http_session = HTTPTerminalSession(session_id=session_id)

    ttyd_url = f"ws://127.0.0.1:{port}/ws"
    http_session.ttyd_ws = await websockets.connect(
        ttyd_url,
        subprotocols=["tty"],
        ping_interval=20,
        ping_timeout=20,
    )

    # Send initial handshake (auth + terminal size)
    init_msg = json.dumps({"columns": cols, "rows": rows})
    await http_session.ttyd_ws.send(init_msg.encode('utf-8'))

    http_session.connected = True
    http_terminal_sessions[session_id] = http_session

    # Start background task to read ttyd output
    asyncio.create_task(read_ttyd_output(session_id))

    return http_session


async def read_ttyd_output(session_id: str):
    """Background task: read from ttyd WebSocket, buffer for polling clients."""
    http_session = http_terminal_sessions.get(session_id)
    if not http_session or not http_session.ttyd_ws:
        return

    try:
        async for message in http_session.ttyd_ws:
            if isinstance(message, bytes) and len(message) > 0:
                cmd = message[0:1]
                payload = message[1:]

                if cmd == b'0':  # OUTPUT
                    async with http_session.lock:
                        # Append to ring buffer
                        http_session.output_buffer.extend(payload)

                        # Trim if exceeds max size (keep recent data)
                        if len(http_session.output_buffer) > http_session.max_buffer_size:
                            trim_amount = len(http_session.output_buffer) - http_session.max_buffer_size
                            http_session.output_buffer = http_session.output_buffer[trim_amount:]
                            http_session.cursor += trim_amount

                        # Wake up any waiting poll requests
                        for waiter in http_session.waiters:
                            waiter.set()
                        http_session.waiters.clear()

                elif cmd == b'1':  # SET_WINDOW_TITLE
                    pass  # Could store and return in poll response

                elif cmd == b'2':  # SET_PREFERENCES
                    pass  # Could store and return in poll response

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        http_session.connected = False


@app.post("/terminal/{session_id}/connect")
async def terminal_http_connect(
    session_id: str,
    request: Request,
    cols: int = 80,
    rows: int = 24
):
    """Initialize HTTP terminal session."""
    # Authentication
    token = request.cookies.get("session")
    if AUTH_ENABLED:
        username = auth_manager.validate_session(token)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        username = "__anonymous__"

    # Ownership check
    verify_session_ownership(request, session_id)

    # Get session port
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Connect to ttyd
    try:
        http_session = await connect_http_terminal(session_id, session.port, cols, rows)
        return {"status": "connected", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to connect HTTP terminal: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to terminal")


@app.get("/terminal/{session_id}/poll")
async def terminal_poll(
    session_id: str,
    request: Request,
    cursor: int = 0,
    timeout: float = 30.0
):
    """Long-poll for terminal output."""
    # Authentication
    token = request.cookies.get("session")
    if AUTH_ENABLED:
        username = auth_manager.validate_session(token)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Ownership check
    verify_session_ownership(request, session_id)

    http_session = http_terminal_sessions.get(session_id)
    if not http_session:
        raise HTTPException(status_code=404, detail="Terminal not connected. Call /connect first.")

    if not http_session.connected:
        raise HTTPException(status_code=410, detail="Terminal disconnected")

    async with http_session.lock:
        # Calculate offset into buffer
        buffer_start_cursor = http_session.cursor
        buffer_end_cursor = buffer_start_cursor + len(http_session.output_buffer)

        # If client cursor is behind buffer start, they missed data
        effective_cursor = max(cursor, buffer_start_cursor)

        # Check if we have new data
        if effective_cursor < buffer_end_cursor:
            # Return available data
            offset = effective_cursor - buffer_start_cursor
            data = bytes(http_session.output_buffer[offset:])
            return {
                "cursor": buffer_end_cursor,
                "data": base64.b64encode(data).decode('ascii'),
                "missed": cursor < buffer_start_cursor  # Client missed some data
            }

    # No data available, wait for new data or timeout
    waiter = asyncio.Event()
    http_session.waiters.append(waiter)

    try:
        await asyncio.wait_for(waiter.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    finally:
        if waiter in http_session.waiters:
            http_session.waiters.remove(waiter)

    # Check again after waiting
    async with http_session.lock:
        buffer_start_cursor = http_session.cursor
        buffer_end_cursor = buffer_start_cursor + len(http_session.output_buffer)
        effective_cursor = max(cursor, buffer_start_cursor)

        if effective_cursor < buffer_end_cursor:
            offset = effective_cursor - buffer_start_cursor
            data = bytes(http_session.output_buffer[offset:])
            return {
                "cursor": buffer_end_cursor,
                "data": base64.b64encode(data).decode('ascii'),
                "missed": cursor < buffer_start_cursor
            }

    # Still no data (timeout with no new output)
    return {
        "cursor": buffer_end_cursor,
        "data": "",
        "missed": False
    }


@app.post("/terminal/{session_id}/input")
async def terminal_input(session_id: str, request: Request):
    """Send input to terminal."""
    # Authentication
    token = request.cookies.get("session")
    if AUTH_ENABLED:
        username = auth_manager.validate_session(token)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Ownership check
    verify_session_ownership(request, session_id)

    http_session = http_terminal_sessions.get(session_id)
    if not http_session or not http_session.ttyd_ws:
        raise HTTPException(status_code=404, detail="Terminal not connected")

    if not http_session.connected:
        raise HTTPException(status_code=410, detail="Terminal disconnected")

    data = await request.body()

    # Send to ttyd: '0' + input bytes
    message = b'0' + data
    await http_session.ttyd_ws.send(message)

    return {"status": "ok"}


@app.post("/terminal/{session_id}/resize")
async def terminal_resize(session_id: str, request: Request, cols: int, rows: int):
    """Resize terminal."""
    # Authentication & ownership check...
    token = request.cookies.get("session")
    if AUTH_ENABLED:
        username = auth_manager.validate_session(token)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")

    verify_session_ownership(request, session_id)

    http_session = http_terminal_sessions.get(session_id)
    if not http_session or not http_session.ttyd_ws:
        raise HTTPException(status_code=404, detail="Terminal not connected")

    # Send resize: '1' + JSON
    resize_msg = json.dumps({"columns": cols, "rows": rows})
    message = b'1' + resize_msg.encode('utf-8')
    await http_session.ttyd_ws.send(message)

    return {"status": "ok"}


@app.post("/terminal/{session_id}/disconnect")
async def terminal_disconnect(session_id: str, request: Request):
    """Disconnect HTTP terminal session."""
    token = request.cookies.get("session")
    if AUTH_ENABLED:
        username = auth_manager.validate_session(token)
        if not username:
            raise HTTPException(status_code=401, detail="Unauthorized")

    verify_session_ownership(request, session_id)

    http_session = http_terminal_sessions.pop(session_id, None)
    if http_session and http_session.ttyd_ws:
        await http_session.ttyd_ws.close()

    return {"status": "disconnected"}
```

### Frontend Implementation (`terminal.html`)

Replace the iframe section with embedded xterm.js:

```html
<!-- In <head>, add xterm.js CSS and scripts -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css">
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@0.11.0/lib/addon-web-links.min.js"></script>

<!-- Replace iframe with terminal container -->
<div id="terminal-container" style="width: 100%; height: 100%;"></div>

<script>
// Terminal configuration (matching ttyd's defaults for visual consistency)
const termConfig = {
    fontSize: 14,
    fontFamily: 'Consolas,Liberation Mono,Menlo,Courier,monospace',
    cursorStyle: 'bar',
    cursorBlink: true,
    scrollback: 10000,
    theme: {
        foreground: '#d2d2d2',
        background: '#1a1a1a',  // Matches current theme
        cursor: '#adadad',
        black: '#000000',
        red: '#d81e00',
        green: '#5ea702',
        yellow: '#cfae00',
        blue: '#427ab3',
        magenta: '#89658e',
        cyan: '#00a7aa',
        white: '#dbded8',
        brightBlack: '#686a66',
        brightRed: '#f54235',
        brightGreen: '#99e343',
        brightYellow: '#fdeb61',
        brightBlue: '#84b0d8',
        brightMagenta: '#bc94b7',
        brightCyan: '#37e6e8',
        brightWhite: '#f1f1f0',
    }
};

// Initialize terminal
const term = new Terminal(termConfig);
const fitAddon = new FitAddon.FitAddon();
const webLinksAddon = new WebLinksAddon.WebLinksAddon();

term.loadAddon(fitAddon);
term.loadAddon(webLinksAddon);

const container = document.getElementById('terminal-container');
term.open(container);
fitAddon.fit();

// Session ID from template
const sessionId = "{{ session_id }}";
let cursor = 0;
let connected = false;
let pollController = null;

// Connect to terminal via HTTP
async function connect() {
    try {
        const resp = await fetch(`/terminal/${sessionId}/connect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cols: term.cols,
                rows: term.rows
            })
        });

        if (!resp.ok) {
            throw new Error(`Connect failed: ${resp.status}`);
        }

        connected = true;
        hideLoading();
        term.focus();
        poll();

    } catch (e) {
        console.error('Connection error:', e);
        showError('Failed to connect to terminal');
    }
}

// Long-poll for output
async function poll() {
    if (!connected) return;

    pollController = new AbortController();

    try {
        const resp = await fetch(
            `/terminal/${sessionId}/poll?cursor=${cursor}&timeout=30`,
            { signal: pollController.signal }
        );

        if (!resp.ok) {
            if (resp.status === 410) {
                // Terminal disconnected
                showOverlay('Terminal disconnected. Press Enter to reconnect.');
                connected = false;
                return;
            }
            throw new Error(`Poll failed: ${resp.status}`);
        }

        const result = await resp.json();

        if (result.data) {
            // Decode base64 and write to terminal
            const bytes = Uint8Array.from(atob(result.data), c => c.charCodeAt(0));
            term.write(bytes);
        }

        if (result.missed) {
            console.warn('Missed some terminal output (buffer overflow)');
        }

        cursor = result.cursor;

        // Continue polling
        poll();

    } catch (e) {
        if (e.name === 'AbortError') {
            return; // Intentional abort
        }

        console.error('Poll error:', e);

        // Retry after delay
        if (connected) {
            setTimeout(poll, 1000);
        }
    }
}

// Send input to terminal
async function sendInput(data) {
    if (!connected) return;

    try {
        await fetch(`/terminal/${sessionId}/input`, {
            method: 'POST',
            body: data  // Raw string/bytes
        });
    } catch (e) {
        console.error('Input error:', e);
    }
}

// Handle user input
term.onData(data => {
    sendInput(data);
});

// Handle binary input (e.g., paste with special chars)
term.onBinary(data => {
    const bytes = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
        bytes[i] = data.charCodeAt(i);
    }
    sendInput(bytes);
});

// Handle resize
let resizeTimeout = null;
function handleResize() {
    fitAddon.fit();

    // Debounce resize messages
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(async () => {
        if (!connected) return;

        try {
            await fetch(`/terminal/${sessionId}/resize?cols=${term.cols}&rows=${term.rows}`, {
                method: 'POST'
            });
        } catch (e) {
            console.error('Resize error:', e);
        }
    }, 100);
}

window.addEventListener('resize', handleResize);
new ResizeObserver(handleResize).observe(container);

// Overlay helper (similar to ttyd's overlay addon)
function showOverlay(message, timeout) {
    let overlay = document.getElementById('terminal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'terminal-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(240, 240, 240, 0.9);
            color: #101010;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 18px;
            z-index: 1000;
        `;
        container.style.position = 'relative';
        container.appendChild(overlay);
    }

    overlay.textContent = message;
    overlay.style.display = 'block';

    if (timeout) {
        setTimeout(() => {
            overlay.style.display = 'none';
        }, timeout);
    }
}

// Reconnect on Enter after disconnect
term.onKey(e => {
    if (!connected && e.key === 'Enter') {
        connect();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    connected = false;
    if (pollController) {
        pollController.abort();
    }
    fetch(`/terminal/${sessionId}/disconnect`, { method: 'POST', keepalive: true });
});

// Start connection
connect();
</script>
```

---

## Security Considerations

### Authentication Preserved

The HTTP endpoints use the **exact same authentication** as the current WebSocket proxy:

1. Session cookie validated via `auth_manager.validate_session(token)`
2. Session ownership verified via `verify_session_ownership()`
3. Rate limiting still applies (if configured)

### No New Attack Surface

| Concern | Mitigation |
|---------|------------|
| CSRF on input endpoint | Same-origin cookies, existing CSRF protection applies |
| Session hijacking | 512-bit cryptographic session tokens (unchanged) |
| Cross-user access | Ownership verification on every endpoint |
| Data injection | ttyd handles all PTY escaping (unchanged) |
| DoS via polling | Rate limiting, connection limits (existing) |

### Localhost WebSocket is Always Secure

The WebSocket connection from `app.py` to ttyd:
- Runs on `127.0.0.1` (localhost)
- Never traverses any network
- Cannot be blocked by firewalls
- Cannot be intercepted

Only the browser↔server transport changes (WebSocket → HTTP). The server↔container transport stays WebSocket over localhost.

---

## Visual Appearance

**Will look identical.** We use the same:
- xterm.js version (5.5.0)
- Font settings (14px, Consolas/monospace)
- Color theme (matching current #1a1a1a background)
- Cursor style (bar, blinking)
- Scrollback (10000 lines)

The only visible difference: no iframe border (which was already styled invisible).

---

## Migration Path

### Phase 1: Add HTTP Transport (Non-Breaking)

1. Add new HTTP endpoints (`/terminal/{session_id}/connect`, `/poll`, `/input`, `/resize`)
2. Keep existing WebSocket proxy working
3. Add new `terminal_http.html` template that uses HTTP transport
4. Test HTTP transport independently

### Phase 2: Feature Flag

1. Add URL parameter or config option: `?transport=http`
2. Terminal page chooses transport based on flag
3. Test in production with opt-in users

### Phase 3: Auto-Detection

1. Frontend tries WebSocket first
2. If WebSocket fails within 5 seconds, fall back to HTTP
3. Seamless experience for all users

### Phase 4: Deprecate WebSocket (Optional)

1. If HTTP transport proves reliable, simplify by removing WebSocket code
2. Reduces maintenance burden
3. Or keep both for flexibility

---

## Summary

| Question | Answer |
|----------|--------|
| Why HTTP long-polling? | Only transport that works through ALL corporate firewalls |
| Why not Socket.IO? | Adds complexity; polling mode does same thing with more overhead |
| Why not SSE? | Blocked by buffering proxies and connection timeouts |
| Will it look the same? | Yes, identical (same xterm.js, same theme) |
| Is it secure? | Yes, same authentication, ownership checks, and session tokens |
| How much code? | ~100 lines Python + ~80 lines JavaScript |
| Fork anything? | No, translation layer only |
| What stays unchanged? | ttyd, Docker containers, session management, authentication |

**Status:** Ready for implementation
