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
