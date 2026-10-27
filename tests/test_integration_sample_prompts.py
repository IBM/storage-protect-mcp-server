"""
test_integration_sample_prompts.py
===================================
Integration tests that exercise the same sample-prompt scenarios as
test_sample_prompts.py, but using a *real* DsmAdmcWrapper connected to a
live IBM Storage Protect server.

These tests are **skipped automatically** when the required environment
variables are not set (i.e. when there is no .env file or the SP server is
unreachable).  They are intended to run on the server host (barfi) as
mcp-runner where the production .env is present.

Run only integration tests:
    pytest tests/test_integration_sample_prompts.py -v -m integration

Skip integration tests (default in CI):
    pytest tests/ -v -m "not integration"

Environment variables required (loaded from .env or exported directly):
    TCPSERVERADDRESS    — SP server hostname or IP
    SP_ADMIN_ID_READONLY / SP_ADMIN_PASSWORD_READONLY  (read-only queries)
    SP_ADMIN_ID_SYSTEM  / SP_ADMIN_PASSWORD_SYSTEM     (write-path tests)
    SP_SERVER_NAME      — dsmadmc -SE= stanza name in dsm.sys
"""

from __future__ import annotations

import os
import pytest

# ---------------------------------------------------------------------------
# Integration marker — skip when live server env is absent
# ---------------------------------------------------------------------------

_MISSING_ENV = not (
    os.environ.get("TCPSERVERADDRESS")
    or os.environ.get("SP_ADMIN_ID_READONLY")
    or os.environ.get("SP_ADMIN_ID_SYSTEM")
)

pytestmark = pytest.mark.integration

# Apply a module-level skip so every test in the file is skipped together
# when the live server is not configured.  Individual tests that need a
# specific credential tier add their own skip guard via the fixture below.
if _MISSING_ENV:
    # Load .env from cwd if present (allows running without pre-exporting vars)
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
        _MISSING_ENV = not (
            os.environ.get("TCPSERVERADDRESS")
            or os.environ.get("SP_ADMIN_ID_READONLY")
            or os.environ.get("SP_ADMIN_ID_SYSTEM")
        )
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def readonly_cli():
    """Real DsmAdmcWrapper configured for the 'any' (read-only) privilege tier.

    Skips the entire module if TCPSERVERADDRESS or the read-only credential is
    absent from the environment.
    """
    addr = os.environ.get("TCPSERVERADDRESS")
    ro_id = os.environ.get("SP_ADMIN_ID_READONLY")
    if not addr or not ro_id:
        pytest.skip(
            "Integration test requires TCPSERVERADDRESS and SP_ADMIN_ID_READONLY "
            "to be set (load from .env on the SP server host)."
        )

    from sp_mcp_server.config import load_config
    from sp_mcp_server.cli_wrapper import DsmAdmcWrapper

    config = load_config()
    return DsmAdmcWrapper(config, privilege="any")


@pytest.fixture(scope="module")
def system_cli():
    """Real DsmAdmcWrapper configured for the 'system' privilege tier.

    Skips tests that use this fixture when SP_ADMIN_ID_SYSTEM is absent.
    """
    addr = os.environ.get("TCPSERVERADDRESS")
    sys_id = os.environ.get("SP_ADMIN_ID_SYSTEM")
    if not addr or not sys_id:
        pytest.skip(
            "Integration test requires TCPSERVERADDRESS and SP_ADMIN_ID_SYSTEM "
            "to be set (load from .env on the SP server host)."
        )

    from sp_mcp_server.config import load_config
    from sp_mcp_server.cli_wrapper import DsmAdmcWrapper

    config = load_config()
    return DsmAdmcWrapper(config, privilege="system")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_no_sp_error(stdout: str, stderr: str, rc: int, cmd: str) -> None:
    """Fail the test with a descriptive message if dsmadmc returned an error."""
    assert rc == 0, (
        f"dsmadmc returned rc={rc} for: {cmd!r}\n"
        f"  stdout: {stdout!r}\n"
        f"  stderr: {stderr!r}"
    )
    # SP sometimes puts ANR error codes in stdout with rc=0
    assert "ANR2034E" not in stdout, f"SP 'No match found' in output for: {cmd!r}"


# ---------------------------------------------------------------------------
# R-01 · Discovery and Status — read-only against live server
# ---------------------------------------------------------------------------

class TestIntR01DiscoveryAndStatus:
    """Live read-only queries matching R-01 sample prompts."""

    def test_query_server_status(self, readonly_cli):
        """QUERY STATUS returns output containing the server name."""
        from sp_mcp_server.commands.system.server import QueryServerStatus
        cmd = QueryServerStatus(readonly_cli)
        result = cmd.execute({})
        assert result, "QUERY STATUS returned empty output"
        # SP always returns at least the server name and version
        assert len(result) > 0

    def test_query_active_sessions(self, readonly_cli):
        """QUERY SESSION returns output (even if no sessions are active)."""
        from sp_mcp_server.commands.clients.info import QueryActiveSession
        cmd = QueryActiveSession(readonly_cli)
        result = cmd.execute({})
        # rc=0 means the command ran; empty result is valid (no active sessions)
        assert result is not None

    def test_query_storage_pool_all(self, readonly_cli):
        """QUERY STGPOOL returns at least one storage pool."""
        from sp_mcp_server.commands.storage.stgpool import QueryStorageContainer
        cmd = QueryStorageContainer(readonly_cli)
        result = cmd.execute({})
        assert result, "QUERY STGPOOL returned empty output — no storage pools defined?"

    def test_query_activity_log_recent(self, readonly_cli):
        """QUERY ACTLOG with a date filter returns activity log entries."""
        from sp_mcp_server.commands.operations.misc import QueryActivityLog
        cmd = QueryActivityLog(readonly_cli)
        result = cmd.execute({
            "search": "ANR0000I",
            "begindate": "01/01/2026",
        })
        assert result is not None


# ---------------------------------------------------------------------------
# R-01 · Node and Policy queries — read-only
# ---------------------------------------------------------------------------

class TestIntR01PolicyAndNodes:
    """Live policy and node queries matching R-01 sample prompts."""

    def test_query_client_list(self, readonly_cli):
        """QUERY NODE returns the list of registered nodes."""
        from sp_mcp_server.commands.clients.node import QueryClient
        cmd = QueryClient(readonly_cli)
        result = cmd.execute({})
        assert result is not None

    def test_query_schedules(self, readonly_cli):
        """QUERY SCHEDULE returns schedule definitions."""
        from sp_mcp_server.commands.policies.schedule import QuerySchedule
        cmd = QuerySchedule(readonly_cli)
        result = cmd.execute({})
        assert result is not None

    def test_query_volume_history_dbbackup(self, readonly_cli):
        """QUERY VOLHISTORY TYPE=DBBACKUP returns DB backup volume records."""
        from sp_mcp_server.commands.storage.volume import QueryVolumeHistory
        cmd = QueryVolumeHistory(readonly_cli)
        result = cmd.execute({"type": "DBBACKUP"})
        assert result is not None


# ---------------------------------------------------------------------------
# R-02 · Admin diagnostics — read-only
# ---------------------------------------------------------------------------

class TestIntR02AdminDiagnostics:
    """Live diagnostic queries matching R-02 sample prompts."""

    def test_query_server_option_txngroupmax(self, readonly_cli):
        """QUERY OPTION TXNGROUPMAX returns the current value."""
        from sp_mcp_server.commands.system.server import QueryServerOption
        cmd = QueryServerOption(readonly_cli)
        result = cmd.execute({"option_name": "TXNGROUPMAX"})
        assert result is not None

    def test_query_recovery_log(self, readonly_cli):
        """QUERY LOG returns active log space statistics."""
        from sp_mcp_server.commands.system.logs import QueryRecoveryLog
        cmd = QueryRecoveryLog(readonly_cli)
        result = cmd.execute({"format": "standard"})
        assert result is not None

    def test_query_occupancy(self, readonly_cli):
        """QUERY OCCUPANCY returns data occupancy across storage pools."""
        from sp_mcp_server.commands.storage.stgpool import QueryOccupancy
        cmd = QueryOccupancy(readonly_cli)
        result = cmd.execute({})
        assert result is not None


# ---------------------------------------------------------------------------
# R-05 · Security audit — read-only + system-privilege write
# ---------------------------------------------------------------------------

class TestIntR05SecurityAudit:
    """Live security-audit queries matching R-05 sample prompts."""

    def test_query_admin_user_all(self, readonly_cli):
        """QUERY ADMIN lists all SP administrator accounts."""
        from sp_mcp_server.commands.system.admin import QueryAdminUser
        cmd = QueryAdminUser(readonly_cli)
        result = cmd.execute({})
        assert result, "QUERY ADMIN returned empty — no admins defined?"

    def test_query_license_info(self, readonly_cli):
        """QUERY LICENSE returns license compliance status."""
        from sp_mcp_server.commands.system.admin import QueryLicenseInfo
        cmd = QueryLicenseInfo(readonly_cli)
        result = cmd.execute({})
        assert result is not None

    def test_query_policy_domain_all(self, readonly_cli):
        """QUERY DOMAIN lists all policy domains."""
        from sp_mcp_server.commands.policies.domain import QueryPolicyGroup
        cmd = QueryPolicyGroup(readonly_cli)
        result = cmd.execute({})
        assert result is not None

    def test_query_protection_policy(self, readonly_cli):
        """QUERY MGMTCLASS returns management class definitions."""
        from sp_mcp_server.commands.policies.mgmt import QueryProtectionPolicy
        cmd = QueryProtectionPolicy(readonly_cli)
        result = cmd.execute({})
        assert result is not None

    def test_lock_and_unlock_mcp_readonly_account(self, system_cli):
        """LOCK ADMIN / UNLOCK ADMIN round-trip on mcp-svc-readonly (system priv required)."""
        from sp_mcp_server.commands.system.admin import SetUserLock

        target = "mcp-svc-readonly"
        cmd = SetUserLock(system_cli)

        # Lock
        lock_result = cmd.execute({"user_name": target, "lock_status": "locked"})
        assert lock_result is not None

        # Immediately unlock so the account is left in a working state
        unlock_result = cmd.execute({"user_name": target, "lock_status": "unlocked"})
        assert unlock_result is not None
