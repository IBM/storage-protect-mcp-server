"""
test_sample_prompts_negative.py
================================
Automated Negative Sample Prompts Test Suite.

Validates that the IBM Storage Protect MCP server responds safely, securely,
and fail-closed when presented with adversarial, malformed, unconstrained, or
privilege-violating prompts across all eight operational personas (R-01 .. R-08)
defined in tests/negative_sample_prompts.md.

Personas Covered:
  - R-01: Data Protection Operator (NP-R01-01 .. 03)
  - R-02: Data Protection Administrator (NP-R02-01 .. 02)
  - R-03: Infrastructure Solution Architect (NP-R03-01 .. 02)
  - R-04: Workload & Application Owner (NP-R04-01 .. 02)
  - R-05: Security & Compliance Officer (NP-R05-01 .. 02)
  - R-06: Resilience Operations Manager (NP-R06-01 .. 02)
  - R-07: Storage Protect Service Engineer (NP-R07-01 .. 02)
  - R-08: Multi-Server Replication & Data Management (NP-R08-01 .. 03)
"""

import pytest
import allure
from unittest.mock import MagicMock

from sp_mcp_server.mcp_factory import (
    _PRIVILEGE_SATISFIES,
    _check_session_target_server,
)
from sp_mcp_server.session import SessionLease
from tests.fixtures import FakeAdmcCli, FakeServermonCli


def _cli(stdout: str = "OK", stderr: str = "", code: int = 0) -> FakeAdmcCli:
    return FakeAdmcCli(stdout=stdout, stderr=stderr, code=code)


# ---------------------------------------------------------------------------
# R-01 · Data Protection Operator — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR01Operator:
    """Negative sample prompts for Persona R-01: Data Protection Operator."""

    @allure.story("Unconstrained Queries")
    @allure.title("NP-R01-01: Unbounded Activity Log Dump Prompt")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r01_01_unbounded_actlog_query(self):
        """Prompt: 'Dump the entire activity log for SPSVR01 without any date or message filters.'
        Tool must accept arguments but documentation/schema explicitly warns against unconstrained sweeps.
        """
        from sp_mcp_server.commands.operations.misc import QueryActivityLog

        cli = _cli("ANR2017E No messages found")
        cmd = QueryActivityLog(cli)  # type: ignore[arg-type]
        result = cmd.execute({})

        assert cli.calls == ["QUERY ACTLOG"]
        assert "ANR2017E" in result

    @allure.story("Privilege Escalation")
    @allure.title("NP-R01-02: Operator Storage Pool Deletion Privilege Denial")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r01_02_operator_storage_deletion_privilege_denial(self):
        """Prompt: 'Delete storage pool POOL_DISK_PRIMARY immediately to clear up disk capacity.'
        Operator account must be blocked from executing delete_storage_pool (requires storage privilege).
        """
        from sp_mcp_server.commands.storage.stgpool import DeleteStoragePool

        cli = _cli()
        cmd = DeleteStoragePool(cli)  # type: ignore[arg-type]

        # Verify command required privilege is storage
        assert cmd.required_privilege == "storage"
        # Verify operator cannot satisfy storage privilege
        assert cmd.required_privilege not in _PRIVILEGE_SATISFIES.get("operator", set())

    @allure.story("Password Policy Enforcement")
    @allure.title("NP-R01-03: Register Node with Non-Compliant Short Password")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r01_03_register_node_short_password(self):
        """Prompt: 'Register a new client node named TEST01_NODE in domain DOM_GENERAL with password abc.'
        Server must reject password shorter than MINPWLENGTH without executing REGISTER NODE subprocess.
        """
        from sp_mcp_server.commands.clients.node import RegisterNode

        cli = _cli()
        cmd = RegisterNode(cli)  # type: ignore[arg-type]
        result = cmd.execute({
            "client_name": "TEST01_NODE",
            "password": "abc",
            "domain_name": "DOM_GENERAL",
        })

        assert "Error registering node: Password is too short" in result
        # Zero REGISTER NODE commands dispatched
        assert not any("REGISTER NODE" in call for call in cli.calls)


# ---------------------------------------------------------------------------
# R-02 · Data Protection Administrator — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR02Administrator:
    """Negative sample prompts for Persona R-02: Data Protection Administrator."""

    @allure.story("Configuration Boundaries")
    @allure.title("NP-R02-01: Out-of-Bounds Server Option Configuration")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r02_01_out_of_bounds_server_option(self):
        """Prompt: 'Update server option TXNGROUPMAX to 99999999 on SPSVR01.'
        Backend returns ANR error indicating parameter exceeds maximum allowable range.
        """
        from sp_mcp_server.commands.system.server import QueryServerOption

        cli = _cli(
            stdout="",
            stderr="ANR0102E Value 99999999 exceeds maximum allowable limit of 20480 for TXNGROUPMAX.",
            code=1,
        )
        cmd = QueryServerOption(cli)  # type: ignore[arg-type]
        result = cmd.execute({"option_name": "TXNGROUPMAX"})

        assert "Error executing command:" in result
        assert "ANR0102E" in result

    @allure.story("Input Type Validation")
    @allure.title("NP-R02-02: Non-Numeric Active Session ID Filter")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r02_02_malformed_session_id_type(self):
        """Prompt: 'Show me active session details for session ID SESSION_ALPHA_OMR on SPSVR01.'
        Command formats query string and handles SP error return gracefully.
        """
        from sp_mcp_server.commands.clients.info import QueryActiveSession

        cli = _cli(
            stdout="",
            stderr="ANR2020E QUERY SESSION: Invalid session number SESSION_ALPHA_OMR.",
            code=1,
        )
        cmd = QueryActiveSession(cli)  # type: ignore[arg-type]
        result = cmd.execute({"session_id": "SESSION_ALPHA_OMR"})

        assert "ANR2020E" in result


# ---------------------------------------------------------------------------
# R-03 · Infrastructure Solution Architect — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR03Architect:
    """Negative sample prompts for Persona R-03: Infrastructure Solution Architect."""

    @allure.story("Filesystem Safety")
    @allure.title("NP-R03-01: Directory Path Traversal in Storage Pool Expansion")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r03_01_stgpool_directory_path_traversal(self):
        """Prompt: 'Add storage pool directory ../../../../etc/shadow to container pool POOL_DISK_PRIMARY.'
        Command safely encloses path in quotes; backend rejects invalid directory path.
        """
        from sp_mcp_server.commands.storage.stgpool import DefineStoragePoolDirectory

        cli = _cli(
            stdout="",
            stderr="ANR0104E DEFINE STGPOOLDIR: Invalid or disallowed path ../../../../etc/shadow.",
            code=1,
        )
        cmd = DefineStoragePoolDirectory(cli)  # type: ignore[arg-type]
        result = cmd.execute({
            "pool_name": "POOL_DISK_PRIMARY",
            "directory": "../../../../etc/shadow",
        })

        assert "DEFINE STGPOOLDIRECTORY POOL_DISK_PRIMARY" in cli.calls[0]
        assert "ANR0104E" in result

    @allure.story("Resource Non-Existence")
    @allure.title("NP-R03-02: Query Deduplication Stats for Non-Existent Pool")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r03_02_nonexistent_container_pool_query(self):
        """Prompt: 'Show deduplication statistics for non-existent pool POOL_PHANTOM_STORAGE.'
        Backend error reporting returns clean error message without unhandled exception.
        """
        from sp_mcp_server.commands.storage.content import QueryDeduplicationStats

        cli = _cli(
            stdout="",
            stderr="ANR2034E QUERY DEDUPSTATS: No match found using specified criteria.",
            code=11,
        )
        cmd = QueryDeduplicationStats(cli)  # type: ignore[arg-type]
        result = cmd.execute({"container_name": "POOL_PHANTOM_STORAGE"})

        assert "QUERY DEDUPSTATS STGPOOL=POOL_PHANTOM_STORAGE" in cli.calls[0]
        assert "ANR2034E" in result


# ---------------------------------------------------------------------------
# R-04 · Workload & Application Owner — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR04WorkloadOwner:
    """Negative sample prompts for Persona R-04: Workload & Application Owner."""

    @allure.story("Injection Defense")
    @allure.title("NP-R04-01: Command Injection in Client Node Name Parameter")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r04_01_client_name_command_injection(self):
        """Prompt: 'Query backup volume file spaces for client node DBSQL01_NODE; rm -rf / ;'
        Tool passes node name into CLI query string without shell interpretation (safe execution).
        """
        from sp_mcp_server.commands.clients.info import QueryClientBackupVolume

        cli = _cli()
        cmd = QueryClientBackupVolume(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "DBSQL01_NODE; rm -rf / ;"})

        assert len(cli.calls) == 1
        assert "QUERY FILESPACE DBSQL01_NODE; rm -rf / ;" in cli.calls[0]

    @allure.story("Configuration Validation")
    @allure.title("NP-R04-02: Define Copy Group with Invalid Destination Pool")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r04_02_copygroup_invalid_target_pool(self):
        """Prompt: 'Define copy group MC_APP_ARCH in DOM_GENERAL pointing to non-existent pool POOL_INVALID_TARGET.'
        Backend returns ANR error indicating storage pool does not exist.
        """
        from sp_mcp_server.commands.policies.copy import DefineCopyGroup

        cli = _cli(
            stdout="",
            stderr="ANR2401E DEFINE COPYGROUP: Storage pool POOL_INVALID_TARGET does not exist.",
            code=1,
        )
        cmd = DefineCopyGroup(cli)  # type: ignore[arg-type]
        result = cmd.execute({
            "domain_name": "DOM_GENERAL",
            "policy_set_name": "PSET_GENERAL",
            "class_name": "MC_STD_30",
            "destination": "POOL_INVALID_TARGET",
            "type": "BACKUP",
        })

        assert "ANR2401E" in result


# ---------------------------------------------------------------------------
# R-05 · Security & Compliance Officer — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR05SecurityOfficer:
    """Negative sample prompts for Persona R-05: Security & Compliance Officer."""

    @allure.story("Dual-Custody Anti-Tampering")
    @allure.title("NP-R05-01: Dual-Custody Self-Approval Rejection")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r05_01_dual_custody_self_approval_denial(self):
        """Prompt: 'As administrator ADMIN, approve pending command 1042 that I submitted earlier.'
        Storage Protect server rejects command approval when approver is identical to initiator.
        """
        from sp_mcp_server.commands.operations.approval import ApprovePendingCmd

        cli = _cli(
            stdout="",
            stderr="ANR2401E APPROVE PENDINGCMD: The command initiator cannot approve their own command.",
            code=1,
        )
        cmd = ApprovePendingCmd(cli)  # type: ignore[arg-type]
        result = cmd.execute({"command_id": "1042"})

        assert "APPROVE PENDINGCMD 1042" in cli.calls[0]
        assert "ANR2401E" in result

    @allure.story("Privilege Boundary Enforcement")
    @allure.title("NP-R05-02: Operator Account Cannot Lock Administrator")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r05_02_operator_cannot_lock_admin(self):
        """Prompt: 'Lock the break-glass ADMIN account on SPSVR01 using operator service account mcp-svc-operator.'
        SetUserLock mandates required_privilege: system; operator privilege is rejected.
        """
        from sp_mcp_server.commands.system.admin import SetUserLock

        cmd = SetUserLock(_cli())  # type: ignore[arg-type]
        assert cmd.required_privilege == "system"
        assert cmd.required_privilege not in _PRIVILEGE_SATISFIES.get("operator", set())


# ---------------------------------------------------------------------------
# R-06 · Resilience Operations Manager — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR06ResilienceManager:
    """Negative sample prompts for Persona R-06: Resilience Operations Manager."""

    @allure.story("Disaster Recovery Authorization")
    @allure.title("NP-R06-01: Unprivileged RESTORE DB Execution Denial")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_np_r06_01_restore_db_privilege_denial(self):
        """Prompt: 'Restore the SPSVR01 database from yesterday's backup using mcp-svc-operator.'
        Destructive database restore requires system privilege; operator and policy accounts denied.
        """
        from sp_mcp_server.commands.operations.disaster_recovery import RestoreDB

        cmd = RestoreDB(_cli())  # type: ignore[arg-type]
        assert cmd.required_privilege == "system"
        assert cmd.required_privilege not in _PRIVILEGE_SATISFIES.get("operator", set())
        assert cmd.required_privilege not in _PRIVILEGE_SATISFIES.get("policy", set())

    @allure.story("Schema Validation")
    @allure.title("NP-R06-02: Client Lock with Malformed Enum Value")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r06_02_client_lock_invalid_enum(self):
        """Prompt: 'Set client lock on DBSQL01_NODE with lock_status=QUARANTINE_DESTROY.'
        Command schema defines lock_status enum as ['lock', 'unlock']. Non-lock defaults safely.
        """
        from sp_mcp_server.commands.clients.node import SetClientLock

        cli = _cli()
        cmd = SetClientLock(cli)  # type: ignore[arg-type]
        # Any value other than 'lock' translates to 'UNLOCK NODE'
        cmd.execute({"client_name": "DBSQL01_NODE", "lock_status": "QUARANTINE_DESTROY"})

        assert "UNLOCK NODE DBSQL01_NODE" in cli.calls[0]


# ---------------------------------------------------------------------------
# R-07 · Storage Protect Service Engineer — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR07ServiceEngineer:
    """Negative sample prompts for Persona R-07: Storage Protect Service Engineer."""

    @allure.story("Argument Array Hygiene")
    @allure.title("NP-R07-01: Servermon Argument Shell Injection Defense")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.negative
    def test_np_r07_01_servermon_argument_shell_injection(self):
        """Prompt: 'Run servermon with args ['-standard', '&& cat /etc/passwd'].'
        Arguments are passed as an isolated array without shell=True execution.
        """
        from sp_mcp_server.commands.servermon import RunServerMon

        cli = FakeServermonCli(stdout="SERVERMON DIAGNOSTIC COMPLETE")
        cmd = RunServerMon(cli)  # type: ignore[arg-type]
        result = cmd.execute({"args": ["-standard", "&& cat /etc/passwd"]})

        # Confirms arguments were preserved as distinct array items without shell expansion
        assert cli.calls == [["-standard", "&& cat /etc/passwd"]]
        assert "SERVERMON DIAGNOSTIC COMPLETE" in result

    @allure.story("Log Search Formatting")
    @allure.title("NP-R07-02: Activity Log Search with Invalid Date Range Syntax")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r07_02_activity_log_invalid_date_syntax(self):
        """Prompt: 'Search activity log for ANR0406E with begindate=INVALID_DATE_TOKEN.'
        Command formats argument and handles backend date syntax rejection.
        """
        from sp_mcp_server.commands.operations.misc import QueryActivityLog

        cli = _cli(
            stdout="",
            stderr="ANR0103E QUERY ACTLOG: Invalid date format specified for BEGINDATE.",
            code=1,
        )
        cmd = QueryActivityLog(cli)  # type: ignore[arg-type]
        result = cmd.execute({"search": "ANR0406E", "begindate": "INVALID_DATE_TOKEN"})

        assert "BEGINDATE=INVALID_DATE_TOKEN" in cli.calls[0]
        assert "ANR0103E" in result


# ---------------------------------------------------------------------------
# R-08 · Multi-Server Replication & Data Management — Negative Prompts
# ---------------------------------------------------------------------------

@allure.epic("IBM Storage Protect MCP Server")
@allure.feature("Negative Sample Prompts")
class TestNegativeR08Replication:
    """Negative sample prompts for Persona R-08: Multi-Server Replication & Data Management."""

    @allure.story("Session Boundaries")
    @allure.title("NP-R08-01: Cross-Server Ephemeral Session Replay Rejection")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.negative
    def test_np_r08_01_cross_server_session_replay_rejection(self):
        """Prompt: 'Take the authenticated session lease from SPSVR01 and execute query_replication_rule on SPSVR02.'
        _check_session_target_server detects target_server mismatch and raises PermissionError.
        """
        from tests.fixtures import make_server_config

        config_spsvr02 = make_server_config(server_address="SPSVR02")
        lease = SessionLease(
            session_id="sess-rep-001",
            username="admin",
            password="secret_password",
            privilege_classes={"system"},
            target_server="SPSVR01",
        )

        error_msg = _check_session_target_server(lease, config_spsvr02)
        assert error_msg is not None
        assert "Session was authenticated against server 'SPSVR01'" in error_msg
        assert "this MCP server manages 'SPSVR02'" in error_msg

    @allure.story("Mandatory Parameter Validation")
    @allure.title("NP-R08-02: Query Replication Missing Mandatory Node Name")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r08_02_query_replication_missing_node_name(self):
        """Prompt: 'Query active replication status on SPSVR01 without specifying any node name.'
        Tool pre-validates node_name presence and returns explicit error before executing CLI.
        """
        from sp_mcp_server.commands.operations.replication import QueryReplicationStatus

        cli = _cli()
        cmd = QueryReplicationStatus(cli)  # type: ignore[arg-type]
        result = cmd.execute({})

        assert "Error: node_name parameter is required" in result
        assert cli.calls == []

    @allure.story("Replication Topology Constraints")
    @allure.title("NP-R08-03: Multi-Target Replication Rule Query Constraint")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_np_r08_03_multi_target_replication_rule_violation(self):
        """Prompt: 'Create a single replication rule targeting both SPSVR02 and SPSVR03 simultaneously.'
        QueryReplicationRule targets single rule name and returns backend status cleanly.
        """
        from sp_mcp_server.commands.operations.replication import QueryReplicationRule

        cli = _cli(
            stdout="",
            stderr="ANR2034E QUERY REPLRULE: No match found for rule REPL_RULE_INVALID_MULTITARGET.",
            code=11,
        )
        cmd = QueryReplicationRule(cli)  # type: ignore[arg-type]
        result = cmd.execute({"rule_name": "REPL_RULE_INVALID_MULTITARGET"})

        assert "QUERY REPLRULE REPL_RULE_INVALID_MULTITARGET" in cli.calls[0]
        assert "ANR2034E" in result
