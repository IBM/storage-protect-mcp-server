"""
Authentication commands for Dynamic & Delegated User Authentication.

Provides the authenticate_session MCP tool for interactive LLM chat clients.
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional, Set
import logging

from ..base import BaseCommand
from ...session import global_session_manager

logger = logging.getLogger(__name__)


def _parse_privileges(stdout: str) -> Set[str]:
    """Parse privilege classes from QUERY ADMIN <username> FORMAT=DETAILED output."""
    privileges = {"any"}
    upper = (stdout or "").upper()
    if "SYSTEM PRIVILEGE: YES" in upper:
        privileges.add("system")
    if "POLICY PRIVILEGE: YES" in upper:
        privileges.add("policy")
    if "STORAGE PRIVILEGE: YES" in upper:
        privileges.add("storage")
    if "OPERATOR PRIVILEGE: YES" in upper:
        privileges.add("operator")
    return privileges


class AuthenticateSession(BaseCommand):
    """
    Authenticate an interactive session with IBM Storage Protect administrator credentials.
    Mints an ephemeral in-memory lease and enables subsequent tool executions.
    """

    @property
    def name(self) -> str:
        return "authenticate_session"

    @property
    def required_privilege(self) -> str:
        # Available without prior authentication to permit login
        return "any"

    @property
    def description(self) -> str:
        return (
            "- Description: Authenticate an interactive session with IBM Storage Protect administrator credentials "
            "to obtain an ephemeral in-memory authorization lease.\n\n"
            "**Input Parameters**:\n"
            "- username (Required): IBM Storage Protect administrator ID.\n"
            "- password (Required): Administrator password.\n"
            "- target_server (Optional): Target SP server instance if multi-server routing is configured.\n\n"
            "**Output Parameters**:\n"
            "- Result: JSON status with session_id, username, expires_in_seconds, and privilege levels."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "IBM Storage Protect administrator ID",
                },
                "password": {
                    "type": "string",
                    "description": "IBM Storage Protect administrator password",
                },
                "target_server": {
                    "type": "string",
                    "description": "Optional target server stanza name if multi-server routing is configured",
                },
            },
            "required": ["username", "password"],
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        username = (arguments.get("username") or "").strip()
        password = arguments.get("password") or ""
        target_server = arguments.get("target_server")

        if not username or not password:
            return json.dumps({
                "success": False,
                "error": "Both 'username' and 'password' parameters are required.",
            }, indent=2)

        # Zero-trace credential verification via execute_silent
        # Command 1: lightweight check against SP server
        stdout, stderr, ret_code = self.cli.execute_silent(
            command="QUERY STATUS",
            admin_id=username,
            password=password,
        )

        if ret_code != 0:
            logger.warning(
                "Dynamic authentication failed for user='%s' (SP returned code %d)",
                username,
                ret_code,
            )
            return json.dumps({
                "success": False,
                "error": "Authentication failed: invalid administrator credentials.",
                "returncode": ret_code,
                "details": (stderr or stdout or "Access denied").strip(),
            }, indent=2)

        # Command 2: query admin authority level to establish privilege bounds
        priv_out, _, _ = self.cli.execute_silent(
            command=f"QUERY ADMIN {username} FORMAT=DETAILED",
            admin_id=username,
            password=password,
        )

        privileges = _parse_privileges(priv_out)

        # Mint session lease in session manager
        lease = global_session_manager.create_session(
            username=username,
            privileges=privileges,
            target_server=target_server,
            password=password,
        )

        # Set identity context for audit & forensics
        from ...mcp_factory import current_audit_user, current_session_id
        current_audit_user.set(username)
        current_session_id.set(lease.session_id)

        response = {
            "success": True,
            "session_id": lease.session_id,
            "username": username,
            "privileges": sorted(list(privileges)),
            "expires_in_seconds": lease.ttl_seconds,
            "message": f"Successfully authenticated as '{username}'. Ephemeral lease active for {lease.ttl_seconds}s.",
        }
        return json.dumps(response, indent=2)


class LogoutSession(BaseCommand):
    """
    Explicitly revoke an active dynamic authentication session lease.
    Zeros the in-memory credential and removes the session from the store.
    """

    @property
    def name(self) -> str:
        return "logout_session"

    @property
    def required_privilege(self) -> str:
        # Available without elevation — any authenticated session holder can log out.
        return "any"

    @property
    def description(self) -> str:
        return (
            "- Description: Revoke the current dynamic authentication session and zero the "
            "in-memory credential. Call this when the interactive session is finished "
            "to release the ephemeral lease immediately rather than waiting for TTL expiry.\n\n"
            "**Input Parameters**:\n"
            "- session_id (Optional): Session ID to revoke. Defaults to the current context session.\n\n"
            "**Output Parameters**:\n"
            "- Result: JSON status confirming revocation or indicating no active session."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to revoke. Omit to revoke the current context session.",
                },
            },
            "required": [],
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        from ...mcp_factory import current_session_id, current_audit_user

        sid = (arguments.get("session_id") or "").strip() or current_session_id.get()

        if not sid:
            return json.dumps({
                "success": False,
                "message": "No active session to revoke.",
            }, indent=2)

        revoked = global_session_manager.revoke_session(sid)

        if revoked:
            logger.info(
                "logout_session: revoked session %s... for user='%s'",
                sid[:8],
                current_audit_user.get() or "unknown",
            )
            # Clear the context variables for this request context.
            try:
                current_session_id.set(None)
                current_audit_user.set(None)
            except Exception:
                pass  # context vars may not be settable outside an async frame
            return json.dumps({
                "success": True,
                "message": "Session revoked. Credentials have been cleared from memory.",
            }, indent=2)

        return json.dumps({
            "success": False,
            "message": f"Session '{sid[:8]}...' not found or already expired.",
        }, indent=2)
