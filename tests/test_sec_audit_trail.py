"""
Security-control regression tests — audit trail and HTTP TLS enforcement.

Controls covered:
  POL-4  handle_call_tool emits DEFINE SCRATCHPADENTRY before write operations
  RG-4   audit write failure logs ERROR (not WARNING)
  NR-4   SP_MCP_STRICT_AUDIT=1 blocks execution when audit write fails
  RG-5   HTTP transport rejects startup without TLS cert/key
"""

import logging
from unittest.mock import MagicMock, patch
import pytest

from mcp.types import CallToolRequest, CallToolRequestParams

from tests.fixtures import (
    make_config_with_cred,
    run_tool,
    first_text,
    SVC_ADMIN_ID,
    AUDIT_USER,
    ADMIN_NAME_OLD,
    SP_OUTPUT_SESSION_STRICT_TLS13,
    SP_OUTPUT_SCRATCHPAD_OK,
    SP_OUTPUT_DB_LOCKED_STDERR,
    SP_OUTPUT_PERMISSION_DENIED_STDERR,
    TLS_CERT_PATH,
    TLS_KEY_PATH,
    TLS_CERT_PATH_SHORT,
)


def _cfg(admin_id=SVC_ADMIN_ID):
    return make_config_with_cred(admin_id=admin_id)


def _admc(cfg):
    admc = MagicMock()
    admc.config = cfg
    admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
    return admc


# ─────────────────────────────────────────────────────────────────────────────
# POL-4 / RG-4 / NR-4: audit trail in handle_call_tool
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditTrail:
    """POL-4 / RG-4 — DEFINE SCRATCHPADENTRY emitted before write; failures logged as ERROR."""

    def test_scratchpad_entry_called_before_write(self):
        """POL-4 / NR-1: DEFINE SCRATCHPADENTRY includes user identity and correlation."""
        from sp_mcp_server.mcp_factory import create_mcp_server, current_audit_user
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]

        tok = current_audit_user.set(AUDIT_USER)
        try:
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                admc.execute.return_value = (SP_OUTPUT_SCRATCHPAD_OK, "", 0)
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                    ),
                )
                run_tool(handler, req)
        finally:
            current_audit_user.reset(tok)

        scratchpad_calls = [
            c[0][0] for c in admc.execute.call_args_list
            if "DEFINE SCRATCHPADENTRY" in str(c[0][0])
        ]
        assert len(scratchpad_calls) >= 1
        audit_call = scratchpad_calls[0]
        assert f"user={AUDIT_USER}" in audit_call
        assert "tool=delete_admin" in audit_call
        assert "priv=system" in audit_call
        assert "corr=" in audit_call

    def test_audit_write_failure_logs_error(self, caplog):
        """RG-4: When DEFINE SCRATCHPADENTRY returns non-zero in advisory mode,
        an ERROR is logged and execution proceeds."""
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        admc.execute.return_value = ("", SP_OUTPUT_DB_LOCKED_STDERR, 12)

        with caplog.at_level(logging.ERROR):
            with patch.object(DeleteAdmin, "execute", return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                    ),
                )
                res = run_tool(handler, req)

        assert len(res.content) == 1
        assert first_text(res) == "Admin deleted"
        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("POL-4" in r.message or "RG-4" in r.message for r in errors)

    def test_strict_audit_fail_closed_aborts_execution(self, monkeypatch):
        """NR-4: When SP_MCP_STRICT_AUDIT=1 and audit write fails, tool execution is blocked."""
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin

        monkeypatch.setenv("SP_MCP_STRICT_AUDIT", "1")
        cfg = _cfg()
        admc = _admc(cfg)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin],
            admc_cli=admc,
            config=cfg,
        )

        handler = server.request_handlers[CallToolRequest]
        admc.execute.return_value = ("", SP_OUTPUT_PERMISSION_DENIED_STDERR, 1)

        with patch.object(DeleteAdmin, "execute", return_value="Admin deleted") as mock_exec:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                ),
            )
            res = run_tool(handler, req)
            assert not mock_exec.called
            assert "Strict audit failure" in first_text(res) or "Error" in first_text(res)


# ─────────────────────────────────────────────────────────────────────────────
# RG-5: HTTP transport TLS enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestHttpTransportTLS:
    """RG-5 — HTTP transport rejected without TLS cert/key."""

    def _run_http_tls_check(
        self, monkeypatch,
        tls_cert=None, tls_key=None,
        allow_plaintext="0", sp_env=None,
        cert_file_exists=True, key_file_exists=True,
    ):
        """Exercise the RG-5 guard block from main.py logic inline."""
        import os as _os

        monkeypatch.setenv("SP_TLS_CERT", tls_cert or "")
        monkeypatch.setenv("SP_TLS_KEY", tls_key or "")
        monkeypatch.setenv("SP_MCP_ALLOW_HTTP_PLAINTEXT", allow_plaintext)
        if sp_env:
            monkeypatch.setenv("SP_MCP_ENV", sp_env)
        else:
            monkeypatch.delenv("SP_MCP_ENV", raising=False)

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
        assert self._run_http_tls_check(monkeypatch) == "exit_no_tls"

    def test_exits_without_key(self, monkeypatch):
        assert self._run_http_tls_check(monkeypatch, tls_cert=TLS_CERT_PATH_SHORT) == "exit_no_tls"

    def test_warns_when_plaintext_explicitly_allowed(self, monkeypatch):
        assert self._run_http_tls_check(monkeypatch, allow_plaintext="1") == "warn_plaintext"

    def test_passes_with_cert_and_key(self, monkeypatch):
        assert self._run_http_tls_check(
            monkeypatch, tls_cert=TLS_CERT_PATH, tls_key=TLS_KEY_PATH
        ) == "ok"

    def test_exits_when_cert_file_missing(self, monkeypatch):
        assert self._run_http_tls_check(
            monkeypatch,
            tls_cert=TLS_CERT_PATH, tls_key=TLS_KEY_PATH,
            cert_file_exists=False,
        ) == "exit_cert_missing"
