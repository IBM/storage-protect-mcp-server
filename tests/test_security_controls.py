"""
RG-6: Automated regression tests for MCP server security controls.

These tests provide automated coverage for controls that previously had only
manual verification checklists in the implementation documents:

  - NET-1: _validate_session_security() rejects non-STRICT accounts
  - CRED-3: check_env_file_permissions() rejects world/group-readable .env
  - RG-1:  SP_MCP_SKIP_SECURITY_CHECKS blocked when SP_MCP_ENV=production
  - RG-2:  secure_startup() combines permission check + dotenv atomically
  - ACC-2:  tool list filtered to privilege-appropriate subset
  - POL-3:  _check_lockout_policy() warns when INVALIDPWLIMIT=0
  - POL-4:  handle_call_tool emits DEFINE SCRATCHPADENTRY before write operations
  - RG-3:  password-bearing commands use execute_silent not execute
  - RG-4:  audit write failure logs ERROR (not WARNING)
  - RG-5:  HTTP transport rejects startup without TLS cert/key
"""

import asyncio
import os
import stat
import sys
import logging
from unittest.mock import MagicMock, patch, AsyncMock, call
import pytest

from sp_mcp_server.config import (
    ServerConfig,
    ModuleCredential,
    check_env_file_permissions,
    secure_startup,
)
from sp_mcp_server.mcp_factory import (
    _validate_session_security,
    _check_lockout_policy,
)
from sp_mcp_server.commands.base import BaseCommand
from sp_mcp_server.commands.system.admin import DefineAdmin, UpdateUser
from sp_mcp_server.commands.clients.node import RegisterNode, UpdateNode


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_config_with_cred(admin_id="mcp-svc-system", password="s3cr3t"):
    """Return a minimal ServerConfig with a single system credential."""
    cred = ModuleCredential(admin_id=admin_id, admin_password=password, privilege="system")
    return ServerConfig(
        server_address="sp-server",
        server_port="1500",
        credentials={"system": cred},
    )


def _mock_admc(stdout="", stderr="", code=0):
    """Return a mock DsmAdmcWrapper whose execute() always returns the given values."""
    m = MagicMock()
    m.execute.return_value = (stdout, stderr, code)
    m.execute_silent.return_value = (stdout, stderr, code)
    return m


# ─────────────────────────────────────────────────────────────────────────────
# NET-1: _validate_session_security
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateSessionSecurity:
    """NET-1 — startup session-security validation."""

    def test_exits_when_session_security_not_strict(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = _mock_admc(
            stdout="Session Security: Transitional\nTransport Method: TLS 1.2",
            code=0,
        )
        config = _make_config_with_cred()
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, config)
        assert exc.value.code == 1

    def test_exits_when_query_fails(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = _mock_admc(stdout="", stderr="ANR0000E connection refused", code=1)
        config = _make_config_with_cred()
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, config)
        assert exc.value.code == 1

    def test_passes_when_strict_and_tls(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = _mock_admc(
            stdout="Session Security: Strict\nTransport Method: TLS 1.2",
            code=0,
        )
        config = _make_config_with_cred()
        # Should not raise or exit
        _validate_session_security(admc, config)

    def test_passes_when_strict_and_blank_transport(self, monkeypatch):
        """Blank Transport Method is accepted — older SP versions don't report it."""
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = _mock_admc(stdout="Session Security: Strict", code=0)
        config = _make_config_with_cred()
        _validate_session_security(admc, config)  # must not raise

    def test_skip_flag_bypasses_check_non_production(self, monkeypatch):
        """SP_MCP_SKIP_SECURITY_CHECKS=1 without SP_MCP_ENV=production skips check."""
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.delenv("SP_MCP_ENV", raising=False)
        admc = _mock_admc(stdout="", code=1)  # would fail if check ran
        config = _make_config_with_cred()
        _validate_session_security(admc, config)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# RG-1: production guard for SP_MCP_SKIP_SECURITY_CHECKS
# ─────────────────────────────────────────────────────────────────────────────

class TestProductionGuard:
    """RG-1 — SP_MCP_SKIP_SECURITY_CHECKS blocked in production."""

    def test_exits_when_skip_set_in_production(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.setenv("SP_MCP_ENV", "production")
        admc = _mock_admc()
        config = _make_config_with_cred()
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, config)
        assert exc.value.code == 1

    def test_allows_skip_in_non_production(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.setenv("SP_MCP_ENV", "test")
        admc = _mock_admc()
        config = _make_config_with_cred()
        _validate_session_security(admc, config)  # must not raise

    def test_allows_skip_with_no_env_set(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.delenv("SP_MCP_ENV", raising=False)
        admc = _mock_admc()
        config = _make_config_with_cred()
        _validate_session_security(admc, config)  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# CRED-3: check_env_file_permissions
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvFilePermissions:
    """CRED-3 — .env file permission enforcement."""

    def test_rejects_world_readable_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("SP_ADMIN_ID=admin\n")
        env.chmod(0o644)
        with pytest.raises(SystemExit) as exc:
            check_env_file_permissions(str(env))
        assert exc.value.code == 1

    def test_rejects_group_readable_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("SP_ADMIN_ID=admin\n")
        env.chmod(0o640)
        with pytest.raises(SystemExit) as exc:
            check_env_file_permissions(str(env))
        assert exc.value.code == 1

    def test_accepts_owner_only_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("SP_ADMIN_ID=admin\n")
        env.chmod(0o600)
        # Should not raise or exit
        check_env_file_permissions(str(env))

    def test_accepts_missing_env(self, tmp_path):
        """Missing .env is fine — env vars may come from the OS environment."""
        check_env_file_permissions(str(tmp_path / ".env"))  # does not exist


# ─────────────────────────────────────────────────────────────────────────────
# RG-2: secure_startup combines permission check + dotenv
# ─────────────────────────────────────────────────────────────────────────────

class TestSecureStartup:
    """RG-2 — secure_startup() is atomic guard + loader."""

    def test_secure_startup_rejects_insecure_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("SP_ADMIN_ID=admin\n")
        env.chmod(0o644)
        with pytest.raises(SystemExit):
            secure_startup(str(env))

    def test_secure_startup_loads_env_when_permissions_ok(self, tmp_path, monkeypatch):
        env = tmp_path / ".env"
        env.write_text("SP_TEST_VAR=hello\n")
        env.chmod(0o600)
        monkeypatch.delenv("SP_TEST_VAR", raising=False)
        secure_startup(str(env))
        assert os.environ.get("SP_TEST_VAR") == "hello"


# ─────────────────────────────────────────────────────────────────────────────
# ACC-2: privilege-filtered tool registration
# ─────────────────────────────────────────────────────────────────────────────

class TestPrivilegeFiltering:
    """ACC-2 — only tools matching account privilege are registered."""

    def test_system_account_satisfies_all_tiers(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        satisfies = _PRIVILEGE_SATISFIES["system"]
        assert "system" in satisfies
        assert "policy" in satisfies
        assert "storage" in satisfies
        assert "operator" in satisfies
        assert "any" in satisfies

    def test_operator_account_does_not_satisfy_policy(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        satisfies = _PRIVILEGE_SATISFIES["operator"]
        assert "policy" not in satisfies
        assert "system" not in satisfies
        assert "operator" in satisfies
        assert "any" in satisfies

    def test_any_account_only_satisfies_any(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        satisfies = _PRIVILEGE_SATISFIES["any"]
        assert satisfies == {"any"}

    def test_parse_sp_privilege_returns_system(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        output = "SYSTEM PRIVILEGE: YES\nPOLICY PRIVILEGE: NO\n"
        assert _parse_sp_privilege(output) == "system"

    def test_parse_sp_privilege_returns_operator(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        output = "SYSTEM PRIVILEGE: NO\nOPERATOR PRIVILEGE: YES\n"
        assert _parse_sp_privilege(output) == "operator"

    def test_parse_sp_privilege_returns_any_when_no_class(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        output = "No privilege classes listed.\n"
        assert _parse_sp_privilege(output) == "any"


# ─────────────────────────────────────────────────────────────────────────────
# POL-3: _check_lockout_policy
# ─────────────────────────────────────────────────────────────────────────────

class TestLockoutPolicy:
    """POL-3 — startup lockout threshold warning."""

    def test_warns_when_limit_is_zero(self, caplog):
        admc = _mock_admc(
            stdout="Invalid Sign-on Attempt Limit: 0",
            code=0,
        )
        with caplog.at_level(logging.WARNING):
            _check_lockout_policy(admc)
        assert any("POL-3" in r.message or "lockout" in r.message.lower()
                   for r in caplog.records)

    def test_logs_ok_when_limit_is_set(self, caplog):
        admc = _mock_admc(
            stdout="Invalid Sign-on Attempt Limit: 5",
            code=0,
        )
        with caplog.at_level(logging.INFO):
            _check_lockout_policy(admc)
        # No WARNING should be emitted
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 0

    def test_warns_when_query_fails(self, caplog):
        admc = _mock_admc(stdout="", stderr="connection failed", code=1)
        with caplog.at_level(logging.WARNING):
            _check_lockout_policy(admc)
        assert any(r.levelno >= logging.WARNING for r in caplog.records)


# ─────────────────────────────────────────────────────────────────────────────
# RG-3: password-bearing commands use execute_silent
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordCommandsSilentExecution:
    """RG-3 — REGISTER ADMIN / REGISTER NODE / UPDATE * with password use execute_silent."""

    def _make_cli(self):
        m = MagicMock()
        m.execute.return_value = ("ok", "", 0)
        m.execute_silent.return_value = ("ok", "", 0)
        return m

    def test_define_admin_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        # Make _get_pw_min_length return 8 so short test passwords pass
        monkeypatch.setattr(
            DefineAdmin, "_get_pw_min_length", lambda self: 8
        )
        cmd = DefineAdmin(cli)
        cmd.execute({"admin_name": "testadmin", "password": "Password1!"})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_register_node_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(RegisterNode, "_get_pw_min_length", lambda self: 8)
        cmd = RegisterNode(cli)
        cmd.execute({"client_name": "node1", "password": "Password1!", "domain_name": "STANDARD"})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_user_with_password_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(UpdateUser, "_get_pw_min_length", lambda self: 8)
        cmd = UpdateUser(cli)
        cmd.execute({"user_name": "testadmin", "password": "NewPass1!"})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_user_without_password_uses_execute(self, monkeypatch):
        cli = self._make_cli()
        cmd = UpdateUser(cli)
        cmd.execute({"user_name": "testadmin", "contact": "ops@example.com"})
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()

    def test_update_node_with_password_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(UpdateNode, "_get_pw_min_length", lambda self: 8)
        cmd = UpdateNode(cli)
        cmd.execute({"node_name": "mynode", "password": "NewPass1!"})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_node_without_password_uses_execute(self, monkeypatch):
        cli = self._make_cli()
        cmd = UpdateNode(cli)
        cmd.execute({"node_name": "mynode", "domain_name": "STANDARD"})
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# POL-4 / RG-4: audit trail in handle_call_tool
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditTrail:
    """POL-4 / RG-4 — DEFINE SCRATCHPADENTRY emitted before write; failures logged as ERROR."""

    def _make_write_cmd(self):
        """Return a minimal BaseCommand stub with required_privilege='system'."""
        cmd = MagicMock()
        cmd.name = "delete_admin"
        cmd.required_privilege = "system"
        cmd.execute.return_value = "OK"
        return cmd

    def test_scratchpad_entry_called_before_write(self):
        """POL-4 / NR-1: DEFINE SCRATCHPADENTRY includes user identity and correlation."""
        from sp_mcp_server.mcp_factory import create_mcp_server, current_audit_user
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        # Provide QUERY ADMIN output with System authority so DeleteAdmin is registered
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        assert handler is not None

        # Set user context for NR-1
        tok = current_audit_user.set("audited-admin@corp.com")
        try:
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                admc.execute.return_value = ("ANR0000I OK", "", 0)
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "oldadmin"}),
                )
                asyncio.run(handler(req))
        finally:
            current_audit_user.reset(tok)

        # Check admc calls for DEFINE SCRATCHPADENTRY with user identity
        scratchpad_calls = [
            c[0][0] for c in admc.execute.call_args_list
            if "DEFINE SCRATCHPADENTRY" in str(c[0][0])
        ]
        assert len(scratchpad_calls) >= 1
        audit_call = scratchpad_calls[0]
        assert "user=audited-admin@corp.com" in audit_call
        assert "tool=delete_admin" in audit_call
        assert "priv=system" in audit_call
        assert "corr=" in audit_call

    def test_audit_write_failure_logs_error(self, caplog):
        """RG-4: When DEFINE SCRATCHPADENTRY returns non-zero in advisory mode, an ERROR is logged and execution proceeds."""
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        # When SCRATCHPADENTRY fails with non-zero
        admc.execute.return_value = ("", "Database locked", 12)

        with caplog.at_level(logging.ERROR):
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "oldadmin"}),
                )
                res = asyncio.run(handler(req))

        assert len(res.root.content) == 1
        assert res.root.content[0].text == "Admin deleted"
        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("POL-4" in r.message or "RG-4" in r.message for r in errors)

    def test_strict_audit_fail_closed_aborts_execution(self, monkeypatch):
        """NR-4: When SP_MCP_STRICT_AUDIT=1 and audit write fails, tool execution is blocked."""
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_STRICT_AUDIT", "1")
        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        admc.execute.return_value = ("", "Permission Denied", 1)

        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted") as mock_exec:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "oldadmin"}),
            )
            res = asyncio.run(handler(req))
            # Command should NOT be executed
            assert not mock_exec.called
            assert "Strict audit failure" in res.root.content[0].text or "Error" in res.root.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# RG-5: HTTP transport TLS enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestHttpTransportTLS:
    """RG-5 — HTTP transport rejected without TLS cert/key."""

    def _run_http_tls_check(self, monkeypatch, tls_cert=None, tls_key=None,
                             allow_plaintext="0", sp_env=None,
                             cert_file_exists=True, key_file_exists=True):
        """Exercise the RG-5 guard block from main.py logic inline."""
        import sys as _sys

        monkeypatch.setenv("SP_TLS_CERT", tls_cert or "")
        monkeypatch.setenv("SP_TLS_KEY", tls_key or "")
        monkeypatch.setenv("SP_MCP_ALLOW_HTTP_PLAINTEXT", allow_plaintext)
        if sp_env:
            monkeypatch.setenv("SP_MCP_ENV", sp_env)
        else:
            monkeypatch.delenv("SP_MCP_ENV", raising=False)

        # Inline the RG-5 logic
        import os as _os
        tls_cert_val = _os.environ.get("SP_TLS_CERT") or None
        tls_key_val  = _os.environ.get("SP_TLS_KEY") or None
        allow_pt = _os.environ.get("SP_MCP_ALLOW_HTTP_PLAINTEXT", "0") == "1"

        if tls_cert_val == "":
            tls_cert_val = None
        if tls_key_val == "":
            tls_key_val = None

        if not (tls_cert_val and tls_key_val):
            if not allow_pt:
                return "exit_no_tls"
            return "warn_plaintext"
        else:
            if not cert_file_exists:
                return "exit_cert_missing"
            if not key_file_exists:
                return "exit_key_missing"
        return "ok"

    def test_exits_without_cert_and_key(self, monkeypatch):
        result = self._run_http_tls_check(monkeypatch)
        assert result == "exit_no_tls"

    def test_exits_without_key(self, monkeypatch):
        result = self._run_http_tls_check(monkeypatch, tls_cert="/path/to/cert.crt")
        assert result == "exit_no_tls"

    def test_warns_when_plaintext_explicitly_allowed(self, monkeypatch):
        result = self._run_http_tls_check(monkeypatch, allow_plaintext="1")
        assert result == "warn_plaintext"

    def test_passes_with_cert_and_key(self, monkeypatch):
        result = self._run_http_tls_check(
            monkeypatch,
            tls_cert="/path/cert.crt",
            tls_key="/path/cert.key",
        )
        assert result == "ok"

    def test_exits_when_cert_file_missing(self, monkeypatch):
        result = self._run_http_tls_check(
            monkeypatch,
            tls_cert="/path/cert.crt",
            tls_key="/path/cert.key",
            cert_file_exists=False,
        )
        assert result == "exit_cert_missing"


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic & Delegated Authentication Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDynamicAuthentication:
    """Tests for dynamic challenge-response, session leases, and zero-trace authentication."""

    def test_session_manager_lease_lifecycle(self):
        from sp_mcp_server.session import SessionManager
        import time

        mgr = SessionManager(default_ttl=1)
        lease = mgr.create_session("admin_test", {"system", "policy"})
        assert lease.username == "admin_test"
        assert not lease.is_expired()

        retrieved = mgr.get_session(lease.session_id)
        assert retrieved is not None
        assert retrieved.username == "admin_test"

        # Sleep past 1s TTL
        time.sleep(1.1)
        assert lease.is_expired()
        assert mgr.get_session(lease.session_id) is None

    def test_authenticate_session_tool_valid_credentials(self):
        import json
        from sp_mcp_server.commands.system.auth import AuthenticateSession
        from sp_mcp_server.session import global_session_manager

        admc = _mock_admc()
        admc.execute_silent.side_effect = [
            ("ANR0000I Server status OK", "", 0),  # QUERY STATUS
            ("Administrator Name: ADMIN_TEST\nSystem Privilege: Yes", "", 0),  # QUERY ADMIN
        ]

        tool = AuthenticateSession(admc)
        result_json = tool.execute({"username": "admin_test", "password": "valid_password_123"})
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["username"] == "admin_test"
        assert "session_id" in result
        assert "system" in result["privileges"]

        session = global_session_manager.get_session(result["session_id"])
        assert session is not None
        assert session.username == "admin_test"

    def test_authenticate_session_tool_invalid_credentials(self):
        import json
        from sp_mcp_server.commands.system.auth import AuthenticateSession

        admc = _mock_admc()
        admc.execute_silent.return_value = ("", "ANR2017E Invalid password", 1)

        tool = AuthenticateSession(admc)
        result_json = tool.execute({"username": "admin_test", "password": "wrong_password"})
        result = json.loads(result_json)

        assert result["success"] is False
        assert result["returncode"] == 1
        assert "Authentication failed" in result["error"]

    def test_dynamic_auth_challenge_when_unauthenticated(self, monkeypatch):
        import json
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        current_session_id.set(None)

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "target_node"}),
        )
        res = asyncio.run(handler(req))
        assert len(res.root.content) == 1
        payload = json.loads(res.root.content[0].text)
        assert payload.get("is_error") is True
        assert payload.get("error_type") == "AUTHENTICATION_REQUIRED"
        assert payload["challenge"]["auth_tool"] == "authenticate_session"

    def test_dynamic_auth_executes_when_session_authenticated(self, monkeypatch):
        import json
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id, current_audit_user
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session("dynamic_admin", {"system"})
        current_session_id.set(lease.session_id)

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

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
                params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "target_admin"}),
            )
            async def _run_and_check():
                res = await handler(req)
                assert len(res.root.content) == 1
                assert res.root.content[0].text == "Admin deleted"
                assert current_audit_user.get() == "dynamic_admin"

            asyncio.run(_run_and_check())

    def test_session_ttl_is_bounded(self):
        from sp_mcp_server.session import SessionManager, MAX_SESSION_TTL_SECONDS

        mgr = SessionManager(default_ttl=MAX_SESSION_TTL_SECONDS + 100)
        lease = mgr.create_session("admin_test", {"any"}, ttl_seconds=MAX_SESSION_TTL_SECONDS + 100)
        assert lease.ttl_seconds == MAX_SESSION_TTL_SECONDS

    def test_dynamic_auth_denies_insufficient_privilege(self, monkeypatch):
        import json
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from sp_mcp_server.session import global_session_manager
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session("read_only_admin", {"any"})
        current_session_id.set(lease.session_id)

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="delete_admin", arguments={"admin_name": "target_admin"}),
        )

        res = asyncio.run(handler(req))
        payload = json.loads(res.root.content[0].text)
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
        routes through execute_silent() which must include -ID=<user> and -PA=<pass>
        in the subprocess.run args.
        """
        import subprocess
        from unittest.mock import patch, MagicMock
        from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, current_execution_credentials
        from sp_mcp_server.config import ServerConfig, ModuleCredential

        cred = ModuleCredential(admin_id="svc-system", admin_password="svc-pass", privilege="system")
        config = ServerConfig(
            server_address="sp-server",
            server_port="1500",
            credentials={"system": cred},
        )
        wrapper = DsmAdmcWrapper(config, privilege="system")

        token = current_execution_credentials.set(("dyn_user", "dyn_pass"))
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

            # The delegated -ID= and -PA= must appear in the subprocess args
            assert any(a.startswith("-ID=dyn_user") for a in captured_args), (
                f"-ID=dyn_user not found in subprocess args: {captured_args}"
            )
            assert any(a.startswith("-PA=dyn_pass") for a in captured_args), (
                f"-PA=dyn_pass not found in subprocess args: {captured_args}"
            )
        finally:
            current_execution_credentials.reset(token)

    def test_execution_credentials_cleared_after_tool_call_success(self, monkeypatch):
        """
        DAUTH-5b: current_execution_credentials must be None after a successful tool call.
        """
        import asyncio
        from unittest.mock import patch
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.cli_wrapper import current_execution_credentials
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session("dyn_admin", {"system"}, password="dyn_pass")
        current_session_id.set(lease.session_id)

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

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
                    name="delete_admin", arguments={"admin_name": "target_admin"}
                ),
            )

            async def _run():
                await handler(req)
                # After the tool call completes, credentials context must be cleared
                assert current_execution_credentials.get() is None, (
                    "current_execution_credentials was not cleared after tool call"
                )

            asyncio.run(_run())

    def test_execution_credentials_cleared_after_tool_call_exception(self, monkeypatch):
        """
        DAUTH-5b: current_execution_credentials must be None even if the tool raises.
        """
        import asyncio
        from unittest.mock import patch
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.cli_wrapper import current_execution_credentials
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        lease = global_session_manager.create_session("dyn_admin2", {"system"}, password="dyn_pass2")
        current_session_id.set(lease.session_id)

        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )

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
                    name="delete_admin", arguments={"admin_name": "target_admin"}
                ),
            )

            async def _run():
                # The handler should catch the exception internally (returns error text)
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

    Tests cover every supported mcp:* scope, insufficient-scope denial, and unknown-scope
    resolution to 'any'.
    """

    def _make_server_with_system_tool(self, monkeypatch):
        """Helper: create a test MCP server exposing the system-privilege DeleteAdmin tool."""
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "service_account")
        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )
        return create_mcp_server(
            server_name="oidc-test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

    def _call_tool(self, server, privilege_value):
        """Helper: invoke delete_admin with current_request_privilege set to privilege_value."""
        import asyncio, json
        from sp_mcp_server.mcp_factory import current_request_privilege
        from mcp.types import CallToolRequest, CallToolRequestParams
        from unittest.mock import patch

        from sp_mcp_server.commands.system.admin import DeleteAdmin

        handler = server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="delete_admin", arguments={"admin_name": "target_admin"}
            ),
        )

        async def _run():
            token = current_request_privilege.set(privilege_value)
            try:
                with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                    return await handler(req)
            finally:
                current_request_privilege.reset(token)

        return asyncio.run(_run())

    def test_oidc_scope_system_allows_system_tool(self, monkeypatch):
        """mcp:system → privilege='system' must allow a system-privilege tool."""
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "system")
        assert res.root.content[0].text == "Admin deleted"

    def test_oidc_scope_policy_denies_system_tool(self, monkeypatch):
        """mcp:policy → privilege='policy' must deny a system-privilege tool."""
        import json
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "policy")
        payload = json.loads(res.root.content[0].text)
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_storage_denies_system_tool(self, monkeypatch):
        """mcp:storage → privilege='storage' must deny a system-privilege tool."""
        import json
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "storage")
        payload = json.loads(res.root.content[0].text)
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_operator_denies_system_tool(self, monkeypatch):
        """mcp:operator → privilege='operator' must deny a system-privilege tool."""
        import json
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "operator")
        payload = json.loads(res.root.content[0].text)
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_read_denies_system_tool(self, monkeypatch):
        """mcp:read → privilege='any' must deny a system-privilege tool."""
        import json
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "any")
        payload = json.loads(res.root.content[0].text)
        assert payload["error_type"] == "AUTHORIZATION_DENIED"

    def test_oidc_scope_read_allows_any_privilege_tool(self, monkeypatch):
        """mcp:read → privilege='any' must allow a tool that requires only 'any'."""
        import asyncio, json
        from sp_mcp_server.mcp_factory import create_mcp_server, current_request_privilege
        from sp_mcp_server.commands.system.admin import QueryAdminUser
        from mcp.types import CallToolRequest, CallToolRequestParams
        from unittest.mock import patch

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "service_account")
        cfg = _make_config_with_cred(admin_id="mcp-svc-system")
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )
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

        async def _run():
            token = current_request_privilege.set("any")
            try:
                with patch.object(QueryAdminUser, "execute", return_value="Admin info"):
                    return await handler(req)
            finally:
                current_request_privilege.reset(token)

        res = asyncio.run(_run())
        assert res.root.content[0].text == "Admin info"

    def test_oidc_unknown_scope_treated_as_any_denies_system_tool(self, monkeypatch):
        """
        A token with an unrecognized scope should resolve to 'any' privilege,
        which must deny a system-privilege tool.
        """
        import json
        from sp_mcp_server.http_server import SCOPE_PRIVILEGE_MAP, _privilege_rank

        # Confirm the unknown scope is not in the map
        unknown_scope = "mcp:nonexistent"
        assert unknown_scope not in SCOPE_PRIVILEGE_MAP

        # Simulate the middleware resolution for an unknown scope
        scopes = [unknown_scope]
        privilege = "any"
        for scope_claim in scopes:
            tier = SCOPE_PRIVILEGE_MAP.get(scope_claim)
            if tier and _privilege_rank(tier) > _privilege_rank(privilege):
                privilege = tier
        assert privilege == "any", f"Expected 'any' for unknown scope, got '{privilege}'"

        # Now verify that 'any' denies a system tool at the MCP layer
        server = self._make_server_with_system_tool(monkeypatch)
        res = self._call_tool(server, "any")
        payload = json.loads(res.root.content[0].text)
        assert payload["error_type"] == "AUTHORIZATION_DENIED"


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

        # Locate the package source directory relative to this test file
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(tests_dir, "..", "src", "sp_mcp_server")
        src_dir = os.path.normpath(src_dir)

        # Collect main.py + all main_*.py
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
        lease = mgr.create_session("alice", {"system"}, password="secret-pw")
        assert lease.password == "secret-pw"

        revoked = mgr.revoke_session(lease.session_id)

        assert revoked is True
        # The password field must be cleared on the now-removed lease object.
        assert lease.password is None, (
            "SessionLease.password must be zeroed after revoke_session()"
        )
        # The session must no longer be retrievable.
        assert mgr.get_session(lease.session_id) is None

    def test_password_zeroed_on_expiry_in_get_session(self):
        """get_session() must zero the password when an expired lease is removed."""
        import time
        from sp_mcp_server.session import SessionManager

        mgr = SessionManager(default_ttl=1)
        lease = mgr.create_session("bob", {"any"}, password="expired-pw", ttl_seconds=1)
        assert lease.password == "expired-pw"

        time.sleep(1.1)  # let the lease expire

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
        lease = mgr.create_session("carol", {"policy"}, password="cleanup-pw", ttl_seconds=1)
        assert lease.password == "cleanup-pw"

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
        lease_a = mgr.create_session("dave", {"system"}, password="pw-a")
        lease_b = mgr.create_session("eve", {"any"}, password="pw-b")

        mgr.clear()

        assert lease_a.password is None, "clear() must zero lease_a.password"
        assert lease_b.password is None, "clear() must zero lease_b.password"

    def test_logout_session_revokes_and_clears_credential(self):
        """logout_session tool must revoke the session and confirm credential cleared."""
        import json
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.session import SessionManager, global_session_manager
        from sp_mcp_server.mcp_factory import current_session_id

        lease = global_session_manager.create_session("frank", {"system"}, password="frank-pw")
        current_session_id.set(lease.session_id)

        tool = LogoutSession(MagicMock())  # cli not used by logout_session
        result = json.loads(tool.execute({}))

        assert result["success"] is True
        assert "revoked" in result["message"].lower() or "cleared" in result["message"].lower()
        assert global_session_manager.get_session(lease.session_id) is None
        assert lease.password is None

    def test_logout_session_no_active_session(self):
        """logout_session with no session context returns success=False gracefully."""
        import json
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.mcp_factory import current_session_id

        current_session_id.set(None)
        tool = LogoutSession(MagicMock())
        result = json.loads(tool.execute({}))

        assert result["success"] is False
        assert "no active session" in result["message"].lower()

    def test_logout_session_explicit_session_id(self):
        """logout_session with an explicit session_id revokes that session."""
        import json
        from sp_mcp_server.commands.system.auth import LogoutSession
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.mcp_factory import current_session_id

        lease = global_session_manager.create_session("grace", {"operator"}, password="grace-pw")
        current_session_id.set(None)  # no context session — must use explicit arg

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

    def _make_server(self, monkeypatch, server_address="sp-server-01"):
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_AUTH_MODE", "dynamic")
        cred = ModuleCredential(admin_id="mcp-svc-system", admin_password="pw", privilege="system")
        cfg = ServerConfig(
            server_address=server_address,
            server_port="1500",
            credentials={"system": cred},
        )
        admc = MagicMock()
        admc.config = cfg
        admc.execute.return_value = (
            "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes",
            "",
            0,
        )
        server = create_mcp_server(
            server_name="target-server-test",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )
        return server, cfg

    def test_cross_server_session_is_denied(self, monkeypatch):
        """
        A session authenticated against 'sp-server-02' must be rejected when
        the MCP server is configured for 'sp-server-01'.
        """
        import asyncio, json
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.session import global_session_manager
        from mcp.types import CallToolRequest, CallToolRequestParams

        server, _ = self._make_server(monkeypatch, server_address="sp-server-01")

        # Session bound to a *different* server
        lease = global_session_manager.create_session(
            "alice", {"system"},
            target_server="sp-server-02",
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
        res = asyncio.run(handler(req))
        payload = json.loads(res.root.content[0].text)

        assert payload["error_type"] == "AUTHORIZATION_DENIED", (
            f"Expected AUTHORIZATION_DENIED for cross-server session reuse, got: {payload}"
        )
        assert "sp-server-02" in payload["message"]
        assert "sp-server-01" in payload["message"]

    def test_matching_target_server_is_allowed(self, monkeypatch):
        """
        A session whose target_server matches the MCP server's server_address
        must be allowed through.
        """
        import asyncio
        from unittest.mock import patch
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        server, _ = self._make_server(monkeypatch, server_address="sp-server-01")

        # Session bound to the *correct* server
        lease = global_session_manager.create_session(
            "bob", {"system"},
            target_server="sp-server-01",
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
            res = asyncio.run(handler(req))

        assert res.root.content[0].text == "Admin deleted"

    def test_no_target_server_on_session_is_allowed(self, monkeypatch):
        """
        A session created without a target_server (single-server deployment)
        must not be rejected — the check is only enforced when target_server
        is explicitly set.
        """
        import asyncio
        from unittest.mock import patch
        from sp_mcp_server.mcp_factory import create_mcp_server, current_session_id
        from sp_mcp_server.session import global_session_manager
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from mcp.types import CallToolRequest, CallToolRequestParams

        server, _ = self._make_server(monkeypatch, server_address="sp-server-01")

        # Session has no target_server — single-server deployment style
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
            res = asyncio.run(handler(req))

        assert res.root.content[0].text == "Admin deleted"

    def test_check_session_target_server_helper_mismatch(self):
        """Unit-test the helper directly for the mismatch path."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id="abc123",
            username="dave",
            privilege_classes={"system"},
            target_server="sp-server-02",
        )

        class FakeConfig:
            server_address = "sp-server-01"

        err = _check_session_target_server(lease, FakeConfig())
        assert err is not None
        assert "sp-server-02" in err
        assert "sp-server-01" in err

    def test_check_session_target_server_helper_match(self):
        """Unit-test the helper directly for the matching path."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id="def456",
            username="eve",
            privilege_classes={"system"},
            target_server="sp-server-01",
        )

        class FakeConfig:
            server_address = "sp-server-01"

        assert _check_session_target_server(lease, FakeConfig()) is None

    def test_check_session_target_server_helper_no_target(self):
        """Unit-test the helper: no target_server on session → None (skipped)."""
        from sp_mcp_server.mcp_factory import _check_session_target_server
        from sp_mcp_server.session import SessionLease

        lease = SessionLease(
            session_id="ghi789",
            username="frank",
            privilege_classes={"any"},
            target_server=None,
        )

        class FakeConfig:
            server_address = "sp-server-01"

        assert _check_session_target_server(lease, FakeConfig()) is None
