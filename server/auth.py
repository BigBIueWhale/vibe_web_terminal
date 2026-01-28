"""
Authentication module for Vibe Web Terminal.

Supports:
  - Local users with bcrypt-hashed passwords (via auth.yaml)
  - LDAP / Active Directory authentication (optional)
  - Server-side sessions with signed cookies

When auth.yaml does not exist, authentication is disabled entirely
and the server operates in localhost-only mode (original behaviour).
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import yaml

logger = logging.getLogger(__name__)

# Path to the auth config file (project root)
AUTH_CONFIG_PATH = Path(__file__).parent.parent / "auth.yaml"


class AuthManager:
    """
    Manages authentication and login sessions.

    Authentication flow:
        1. User submits username + password to /login
        2. authenticate() checks local users first, then LDAP
        3. On success, create_session() returns a signed token
        4. Token is stored in an HttpOnly cookie
        5. validate_session() checks the token on each request
        6. destroy_session() removes the token on logout

    Session tokens are random 256-bit values. Session state is held
    in server memory (dict). Restarting the server logs everyone out.
    """

    def __init__(self, config_path: Path = AUTH_CONFIG_PATH):
        self._config_path = config_path
        self._config = self._load_config()
        self._sessions: dict[str, dict] = {}  # token -> {username, created_at}
        self._secret: str = self._config.get("session_secret", "")
        self._timeout = timedelta(
            hours=self._config.get("session_timeout_hours", 24)
        )
        logger.info("Authentication enabled — %d local user(s) configured",
                     len(self._config.get("users", {})))
        ldap_cfg = self._config.get("ldap", {})
        if ldap_cfg.get("enabled"):
            logger.info("LDAP authentication enabled — server %s",
                         ldap_cfg.get("server_url", "(not set)"))

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        """Load and validate auth.yaml."""
        with open(self._config_path) as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError(f"auth.yaml must be a YAML mapping, got {type(config)}")
        if config.get("session_secret", "CHANGE_ME") == "CHANGE_ME":
            logger.warning(
                "session_secret is 'CHANGE_ME' — generating a random one. "
                "Run edit_user.py to persist a proper secret."
            )
            config["session_secret"] = secrets.token_hex(32)
        return config

    def reload_config(self) -> None:
        """Hot-reload auth.yaml (e.g. after edit_user.py changes)."""
        try:
            self._config = self._load_config()
            self._secret = self._config.get("session_secret", "")
            self._timeout = timedelta(
                hours=self._config.get("session_timeout_hours", 24)
            )
            logger.info("Auth config reloaded")
        except Exception as e:
            logger.error("Failed to reload auth config: %s", e)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate a user against local users, then LDAP.

        Returns True if credentials are valid.
        """
        if not username or not password:
            return False

        # 1. Check local users first
        users = self._config.get("users") or {}
        if username in users:
            stored_hash = users[username].get("password_hash", "")
            try:
                return bcrypt.checkpw(
                    password.encode("utf-8"),
                    stored_hash.encode("utf-8"),
                )
            except (ValueError, TypeError):
                logger.warning("Invalid password hash for local user '%s'", username)
                return False

        # 2. Try LDAP if enabled
        ldap_cfg = self._config.get("ldap") or {}
        if ldap_cfg.get("enabled"):
            return self._ldap_authenticate(username, password, ldap_cfg)

        return False

    # ------------------------------------------------------------------
    # LDAP
    # ------------------------------------------------------------------

    def _ldap_authenticate(self, username: str, password: str, cfg: dict) -> bool:
        """
        Authenticate via LDAP using bind-then-search pattern.

        Steps:
            1. Bind with service account
            2. Search for user DN by username
            3. (Optional) Verify group membership
            4. Re-bind as user with their password
        """
        try:
            import ldap3
            from ldap3 import Server, Connection, Tls, ALL
            import ssl as _ssl
        except ImportError:
            logger.error(
                "ldap3 package is required for LDAP authentication. "
                "Install it with: pip install ldap3"
            )
            return False

        server_url = cfg.get("server_url", "")
        timeout = cfg.get("timeout", 10)

        # TLS configuration
        tls_config = None
        if cfg.get("tls_verify", True):
            tls_config = Tls(validate=_ssl.CERT_REQUIRED)
        else:
            tls_config = Tls(validate=_ssl.CERT_NONE)

        try:
            server = Server(server_url, get_info=ALL, tls=tls_config,
                            connect_timeout=timeout)

            # Step 1: Bind with service account
            bind_dn = cfg.get("bind_dn", "")
            bind_password = cfg.get("bind_password", "")
            conn = Connection(
                server, bind_dn, bind_password,
                auto_bind=False, receive_timeout=timeout,
            )

            if not conn.bind():
                logger.error("LDAP service account bind failed: %s", conn.result)
                return False

            if cfg.get("use_starttls") and not server_url.startswith("ldaps://"):
                conn.start_tls()

            # Step 2: Search for user
            search_base = cfg.get("search_base", "")
            search_filter = cfg.get("search_filter", "(uid={username})")
            # Escape special LDAP characters in username
            safe_username = ldap3.utils.conv.escape_filter_chars(username)
            resolved_filter = search_filter.replace("{username}", safe_username)

            conn.search(search_base, resolved_filter, attributes=["*"])

            if not conn.entries:
                logger.info("LDAP user not found: '%s'", username)
                conn.unbind()
                return False

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn

            # Step 3: Check group membership (optional)
            required_group = cfg.get("required_group_dn", "")
            if required_group:
                group_base = cfg.get("group_search_base", search_base)
                group_filter_tmpl = cfg.get(
                    "group_search_filter",
                    "(&(objectClass=groupOfNames)(member={user_dn}))"
                )
                group_filter = group_filter_tmpl.replace("{user_dn}", user_dn)
                conn.search(group_base, group_filter)
                if not conn.entries:
                    logger.info(
                        "LDAP user '%s' is not a member of required group '%s'",
                        username, required_group,
                    )
                    conn.unbind()
                    return False

            conn.unbind()

            # Step 4: Authenticate as the user
            user_conn = Connection(
                server, user_dn, password,
                auto_bind=False, receive_timeout=timeout,
            )
            if cfg.get("use_starttls") and not server_url.startswith("ldaps://"):
                user_conn.start_tls()

            authenticated = user_conn.bind()
            user_conn.unbind()

            if authenticated:
                logger.info("LDAP authentication successful for '%s'", username)
            else:
                logger.info("LDAP authentication failed for '%s'", username)

            return authenticated

        except Exception as e:
            logger.error("LDAP authentication error: %s", e)
            return False

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, username: str) -> str:
        """Create a new login session. Returns the session token."""
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {
            "username": username,
            "created_at": datetime.now(),
        }
        logger.info("Session created for user '%s'", username)
        return token

    def validate_session(self, token: str) -> Optional[str]:
        """
        Validate a session token.

        Returns the username if valid, None otherwise.
        Expired sessions are cleaned up automatically.
        """
        if not token:
            return None
        session = self._sessions.get(token)
        if not session:
            return None
        if datetime.now() - session["created_at"] > self._timeout:
            del self._sessions[token]
            return None
        return session["username"]

    def destroy_session(self, token: str) -> None:
        """Remove a session (logout)."""
        self._sessions.pop(token, None)

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        now = datetime.now()
        expired = [
            tok for tok, sess in self._sessions.items()
            if now - sess["created_at"] > self._timeout
        ]
        for tok in expired:
            del self._sessions[tok]
        return len(expired)


def is_auth_enabled() -> bool:
    """Check if auth.yaml exists (authentication enabled)."""
    return AUTH_CONFIG_PATH.is_file()


def create_auth_manager() -> Optional[AuthManager]:
    """
    Create an AuthManager if auth.yaml exists.

    Returns None if auth is not configured (localhost-only mode).
    """
    if not is_auth_enabled():
        return None
    try:
        return AuthManager()
    except Exception as e:
        logger.error("Failed to initialize authentication: %s", e)
        raise
