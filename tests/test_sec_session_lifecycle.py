"""
Security-control regression tests — session lifecycle and target-server binding.

Controls covered:
  AUD-05  Entry-point secure_startup() inventory validation
  AUD-08  Session-management credential zeroing in all removal paths
  DAUTH-7 Target-server binding — cross-server session reuse prevention
"""

import asyncio
import json
from unittest.mock import MagicMock, patch
import pytest

from mcp.types import CallToolRequest, CallToolRequestParams

from tests.fixtures import (
    make_config_with_cred,
    make_system_cred_config,
    run_tool,
    first_text,
    SVC_ADMIN_ID,
    TARGET_SERVER_01,
    TARGET_SERVER_02,
    SESSION_LEASE_ID_A,
    SESSION_LEASE_ID_B,
    SESSION_LEASE_ID_C,
    SESSION_PASSWORD_ALICE,
    SESSION_PASSWORD_BOB,
    SESSION_PASSWORD_CAROL,
    SESSION_PASSWORD_DAVE,
    SESSION_PASSWORD_EVE,
    SESSION_PASSWORD_FRANK,
    SESSION_PASSWORD_GRACE,
    SP_OUTPUT_SESSION_STRICT_TLS13,
    ADMIN_NAME_TARGET,
)


def _cfg(admin_id=SVC_ADMIN_ID):
    return make_config_with_cred(admin_id=admin_id)


def _admc(cfg):
    admc = MagicMock()
    admc.config = cfg
    admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
    return admc


# ─────────────────────────────────────────────────────────────────────────────
# AUD-05: Entry-point secure_startup inventory validation
# ─────────────────────────────────────────────────────────────────────────────

class TestEntryPointStartup:
    """
    AUD-05 — Automated inventory test: every main*.py entry point must import
    and call secure_startup() to prevent new entry points from bypassing the
    startup security helper.
    """

    def test_all_main_entry_points_use_secure_startup(self):
        """
        Scan all main.py and main_*.py entry points in the sp_mcp_server package
        and assert that each file contains a call to secure_startup().
        """
        import glob as _glob
        import os

        tests_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.normpath(os.path.join(tests_dir, "..", "src", "sp_mcp_server"))

        entry_points = _glob.glob(os.path.join(src_dir, "main.py"))
        entry_points += _glob.glob(os.path.join(src_dir, "main_*.py"))

        assert len(entry_points) > 0, (
            f"No main*.py entry points found under {src_dir}. "
            "Check the source directory path."
        )

        missing = []
        for path in sorted(entry_points):
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            if "secure_startup" not in content:
                missing.append(os.path.basename(path))

        assert missing == [], (
            f"The following entry points do not call secure_startup(): {missing}. "
            "All main*.py files must import and invoke secure_startup() at startup."
        )


# ─────────────────────────────────────────────────────────────────────────────
# AUD-08: Session-management credential-lifecycle and logout_session tool
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionCredentialLifecycle:
    """
    AUD-08 — Verify that SessionLease.password is zeroed (set to None) in
    every removal path: explicit revocation, expiry on get_session(), and
    bulk cleanup_expired().
    """

    def test_password_zeroed_on_revoke(self):
        """revoke_session() must set lease.password = None before removing."""
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=900)
        lease = mgr.create_session("alice", {"system"}, password=SESSION_PASSWORD_ALICE)
        assert lease.password == SESSION_PASSWORD_ALICE

        revoked = mgr.revoke_session(lease.session_id)

        assert revoked is True
        assert lease.password is None, (
            "SessionLease.password must be zeroed after revoke_session()"
        )
        assert mgr.get_session(lease.session_id) is None

    def test_password_zeroed_on_expiry_in_get_session(self):
        """get_session() must zero the password when an expired lease is removed."""
        import time
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=1)
        lease = mgr.create_session("bob", {"any"}, password=SESSION_PASSWORD_BOB, ttl_seconds=1)
        assert lease.password == SESSION_PASSWORD_BOB

        time.sleep(1.1)

        result = mgr.get_session(lease.session_id)
        assert result is None
        assert lease.password is None, (
            "SessionLease.password must be zeroed when an expired lease is removed in get_session()"
        )

    def test_password_zeroed_on_cleanup_expired(self):
        """cleanup_expired() must zero the password on each expired lease."""
        import time
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=1)
        lease = mgr.create_session(
            "carol", {"policy"}, password=SESSION_PASSWORD_CAROL, ttl_seconds=1
        )
        assert lease.password == SESSION_PASSWORD_CAROL

        time.sleep(1.1)

        count = mgr.cleanup_expired()
        assert count == 1
        assert lease.password is None, (
            "SessionLease.password must be zeroed during cleanup_expired()"
        )

    def test_password_zeroed_on_clear(self):
        """clear() must zero the password on every lease before clearing the store."""
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=900)
        lease_a = mgr.create_session("dave", {"system"}, password=SESSION_PASSWORD_DAVE)
        lease_b = mgr.create_session("eve", {"any"}, password=SESSION_PASSWORD_EVE)

        mgr.clear()

        assert lease_a.password is None, "clear() must zero lease_a.password"
        assert lease_b.password is None, "clear() must zero lease_b.password"

    def test_logout_session_revokes_and_clears_credential(self):
        """logout_session tool must revoke the session and confirm credential cleared."""
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.mcp_factory import current_session_id

        lease = global_session_manager.create_session(
            "frank", {"system"}, password=SESSION_PASSWORD_FRANK
        )
        current_session_id.set(lease.session_id)

        tool = LogoutSession(MagicMock())
        result = json.loads(tool.execute({}))

        assert result["success"] is True
        assert "revoked" in result["message"].lower() or "cleared" in result["message"].lower()
        assert global_session_manager.get_session(lease.session_id) is None
        assert lease.password is None

    def test_logout_session_no_active_session(self):
        """logout_session with no session context returns success=False gracefully."""
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.mcp_factory import current_session_id

        current_session_id.set(None)
        tool = LogoutSession(MagicMock())
        result = json.loads(tool.execute({}))

        assert result["success"] is False
        assert "no active session" in result["message"].lower()

    def test_logout_session_explicit_session_id(self):
        """logout_session with an explicit session_id revokes that session."""
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.mcp_factory import current_session_id

        lease = global_session_manager.create_session(
            "grace", {"operator"}, password=SESSION_PASSWORD_GRACE
        )
        current_session_id.set(None)

        tool = LogoutSession(MagicMock())
        result = json.loads(tool.execute({"session_id": lease.session_id}))

        assert result["success"] is True
        assert global_session_manager.get_session(lease.session_id) is None
        assert lease.password is None


# ─────────────────────────────────────────────────────────────────────────────
# DAUTH-7: target_server binding — cross-server session reuse prevention
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetServerBinding:
    """
    DAUTH-7 — Verify that a session whose target_server does not match the
    active server configuration is rejected with AUTHORIZATION_DENIED before
    any command executes.
    """

    def _make_server(self, monkeypatch, server_address=TARGET_SERVER_01):
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        cfg = make_system_cred_config(server_address=server_address)
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
        server = create_mcp_server(
            server_name="target-server-test",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        return server, cfg

    def test_cross_server_session_is_denied(self, monkeypatch):
        """
        A session authenticated against TARGET_SERVER_02 must be rejected when
        the MCP server is configured for TARGET_SERVER_01.
        """
        from sp_mcp_server.mcp_factory import current_session_id
        from sp_mcp_server.session import global_session_manager

        server, _ = self._make_server(monkeypatch, server_address=TARGET_SERVER_01)

        lease = global_session_manager.create_session(
            "alice", {"system"},
            target_server=TARGET_SERVER_02,
            password="pw",
        )
        current_session_id.set(lease.session_id)

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": "target"}
            ),
        )
        res = run_tool(handler, req)
        payload = json.loads(first_text(res))

        assert payload["error_type"] == "AUTHORIZATION_DENIED", (
            f"Expected AUTHORIZATION_DENIED for cross-server session reuse, got: {payload}"
        )
        assert TARGET_SERVER_02 in payload["message"]
        assert TARGET_SERVER_01 in payload["message"]

    def test_matching_target_server_is_allowed(self, monkeypatch):
        """
        A session whose target_server matches the MCP server's server_address
        must be allowed through.
        """
        from sp_mcp_server.mcp_factory import current_session_id
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        server, _ = self._make_server(monkeypatch, server_address=TARGET_SERVER_01)

        lease = global_session_manager.create_session(
            "bob", {"system"},
            target_server=TARGET_SERVER_01,
            password="pw",
        )
        current_session_id.set(lease.session_id)

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": "target"}
            ),
        )
        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
            res = run_tool(handler, req)
        assert first_text(res) == "Admin deleted"

    def test_no_target_server_on_session_is_allowed(self, monkeypatch):
        """
        A session created without a target_server (single-server deployment)
        must not be rejected.
        """
        from sp_mcp_server.mcp_factory import current_session_id
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        server, _ = self._make_server(monkeypatch, server_address=TARGET_SERVER_01)

        lease = global_session_manager.create_session(
            "carol", {"system"},
            target_server=None,
            password="pw",
        )
        current_session_id.set(lease.session_id)

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": "target"}
            ),
        )
        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
            res = run_tool(handler, req)
        assert first_text(res) == "Admin deleted"

    def test_check_session_target_server_helper_mismatch(self):
        """Unit-test the helper directly for the mismatch path."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id=SESSION_LEASE_ID_A,
            username="dave",
            privilege_classes={"system"},
            target_server=TARGET_SERVER_02,
        )

        class FakeConfig:
            server_address = TARGET_SERVER_01

        err = _check_session_target_server(lease, FakeConfig())
        assert err is not None
        assert TARGET_SERVER_02 in err
        assert TARGET_SERVER_01 in err

    def test_check_session_target_server_helper_match(self):
        """Unit-test the helper directly for the matching path."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id=SESSION_LEASE_ID_B,
            username="eve",
            privilege_classes={"system"},
            target_server=TARGET_SERVER_01,
        )

        class FakeConfig:
            server_address = TARGET_SERVER_01

        assert _check_session_target_server(lease, FakeConfig()) is None

    def test_check_session_target_server_helper_no_target(self):
        """Unit-test the helper: no target_server on session → None (skipped)."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id=SESSION_LEASE_ID_C,
            username="frank",
            privilege_classes={"any"},
            target_server=None,
        )

        class FakeConfig:
            server_address = TARGET_SERVER_01

        assert _check_session_target_server(lease, FakeConfig()) is None
