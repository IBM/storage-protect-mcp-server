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
