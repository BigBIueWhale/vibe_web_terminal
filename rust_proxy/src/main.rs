//! Vibe Reverse Proxy - High-performance SSL-terminating reverse proxy
//!
//! A Rust reverse proxy that sits in front of the Vibe Web Terminal server.
//! Handles TLS termination, WebSocket proxying, and security headers.
//!
//! Architecture:
//!     Internet --> rust_proxy :8443 (SSL) --> localhost:8081 (vibe server)

use std::net::SocketAddr;
use std::panic::AssertUnwindSafe;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use axum::body::Body;
use axum::extract::ws::{CloseFrame as AxumCloseFrame, Message as AxumMessage, WebSocket, WebSocketUpgrade};
use axum::extract::{ConnectInfo, FromRequest, Request, State};
use axum::http::{header, HeaderMap, HeaderName, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::any;
use axum::Router;
use axum_server::Handle;
use clap::Parser;
use futures::future::FutureExt;
use futures::stream::StreamExt;
use futures::SinkExt;
use http_body_util::BodyExt;
use rustls::pki_types::CertificateDer;
use tokio::signal;
use tokio_tungstenite::tungstenite::{
    self,
    protocol::CloseFrame as TungsteniteCloseFrame,
    Message as TungsteniteMessage,
};
use tower_http::limit::RequestBodyLimitLayer;
use tracing::{debug, error, info, warn, Level};

// ============================================================================
// Configuration
// ============================================================================

const DEFAULT_UPSTREAM_HOST: &str = "127.0.0.1";
const DEFAULT_UPSTREAM_PORT: u16 = 8081;
const DEFAULT_HTTPS_PORT: u16 = 8443;
const DEFAULT_HTTP_PORT: u16 = 8080;
const MAX_BODY_SIZE: usize = 500 * 1024 * 1024; // 500MB
const RENEWAL_CHECK_INTERVAL_HOURS: u64 = 12;

/// Headers to strip when proxying (hop-by-hop headers)
const HOP_BY_HOP_HEADERS: &[&str] = &[
    "connection",
    "keep-alive",
    "transfer-encoding",
    "te",
    "trailers",
    "upgrade",
    "proxy-authorization",
    "proxy-authenticate",
    "proxy-connection",
];

/// Security headers added to all responses
fn security_headers() -> [(HeaderName, HeaderValue); 4] {
    [
        (
            HeaderName::from_static("strict-transport-security"),
            HeaderValue::from_static("max-age=63072000; includeSubDomains; preload"),
        ),
        (
            HeaderName::from_static("x-content-type-options"),
            HeaderValue::from_static("nosniff"),
        ),
        (
            HeaderName::from_static("x-frame-options"),
            HeaderValue::from_static("SAMEORIGIN"),
        ),
        (
            HeaderName::from_static("referrer-policy"),
            HeaderValue::from_static("strict-origin-when-cross-origin"),
        ),
    ]
}

// ============================================================================
// CLI Arguments
// ============================================================================

#[derive(Parser, Debug, Clone)]
#[command(
    name = "rust_proxy",
    about = "SSL-terminating reverse proxy for Vibe Web Terminal",
    long_about = "A high-performance reverse proxy that handles TLS termination, \
                  WebSocket proxying, and security headers for the Vibe Web Terminal.",
    after_help = r#"EXAMPLES:
    # Manual / self-signed certificates (port 8443):
    rust_proxy \
        --cert certs/self-signed/fullchain.pem \
        --key certs/self-signed/privkey.pem

    # Auto-SSL with Let's Encrypt (needs root for ACME on port 80):
    sudo rust_proxy \
        --domain vibe.example.com \
        --email admin@example.com \
        --auto-ssl

    # Development (no SSL):
    rust_proxy --no-ssl --port 8080
"#
)]
struct Args {
    /// Obtain and renew SSL certificates from Let's Encrypt automatically
    #[arg(long)]
    auto_ssl: bool,

    /// Path to SSL certificate (fullchain.pem)
    #[arg(long)]
    cert: Option<PathBuf>,

    /// Path to SSL private key (privkey.pem)
    #[arg(long)]
    key: Option<PathBuf>,

    /// Run without SSL (development only)
    #[arg(long)]
    no_ssl: bool,

    /// Domain name for Let's Encrypt (required with --auto-ssl)
    #[arg(long)]
    domain: Option<String>,

    /// Email for Let's Encrypt notifications (required with --auto-ssl)
    #[arg(long)]
    email: Option<String>,

    /// HTTPS port (default: 8443, or 8080 with --no-ssl)
    #[arg(long, default_value_t = DEFAULT_HTTPS_PORT)]
    port: u16,

    /// Upstream server port
    #[arg(long, default_value_t = DEFAULT_UPSTREAM_PORT)]
    upstream_port: u16,
}

// ============================================================================
// Application State
// ============================================================================

#[derive(Clone)]
struct AppState {
    upstream_url: String,
    http_client: reqwest::Client,
}

impl AppState {
    fn new(upstream_port: u16) -> Self {
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(300))
            .connect_timeout(Duration::from_secs(10))
            .pool_max_idle_per_host(100)
            .build()
            .expect("Failed to create HTTP client");

        Self {
            upstream_url: format!("http://{}:{}", DEFAULT_UPSTREAM_HOST, upstream_port),
            http_client,
        }
    }
}

// ============================================================================
// WebSocket Message Conversion
// ============================================================================

/// Convert axum WebSocket Message to tungstenite Message.
/// These are different types with the same structure, requiring manual conversion.
fn axum_to_tungstenite(msg: AxumMessage) -> TungsteniteMessage {
    match msg {
        AxumMessage::Text(text) => {
            // Utf8Bytes implements Deref<Target=str>, so we can get &str
            TungsteniteMessage::Text(text.as_str().to_string().into())
        }
        AxumMessage::Binary(data) => {
            TungsteniteMessage::Binary(data.to_vec().into())
        }
        AxumMessage::Ping(data) => {
            TungsteniteMessage::Ping(data.to_vec().into())
        }
        AxumMessage::Pong(data) => {
            TungsteniteMessage::Pong(data.to_vec().into())
        }
        AxumMessage::Close(frame) => {
            TungsteniteMessage::Close(frame.map(|f| TungsteniteCloseFrame {
                code: tungstenite::protocol::frame::coding::CloseCode::from(f.code),
                reason: f.reason.to_string().into(),
            }))
        }
    }
}

/// Convert tungstenite Message to axum WebSocket Message.
fn tungstenite_to_axum(msg: TungsteniteMessage) -> Option<AxumMessage> {
    match msg {
        TungsteniteMessage::Text(text) => {
            Some(AxumMessage::Text(text.as_str().to_string().into()))
        }
        TungsteniteMessage::Binary(data) => {
            Some(AxumMessage::Binary(data.to_vec().into()))
        }
        TungsteniteMessage::Ping(data) => {
            Some(AxumMessage::Ping(data.to_vec().into()))
        }
        TungsteniteMessage::Pong(data) => {
            Some(AxumMessage::Pong(data.to_vec().into()))
        }
        TungsteniteMessage::Close(frame) => {
            Some(AxumMessage::Close(frame.map(|f| AxumCloseFrame {
                code: f.code.into(),
                reason: f.reason.to_string().into(),
            })))
        }
        TungsteniteMessage::Frame(_) => None, // Internal frame, skip
    }
}

// ============================================================================
// Reverse Proxy Handler
// ============================================================================

/// Combined proxy handler - handles both HTTP and WebSocket requests
///
/// Uses Request to check for WebSocket upgrade header, then either upgrades
/// to WebSocket or proxies as HTTP.
#[axum::debug_handler]
async fn proxy_handler(
    State(state): State<AppState>,
    ConnectInfo(client_addr): ConnectInfo<SocketAddr>,
    req: Request,
) -> Response {
    // Wrap the actual handler in panic catch for robustness
    let result = AssertUnwindSafe(proxy_handler_inner(state, client_addr, req))
        .catch_unwind()
        .await;

    match result {
        Ok(response) => response,
        Err(panic_payload) => {
            let msg = panic_payload
                .downcast_ref::<&str>()
                .map(|s| s.to_string())
                .or_else(|| panic_payload.downcast_ref::<String>().cloned())
                .unwrap_or_else(|| "Unknown panic".to_string());
            error!(panic = %msg, "PANIC caught in request handler");
            (StatusCode::INTERNAL_SERVER_ERROR, "Internal server error").into_response()
        }
    }
}

async fn proxy_handler_inner(
    state: AppState,
    client_addr: SocketAddr,
    req: Request,
) -> Response {
    // Check for WebSocket upgrade by looking at headers
    let is_websocket = req
        .headers()
        .get(header::UPGRADE)
        .and_then(|v| v.to_str().ok())
        .map(|v| v.eq_ignore_ascii_case("websocket"))
        .unwrap_or(false);

    if is_websocket {
        // Extract WebSocket upgrade manually
        let (parts, body) = req.into_parts();
        let path = parts.uri.path_and_query().map(|pq| pq.to_string()).unwrap_or_default();
        let headers = parts.headers.clone();

        // Reconstruct request for WebSocketUpgrade extractor
        let req = Request::from_parts(parts, body);

        // Use WebSocketUpgrade extractor
        match WebSocketUpgrade::from_request(req, &state).await {
            Ok(ws) => {
                return ws
                    .protocols(extract_protocols(&headers))
                    .on_upgrade(move |socket| websocket_proxy(socket, state, path, headers, client_addr));
            }
            Err(rejection) => {
                error!(error = ?rejection, "WebSocket upgrade failed");
                return rejection.into_response();
            }
        }
    }

    // Regular HTTP proxy
    http_proxy(state, req, client_addr).await
}

/// Extract WebSocket subprotocols from request headers
fn extract_protocols(headers: &HeaderMap) -> Vec<String> {
    headers
        .get("sec-websocket-protocol")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.split(',').map(|p| p.trim().to_string()).collect())
        .unwrap_or_default()
}

/// Proxy an HTTP request to the upstream server
async fn http_proxy(state: AppState, req: Request, client_addr: SocketAddr) -> Response {
    let method = req.method().clone();
    let uri = req.uri().clone();
    let path_query = uri.path_and_query().map(|pq| pq.as_str()).unwrap_or("/");
    let target_url = format!("{}{}", state.upstream_url, path_query);

    debug!(
        method = %method,
        path = %path_query,
        client = %client_addr,
        "Proxying HTTP request"
    );

    // Build upstream request headers
    let mut upstream_headers = HeaderMap::new();
    for (key, value) in req.headers() {
        let key_lower = key.as_str().to_lowercase();
        if !HOP_BY_HOP_HEADERS.contains(&key_lower.as_str()) {
            upstream_headers.insert(key.clone(), value.clone());
        }
    }

    // Add forwarding headers
    let upstream_port = state.upstream_url.split(':').last().unwrap_or("8081");
    if let Ok(host_value) = HeaderValue::from_str(&format!("{}:{}", DEFAULT_UPSTREAM_HOST, upstream_port)) {
        upstream_headers.insert(header::HOST, host_value);
    }
    if let Ok(ip_value) = HeaderValue::from_str(&client_addr.ip().to_string()) {
        upstream_headers.insert(HeaderName::from_static("x-forwarded-for"), ip_value.clone());
        upstream_headers.insert(HeaderName::from_static("x-real-ip"), ip_value);
    }
    upstream_headers.insert(
        HeaderName::from_static("x-forwarded-proto"),
        HeaderValue::from_static("https"),
    );

    // Read request body
    let body_bytes = match req.into_body().collect().await {
        Ok(collected) => collected.to_bytes(),
        Err(e) => {
            error!(error = %e, "Failed to read request body");
            return (StatusCode::BAD_REQUEST, "Failed to read request body").into_response();
        }
    };

    // Send request to upstream
    let upstream_request = state
        .http_client
        .request(method.clone(), &target_url)
        .headers(upstream_headers)
        .body(body_bytes);

    let upstream_response = match upstream_request.send().await {
        Ok(resp) => resp,
        Err(e) => {
            error!(
                upstream = %target_url,
                client = %client_addr,
                error = %e,
                "Proxy request failed"
            );
            return (StatusCode::BAD_GATEWAY, "Bad Gateway").into_response();
        }
    };

    // Build response
    let status = upstream_response.status();
    let mut response_headers = HeaderMap::new();

    // Add security headers
    for (name, value) in security_headers() {
        response_headers.insert(name, value);
    }

    // Copy upstream response headers (except hop-by-hop)
    for (key, value) in upstream_response.headers() {
        let key_lower = key.as_str().to_lowercase();
        if !HOP_BY_HOP_HEADERS.contains(&key_lower.as_str()) && key_lower != "content-length" {
            response_headers.insert(key.clone(), value.clone());
        }
    }

    // Stream response body
    let body_stream = upstream_response.bytes_stream();
    let body = Body::from_stream(body_stream);

    let mut response = Response::new(body);
    *response.status_mut() = status;
    *response.headers_mut() = response_headers;

    response
}

/// Proxy a WebSocket connection to the upstream server
async fn websocket_proxy(
    client_socket: WebSocket,
    state: AppState,
    path: String,
    headers: HeaderMap,
    client_addr: SocketAddr,
) {
    let ws_url = format!(
        "ws://{}{}",
        state.upstream_url.trim_start_matches("http://"),
        path
    );

    debug!(
        upstream = %ws_url,
        client = %client_addr,
        "Opening WebSocket proxy connection"
    );

    // Build upstream request with auth headers
    let mut request = match tungstenite::http::Request::builder()
        .uri(&ws_url)
        .body(())
    {
        Ok(req) => req,
        Err(e) => {
            error!(error = %e, "Failed to build WebSocket request");
            return;
        }
    };

    // Forward Cookie and Authorization headers
    for key in ["cookie", "authorization"] {
        if let Some(value) = headers.get(key) {
            if let Ok(header_name) = tungstenite::http::HeaderName::try_from(key) {
                if let Ok(header_value) = tungstenite::http::HeaderValue::from_bytes(value.as_bytes()) {
                    request.headers_mut().insert(header_name, header_value);
                }
            }
        }
    }

    // Connect to upstream WebSocket
    let upstream_socket = match tokio_tungstenite::connect_async(request).await {
        Ok((socket, _)) => socket,
        Err(e) => {
            error!(
                upstream = %ws_url,
                client = %client_addr,
                error = %e,
                "WebSocket upstream connection failed"
            );
            return;
        }
    };

    let (mut client_sink, mut client_stream) = client_socket.split();
    let (mut upstream_sink, mut upstream_stream) = upstream_socket.split();

    // Bidirectional forwarding using tokio::select!
    let client_to_upstream = async {
        while let Some(result) = client_stream.next().await {
            match result {
                Ok(msg) => {
                    let tungstenite_msg = axum_to_tungstenite(msg);
                    if upstream_sink.send(tungstenite_msg).await.is_err() {
                        break;
                    }
                }
                Err(e) => {
                    debug!(error = %e, "Client WebSocket error");
                    break;
                }
            }
        }
        let _ = upstream_sink.close().await;
    };

    let upstream_to_client = async {
        while let Some(result) = upstream_stream.next().await {
            match result {
                Ok(msg) => {
                    if let Some(axum_msg) = tungstenite_to_axum(msg) {
                        if client_sink.send(axum_msg).await.is_err() {
                            break;
                        }
                    }
                }
                Err(e) => {
                    debug!(error = %e, "Upstream WebSocket error");
                    break;
                }
            }
        }
        let _ = client_sink.close().await;
    };

    // Run both directions concurrently until one closes
    tokio::select! {
        _ = client_to_upstream => {
            debug!(client = %client_addr, "Client closed WebSocket");
        }
        _ = upstream_to_client => {
            debug!(client = %client_addr, "Upstream closed WebSocket");
        }
    }

    debug!(client = %client_addr, "WebSocket proxy connection closed");
}

// ============================================================================
// TLS Configuration
// ============================================================================

/// Load TLS certificates and key from files
fn load_rustls_config(cert_path: &PathBuf, key_path: &PathBuf) -> Result<rustls::ServerConfig, Box<dyn std::error::Error + Send + Sync>> {
    let cert_file = std::fs::File::open(cert_path)
        .map_err(|e| format!("Failed to open certificate file {}: {}", cert_path.display(), e))?;
    let key_file = std::fs::File::open(key_path)
        .map_err(|e| format!("Failed to open key file {}: {}", key_path.display(), e))?;

    let mut cert_reader = std::io::BufReader::new(cert_file);
    let mut key_reader = std::io::BufReader::new(key_file);

    let certs: Vec<CertificateDer<'static>> = rustls_pemfile::certs(&mut cert_reader)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Failed to parse certificates: {}", e))?;

    if certs.is_empty() {
        return Err("No certificates found in certificate file".into());
    }

    let key = rustls_pemfile::private_key(&mut key_reader)
        .map_err(|e| format!("Failed to parse private key: {}", e))?
        .ok_or("No private key found in key file")?;

    let config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .map_err(|e| format!("Failed to build TLS config: {}", e))?;

    Ok(config)
}

// ============================================================================
// Certificate Manager (for Auto-SSL)
// ============================================================================

struct CertManager {
    domain: String,
    email: String,
    cert_dir: PathBuf,
    cert_path: PathBuf,
    key_path: PathBuf,
    acme_webroot: PathBuf,
}

impl CertManager {
    fn new(domain: String, email: String, base_dir: PathBuf) -> Self {
        let cert_dir = base_dir.join("certs").join(&domain);
        let cert_path = cert_dir.join("fullchain.pem");
        let key_path = cert_dir.join("privkey.pem");
        let acme_webroot = base_dir.join("acme-webroot");

        Self {
            domain,
            email,
            cert_dir,
            cert_path,
            key_path,
            acme_webroot,
        }
    }

    fn has_certificates(&self) -> bool {
        self.cert_path.is_file() && self.key_path.is_file()
    }

    async fn obtain_certificate(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let certbot = which_certbot()?;

        tokio::fs::create_dir_all(&self.acme_webroot).await?;
        tokio::fs::create_dir_all(&self.cert_dir).await?;

        info!("Running certbot to obtain certificate for {} ...", self.domain);

        let output = tokio::process::Command::new(&certbot)
            .args([
                "certonly",
                "--webroot",
                "--webroot-path", self.acme_webroot.to_str().unwrap_or("."),
                "--domain", &self.domain,
                "--email", &self.email,
                "--agree-tos",
                "--non-interactive",
                "--cert-path", self.cert_path.to_str().unwrap_or("cert.pem"),
                "--key-path", self.key_path.to_str().unwrap_or("key.pem"),
                "--fullchain-path", self.cert_path.to_str().unwrap_or("fullchain.pem"),
            ])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await?;

        if output.status.success() {
            info!("Certificate obtained successfully");
            self.copy_from_certbot_live().await;
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("certbot failed: {}", stderr).into())
        }
    }

    async fn copy_from_certbot_live(&self) {
        let live_dir = PathBuf::from(format!("/etc/letsencrypt/live/{}", self.domain));
        if !live_dir.is_dir() || self.has_certificates() {
            return;
        }

        for (src_name, dst_path) in [
            ("fullchain.pem", &self.cert_path),
            ("privkey.pem", &self.key_path),
        ] {
            let src = live_dir.join(src_name);
            if src.is_file() {
                if let Err(e) = tokio::fs::copy(&src, dst_path).await {
                    warn!("Could not copy {} to {}: {}", src.display(), dst_path.display(), e);
                } else {
                    info!("Copied {} to {}", src.display(), dst_path.display());
                }
            }
        }
    }

    async fn renew_certificate(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let certbot = which_certbot()?;

        info!("Checking certificate renewal for {} ...", self.domain);

        let output = tokio::process::Command::new(&certbot)
            .args(["renew", "--non-interactive", "--quiet"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await?;

        if output.status.success() {
            self.copy_from_certbot_live().await;
            info!("Certificate renewal check complete");
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("certbot renew failed: {}", stderr).into())
        }
    }

    async fn needs_renewal(&self) -> bool {
        if !self.has_certificates() {
            return true;
        }

        let output = tokio::process::Command::new("openssl")
            .args(["x509", "-enddate", "-noout", "-in"])
            .arg(&self.cert_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await;

        match output {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                if let Some(date_str) = stdout.strip_prefix("notAfter=") {
                    info!("Certificate expiry: {}", date_str.trim());
                    false
                } else {
                    true
                }
            }
            _ => true,
        }
    }
}

fn which_certbot() -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
    for path in ["/usr/bin/certbot", "/usr/local/bin/certbot", "/snap/bin/certbot"] {
        if PathBuf::from(path).is_file() {
            return Ok(PathBuf::from(path));
        }
    }
    if let Ok(output) = std::process::Command::new("which").arg("certbot").output() {
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !path.is_empty() {
                return Ok(PathBuf::from(path));
            }
        }
    }
    Err("certbot not found. Install it with: sudo apt install certbot".into())
}

// ============================================================================
// HTTP Redirect Server (for ACME challenges)
// ============================================================================

#[derive(Clone)]
struct HttpRedirectState {
    acme_webroot: PathBuf,
    https_port: u16,
}

/// Handle HTTP requests on port 80 for ACME challenges and HTTPS redirect
async fn http_redirect_handler(
    State(state): State<HttpRedirectState>,
    req: Request,
) -> Response {
    let path = req.uri().path();

    // Serve ACME challenge files
    if path.starts_with("/.well-known/acme-challenge/") {
        let token = path.trim_start_matches("/.well-known/acme-challenge/");
        let challenge_path = state.acme_webroot.join(".well-known/acme-challenge").join(token);

        if challenge_path.is_file() {
            match tokio::fs::read_to_string(&challenge_path).await {
                Ok(content) => return (StatusCode::OK, content).into_response(),
                Err(e) => {
                    error!(path = %challenge_path.display(), error = %e, "Failed to read ACME challenge");
                    return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to read challenge").into_response();
                }
            }
        }
        return (StatusCode::NOT_FOUND, "Challenge not found").into_response();
    }

    // Redirect everything else to HTTPS
    let host = req
        .headers()
        .get("host")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("localhost");
    let host_without_port = host.split(':').next().unwrap_or(host);
    let https_url = format!("https://{}:{}{}", host_without_port, state.https_port, path);

    Response::builder()
        .status(StatusCode::MOVED_PERMANENTLY)
        .header("location", https_url)
        .body(Body::empty())
        .unwrap_or_else(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Redirect failed").into_response())
}

// ============================================================================
// Server Runners
// ============================================================================

fn create_proxy_router(upstream_port: u16) -> Router {
    let state = AppState::new(upstream_port);

    Router::new()
        .route("/{*path}", any(proxy_handler))
        .route("/", any(proxy_handler))
        .layer(RequestBodyLimitLayer::new(MAX_BODY_SIZE))
        .with_state(state)
}

/// Wait for shutdown signal and trigger graceful shutdown on the handle
async fn shutdown_signal(handle: Handle) {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }

    info!("Shutdown signal received, draining connections...");
    // 10 seconds is how long Docker waits before SIGKILL
    handle.graceful_shutdown(Some(Duration::from_secs(10)));
}

/// Run with manually provided SSL certificates
async fn run_manual_ssl(
    cert_path: PathBuf,
    key_path: PathBuf,
    port: u16,
    upstream_port: u16,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("Vibe Reverse Proxy starting");
    info!("Mode: manual-ssl");
    info!("Upstream: http://{}:{}", DEFAULT_UPSTREAM_HOST, upstream_port);
    info!("Listening: https://0.0.0.0:{}", port);
    info!("Certificate: {}", cert_path.display());

    let tls_config = load_rustls_config(&cert_path, &key_path)?;
    let app = create_proxy_router(upstream_port);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let rustls_config = axum_server::tls_rustls::RustlsConfig::from_config(Arc::new(tls_config));

    // Create handle for graceful shutdown
    let handle = Handle::new();
    tokio::spawn(shutdown_signal(handle.clone()));

    info!("Ready to accept connections");

    axum_server::bind_rustls(addr, rustls_config)
        .handle(handle)
        .serve(app.into_make_service_with_connect_info::<SocketAddr>())
        .await?;

    info!("Reverse proxy stopped");
    Ok(())
}

/// Run with automatic Let's Encrypt SSL certificates
async fn run_auto_ssl(
    domain: String,
    email: String,
    port: u16,
    upstream_port: u16,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("Vibe Reverse Proxy starting");
    info!("Mode: auto-ssl (Let's Encrypt via certbot)");
    info!("Domain: {}", domain);
    info!("Upstream: http://{}:{}", DEFAULT_UPSTREAM_HOST, upstream_port);
    info!("Listening: https://0.0.0.0:{}", port);

    let base_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.parent().unwrap_or(p).to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    let cert_manager = CertManager::new(domain.clone(), email.clone(), base_dir.clone());

    let challenge_dir = cert_manager.acme_webroot.join(".well-known/acme-challenge");
    tokio::fs::create_dir_all(&challenge_dir).await?;

    info!("ACME webroot: {}", cert_manager.acme_webroot.display());

    // Start HTTP server on port 80 for ACME challenges
    let http_state = HttpRedirectState {
        acme_webroot: cert_manager.acme_webroot.clone(),
        https_port: port,
    };

    let http_app = Router::new()
        .route("/{*path}", any(http_redirect_handler))
        .route("/", any(http_redirect_handler))
        .with_state(http_state);

    let http_addr = SocketAddr::from(([0, 0, 0, 0], 80));
    let http_listener = tokio::net::TcpListener::bind(http_addr).await?;

    info!("HTTP server started on port 80 (ACME challenges + redirect)");

    let http_handle = tokio::spawn(async move {
        if let Err(e) = axum::serve(http_listener, http_app).await {
            error!("HTTP server error: {}", e);
        }
    });

    // Obtain certificate if needed
    if !cert_manager.has_certificates() {
        info!("No certificates found - obtaining from Let's Encrypt...");
        cert_manager.obtain_certificate().await?;
    } else {
        info!("Using existing certificates from {}", cert_manager.cert_dir.display());
    }

    let tls_config = load_rustls_config(&cert_manager.cert_path, &cert_manager.key_path)?;
    let app = create_proxy_router(upstream_port);

    let https_addr = SocketAddr::from(([0, 0, 0, 0], port));
    let rustls_config = axum_server::tls_rustls::RustlsConfig::from_config(Arc::new(tls_config));

    // Create handle for graceful shutdown
    let handle = Handle::new();
    tokio::spawn(shutdown_signal(handle.clone()));

    info!("Ready to accept connections");
    info!("Your site is live at https://{}:{}", domain, port);

    // Spawn renewal task
    let renewal_cert_manager = CertManager::new(domain.clone(), email.clone(), base_dir);
    let renewal_handle = tokio::spawn(async move {
        let interval = Duration::from_secs(RENEWAL_CHECK_INTERVAL_HOURS * 3600);
        loop {
            tokio::time::sleep(interval).await;
            if renewal_cert_manager.needs_renewal().await {
                info!("Certificate renewal needed - running certbot...");
                if let Err(e) = renewal_cert_manager.renew_certificate().await {
                    error!("Certificate renewal failed: {}", e);
                }
            } else {
                info!("Certificate renewal not needed");
            }
        }
    });

    let result = axum_server::bind_rustls(https_addr, rustls_config)
        .handle(handle)
        .serve(app.into_make_service_with_connect_info::<SocketAddr>())
        .await;

    renewal_handle.abort();
    http_handle.abort();

    if let Err(e) = result {
        error!("HTTPS server error: {}", e);
        return Err(e.into());
    }

    info!("Reverse proxy stopped");
    Ok(())
}

/// Run without SSL (development mode)
async fn run_no_ssl(port: u16, upstream_port: u16) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("Vibe Reverse Proxy starting");
    info!("Mode: no-ssl (development)");
    info!("Upstream: http://{}:{}", DEFAULT_UPSTREAM_HOST, upstream_port);
    info!("Listening: http://0.0.0.0:{}", port);
    warn!("Running without SSL - for development only!");

    let app = create_proxy_router(upstream_port);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let listener = tokio::net::TcpListener::bind(addr).await?;

    info!("Ready to accept connections");

    // For plain HTTP, axum::serve has with_graceful_shutdown
    let ctrl_c = async {
        signal::ctrl_c().await.expect("Failed to install Ctrl+C handler");
        info!("Shutdown signal received");
    };

    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(ctrl_c)
    .await?;

    info!("Reverse proxy stopped");
    Ok(())
}

// ============================================================================
// Main
// ============================================================================

#[tokio::main]
async fn main() {
    // Install rustls crypto provider (required by rustls 0.23+)
    rustls::crypto::ring::default_provider()
        .install_default()
        .expect("Failed to install rustls crypto provider");

    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(Level::INFO.into()),
        )
        .init();

    let args = Args::parse();

    let result = if args.auto_ssl {
        let domain = args.domain.unwrap_or_else(|| {
            eprintln!("Error: --domain is required with --auto-ssl");
            std::process::exit(1);
        });
        let email = args.email.unwrap_or_else(|| {
            eprintln!("Error: --email is required with --auto-ssl");
            std::process::exit(1);
        });
        run_auto_ssl(domain, email, args.port, args.upstream_port).await
    } else if let (Some(cert), Some(key)) = (args.cert, args.key) {
        run_manual_ssl(cert, key, args.port, args.upstream_port).await
    } else if args.no_ssl {
        let port = if args.port == DEFAULT_HTTPS_PORT {
            DEFAULT_HTTP_PORT
        } else {
            args.port
        };
        run_no_ssl(port, args.upstream_port).await
    } else {
        eprintln!(
            "Error: Choose an SSL mode:\n\
             \n  --auto-ssl --domain DOMAIN --email EMAIL\n\
             \n  --cert FILE --key FILE\n\
             \n  --no-ssl"
        );
        std::process::exit(1);
    };

    if let Err(e) = result {
        error!("Fatal error: {}", e);
        std::process::exit(1);
    }
}
