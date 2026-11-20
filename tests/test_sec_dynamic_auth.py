"""
Security-control regression tests — dynamic/delegated authentication and OIDC.

Controls covered:
  Dynamic  Session-manager lease lifecycle, challenge-response, TTL bounding
  AUD-02   Delegated subprocess credential arguments and context cleanup
  AUD-03   OIDC middleware-to-MCP scope authorization
  DAUTH-10 Multi-client transport isolation & Anti-IDOR enforcement (HackerOne #4212881)

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
)


def _cfg(admin_id=SVC_ADMIN_ID):
    return make_config_with_cred(admin_id=admin_id)


def _admc(cfg):
    admc = MagicMock()
    admc.config = cfg
    admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
    return admc


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
# DAUTH-10: Multi-Client Transport Isolation & Anti-IDOR Enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiClientDynamicAuthIsolation:
    """
    Regression suite for HackerOne #4212881 and DAUTH-10 control.
    Verifies multi-client isolation, anti-IDOR explicit parameter protection,
    protected logout revocation, compound dual-identity audit trail, and
    SSE endpoint path advertisement.
    """

    def test_cross_client_session_bleed_denied(self, monkeypatch):
        """
        TC-DAUTH-24: Client B cannot inherit Client A's session in the same process.
        When Client A authenticates with high privilege (system), Client B on a separate
        connection/OIDC identity without credentials receives AUTHENTICATION_REQUIRED
        and does not inherit Client A's session lease or execution credentials.
        """
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_session_id,
            current_connection_id,
            current_oidc_subject,
            current_audit_user,
            current_request_privilege,
        )
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Client A authenticates and establishes a system-privilege session
        lease_a = global_session_manager.create_session(
            "alice_admin",
            {"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_alice",
            password="alice_password",
        )

        # Client B sends a request on a distinct connection (conn_bob) and subject (bob_oidc)
        # without an active session
        tok_conn = current_connection_id.set("conn_bob")
        tok_sub = current_oidc_subject.set("bob_oidc")
        tok_audit = current_audit_user.set("bob_oidc")
        tok_priv = current_request_privilege.set("system")
        tok_sess = current_session_id.set(None)

        try:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                ),
            )
            res = run_tool(handler, req)
            payload = json.loads(first_text(res))
            assert payload.get("is_error") is True
            assert payload.get("error_type") == "AUTHENTICATION_REQUIRED"
        finally:
            current_session_id.reset(tok_sess)
            current_request_privilege.reset(tok_priv)
            current_audit_user.reset(tok_audit)
            current_oidc_subject.reset(tok_sub)
            current_connection_id.reset(tok_conn)

    def test_explicit_session_id_idor_rejected(self, monkeypatch):
        """
        TC-DAUTH-25: Supplying another client's explicit _session_id returns AUTHORIZATION_DENIED.
        Client A holds an active session bound to 'alice_oidc'. Client B ('bob_oidc') attempts
        to redeem Client A's session by passing arguments["_session_id"] = lease_a.session_id.
        Anti-IDOR ownership check must reject this with AUTHORIZATION_DENIED.
        """
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_session_id,
            current_connection_id,
            current_oidc_subject,
            current_audit_user,
            current_request_privilege,
        )
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        # Client A creates a system session
        lease_a = global_session_manager.create_session(
            "alice_admin",
            {"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_alice",
            password="alice_password",
        )

        # Client B passes Client A's session ID explicitly
        tok_conn = current_connection_id.set("conn_bob")
        tok_sub = current_oidc_subject.set("bob_oidc")
        tok_audit = current_audit_user.set("bob_oidc")
        tok_priv = current_request_privilege.set("system")
        tok_sess = current_session_id.set(None)

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
            assert "belong" in payload.get("message", "").lower()
        finally:
            current_session_id.reset(tok_sess)
            current_request_privilege.reset(tok_priv)
            current_audit_user.reset(tok_audit)
            current_oidc_subject.reset(tok_sub)
            current_connection_id.reset(tok_conn)

    def test_logout_does_not_terminate_other_client_sessions(self, monkeypatch):
        """
        TC-DAUTH-26: Client B logout does not disrupt Client A's active session.
        Verifies anti-IDOR on logout (Client B cannot revoke Client A's lease by ID)
        and verifies that Client B revoking its own lease leaves Client A's lease intact.
        """
        from sp_mcp_server.mcp_factory import (
            current_session_id,
            current_connection_id,
            current_oidc_subject,
            current_audit_user,
        )
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.auth import LogoutSession

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")

        # Client A lease
        lease_a = global_session_manager.create_session(
            "alice_admin",
            {"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_alice",
            password="alice_password",
        )

        # Client B lease
        lease_b = global_session_manager.create_session(
            "bob_admin",
            {"operator"},
            oidc_subject="bob_oidc",
            connection_id="conn_bob",
            password="bob_password",
        )

        logout_tool = LogoutSession(MagicMock())

        # 1. Client B attempts to revoke Client A's lease directly -> rejected
        tok_conn = current_connection_id.set("conn_bob")
        tok_sub = current_oidc_subject.set("bob_oidc")
        tok_audit = current_audit_user.set("bob_oidc")
        tok_sess = current_session_id.set(lease_b.session_id)

        try:
            idor_result = json.loads(logout_tool.execute({"session_id": lease_a.session_id}))
            assert idor_result.get("is_error") is True
            assert idor_result.get("error_type") == "AUTHORIZATION_DENIED"

            # Confirm Client A lease is still active
            retrieved_a = global_session_manager.get_session(lease_a.session_id)
            assert retrieved_a is not None
            assert retrieved_a.password == "alice_password"

            # 2. Client B revokes its own lease -> succeeds
            own_result = json.loads(logout_tool.execute({"session_id": lease_b.session_id}))
            assert own_result.get("success") is True

            # Confirm Client B lease is gone and password cleared
            assert global_session_manager.get_session(lease_b.session_id) is None
            assert lease_b.password is None

            # Confirm Client A lease remains intact
            retrieved_a_after = global_session_manager.get_session(lease_a.session_id)
            assert retrieved_a_after is not None
            assert retrieved_a_after.password == "alice_password"
        finally:
            current_session_id.reset(tok_sess)
            current_audit_user.reset(tok_audit)
            current_oidc_subject.reset(tok_sub)
            current_connection_id.reset(tok_conn)

    def test_dual_audit_attribution_logged(self, monkeypatch):
        """
        TC-DAUTH-27: POL-4 audit logs record both OIDC sub and SP admin username.
        When a mutating command executes under a dynamic session over HTTP/SSE,
        the Activity Log scratchpad entry contains both oidc_user and sp_admin.
        """
        from sp_mcp_server.mcp_factory import (
            create_mcp_server,
            current_session_id,
            current_connection_id,
            current_oidc_subject,
            current_audit_user,
            current_auth_model,
            current_request_privilege,
        )
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        cfg = _cfg()
        admc = _admc(cfg)
        admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]

        lease = global_session_manager.create_session(
            "admin_alice",
            {"system"},
            oidc_subject="alice_oidc",
            connection_id="conn_alice",
            password="alice_password",
        )

        tok_conn = current_connection_id.set("conn_alice")
        tok_sub = current_oidc_subject.set("alice_oidc")
        tok_audit = current_audit_user.set("alice_oidc")
        tok_sess = current_session_id.set(lease.session_id)
        tok_auth = current_auth_model.set("dynamic_session")
        tok_priv = current_request_privilege.set("system")

        try:
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET}
                    ),
                )
                res = run_tool(handler, req)
                assert first_text(res) == "Admin deleted"

            scratchpad_calls = [
                c[0][0] for c in admc.execute.call_args_list
                if "DEFINE SCRATCHPADENTRY" in str(c[0][0])
            ]
            assert len(scratchpad_calls) >= 1
            audit_call = scratchpad_calls[0]
            assert "oidc_user=alice_oidc" in audit_call
            assert "sp_admin=admin_alice" in audit_call
            assert "authmodel=dynamic_session" in audit_call
        finally:
            current_request_privilege.reset(tok_priv)
            current_auth_model.reset(tok_auth)
            current_session_id.reset(tok_sess)
            current_audit_user.reset(tok_audit)
            current_oidc_subject.reset(tok_sub)
            current_connection_id.reset(tok_conn)

    def test_sse_endpoint_advertisement_correct(self):
        """
        TC-DAUTH-28: SSE endpoint advertises /mcp/messages without path duplication.
        Verify that SseServerTransport in create_http_app is initialized with
        relative 'messages' path so that under Starlette Mount('/mcp', ...)
        the advertised POST message endpoint resolves to /mcp/messages.
        """
        from sp_mcp_server.http_server import create_http_app
        from starlette.routing import Mount

        mock_server = MagicMock()
        mock_server.create_initialization_options.return_value = {}

        app = create_http_app(
            mcp_server=mock_server,
            oidc_issuer="https://issuer.example.com/oauth",
            oidc_audience="sp-mcp-server",
        )

        # Locate /mcp Mount
        mcp_mount = next((r for r in app.routes if isinstance(r, Mount) and r.path == "/mcp"), None)
        assert mcp_mount is not None, "Could not find /mcp mount in Starlette routes"

        # Check subroutes under /mcp
        route_paths = [r.path for r in mcp_mount.routes]
        assert "/sse" in route_paths
        assert "/messages" in route_paths
