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
from sp_mcp_server.commands.storage.datamover import DefineDataMover, UpdateDataMover
from sp_mcp_server.commands.system.server import DefineServer, UpdateServer
from sp_mcp_server.cli_wrapper import _redact_command

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

    @pytest.mark.parametrize("payload", [
        {
            "name": "DM1", "hl_address": "10.0.0.1", "data_format": "NETAPPDUMP",
            "user_id": "nasuser", "password": TEST_PASSWORD_VALUE,
        },
        {
            "name": "DM1", "type": "nas", "hl_address": "10.0.0.5",
            "data_format": "netappdump", "user_id": "dmuser", "password": TEST_PASSWORD_VALUE,
        },
    ])
    def test_define_data_mover_uses_execute_silent(self, payload):
        cli = self._make_cli()
        DefineDataMover(cli).execute(payload)
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_data_mover_with_password_uses_execute_silent(self):
        cli = self._make_cli()
        UpdateDataMover(cli).execute({"name": "DM1", "password": TEST_PASSWORD_NEW})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    @pytest.mark.parametrize("payload", [
        {"name": "DM1", "online": "YES"},
        {"name": "DM1", "hl_address": "10.0.0.6"},
    ])
    def test_update_data_mover_without_password_uses_execute(self, payload):
        cli = self._make_cli()
        UpdateDataMover(cli).execute(payload)
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()

    @pytest.mark.parametrize("payload", [
        {
            "server_name": "SRV2", "password": TEST_PASSWORD_VALUE,
            "hl_address": "10.0.0.2", "ll_address": "1500",
        },
        {
            "server_name": "REMOTE_SP", "password": TEST_PASSWORD_VALUE,
            "hl_address": "10.0.0.1", "ll_address": "1500",
        },
    ])
    def test_define_server_uses_execute_silent(self, payload):
        cli = self._make_cli()
        DefineServer(cli).execute(payload)
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    def test_update_server_with_password_uses_execute_silent(self):
        cli = self._make_cli()
        UpdateServer(cli).execute({"server_name": "SRV2", "password": TEST_PASSWORD_NEW})
        cli.execute_silent.assert_called_once()
        cli.execute.assert_not_called()

    @pytest.mark.parametrize("payload", [
        {"server_name": "SRV2", "description": "d"},
        {"server_name": "REMOTE_SP", "hl_address": "10.0.0.2"},
    ])
    def test_update_server_without_password_uses_execute(self, payload):
        cli = self._make_cli()
        UpdateServer(cli).execute(payload)
        cli.execute.assert_called_once()
        cli.execute_silent.assert_not_called()

    def test_redact_command_masks_passwords(self):
        cmd1 = 'DEFINE SERVER S1 PASSWORD=SecretPass123 HLADDRESS=1.2.3.4 LLADDRESS=1500'
        cmd2 = 'DEFINE DATAMOVER D1 USERID=u1 PASSWORD="QuotedSecret!"'
        cmd3 = 'REGISTER NODE NODE1 PwD12345! DOMAIN=STANDARD'
        cmd4 = 'REGISTER ADMIN ADM1 AdminSecret9!'
        cmd5 = 'QUERY NODE *'

        assert _redact_command(cmd1) == 'DEFINE SERVER S1 PASSWORD=*** HLADDRESS=1.2.3.4 LLADDRESS=1500'
        assert _redact_command(cmd2) == 'DEFINE DATAMOVER D1 USERID=u1 PASSWORD="***"'
        assert _redact_command(cmd3) == 'REGISTER NODE NODE1 *** DOMAIN=STANDARD'
        assert _redact_command(cmd4) == 'REGISTER ADMIN ADM1 ***'
        assert _redact_command(cmd5) == 'QUERY NODE *'
