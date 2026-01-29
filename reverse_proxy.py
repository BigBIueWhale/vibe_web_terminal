#!/usr/bin/env python3
"""
SSL-Terminating Reverse Proxy for Vibe Web Terminal

A standalone Python reverse proxy using aiohttp that sits in front of the
Vibe Web Terminal server (localhost:8081). It handles:

  - TLS/SSL termination (HTTPS on port 8443 by default)
  - WebSocket proxying (required for terminal connections)
  - Security headers (HSTS, X-Frame-Options, etc.)

Only this proxy is exposed to the public internet. The backend server
remains bound to localhost.

Architecture:
    Internet --> reverse_proxy.py :8443 (SSL) --> localhost:8081 (vibe server)

Usage:
    python3 reverse_proxy.py \\
        --cert certs/self-signed/fullchain.pem \\
        --key certs/self-signed/privkey.pem

Prerequisites:
    pip install aiohttp
"""

import argparse
import asyncio
import logging
import os
import shutil
import ssl
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
from aiohttp import web

# ============================================================================
# Configuration
# ============================================================================

UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8081
CERTS_DIR = Path(__file__).parent / "certs"
ACME_WEBROOT = Path(__file__).parent / "acme-webroot"

# How often to check if certificate needs renewal (hours)
RENEWAL_CHECK_INTERVAL_HOURS = 12

# Renew when certificate expires within this many days
RENEWAL_THRESHOLD_DAYS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reverse-proxy")
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


# ============================================================================
# Certificate Management
# ============================================================================

class CertManager:
    """
    Manages SSL certificates — either manual files or Let's Encrypt via certbot.

    For Let's Encrypt:
      1. Serves ACME HTTP-01 challenges from acme-webroot/
      2. Runs certbot in --webroot mode to obtain/renew certificates
      3. Stores certificates in certs/<domain>/
      4. Checks for renewal every 12 hours
    """

    def __init__(self, domain: str, email: str):
        self.domain = domain
        self.email = email
        self.cert_dir = CERTS_DIR / domain
        self.cert_path = self.cert_dir / "fullchain.pem"
        self.key_path = self.cert_dir / "privkey.pem"

    def has_certificates(self) -> bool:
        """Check if certificate files exist."""
        return self.cert_path.is_file() and self.key_path.is_file()

    def obtain_certificate(self) -> bool:
        """
        Obtain a certificate from Let's Encrypt using certbot.

        Requires the HTTP server to be running on port 80 to serve
        ACME challenge files from the webroot directory.
        """
        certbot = shutil.which("certbot")
        if not certbot:
            logger.error(
                "certbot not found. Install it with:\n"
                "  Ubuntu/Debian: sudo apt install certbot\n"
                "  pip:           pip install certbot"
            )
            return False

        # Ensure directories exist
        ACME_WEBROOT.mkdir(parents=True, exist_ok=True)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        # Build certbot command
        cmd = [
            certbot, "certonly",
            "--webroot",
            "--webroot-path", str(ACME_WEBROOT),
            "--domain", self.domain,
            "--email", self.email,
            "--agree-tos",
            "--non-interactive",
            "--cert-path", str(self.cert_path),
            "--key-path", str(self.key_path),
            "--fullchain-path", str(self.cert_path),
        ]

        logger.info("Running certbot to obtain certificate for %s ...", self.domain)
        logger.info("Command: %s", " ".join(cmd))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info("Certificate obtained successfully")
                # Copy from certbot's default location if our paths weren't used
                self._copy_from_certbot_live()
                return True
            else:
                logger.error("certbot failed (exit %d):\n%s\n%s",
                             result.returncode, result.stdout, result.stderr)
                return False
        except subprocess.TimeoutExpired:
            logger.error("certbot timed out after 120 seconds")
            return False
        except Exception as e:
            logger.error("Failed to run certbot: %s", e)
            return False

    def _copy_from_certbot_live(self) -> None:
        """Copy certs from certbot's default live directory if needed."""
        live_dir = Path(f"/etc/letsencrypt/live/{self.domain}")
        if live_dir.is_dir() and not self.has_certificates():
            try:
                self.cert_dir.mkdir(parents=True, exist_ok=True)
                for src_name, dst_path in [
                    ("fullchain.pem", self.cert_path),
                    ("privkey.pem", self.key_path),
                ]:
                    src = live_dir / src_name
                    if src.is_file():
                        shutil.copy2(src, dst_path)
                        logger.info("Copied %s to %s", src, dst_path)
            except Exception as e:
                logger.warning("Could not copy certs from %s: %s", live_dir, e)

    def renew_certificate(self) -> bool:
        """
        Attempt to renew the certificate via certbot renew.

        Returns True if renewal succeeded or wasn't needed.
        """
        certbot = shutil.which("certbot")
        if not certbot:
            return False

        logger.info("Checking certificate renewal for %s ...", self.domain)
        try:
            result = subprocess.run(
                [certbot, "renew", "--non-interactive", "--quiet"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                self._copy_from_certbot_live()
                logger.info("Certificate renewal check complete")
                return True
            else:
                logger.warning("certbot renew returned %d: %s",
                               result.returncode, result.stderr)
                return False
        except Exception as e:
            logger.error("Certificate renewal error: %s", e)
            return False

    def needs_renewal(self) -> bool:
        """Check if the certificate expires within the threshold."""
        if not self.has_certificates():
            return True
        try:
            import ssl as _ssl
            cert_info = _ssl.SSLContext().load_cert_chain(
                str(self.cert_path), str(self.key_path)
            )
            # Use openssl to check expiry
            result = subprocess.run(
                ["openssl", "x509", "-enddate", "-noout", "-in", str(self.cert_path)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                # Parse "notAfter=Jan 29 12:00:00 2025 GMT"
                line = result.stdout.strip()
                date_str = line.split("=", 1)[1]
                from email.utils import parsedate_to_datetime
                expiry = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - datetime.utcnow()).days
                logger.info("Certificate expires in %d days", days_left)
                return days_left < RENEWAL_THRESHOLD_DAYS
        except Exception as e:
            logger.warning("Could not check cert expiry: %s", e)
        return False


def create_ssl_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    """Create an SSL context for the HTTPS server."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    # Modern TLS settings
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers(
        "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
    )
    return ctx


# ============================================================================
# Reverse Proxy Handlers
# ============================================================================

# Shared client session (reused across requests)
_client_session: aiohttp.ClientSession | None = None


async def get_client_session() -> aiohttp.ClientSession:
    """Get or create the shared HTTP client session."""
    global _client_session
    if _client_session is None or _client_session.closed:
        _client_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300, connect=10),
        )
    return _client_session


# Headers to strip when proxying
HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "transfer-encoding", "te", "trailers",
    "upgrade", "proxy-authorization", "proxy-authenticate",
    "proxy-connection",
})

# Security headers added to all responses
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


async def proxy_handler(request: web.Request) -> web.StreamResponse:
    """
    Main proxy handler — routes HTTP and WebSocket requests to upstream.

    WebSocket detection: checks the Upgrade header. If present and set to
    "websocket", the request is handled as a WebSocket proxy. Otherwise,
    it's a standard HTTP reverse proxy.
    """
    # WebSocket upgrade
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await websocket_proxy(request)

    # Regular HTTP proxy
    return await http_proxy(request)


async def http_proxy(request: web.Request) -> web.StreamResponse:
    """Proxy an HTTP request to the upstream server."""
    target_url = f"http://{UPSTREAM_HOST}:{UPSTREAM_PORT}{request.path_qs}"

    # Build upstream headers (strip hop-by-hop)
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in HOP_BY_HOP:
            headers[key] = value
    # Set correct Host and forwarding headers
    headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
    headers["X-Forwarded-For"] = request.remote or "unknown"
    headers["X-Forwarded-Proto"] = request.scheme
    headers["X-Real-IP"] = request.remote or "unknown"

    try:
        session = await get_client_session()
        body = await request.read()

        async with session.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=body,
            allow_redirects=False,
        ) as upstream_resp:
            # Build response headers
            resp_headers = dict(SECURITY_HEADERS)
            for key, value in upstream_resp.headers.items():
                if key.lower() not in HOP_BY_HOP and key.lower() != "content-length":
                    resp_headers[key] = value

            response = web.StreamResponse(
                status=upstream_resp.status,
                headers=resp_headers,
            )
            await response.prepare(request)

            async for chunk in upstream_resp.content.iter_any():
                await response.write(chunk)

            await response.write_eof()
            return response

    except aiohttp.ClientError as e:
        logger.error("Proxy error: %s", e)
        return web.Response(status=502, text="Bad Gateway")


async def websocket_proxy(request: web.Request) -> web.WebSocketResponse:
    """
    Proxy a WebSocket connection to the upstream server.

    Handles bidirectional message forwarding between the browser client
    and the upstream ttyd WebSocket. Supports both binary and text frames
    (ttyd uses binary frames for terminal I/O).
    """
    # Extract subprotocols from client request
    protocols = []
    if "Sec-WebSocket-Protocol" in request.headers:
        protocols = [
            p.strip()
            for p in request.headers["Sec-WebSocket-Protocol"].split(",")
        ]

    # Accept the client WebSocket
    ws_server = web.WebSocketResponse(protocols=protocols or None)
    await ws_server.prepare(request)

    # Connect to upstream WebSocket, forwarding cookies and relevant headers
    target_url = f"http://{UPSTREAM_HOST}:{UPSTREAM_PORT}{request.path_qs}"
    ws_url = target_url.replace("http://", "ws://")

    # Forward headers that the upstream may need (especially Cookie for auth)
    upstream_headers = {}
    for key, value in request.headers.items():
        if key.lower() in ("cookie", "authorization"):
            upstream_headers[key] = value

    try:
        session = await get_client_session()
        async with session.ws_connect(
            ws_url,
            protocols=protocols or None,
            headers=upstream_headers,
        ) as ws_upstream:

            async def forward_to_upstream():
                """Forward messages from client to upstream."""
                try:
                    async for msg in ws_server:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_upstream.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_upstream.send_str(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE,
                                          aiohttp.WSMsgType.CLOSING,
                                          aiohttp.WSMsgType.CLOSED,
                                          aiohttp.WSMsgType.ERROR):
                            break
                except Exception as e:
                    logger.debug("WS forward to upstream ended: %s", e)

            async def forward_to_client():
                """Forward messages from upstream to client."""
                try:
                    async for msg in ws_upstream:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_server.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_server.send_str(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE,
                                          aiohttp.WSMsgType.CLOSING,
                                          aiohttp.WSMsgType.CLOSED,
                                          aiohttp.WSMsgType.ERROR):
                            break
                except Exception as e:
                    logger.debug("WS forward to client ended: %s", e)

            # Run both directions concurrently
            await asyncio.gather(
                forward_to_upstream(),
                forward_to_client(),
                return_exceptions=True,
            )

    except aiohttp.ClientError as e:
        logger.error("WebSocket proxy connection error: %s", e)
        if not ws_server.closed:
            await ws_server.close(code=1011, message=b"Upstream connection failed")

    return ws_server


# ============================================================================
# HTTP Server (port 80) — ACME challenges only (used by --auto-ssl)
# ============================================================================

async def http_redirect_handler(request: web.Request) -> web.Response:
    """
    Handle HTTP requests on port 80 (auto-ssl mode only):
      - /.well-known/acme-challenge/*  → serve ACME challenge files
      - Everything else               → 301 redirect to HTTPS on port 8443
    """
    # Serve ACME challenge files for Let's Encrypt
    if request.path.startswith("/.well-known/acme-challenge/"):
        token = request.path.split("/")[-1]
        challenge_file = ACME_WEBROOT / ".well-known" / "acme-challenge" / token
        if challenge_file.is_file():
            return web.FileResponse(challenge_file)
        return web.Response(status=404, text="Challenge not found")

    # Redirect everything else to HTTPS on port 8443
    host = request.headers.get("Host", request.host)
    # Strip port if present
    if ":" in host:
        host = host.split(":")[0]
    https_url = f"https://{host}:8443{request.path_qs}"
    return web.HTTPMovedPermanently(https_url)


# ============================================================================
# Background Tasks
# ============================================================================

async def renewal_loop(cert_manager: CertManager, ssl_context: ssl.SSLContext):
    """
    Background task: periodically check and renew the SSL certificate.

    Runs every RENEWAL_CHECK_INTERVAL_HOURS. On successful renewal,
    reloads the SSL context (existing connections are unaffected;
    new connections use the new certificate).
    """
    interval = RENEWAL_CHECK_INTERVAL_HOURS * 3600
    while True:
        await asyncio.sleep(interval)
        try:
            if cert_manager.needs_renewal():
                logger.info("Certificate renewal needed — running certbot ...")
                if cert_manager.renew_certificate():
                    # Reload SSL context with new certificate
                    ssl_context.load_cert_chain(
                        str(cert_manager.cert_path),
                        str(cert_manager.key_path),
                    )
                    logger.info("SSL context reloaded with renewed certificate")
            else:
                logger.info("Certificate renewal not needed")
        except Exception as e:
            logger.error("Renewal check failed: %s", e)


# ============================================================================
# Application Setup
# ============================================================================

async def on_shutdown(app: web.Application):
    """Clean up the shared client session on shutdown."""
    global _client_session
    if _client_session and not _client_session.closed:
        await _client_session.close()


def create_https_app() -> web.Application:
    """Create the HTTPS reverse proxy application."""
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    # Catch-all route — proxy everything to upstream
    app.router.add_route("*", "/{path_info:.*}", proxy_handler)
    return app


def create_http_app() -> web.Application:
    """Create the HTTP redirect + ACME challenge application."""
    app = web.Application()
    app.router.add_route("*", "/{path_info:.*}", http_redirect_handler)
    return app


# ============================================================================
# Main
# ============================================================================

async def run_auto_ssl(domain: str, email: str):
    """Run with automatic Let's Encrypt SSL certificates."""
    cert_manager = CertManager(domain, email)

    # Ensure ACME webroot exists
    acme_challenge_dir = ACME_WEBROOT / ".well-known" / "acme-challenge"
    acme_challenge_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Start HTTP server on port 80 (for ACME challenges)
    http_app = create_http_app()
    http_runner = web.AppRunner(http_app)
    await http_runner.setup()
    http_site = web.TCPSite(http_runner, "0.0.0.0", 80)
    await http_site.start()
    logger.info("HTTP server started on port 80 (ACME challenges + redirect)")

    # Step 2: Obtain certificate if needed
    if not cert_manager.has_certificates():
        logger.info("No certificates found — obtaining from Let's Encrypt ...")
        if not cert_manager.obtain_certificate():
            logger.error(
                "Failed to obtain certificate. Ensure:\n"
                "  1. DNS for %s points to this server's public IP\n"
                "  2. Port 80 is accessible from the internet\n"
                "  3. certbot is installed",
                domain,
            )
            await http_runner.cleanup()
            return
    else:
        logger.info("Using existing certificates from %s", cert_manager.cert_dir)

    # Step 3: Start HTTPS server on port 8443
    ssl_ctx = create_ssl_context(
        str(cert_manager.cert_path),
        str(cert_manager.key_path),
    )

    https_app = create_https_app()
    https_runner = web.AppRunner(https_app)
    await https_runner.setup()
    https_site = web.TCPSite(https_runner, "0.0.0.0", 8443, ssl_context=ssl_ctx)
    await https_site.start()
    logger.info("HTTPS reverse proxy started on port 8443 -> %s:%d",
                UPSTREAM_HOST, UPSTREAM_PORT)
    logger.info("Your site is live at https://%s:8443", domain)

    # Step 4: Start renewal background task
    renewal_task = asyncio.create_task(renewal_loop(cert_manager, ssl_ctx))

    # Run forever
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        renewal_task.cancel()
        await https_runner.cleanup()
        await http_runner.cleanup()
        logger.info("Reverse proxy stopped")


async def run_manual_ssl(cert_path: str, key_path: str, port: int = 8443):
    """Run with manually provided SSL certificates."""
    if not Path(cert_path).is_file():
        logger.error("Certificate file not found: %s", cert_path)
        return
    if not Path(key_path).is_file():
        logger.error("Key file not found: %s", key_path)
        return

    ssl_ctx = create_ssl_context(cert_path, key_path)

    # Start HTTPS proxy
    https_app = create_https_app()
    https_runner = web.AppRunner(https_app)
    await https_runner.setup()
    https_site = web.TCPSite(https_runner, "0.0.0.0", port, ssl_context=ssl_ctx)
    await https_site.start()
    logger.info("HTTPS reverse proxy started on port %d -> %s:%d",
                port, UPSTREAM_HOST, UPSTREAM_PORT)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await https_runner.cleanup()
        logger.info("Reverse proxy stopped")


async def run_no_ssl(port: int = 8080):
    """Run without SSL (development mode)."""
    app = create_https_app()  # Same proxy logic, just no SSL
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("HTTP reverse proxy (no SSL) on port %d -> %s:%d",
                port, UPSTREAM_HOST, UPSTREAM_PORT)
    logger.warning("Running without SSL — for development only!")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.cleanup()


def main():
    global UPSTREAM_PORT

    parser = argparse.ArgumentParser(
        description="SSL-terminating reverse proxy for Vibe Web Terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Manual / self-signed certificates (port 8443):\n"
            "  python3 reverse_proxy.py \\\n"
            "      --cert certs/self-signed/fullchain.pem \\\n"
            "      --key certs/self-signed/privkey.pem\n"
            "\n"
            "  # Auto-SSL with Let's Encrypt (needs root for ACME on port 80):\n"
            "  sudo python3 reverse_proxy.py \\\n"
            "      --domain vibe.example.com \\\n"
            "      --email admin@example.com \\\n"
            "      --auto-ssl\n"
            "\n"
            "  # Development (no SSL):\n"
            "  python3 reverse_proxy.py --no-ssl --port 8080\n"
        ),
    )

    ssl_group = parser.add_argument_group("SSL mode (choose one)")
    ssl_group.add_argument(
        "--auto-ssl", action="store_true",
        help="Obtain and renew SSL certificates from Let's Encrypt automatically"
    )
    ssl_group.add_argument(
        "--cert",
        help="Path to SSL certificate (fullchain.pem)"
    )
    ssl_group.add_argument(
        "--key",
        help="Path to SSL private key (privkey.pem)"
    )
    ssl_group.add_argument(
        "--no-ssl", action="store_true",
        help="Run without SSL (development only)"
    )

    parser.add_argument(
        "--domain",
        help="Domain name for Let's Encrypt (required with --auto-ssl)"
    )
    parser.add_argument(
        "--email",
        help="Email for Let's Encrypt notifications (required with --auto-ssl)"
    )
    parser.add_argument(
        "--port", type=int, default=8443,
        help="HTTPS port (default: 8443, or 8080 with --no-ssl)"
    )
    parser.add_argument(
        "--upstream-port", type=int, default=UPSTREAM_PORT,
        help=f"Upstream server port (default: {UPSTREAM_PORT})"
    )

    args = parser.parse_args()

    # Update upstream port if specified
    UPSTREAM_PORT = args.upstream_port

    # Validate arguments
    if args.auto_ssl:
        if not args.domain:
            parser.error("--domain is required with --auto-ssl")
        if not args.email:
            parser.error("--email is required with --auto-ssl")
        asyncio.run(run_auto_ssl(args.domain, args.email))

    elif args.cert and args.key:
        asyncio.run(run_manual_ssl(args.cert, args.key, args.port))

    elif args.no_ssl:
        port = args.port if args.port != 8443 else 8080
        asyncio.run(run_no_ssl(port))

    else:
        parser.error(
            "Choose an SSL mode:\n"
            "  --auto-ssl --domain DOMAIN --email EMAIL\n"
            "  --cert FILE --key FILE\n"
            "  --no-ssl"
        )


if __name__ == "__main__":
    main()
