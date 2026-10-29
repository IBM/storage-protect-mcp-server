"""
Session management module for Dynamic & Delegated User Authentication.

Implements ephemeral in-memory session leases with sliding-window inactivity
expiration for interactive chat clients (Claude Desktop, Web UIs) connecting
to IBM Storage Protect.

Cleanup guarantee (AUD-08):
  Expired leases are removed opportunistically — during ``create_session()``
  and explicit ``cleanup_expired()`` calls.  In deployments where new sessions
  are never created (e.g. a long-running server whose users only log out),
  expired leases accumulate until the next ``create_session()`` or an operator
  calls ``global_session_manager.cleanup_expired()`` directly.  Operators of
  long-lived processes should schedule periodic cleanup or use
  ``SP_MCP_SESSION_MAX_TTL`` (default 3600 s) to bound the absolute lease
  lifetime.

Credential lifecycle (AUD-08):
  ``SessionLease.password`` is zeroed (set to ``None``) as soon as the lease
  is removed from the store — whether via explicit revocation, expiry on
  ``get_session()``, or bulk cleanup.  This limits the window during which the
  plaintext credential survives in the Python object graph after the lease is
  logically terminated.
"""

from __future__ import annotations
import os
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Set
from threading import RLock

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TTL_SECONDS = int(os.environ.get("SP_MCP_SESSION_TTL", "900"))  # 15 minutes
MAX_SESSION_TTL_SECONDS = int(os.environ.get("SP_MCP_SESSION_MAX_TTL", "3600"))  # 60 minutes


@dataclass
class SessionLease:
    """Represents an active ephemeral authentication lease for an interactive user."""

    session_id: str
    username: str
    privilege_classes: Set[str]
    password: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    target_server: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the session has exceeded its sliding inactivity TTL or max TTL."""
        now = datetime.now(timezone.utc)
        inactive_seconds = (now - self.last_accessed_at).total_seconds()
        total_seconds = (now - self.created_at).total_seconds()
        
        # Inactive timeout or absolute max session limit reached
        if inactive_seconds > self.ttl_seconds or total_seconds > MAX_SESSION_TTL_SECONDS:
            return True
        return False

    def touch(self) -> None:
        """Update last accessed timestamp to extend sliding window lease."""
        self.last_accessed_at = datetime.now(timezone.utc)


class SessionManager:
    """Thread-safe in-memory session manager for dynamic authentication."""

    def __init__(self, default_ttl: int = DEFAULT_SESSION_TTL_SECONDS):
        self._sessions: Dict[str, SessionLease] = {}
        self._lock = RLock()
        self._default_ttl = min(max(default_ttl, 1), MAX_SESSION_TTL_SECONDS)

    def create_session(
        self,
        username: str,
        privileges: Optional[Set[str]] = None,
        target_server: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        password: Optional[str] = None,
    ) -> SessionLease:
        """Create and store a new ephemeral session lease."""
        with self._lock:
            self.cleanup_expired()
            session_id = uuid.uuid4().hex
            lease = SessionLease(
                session_id=session_id,
                username=username,
                privilege_classes=privileges or {"any"},
                password=password,
                ttl_seconds=min(max(ttl_seconds or self._default_ttl, 1), MAX_SESSION_TTL_SECONDS),
                target_server=target_server,
            )
            self._sessions[session_id] = lease
        logger.info(
            "Created ephemeral session lease for user='%s' (session_id=%s..., TTL=%ds)",
            username,
            session_id[:8],
            lease.ttl_seconds,
        )
        return lease

    def get_session(self, session_id: str) -> Optional[SessionLease]:
        """Retrieve and refresh a session lease if valid and unexpired."""
        with self._lock:
            lease = self._sessions.get(session_id)
            if lease is None:
                return None

            if lease.is_expired():
                logger.info(
                    "Session lease %s... for user='%s' expired. Removing.",
                    session_id[:8],
                    lease.username,
                )
                lease.password = None  # AUD-08: zero credential before discard
                self._sessions.pop(session_id, None)
                return None

            lease.touch()
            return lease

    def revoke_session(self, session_id: str) -> bool:
        """Explicitly terminate a session lease.

        Zeros the in-memory password field before removing the lease so the
        plaintext credential does not linger in the Python object graph after
        logical termination (AUD-08).
        """
        with self._lock:
            lease = self._sessions.get(session_id)
            if lease is None:
                return False
            lease.password = None  # AUD-08: zero credential before discard
            del self._sessions[session_id]
        logger.info("Revoked session lease %s...", session_id[:8])
        return True

    def cleanup_expired(self) -> int:
        """Remove all expired sessions from memory.

        Zeros the password field on each expired lease before discarding it
        (AUD-08).  Called automatically inside ``create_session()`` and
        available for operator-scheduled periodic cleanup.
        """
        with self._lock:
            expired = [sid for sid, lease in self._sessions.items() if lease.is_expired()]
            for sid in expired:
                lease = self._sessions.pop(sid, None)
                if lease is not None:
                    lease.password = None  # AUD-08: zero credential before discard
        if expired:
            logger.debug("Cleaned up %d expired session leases.", len(expired))
        return len(expired)

    def clear(self) -> None:
        """Clear all active sessions (e.g. at shutdown or reset).

        Zeros the password field on every lease before clearing the store
        (AUD-08).
        """
        with self._lock:
            for lease in self._sessions.values():
                lease.password = None  # AUD-08: zero credentials before discard
            self._sessions.clear()


# Global default session manager instance
global_session_manager = SessionManager()
