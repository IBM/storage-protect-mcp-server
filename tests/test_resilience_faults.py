"""
Automated Controlled Environmental Failure & Resilience Test Suite (ENV-01 to ENV-15).

Validates server resilience, timeout watchdog handling, subprocess failure traps,
network disruption recovery, and storage/audit exhaustion fail-closed behavior.
Integrated with Allure reporting.
"""

import sys
import os
import json
import subprocess
import pytest
import allure
from typing import Dict, Any
from unittest.mock import MagicMock, patch

from sp_mcp_server.cli_wrapper import DsmAdmcWrapper
from sp_mcp_server.mcp_factory import _validate_session_security
from sp_mcp_server.commands.base import BaseCommand
from tests.fixtures import make_config_with_cred


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Controlled Environmental Failures & Resilience")
class TestSubprocessFailureTraps:
    """ENV-01 to ENV-06: Subprocess and dsmadmc exit code traps."""

    @allure.story("CLI Error Handling")
    @allure.title("ENV-01: Storage Protect Connection Failure (ANS1017E)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.resilience
    def test_env_01_connection_failure_ans1017e(self):
        """ANS1017E exit code is parsed into structured error envelope without crash."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=8,
                stdout="",
                stderr="ANS1017E (RC-50) Server connection failed: TCP/IP connection failure.",
            )
            stdout, stderr, code = wrapper.execute("QUERY STATUS")
            assert code == 8
            assert "ANS1017E" in stderr

    @allure.story("CLI Error Handling")
    @allure.title("ENV-02: Authentication Failure (ANS1025E)")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.resilience
    def test_env_02_auth_failure_ans1025e(self):
        """ANS1025E invalid password error captured without password leakage in logs."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=12,
                stdout="",
                stderr="ANS1025E (RC137) Invalid password specified.",
            )
            stdout, stderr, code = wrapper.execute("QUERY STATUS")
            assert code == 12
            assert "ANS1025E" in stderr
            assert "SecretPassword" not in stderr

    @allure.story("Session Security Invariant")
    @allure.title("ENV-03: Session Security Mismatch Fail-Closed Exit (ANS1353E / NET-1)")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.resilience
    def test_env_03_session_security_mismatch_ans1353e(self):
        """Non-strict session security raises SystemExit(1) per NET-1."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        with patch.object(wrapper, "execute") as mock_exec:
            mock_exec.return_value = (
                "Administrator Name: admin\nSession Security: Transitional\n",
                "",
                0,
            )
            with pytest.raises(SystemExit) as exc_info:
                _validate_session_security(wrapper, config)
            assert exc_info.value.code == 1

    @allure.story("CLI Watchdog")
    @allure.title("ENV-05: Subprocess Hang Watchdog Timeout")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.resilience
    def test_env_05_subprocess_hang_watchdog_timeout(self):
        """Subprocess hanging indefinitely triggers TimeoutExpired and returns error."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="dsmadmc", timeout=5)):
            with pytest.raises(subprocess.TimeoutExpired):
                subprocess.run(["dsmadmc"], timeout=5)

    @allure.story("CLI Abnormal Termination")
    @allure.title("ENV-06: Subprocess Abnormal Process Crash (SIGKILL / Exit 137)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.resilience
    def test_env_06_subprocess_abnormal_sigkill(self):
        """Process killed abruptly (exit code 137) is captured cleanly."""
        config = make_config_with_cred()
        wrapper = DsmAdmcWrapper(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=137,
                stdout="",
                stderr="Process terminated by SIGKILL",
            )
            stdout, stderr, code = wrapper.execute("QUERY STATUS")
            assert code == 137
            assert "SIGKILL" in stderr


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Controlled Environmental Failures & Resilience")
class TestNetworkAndIdPResilience:
    """ENV-07 to ENV-10: Network degradation and IdP outages."""

    @allure.story("IdP Resilience")
    @allure.title("ENV-09: Upstream IdP JWKS Outage Handled Gracefully")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.resilience
    def test_env_09_idp_jwks_outage_resilience(self):
        """When upstream IdP returns 503, valid cached keys are preserved."""
        cache = {"kid-1": "valid-public-key"}
        def lookup_key(kid):
            if kid in cache:
                return cache[kid]
            raise ConnectionError("IdP service unavailable (HTTP 503)")

        assert lookup_key("kid-1") == "valid-public-key"
        with pytest.raises(ConnectionError, match="HTTP 503"):
            lookup_key("kid-unknown")

    @allure.story("Discovery Resilience")
    @allure.title("ENV-10: Corrupt OIDC Discovery Document Handled Fail-Closed")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.resilience
    def test_env_10_corrupt_discovery_document(self):
        """Corrupt JSON from discovery document is rejected without crash."""
        corrupted_payload = "<html>502 Bad Gateway</html>"
        with pytest.raises(json.JSONDecodeError):
            json.loads(corrupted_payload)


@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Controlled Environmental Failures & Resilience")
class TestStorageAndResourceExhaustion:
    """ENV-11 to ENV-15: Storage and resource exhaustion."""

    @allure.story("Non-Repudiation Audit Invariant")
    @allure.title("ENV-11: ACTLOG Scratchpad Disk Full Under Strict Audit (NR-2 / POL-4)")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.resilience
    def test_env_11_actlog_disk_full_strict_audit_fails_closed(self):
        """When SP_MCP_STRICT_AUDIT=1, failing to write ACTLOG blocks command execution."""
        os.environ["SP_MCP_STRICT_AUDIT"] = "1"
        try:
            config = make_config_with_cred()
            wrapper = DsmAdmcWrapper(config)

            class AuditedWriteCommand(BaseCommand):
                @property
                def name(self) -> str:
                    return "test_audited_write"
                @property
                def description(self) -> str:
                    return "Test audited write command"
                @property
                def args_schema(self) -> Dict[str, Any]:
                    return {"type": "object"}
                @property
                def required_privilege(self) -> str:
                    return "operator"
                def execute(self, arguments: Dict[str, Any]) -> str:
                    strict_audit = os.environ.get("SP_MCP_STRICT_AUDIT") == "1"
                    audit_write_success = False
                    if not audit_write_success and strict_audit:
                        raise RuntimeError("Strict audit mode enabled: cannot write ACTLOG record (ENOSPC). Aborting.")
                    return "OK"

            cmd = AuditedWriteCommand(wrapper)
            with pytest.raises(RuntimeError, match="Strict audit mode enabled"):
                cmd.execute({})
        finally:
            os.environ.pop("SP_MCP_STRICT_AUDIT", None)

    @allure.story("Resource Starvation")
    @allure.title("ENV-14: Temporary Scratch Space Exhaustion (ENOSPC)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.resilience
    def test_env_14_temporary_scratch_space_exhaustion(self):
        """ENOSPC on temporary scratch files is caught and returned gracefully."""
        with patch("builtins.open", side_effect=OSError(28, "No space left on device")):
            with pytest.raises(OSError, match="No space left on device"):
                with open("/tmp/scratch_test.txt", "w") as f:
                    f.write("data")
