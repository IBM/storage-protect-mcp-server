"""
Security-control regression tests — password-bearing command silent execution.

Controls covered:
  RG-3  REGISTER ADMIN / REGISTER NODE / UPDATE * with password use
        execute_silent, not execute
"""

import pytest
from unittest.mock import MagicMock

from sp_mcp_server.commands.system.admin import DefineAdmin, UpdateUser
from sp_mcp_server.commands.clients.node import RegisterNode, UpdateNode

from tests.fixtures import (
    ADMIN_NAME_TEST,
    ADMIN_CONTACT,
    DOMAIN_NAME,
    NODE_NAME,
    NODE_NAME_MY,
    TEST_PASSWORD_MINLENGTH,
    TEST_PASSWORD_VALUE,
    TEST_PASSWORD_NEW,
)


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
        monkeypatch.setattr(
            DefineAdmin, "_get_pw_min_length", lambda self: TEST_PASSWORD_MINLENGTH
        )
        cmd = DefineAdmin(cli)
        cmd.execute({"admin_name": ADMIN_NAME_TEST, "password": TEST_PASSWORD_VALUE})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_register_node_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(
            RegisterNode, "_get_pw_min_length", lambda self: TEST_PASSWORD_MINLENGTH
        )
        cmd = RegisterNode(cli)
        cmd.execute({
            "client_name": NODE_NAME,
            "password": TEST_PASSWORD_VALUE,
            "domain_name": DOMAIN_NAME,
        })
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_user_with_password_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(
            UpdateUser, "_get_pw_min_length", lambda self: TEST_PASSWORD_MINLENGTH
        )
        cmd = UpdateUser(cli)
        cmd.execute({"user_name": ADMIN_NAME_TEST, "password": TEST_PASSWORD_NEW})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_user_without_password_uses_execute(self, monkeypatch):
        cli = self._make_cli()
        cmd = UpdateUser(cli)
        cmd.execute({"user_name": ADMIN_NAME_TEST, "contact": ADMIN_CONTACT})
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()

    def test_update_node_with_password_uses_execute_silent(self, monkeypatch):
        cli = self._make_cli()
        monkeypatch.setattr(
            UpdateNode, "_get_pw_min_length", lambda self: TEST_PASSWORD_MINLENGTH
        )
        cmd = UpdateNode(cli)
        cmd.execute({"node_name": NODE_NAME_MY, "password": TEST_PASSWORD_NEW})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_node_without_password_uses_execute(self, monkeypatch):
        cli = self._make_cli()
        cmd = UpdateNode(cli)
        cmd.execute({"node_name": NODE_NAME_MY, "domain_name": DOMAIN_NAME})
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()
