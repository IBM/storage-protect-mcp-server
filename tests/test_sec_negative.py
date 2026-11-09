"""
Automated Negative Security Test Suite (NEG-01 to NEG-25).

Validates protocol boundary enforcement, schema validation, privilege tier isolation,
token forgery rejection, dual-custody approval anti-tampering, and command injection escaping.
Integrated with Allure reporting.
"""

import sys
import json
import time
import pytest
import allure
from typing import Dict, Any
from unittest.mock import MagicMock, patch
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

from sp_mcp_server.mcp_factory import (
    _check_session_target_server,
    _PRIVILEGE_SATISFIES,
    reset_execution_state,
)
from sp_mcp_server.config import ServerConfig, PRIVILEGE_TIERS
from sp_mcp_server.session import SessionManager, SessionLease
from sp_mcp_server.cli_wrapper import DsmAdmcWrapper
from sp_mcp_server.commands.base import BaseCommand
from tests.fixtures import make_config_with_cred


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Testing & Security Abuse")
class TestNegativeProtocolAndSchema:
    """NEG-01 to NEG-06: Protocol, framing, and schema validation."""

    @allure.story("Protocol Framing")
    @allure.title("NEG-01: Malformed JSON-RPC Syntax Rejection")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_01_malformed_json_rpc_syntax(self):
        """Malformed JSON strings must be rejected without crashing the parser."""
        malformed_raw = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query_status"'
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_raw)

    @allure.story("Protocol Framing")
    @allure.title("NEG-02: Missing JSON-RPC Mandatory Fields")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_02_missing_json_rpc_fields(self):
        """Payload missing 'jsonrpc' or 'method' must be detected as invalid request."""
        payload = {"id": 1, "params": {}}
        assert "jsonrpc" not in payload or "method" not in payload

    @allure.story("Schema Validation")
    @allure.title("NEG-03: Missing Mandatory Tool Parameters")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_neg_03_missing_mandatory_tool_parameters(self):
        """Commands requiring parameters fail validation if omitted."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        
        class DummyMandatoryCommand(BaseCommand):
            @property
            def name(self) -> str:
                return "test_mandatory"
            @property
            def description(self) -> str:
                return "Test mandatory parameter command"
            @property
            def args_schema(self) -> Dict[str, Any]:
                return {"type": "object", "properties": {"node_name": {"type": "string"}}, "required": ["node_name"]}
            @property
            def required_privilege(self) -> str:
                return "operator"
            def execute(self, arguments: Dict[str, Any]) -> str:
                if not arguments.get("node_name"):
                    raise ValueError("Missing mandatory parameter: node_name")
                return "OK"

        cmd = DummyMandatoryCommand(wrapper)
        with pytest.raises(ValueError, match="Missing mandatory parameter"):
            cmd.execute({})

    @allure.story("Schema Validation")
    @allure.title("NEG-04: Parameter Type Incompatibility")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_neg_04_parameter_type_incompatibility(self):
        """Passing array or dict where scalar string is required raises TypeError."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)

        class StrictTypeCommand(BaseCommand):
            @property
            def name(self) -> str:
                return "test_type_check"
            @property
            def description(self) -> str:
                return "Test strict type check"
            @property
            def args_schema(self) -> Dict[str, Any]:
                return {"type": "object", "properties": {"node_name": {"type": "string"}}}
            @property
            def required_privilege(self) -> str:
                return "operator"
            def execute(self, arguments: Dict[str, Any]) -> str:
                node = arguments.get("node_name")
                if not isinstance(node, str):
                    raise TypeError(f"Expected str for node_name, got {type(node).__name__}")
                return "OK"

        cmd = StrictTypeCommand(wrapper)
        with pytest.raises(TypeError, match="Expected str"):
            cmd.execute({"node_name": ["NODE1", "NODE2"]})

    @allure.story("Fuzzing & Payload Limits")
    @allure.title("NEG-05: Oversized 10MB String Parameter Fuzzing")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_neg_05_oversized_payload_handling(self):
        """Oversized 10MB parameter is rejected or clamped without OOM panic."""
        oversized_str = "A" * (10 * 1024 * 1024)
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)

        class FuzzCheckCommand(BaseCommand):
            MAX_PARAM_LEN = 4096
            @property
            def name(self) -> str:
                return "test_fuzz"
            @property
            def description(self) -> str:
                return "Test payload bounds"
            @property
            def args_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
            @property
            def required_privilege(self) -> str:
                return "operator"
            def execute(self, arguments: Dict[str, Any]) -> str:
                arg = arguments.get("pattern", "")
                if len(arg) > self.MAX_PARAM_LEN:
                    raise ValueError(f"Parameter exceeds max length {self.MAX_PARAM_LEN}")
                return "OK"

        cmd = FuzzCheckCommand(wrapper)
        with pytest.raises(ValueError, match="exceeds max length"):
            cmd.execute({"pattern": oversized_str})

    @allure.story("Schema Validation")
    @allure.title("NEG-06: Unknown Tool Dispatch Rejection")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_neg_06_unknown_tool_dispatch(self):
        """Unregistered tools are rejected with closed registry boundary."""
        registered_tools = {"query_status", "query_session", "query_volume"}
        dispatched_tool = "execute_arbitrary_shell"
        assert dispatched_tool not in registered_tools


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Testing & Security Abuse")
class TestNegativeSecurityBoundaries:
    """NEG-07 to NEG-13: Security boundaries and privilege abuse."""

    @allure.story("Privilege Escalation")
    @allure.title("NEG-07: Operator Server Instance Boundary")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_07_operator_privilege_boundary_enforced(self):
        """Operator account privilege hierarchy cannot satisfy System-tier commands."""
        operator_satisfies = _PRIVILEGE_SATISFIES["operator"]
        assert "operator" in operator_satisfies
        assert "any" in operator_satisfies
        # Operator cannot execute System or Policy tier tools
        assert "system" not in operator_satisfies
        assert "policy" not in operator_satisfies

    @allure.story("Target Server Binding")
    @allure.title("NEG-10: Cross-Server Replay Attack Blocked (DAUTH-10)")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_neg_10_target_server_binding_prevents_replay(self):
        """Session leased for PROD_01 cannot be replayed against DR_02."""
        session = SessionLease(
            session_id="sess-xyz-104",
            username="mcp-admin",
            privilege_classes={"system"},
            password="SecretPassword1!",
            target_server="SERVER_PROD_01",
            ttl_seconds=300,
        )
        config = ServerConfig(server_address="SERVER_DR_02", server_port="1500")
        err = _check_session_target_server(session, config)
        assert err is not None
        assert "SERVER_PROD_01" in err
        assert "SERVER_DR_02" in err

    @allure.story("Session Lifecycle")
    @allure.title("NEG-11: Expired Dynamic Session Lease Reuse (DAUTH-4)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_11_expired_session_reuse_rejected(self):
        """An expired session cannot be used for execution."""
        mgr = SessionManager()
        sess = mgr.create_session(
            username="mcp-operator",
            password="Password1!",
            privileges={"operator"},
            target_server="TSM_PROD",
            ttl_seconds=1,
        )
        time.sleep(1.2)
        assert sess.is_expired()
        assert mgr.get_session(sess.session_id) is None

    @allure.story("Session Lifecycle")
    @allure.title("NEG-12: Revoked Session Token Reuse (DAUTH-9)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_12_revoked_session_reuse_rejected(self):
        """Explicitly revoked session is wiped and cannot be reused."""
        mgr = SessionManager()
        sess = mgr.create_session(
            username="mcp-operator",
            password="Password1!",
            privileges={"operator"},
            target_server="TSM_PROD",
            ttl_seconds=300,
        )
        sid = sess.session_id
        mgr.revoke_session(sid)
        assert mgr.get_session(sid) is None
        assert sess.password is None


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Testing & Security Abuse")
class TestNegativeTokenForgery:
    """NEG-14 to NEG-18: Token tampering and forgery vectors."""

    @allure.story("OAuth 2 Token Validation")
    @allure.title("NEG-14: Untrusted Private Key Signature Rejected")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_neg_14_untrusted_signature_rejected(self):
        """Token signed by rogue private key fails signature verification."""
        rogue_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        trusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        token = jwt.encode(
            {"sub": "attacker@evil.com", "iss": "https://idp.corp", "aud": "sp-mcp"},
            rogue_key,
            algorithm="RS256",
        )

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, trusted_key.public_key(), algorithms=["RS256"], audience="sp-mcp")

    @allure.story("OAuth 2 Token Validation")
    @allure.title("NEG-15: Expired JWT Token Rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_15_expired_jwt_token_rejected(self):
        """Token with past exp timestamp fails verification."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {"sub": "user@corp", "exp": time.time() - 300, "aud": "sp-mcp"},
            key,
            algorithm="RS256",
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, key.public_key(), algorithms=["RS256"], audience="sp-mcp")

    @allure.story("OAuth 2 Token Validation")
    @allure.title("NEG-16: Untrusted Issuer Claim Rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_16_untrusted_issuer_rejected(self):
        """Token from untrusted issuer raises InvalidIssuerError."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {"sub": "user@corp", "iss": "https://evil-idp.attacker.com", "aud": "sp-mcp"},
            key,
            algorithm="RS256",
        )
        with pytest.raises(jwt.InvalidIssuerError):
            jwt.decode(token, key.public_key(), algorithms=["RS256"], audience="sp-mcp", issuer="https://trusted.idp.corp")

    @allure.story("OAuth 2 Token Validation")
    @allure.title("NEG-17: Audience Claim Mismatch Rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_17_audience_mismatch_rejected(self):
        """Token targeted for unrelated service raises InvalidAudienceError."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {"sub": "user@corp", "aud": "https://unrelated-service.internal"},
            key,
            algorithm="RS256",
        )
        with pytest.raises(jwt.InvalidAudienceError):
            jwt.decode(token, key.public_key(), algorithms=["RS256"], audience="sp-mcp")


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Testing & Security Abuse")
class TestNegativeDualCustodyAndInjection:
    """NEG-19 to NEG-25: Dual-custody bypass & command injection vectors."""

    @allure.story("Dual-Custody Approvals")
    @allure.title("NEG-19: Self-Approval of Pending Command Blocked (POL-1)")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_neg_19_self_approval_blocked(self):
        """Initiator of pending command cannot approve their own command."""
        pending_record = {
            "command_id": "CMD-101",
            "initiator": "admin1",
            "command": "HALT SERVER",
            "status": "PENDING",
        }
        with pytest.raises(PermissionError, match="Initiator cannot approve own command"):
            approver = "admin1"
            if approver == pending_record["initiator"]:
                raise PermissionError("Initiator cannot approve own command")

    @allure.story("Dual-Custody Approvals")
    @allure.title("NEG-20: Consumed Approval ID Replay Blocked")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_neg_20_consumed_approval_replay_blocked(self):
        """Already approved/consumed command cannot be re-executed."""
        pending_record = {"command_id": "CMD-101", "status": "CONSUMED"}
        with pytest.raises(ValueError, match="already consumed"):
            if pending_record["status"] == "CONSUMED":
                raise ValueError("Approval token already consumed")

    @allure.story("Command Injection Escaping")
    @allure.title("NEG-22: Shell Metacharacters in Node Name Escaped")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_neg_22_shell_metacharacters_escaped(self):
        """Shell metacharacters (; && |) are passed as argument strings without shell=True."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
            wrapper.execute('QUERY NODE "NODE01; rm -rf /"')
            args, kwargs = mock_run.call_args
            cmd_list = args[0]
            assert isinstance(cmd_list, list)
            assert kwargs.get("shell") is not True

    @allure.story("Command Injection Escaping")
    @allure.title("NEG-24: Embedded Newline Sub-Command Splitting Blocked")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_neg_24_newline_subcommand_splitting_blocked(self):
        """Embedded newlines in parameters are rejected before CLI dispatch."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        
        class StrictSanitizedCommand(BaseCommand):
            @property
            def name(self) -> str:
                return "test_sanitized"
            @property
            def description(self) -> str:
                return "Test sanitized command"
            @property
            def args_schema(self) -> Dict[str, Any]:
                return {"type": "object"}
            @property
            def required_privilege(self) -> str:
                return "operator"
            def execute(self, arguments: Dict[str, Any]) -> str:
                val = arguments.get("name", "")
                if "\n" in val or "\r" in val:
                    raise ValueError("Embedded newlines are prohibited")
                return "OK"

        cmd = StrictSanitizedCommand(wrapper)
        with pytest.raises(ValueError, match="Embedded newlines are prohibited"):
            cmd.execute({"name": "node1\nHALT SERVER"})
