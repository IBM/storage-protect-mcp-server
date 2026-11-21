"""
Security-control regression tests — dynamic/delegated authentication and OIDC.

Controls covered:
  Dynamic  Session-manager lease lifecycle, challenge-response, TTL bounding
  AUD-02   Delegated subprocess credential arguments and context cleanup
  AUD-03   OIDC middleware-to-MCP scope authorization

Known pre-existing failures (do NOT treat as regressions):
  test_dynamic_auth_challenge_when_unauthenticated
      DeleteAdmin applies its own SYSTEM-account guard before dynamic auth runs,
      returning plain text instead of JSON AUTHENTICATION_REQUIRED.
  test_dynamic_auth_executes_when_session_authenticated
      current_audit_user stays as admin_test instead of switching to the
      dynamic session username.
  test_dynamic_auth_denies_insufficient_privilege
      Same guard issue as above.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch
import pytest

from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult, TextContent

from tests.fixtures import (
    make_config_with_cred,
    run_tool,
    first_text,
    mock_admc,
    SVC_ADMIN_ID,
    DYNAMIC_ADMIN_USER,
    DELEGATED_USER_2,
    DELEGATED_PASS_2,
    DELEGATED_USER_3,
    DELEGATED_PASS_3,
    ADMIN_NAME_TARGET,
    ADMIN_NAME_TARGET_NODE,
    SP_OUTPUT_SESSION_STRICT_TLS13,
    SP_OUTPUT_AUTH_OK,
    SP_OUTPUT_AUTH_FAIL_STDERR,
    SP_OUTPUT_SCRATCHPAD_OK,
)


def _cfg(admin_id=SVC_ADMIN_ID):
    return make_config_with_cred(admin_id=admin_id)


def _admc(cfg):
    admc = MagicMock()
    admc.config = cfg
    admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
    return admc


@pytest.fixture(autouse=True)
def clean_session_context():
    """Ensure clean global session store and task contextvars between tests."""
    from sp_mcp_server.session import global_session_manager
    from sp_mcp_server.mcp_factory import current_session_id, current_audit_user, current_connection_id
    global_session_manager.clear()
    tok_sid = current_session_id.set(None)
    tok_user = current_audit_user.set(None)
    tok_conn = current_connection_id.set(None)
    yield
    global_session_manager.clear()
    current_session_id.reset(tok_sid)
    current_audit_user.reset(tok_user)
    current_connection_id.reset(tok_conn)


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic authentication: session manager lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestDynamicAuthentication:
    """Tests for dynamic challenge-response, session leases, and zero-trace authentication."""

    def test_session_manager_lease_lifecycle(self):
        import time
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=1)
        lease = mgr.create_session(DYNAMIC_ADMIN_USER, {"system", "policy"})
        assert lease.username == DYNAMIC_ADMIN_USER
        assert not lease.is_expired()

        retrieved = mgr.get_session(lease.session_id)
        assert retrieved is not None
        assert retrieved.username == DYNAMIC_ADMIN_USER

        time.sleep(1.1)
        assert lease.is_expired()
        assert mgr.get_session(lease.session_id) is None

    def test_authenticate_session_tool_valid_credentials(self):
        from sp_mcp_server.commands.system.auth import AuthenticateSession
        from sp_mcp_server.session import global_session_manager

        admc = mock_admc()
        admc.execute_silent.side_effect = [
            (SP_OUTPUT_AUTH_OK, "", 0),
            ("Administrator Name: ADMIN_TEST\nSystem Privilege: Yes", "", 0),
        ]

        tool = AuthenticateSession(admc)
        result = json.loads(tool.execute({"username": "admin_test", "password": "valid_password_123"}))

        assert result["success"] is True
        assert result["username"] == "admin_test"
        assert "session_id" in result
        assert "system" in result["privileges"]

        session = global_session_manager.get_session(result["session_id"])
        assert session is not None
        assert session.username == "admin_test"

    def test_authenticate_session_tool_invalid_credentials(self):
        from sp_mcp_server.commands.system.auth import AuthenticateSession

        admc = mock_admc()
        admc.execute_silent.return_value = ("", "ANR2017E Invalid password", 1)

        tool = AuthenticateSession(admc)
        result = json.loads(tool.execute({"username": "admin_test", "password": "wrong_password"}))

        assert result["success"] is False
        assert result["returncode"] == 1
        assert "Authentication failed" in result["error"]

    def test_dynamic_auth_challenge_when_unauthenticated(self, monkeypatch):
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        current_session_id.set(None)

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET_NODE}
            ),
        )
        res = run_tool(handler, req)
        assert len(res.content) == 1
        payload = json.loads(first_text(res))
        assert payload.get("is_error") is True
        assert payload.get("error_type") == "AUTHENTICATION_REQUIRED"
        assert payload["challenge"]["auth_tool"] == "authenticate_session"

    def test_dynamic_auth_executes_when_session_authenticated(self, monkeypatch):
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id, current_audit_user
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session(DELEGATED_USER_2, {"system"})
        current_session_id.set(lease.session_id)

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                ),
            )

            async def _run_and_check():
                server_result = await handler(req)
                assert isinstance(server_result.root, CallToolResult)
                assert len(server_result.root.content) == 1
                block = server_result.root.content[0]
                assert isinstance(block, TextContent)
                assert block.text == "Admin deleted"
                assert current_audit_user.get() == DELEGATED_USER_2

            asyncio.run(_run_and_check())

    def test_session_ttl_is_bounded(self):
        from sp_mcp_server.session import SessionManager, MAX_SESSION_TTL_SECONDS

        mgr = SessionManager(default_ttl=MAX_SESSION_TTL_SECONDS + 100)
        lease = mgr.create_session(
            DYNAMIC_ADMIN_USER, {"any"},
            ttl_seconds=MAX_SESSION_TTL_SECONDS + 100,
        )
        assert lease.ttl_seconds == MAX_SESSION_TTL_SECONDS

    def test_dynamic_auth_denies_insufficient_privilege(self, monkeypatch):
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        _READ_ONLY_USER = "read_only_admin"
        lease = global_session_manager.create_session(_READ_ONLY_USER, {"any"})
        current_session_id.set(lease.session_id)

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
            ),
        )
        res = run_tool(handler, req)
        payload = json.loads(first_text(res))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"


# ─────────────────────────────────────────────────────────────────────────────
# AUD-02: Delegated subprocess credential arguments and context cleanup
# ─────────────────────────────────────────────────────────────────────────────

class TestDelegatedSubprocess:
    """
    AUD-02 — Verify that delegated session credentials are passed as -ID= / -PA=
    arguments to the subprocess, and that current_execution_credentials is cleared
    after each tool call in both the success and exception paths.
    """

    def test_delegated_credentials_passed_to_subprocess(self):
        """
        DAUTH-5a: When current_execution_credentials is set, DsmAdmcWrapper.execute()
        must include -ID=<user> and -PA=<pass> in the subprocess.run args.
        """
        import subprocess
        from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, current_execution_credentials
        from sp_mcp_server.config import ServerConfig, ModuleCredential
        from tests.fixtures import (
            SVC_ADMIN_ID, SVC_ADMIN_PASSWORD,
            TARGET_SERVER_01, SP_SERVER_PORT,
            DELEGATED_USER, DELEGATED_PASS,
        )

        cred = ModuleCredential(
            admin_id=SVC_ADMIN_ID,
            admin_password=SVC_ADMIN_PASSWORD,
            privilege="system",
        )
        config = ServerConfig(
            server_address=TARGET_SERVER_01,
            server_port=SP_SERVER_PORT,
            credentials={"system": cred},
        )
        wrapper = DsmAdmcWrapper(config, privilege="system")

        token = current_execution_credentials.set((DELEGATED_USER, DELEGATED_PASS))
        try:
            captured_args = []

            def fake_run(args, **kwargs):
                captured_args.extend(args)
                result = MagicMock()
                result.returncode = 0
                result.stdout = "OK"
                result.stderr = ""
                return result

            with patch("subprocess.run", side_effect=fake_run):
                wrapper.execute("QUERY STATUS")

            assert any(a.startswith(f"-ID={DELEGATED_USER}") for a in captured_args), (
                f"-ID={DELEGATED_USER} not found in subprocess args: {captured_args}"
            )
            assert any(a.startswith(f"-PA={DELEGATED_PASS}") for a in captured_args), (
                f"-PA={DELEGATED_PASS} not found in subprocess args: {captured_args}"
            )
        finally:
            current_execution_credentials.reset(token)

    def test_execution_credentials_cleared_after_tool_call_success(self, monkeypatch):
        """DAUTH-5b: current_execution_credentials must be None after a successful tool call."""
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.cli_wrapper import current_execution_credentials
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session(
            DELEGATED_USER_2, {"system"}, password=DELEGATED_PASS_2
        )
        current_session_id.set(lease.session_id)

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                ),
            )

            async def _run():
                await handler(req)
                assert current_execution_credentials.get() is None, (
                    "current_execution_credentials was not cleared after tool call"
                )

            asyncio.run(_run())

    def test_execution_credentials_cleared_after_tool_call_exception(self, monkeypatch):
        """DAUTH-5b: current_execution_credentials must be None even if the tool raises."""
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.cli_wrapper import current_execution_credentials
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session(
            DELEGATED_USER_3, {"system"}, password=DELEGATED_PASS_3
        )
        current_session_id.set(lease.session_id)

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        with patch.object(DeleteAdmin, "execute", side_effect=RuntimeError("boom")):
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                ),
            )

            async def _run():
                await handler(req)
                assert current_execution_credentials.get() is None, (
                    "current_execution_credentials was not cleared after tool exception"
                )

            asyncio.run(_run())


# ─────────────────────────────────────────────────────────────────────────────
# AUD-03: OIDC middleware-to-MCP scope authorization
# ─────────────────────────────────────────────────────────────────────────────

class TestOIDCAuthorization:
    """
    AUD-03 — Verify per-scope OIDC authorization through current_request_privilege
    context variable at MCP tool invocation.

    Tests cover every supported mcp:* scope, insufficient-scope denial, and
    unknown-scope resolution to 'any'.
    """

    def _make_server_with_system_tool(self, monkeypatch):
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "service_account")
        cfg = _cfg()
        admc = _admc(cfg)
        return create_mcp_server(
            server_name="oidc-test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

    def _call_tool(self, server, privilege_value):
        from sp_mcp_server.mcp_factory import current_request_privilege
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
            ),
        )
        token = current_request_privilege.set(privilege_value)
        try:
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                return run_tool(handler, req)
        finally:
            current_request_privilege.reset(token)

    def test_oidc_scope_system_allows_system_tool(self, monkeypatch):
        """mcp:system → privilege='system' must allow a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        assert first_text(self._call_tool(server, "system")) == "Admin deleted"

    def test_oidc_scope_policy_denies_system_tool(self, monkeypatch):
        """mcp:policy → privilege='policy' must deny a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        payload = json.loads(first_text(self._call_tool(server, "policy")))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_storage_denies_system_tool(self, monkeypatch):
        """mcp:storage → privilege='storage' must deny a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        payload = json.loads(first_text(self._call_tool(server, "storage")))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_operator_denies_system_tool(self, monkeypatch):
        """mcp:operator → privilege='operator' must deny a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        payload = json.loads(first_text(self._call_tool(server, "operator")))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_read_denies_system_tool(self, monkeypatch):
        """mcp:read → privilege='any' must deny a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        payload = json.loads(first_text(self._call_tool(server, "any")))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_read_allows_any_privilege_tool(self, monkeypatch):
        """mcp:read → privilege='any' must allow a tool that requires only 'any'."""
        from sp_mcp_server.mcp_factory import create_mcp_server, current_request_privilege
        from sp_mcp_server.commands.system.admin import QueryAdminUser

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "service_account")
        cfg = _cfg()
        admc = _admc(cfg)
        server = create_mcp_server(
            server_name="oidc-read-server",
            tool_classes=[QueryAdminUser],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="query_admin_user", arguments={"admin_name": "admin1"}
            ),
        )
        token = current_request_privilege.set("any")
        try:
            with patch.object(QueryAdminUser, "execute", return_value="Admin info"):
                res = run_tool(handler, req)
        finally:
            current_request_privilege.reset(token)
        assert first_text(res) == "Admin info"

    def test_oidc_unknown_scope_treated_as_any_denies_system_tool(self, monkeypatch):
        """
        A token with an unrecognized scope should resolve to 'any' privilege,
        which must deny a system-privilege tool.
        """
        from sp_mcp_server.http_server import SCOPE_PRIVILEGE_MAP, _privilege_rank

        unknown_scope = "mcp:nonexistent"
        assert unknown_scope not in SCOPE_PRIVILEGE_MAP

        scopes = [unknown_scope]
        privilege = "any"
        for scope_claim in scopes:
            tier = SCOPE_PRIVILEGE_MAP.get(scope_claim)
            if tier and _privilege_rank(tier) > _privilege_rank(privilege):
                privilege = tier
        assert privilege == "any", f"Expected 'any' for unknown scope, got '{privilege}'"

        server = self._make_server_with_system_tool(monkeypatch)
        payload = json.loads(first_text(self._call_tool(server, "any")))
        assert payload["error_type"] == "AUTHORIZATION_DENIED"


# ─────────────────────────────────────────────────────────────────────────────
# DAUTH-10: Multi-Client Transport Isolation & Session Binding
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiClientDynamicAuthIsolation:
    """
    Regression test suite for DAUTH-10 requirements:
    - Cryptographic OIDC principal and connection binding on ephemeral leases
    - Elimination of process-wide session bleeding across concurrent clients
    - Rejection of cross-client IDOR session redemption with AUTHORIZATION_DENIED
    - Isolation of logout revocation to the caller's own session
    - Dual-identity attribution logging in compound ACTLOG records
    - Correct SSE route path advertisement
    """

    def test_cross_client_session_bleed_denied(self, monkeypatch):
        """Client B must not inherit Client A's session in the same server process."""
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_session_id,
            current_audit_user,
            current_connection_id,
        )
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        current_session_id.set(None)

        # Client A authenticates and creates a session lease bound to alice_sub / conn_1
        lease_a = global_session_manager.create_session(
            username="alice_sp",
            privileges={"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_1",
            transport_mode="http",
        )

        cfg = _cfg()
        admc = _admc(cfg)
        server = create_mcp_server(
            server_name="bleed-test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Client B sends a tool request from conn_2 with bob_oidc identity and no session arg
        tok_user = current_audit_user.set("bob_oidc")
        tok_conn = current_connection_id.set("conn_2")
        tok_sid = current_session_id.set(None)
        try:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                ),
            )
            res = run_tool(handler, req)
            payload = json.loads(first_text(res))
            # Must trigger AUTHENTICATION_REQUIRED, not inherit Client A's session
            assert payload.get("is_error") is True
            assert payload.get("error_type") == "AUTHENTICATION_REQUIRED"
        finally:
            current_connection_id.reset(tok_conn)
            current_audit_user.reset(tok_user)
            current_session_id.reset(tok_sid)
            global_session_manager.revoke_session(lease_a.session_id)

    def test_explicit_session_id_idor_rejected(self, monkeypatch):
        """Passing another user's session_id must fail OIDC subject check with AUTHORIZATION_DENIED."""
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_audit_user,
            current_connection_id,
            current_session_id,
        )
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        current_session_id.set(None)

        # Client A creates a system-privileged lease
        lease_a = global_session_manager.create_session(
            username="alice_sp",
            privileges={"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_1",
            transport_mode="http",
        )

        cfg = _cfg()
        admc = _admc(cfg)
        server = create_mcp_server(
            server_name="idor-test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Client B attempts to use Client A's session ID explicitly
        tok_user = current_audit_user.set("bob_oidc")
        tok_conn = current_connection_id.set("conn_2")
        try:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin",
                    arguments={
                        "admin_name": ADMIN_NAME_TARGET,
                        "_session_id": lease_a.session_id,
                    },
                ),
            )
            res = run_tool(handler, req)
            payload = json.loads(first_text(res))
            assert payload.get("is_error") is True
            assert payload.get("error_type") == "AUTHORIZATION_DENIED"
            assert "Session does not belong to the authenticated user" in payload.get("message", "")
        finally:
            current_connection_id.reset(tok_conn)
            current_audit_user.reset(tok_user)
            global_session_manager.revoke_session(lease_a.session_id)

    def test_logout_does_not_terminate_other_client_sessions(self, monkeypatch):
        """Client B logging out must not terminate or affect Client A's active session lease."""
        from sp_mcp_server.mcp_factory import current_audit_user, current_connection_id, current_session_id
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.session import global_session_manager

        lease_a = global_session_manager.create_session(
            username="alice_sp",
            privileges={"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_1",
            transport_mode="http",
        )
        lease_b = global_session_manager.create_session(
            username="bob_sp",
            privileges={"system"},
            oidc_subject="bob_oidc",
            connection_id="conn_2",
            transport_mode="http",
        )

        admc = mock_admc()
        logout_tool = LogoutSession(admc)

        # 1. Bob attempts IDOR logout of Alice's session
        tok_user = current_audit_user.set("bob_oidc")
        tok_conn = current_connection_id.set("conn_2")
        tok_sid = current_session_id.set(lease_b.session_id)
        try:
            idor_res = json.loads(logout_tool.execute({"session_id": lease_a.session_id}))
            assert idor_res["success"] is False
            assert idor_res.get("error_type") == "AUTHORIZATION_DENIED"

            # Alice's session must still be intact
            assert global_session_manager.get_session(lease_a.session_id) is not None

            # 2. Bob revokes his own session
            bob_res = json.loads(logout_tool.execute({}))
            assert bob_res["success"] is True

            # Bob's session is revoked, but Alice's session remains active
            assert global_session_manager.get_session(lease_b.session_id) is None
            assert global_session_manager.get_session(lease_a.session_id) is not None
        finally:
            current_session_id.reset(tok_sid)
            current_connection_id.reset(tok_conn)
            current_audit_user.reset(tok_user)
            global_session_manager.revoke_session(lease_a.session_id)

    def test_dual_audit_attribution_logged(self, monkeypatch):
        """POL-4 / NR-1: Mutating tools in dynamic mode log compound attribution (oidc_user + sp_admin)."""
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_audit_user,
            current_connection_id,
            current_session_id,
        )
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session(
            username="alice_sp_admin",
            privileges={"system"},
            oidc_subject="alice_oidc_sub",
            connection_id="conn_sse_101",
            transport_mode="http",
        )

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="audit-dual-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        admc.execute.return_value = (SP_OUTPUT_SCRATCHPAD_OK, "", 0)

        tok_user = current_audit_user.set("alice_oidc_sub")
        tok_conn = current_connection_id.set("conn_sse_101")
        tok_sid = current_session_id.set(lease.session_id)
        try:
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                    ),
                )
                run_tool(handler, req)

            # Inspect DEFINE SCRATCHPADENTRY calls
            scratchpad_calls = [
                c[0][0] for c in admc.execute.call_args_list
                if "DEFINE SCRATCHPADENTRY" in str(c[0][0])
            ]
            assert len(scratchpad_calls) >= 1
            audit_call = scratchpad_calls[0]
            assert "oidc_user=alice_oidc_sub" in audit_call
            assert "sp_admin=alice_sp_admin" in audit_call
            assert "tool=delete_admin" in audit_call
            assert "corr=" in audit_call
        finally:
            current_session_id.reset(tok_sid)
            current_connection_id.reset(tok_conn)
            current_audit_user.reset(tok_user)
            global_session_manager.revoke_session(lease.session_id)

    def test_sse_endpoint_advertisement_correct(self):
        """SseServerTransport must advertise relative 'messages' to avoid double-prefix routing."""
        from sp_mcp_server.http_server import create_http_app
        from unittest.mock import MagicMock

        mock_server = MagicMock()
        app = create_http_app(mock_server, "https://login.example.com", "test-audience")

        # Find the Mount for /mcp
        mcp_mount = next((r for r in app.routes if getattr(r, "path", None) == "/mcp"), None)
        assert mcp_mount is not None

        # Verify /mcp has /sse and /messages sub-routes
        sub_paths = [getattr(r, "path", None) for r in mcp_mount.routes]
        assert "/sse" in sub_paths
        assert "/messages" in sub_paths

    @pytest.mark.asyncio
    async def test_stdio_dynamic_auth_multi_turn_sequence(self, monkeypatch):
        """
        DAUTH-10: Sequential dispatch of authenticate_session and subsequent tool calls
        across discrete asyncio.Task instances succeeds via single-tenant stdio fallback.
        """
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.auth import AuthenticateSession
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")

        cfg = _cfg()
        admc = _admc(cfg)
        admc.execute_silent.side_effect = [
            (SP_OUTPUT_AUTH_OK, "", 0),
            ("Administrator Name: DYN_ADMIN\nSystem Privilege: Yes", "", 0),
        ]

        server = create_mcp_server(
            server_name="stdio-turn-server",
            tool_classes=[AuthenticateSession, DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Task 1: Human admin authenticates in first interaction turn
        async def turn_1():
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="authenticate_session",
                    arguments={"username": "dyn_admin", "password": "valid_password_123"},
                ),
            )
            return await handler(req)

        t1_res = await asyncio.create_task(turn_1())
        t1_payload = json.loads(t1_res.root.content[0].text)
        assert t1_payload["success"] is True
        assert t1_payload["username"] == "dyn_admin"
        sid = t1_payload["session_id"]
        assert global_session_manager.get_session_id_for_connection("stdio") == sid

        # Task 2: Discrete asyncio.Task executes subsequent tool WITHOUT explicit _session_id or inherited contextvar
        async def turn_2():
            with patch.object(DeleteAdmin, "execute", return_value="Admin target deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin",
                        arguments={"admin_name": ADMIN_NAME_TARGET},
                    ),
                )
                return await handler(req)

        t2_res = await asyncio.create_task(turn_2())
        assert isinstance(t2_res.root, CallToolResult)
        assert t2_res.root.content[0].text == "Admin target deleted"

    @pytest.mark.asyncio
    async def test_stdio_reauthentication_supersedes_prior_lease(self, monkeypatch):
        """
        DAUTH-10: Sequential re-authentication under a new admin account supersedes prior lease
        in reverse-chronological order.
        """
        from sp_mcp_server.mcp_factory import create_mcp_server, current_execution_credentials
        from sp_mcp_server.commands.system.auth import AuthenticateSession
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="stdio-reauth-server",
            tool_classes=[AuthenticateSession, DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Mint Lease 1: Alice (Storage privilege)
        lease_alice = global_session_manager.create_session(
            username="alice_sp",
            privileges={"storage"},
            connection_id="stdio",
            transport_mode="stdio",
            password="alice_password",
        )

        # Mint Lease 2: Bob (System privilege) - created later, must supersede Lease 1
        lease_bob = global_session_manager.create_session(
            username="bob_sp",
            privileges={"system"},
            connection_id="stdio",
            transport_mode="stdio",
            password="bob_password",
        )

        # Verify reverse lookup resolves to Bob
        resolved_sid = global_session_manager.get_session_id_for_connection("stdio")
        assert resolved_sid == lease_bob.session_id

        # Execute tool requiring 'system' privilege in a fresh task
        captured_cred = None

        def record_and_run(*a, **kw):
            nonlocal captured_cred
            captured_cred = current_execution_credentials.get()
            return "Deleted by Bob"

        async def run_tool_turn():
            with patch.object(DeleteAdmin, "execute", side_effect=record_and_run):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin",
                        arguments={"admin_name": ADMIN_NAME_TARGET},
                    ),
                )
                return await handler(req)

        res = await asyncio.create_task(run_tool_turn())
        assert res.root.content[0].text == "Deleted by Bob"
        assert captured_cred == ("bob_sp", "bob_password")

    def test_sse_cross_user_post_rejected_with_403(self):
        """
        DAUTH-11: Foreign caller POST to active stream UUID is rejected with HTTP 403 Forbidden.
        """
        from starlette.testclient import TestClient
        from unittest.mock import MagicMock
        from sp_mcp_server.http_server import (
            create_http_app,
            record_stream_owner,
            remove_stream_owner,
            OIDCBearerMiddleware,
        )

        mock_server = MagicMock()
        app = create_http_app(mock_server, "https://login.example.com", "test-aud")

        async def mock_get_jwks(self):
            self._jwks_uri = "https://login.example.com/jwks"
            return {"keys": []}

        stream_sid = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
        record_stream_owner(stream_sid, "alice_oidc_sub")
        try:
            client = TestClient(app, raise_server_exceptions=False)
            with patch.object(OIDCBearerMiddleware, "_get_jwks", mock_get_jwks):
                with patch("jwt.PyJWKClient.get_signing_key_from_jwt"):
                    with patch("jwt.decode", return_value={
                        "sub": "bob_oidc_sub",
                        "scope": "mcp:system",
                        "exp": 9999999999,
                        "iat": 1000000000,
                    }):
                        resp = client.post(
                            f"/mcp/messages?session_id={stream_sid}",
                            headers={"Authorization": "Bearer bob_token"},
                            json={"jsonrpc": "2.0", "method": "tools/call", "params": {}, "id": 1},
                        )

            assert resp.status_code == 403
            err_body = resp.json()
            assert err_body["error"]["code"] == -32001
            assert "Forbidden: stream does not belong to authenticated user" in err_body["error"]["message"]
        finally:
            remove_stream_owner(stream_sid)

    def test_sse_legitimate_post_accepted_with_202(self):
        """
        DAUTH-11: Legitimate stream owner POST to matching stream UUID is accepted with HTTP 202.
        """
        from starlette.testclient import TestClient
        from unittest.mock import MagicMock, AsyncMock
        import uuid
        from sp_mcp_server.http_server import (
            create_http_app,
            record_stream_owner,
            remove_stream_owner,
            OIDCBearerMiddleware,
        )

        mock_server = MagicMock()
        app = create_http_app(mock_server, "https://login.example.com", "test-aud")

        async def mock_get_jwks(self):
            self._jwks_uri = "https://login.example.com/jwks"
            return {"keys": []}

        stream_uuid = uuid.UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")
        mock_writer = AsyncMock()

        mcp_mount = next(r for r in app.routes if getattr(r, "path", None) == "/mcp")
        msg_mount = next(r for r in mcp_mount.routes if getattr(r, "path", None) == "/messages")

        transport = None
        for cell in (msg_mount.app.__closure__ or []):
            if hasattr(cell.cell_contents, "_read_stream_writers"):
                transport = cell.cell_contents
                break

        assert transport is not None
        transport._read_stream_writers[stream_uuid] = mock_writer

        record_stream_owner(str(stream_uuid), "alice_oidc_sub")
        try:
            client = TestClient(app, raise_server_exceptions=False)
            with patch.object(OIDCBearerMiddleware, "_get_jwks", mock_get_jwks):
                with patch("jwt.PyJWKClient.get_signing_key_from_jwt"):
                    with patch("jwt.decode", return_value={
                        "sub": "alice_oidc_sub",
                        "scope": "mcp:system",
                        "exp": 9999999999,
                        "iat": 1000000000,
                    }):
                        resp = client.post(
                            f"/mcp/messages?session_id={stream_uuid.hex}",
                            headers={"Authorization": "Bearer alice_token"},
                            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
                        )

            assert resp.status_code == 202
        finally:
            transport._read_stream_writers.pop(stream_uuid, None)
            remove_stream_owner(str(stream_uuid))

    @pytest.mark.asyncio
    async def test_cross_transport_stdio_leak_blocked(self, monkeypatch):
        """
        DAUTH-10: Network HTTP/SSE request never inherits local "stdio" lease.
        """
        from sp_mcp_server.mcp_factory import create_mcp_server, current_connection_id
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")

        # Mint a local stdio session lease
        stdio_lease = global_session_manager.create_session(
            username="local_admin",
            privileges={"system"},
            connection_id="stdio",
            transport_mode="stdio",
            password="secret_password",
        )

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="cross-transport-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # 1. Unauthenticated network connection (has conn_id from SSE transport, but no session)
        tok_conn = current_connection_id.set("conn_sse_net_100")
        try:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin",
                    arguments={"admin_name": ADMIN_NAME_TARGET},
                ),
            )
            res1 = await handler(req)
            payload1 = json.loads(res1.root.content[0].text)
            # Must trigger dynamic auth challenge and NOT inherit the stdio lease
            assert payload1.get("is_error") is True
            assert payload1.get("error_type") == "AUTHENTICATION_REQUIRED"

            # 2. Network caller attempts explicit IDOR using the stdio lease ID
            req_idor = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin",
                    arguments={"admin_name": ADMIN_NAME_TARGET, "_session_id": stdio_lease.session_id},
                ),
            )
            res2 = await handler(req_idor)
            payload2 = json.loads(res2.root.content[0].text)
            assert payload2.get("is_error") is True
            assert payload2.get("error_type") == "AUTHORIZATION_DENIED"
            assert "Cross-transport session access denied" in payload2.get("message", "")
        finally:
            current_connection_id.reset(tok_conn)
