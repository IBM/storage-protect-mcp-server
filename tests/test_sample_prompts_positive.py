"""
test_sample_prompts_positive.py
================================
Positive sample prompt test suite (unit tests and live integration tests)
validating tools referenced across all eight operational personas (R-01 .. R-08)
in docs/example/sample-prompts.md.

Part 1: Unit tests with FakeAdmcCli (Personas R-01 through R-08 + Tool Annotations).
Part 2: Live integration tests with real DsmAdmcWrapper against SP server (skipped in CI).
"""

from __future__ import annotations
import pytest

from tests.fixtures import FakeAdmcCli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cli(stdout: str = "OK") -> FakeAdmcCli:
    return FakeAdmcCli(stdout=stdout)


# ---------------------------------------------------------------------------
# R-01 · Data Protection Operator
# ---------------------------------------------------------------------------

class TestR01DiscoveryAndStatus:
    """Prompt: 'Show me all active client sessions on SPSVR01 right now'
               'What is the current utilisation of all storage pools on SPSVR01?'
    """

    def test_query_active_sessions(self):
        """query_active_session with no filter returns QUERY SESSION."""
        from sp_mcp_server.commands.clients.info import QueryActiveSession

        cli = _cli()
        cmd = QueryActiveSession(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY SESSION"]

    def test_query_active_session_by_id(self):
        """query_active_session with a specific session_id filters the query."""
        from sp_mcp_server.commands.clients.info import QueryActiveSession

        cli = _cli()
        cmd = QueryActiveSession(cli)  # type: ignore[arg-type]
        cmd.execute({"session_id": "42"})

        assert cli.calls == ["QUERY SESSION 42"]

    def test_query_storage_pool_all(self):
        """query_storage_container with no filter lists all pools."""
        from sp_mcp_server.commands.storage.stgpool import QueryStorageContainer

        cli = _cli()
        cmd = QueryStorageContainer(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert len(cli.calls) == 1
        assert "QUERY STGPOOL" in cli.calls[0]

    def test_query_storage_pool_named(self):
        """query_storage_container filtered to POOL_DISK_PRIMARY."""
        from sp_mcp_server.commands.storage.stgpool import QueryStorageContainer

        cli = _cli()
        cmd = QueryStorageContainer(cli)  # type: ignore[arg-type]
        cmd.execute({"container_name": "POOL_DISK_PRIMARY"})

        assert "POOL_DISK_PRIMARY" in cli.calls[0]

    def test_query_server_status(self):
        """query_server_status emits QUERY STATUS."""
        from sp_mcp_server.commands.system.server import QueryServerStatus

        cli = _cli("SERVER1,,1500")
        cmd = QueryServerStatus(cli)  # type: ignore[arg-type]
        result = cmd.execute({})

        assert cli.calls == ["QUERY STATUS"]
        assert result == "SERVER1,,1500"


class TestR01BackupPolicyAndScheduling:
    """Prompts:
    - 'Create a management class named MC_WEB_60 in DOM_GENERAL …'
    - 'Define a daily incremental backup schedule SCHED_WEB_DAILY …'
    - 'What backup schedules are currently defined for DOM_DATABASE?'
    - 'Node DBSQL01_NODE missed its last three runs of SCHED_DB_NIGHTLY …'
    """

    def test_define_management_class(self):
        """define_management_class emits DEFINE MGMTCLASS with domain and policy set."""
        from sp_mcp_server.commands.policies.mgmt import DefineManagementClass

        cli = _cli()
        cmd = DefineManagementClass(cli)  # type: ignore[arg-type]
        cmd.execute({
            "domain_name": "DOM_GENERAL",
            "policy_set_name": "PSET_GENERAL",
            "class_name": "MC_WEB_60",
            "description": "Web tier 60-day retention",
        })

        assert "DEFINE MGMTCLASS" in cli.calls[0]
        assert "DOM_GENERAL" in cli.calls[0]
        assert "PSET_GENERAL" in cli.calls[0]
        assert "MC_WEB_60" in cli.calls[0]

    def test_define_copy_group_for_mc_web_60(self):
        """define_copy_group emits DEFINE COPYGROUP with correct retention params."""
        from sp_mcp_server.commands.policies.copy import DefineCopyGroup

        cli = _cli()
        cmd = DefineCopyGroup(cli)  # type: ignore[arg-type]
        cmd.execute({
            "domain_name": "DOM_GENERAL",
            "policy_set_name": "PSET_GENERAL",
            "class_name": "MC_WEB_60",
            "type": "BACKUP",
            "destination": "POOL_DISK_PRIMARY",
            "verexists": "5",
            "retextra": "60",
        })

        assert "DEFINE COPYGROUP" in cli.calls[0]
        assert "DOM_GENERAL" in cli.calls[0]
        assert "MC_WEB_60" in cli.calls[0]
        assert "POOL_DISK_PRIMARY" in cli.calls[0]

    def test_define_schedule_daily_incremental(self):
        """define_schedule emits DEFINE SCHEDULE with start time and period."""
        from sp_mcp_server.commands.policies.schedule import DefineSchedule

        cli = _cli()
        cmd = DefineSchedule(cli)  # type: ignore[arg-type]
        cmd.execute({
            "domain_name": "DOM_GENERAL",
            "schedule_name": "SCHED_WEB_DAILY",
            "action": "INCREMENTAL",
            "start_time": "22:30",
            "duration": "1",
            "period": "1",
        })

        assert "DEFINE SCHEDULE" in cli.calls[0]
        assert "DOM_GENERAL" in cli.calls[0]
        assert "SCHED_WEB_DAILY" in cli.calls[0]

    def test_query_schedules_for_domain(self):
        """query_schedule filtered by DOM_DATABASE returns only that domain's schedules."""
        from sp_mcp_server.commands.policies.schedule import QuerySchedule

        cli = _cli()
        cmd = QuerySchedule(cli)  # type: ignore[arg-type]
        cmd.execute({"domain_name": "DOM_DATABASE"})

        assert "QUERY SCHEDULE" in cli.calls[0]
        assert "DOM_DATABASE" in cli.calls[0]

    def test_query_scheduled_events_for_missed_runs(self):
        """query_scheduled_event for SCHED_DB_NIGHTLY returns event history."""
        from sp_mcp_server.commands.policies.schedule import QueryScheduledEvent

        cli = _cli()
        cmd = QueryScheduledEvent(cli)  # type: ignore[arg-type]
        cmd.execute({
            "policy_group": "DOM_DATABASE",
            "schedule_name": "SCHED_DB_NIGHTLY",
        })

        assert "QUERY EVENT" in cli.calls[0]
        assert "SCHED_DB_NIGHTLY" in cli.calls[0]

    def test_query_activity_log_for_node(self):
        """query_activity_log with node search and date window for triage."""
        from sp_mcp_server.commands.operations.misc import QueryActivityLog

        cli = _cli()
        cmd = QueryActivityLog(cli)  # type: ignore[arg-type]
        cmd.execute({
            "search": "DBSQL01_NODE",
            "begindate": "07/01/2026",
            "enddate": "07/04/2026",
        })

        assert "QUERY ACTLOG" in cli.calls[0]
        assert "DBSQL01_NODE" in cli.calls[0]


class TestR01NodeLifecycle:
    """Prompts:
    - 'Register a new client node APPSVR02_NODE in DOM_GENERAL …'
    - 'Lock node LEGACY01_NODE immediately …'
    - 'Rename node APPSVR01_NODE to APPSVR01_RHEL9 …'
    """

    def test_register_node(self):
        """register_node emits REGISTER NODE with domain."""
        from sp_mcp_server.commands.clients.node import RegisterNode

        cli = _cli()
        cmd = RegisterNode(cli)  # type: ignore[arg-type]
        cmd.execute({
            "client_name": "APPSVR02_NODE",
            "password": "NodePass1!xxxxx",
            "domain_name": "DOM_GENERAL",
        })

        # RegisterNode issues QUERY OPTION MINPWLENGTH first (POL-2 pre-flight),
        # then REGISTER NODE — search across all captured calls.
        register_calls = [c for c in cli.calls if "REGISTER NODE" in c]
        assert register_calls, f"REGISTER NODE not found in calls: {cli.calls}"
        assert "APPSVR02_NODE" in register_calls[0]
        assert "DOM_GENERAL" in register_calls[0]
        # RG-3 silent execution is tested in test_sec_password_commands.py;
        # FakeAdmcCli.execute_silent records to the same calls list so a
        # "password not in calls" check would always fail in the test harness.

    def test_lock_decommissioned_node(self):
        """set_client_lock with lock_status=locked emits LOCK NODE."""
        from sp_mcp_server.commands.clients.node import SetClientLock

        cli = _cli()
        cmd = SetClientLock(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "LEGACY01_NODE", "lock_status": "locked"})

        assert "LOCK NODE" in cli.calls[0]
        assert "LEGACY01_NODE" in cli.calls[0]

    def test_unlock_node(self):
        """set_client_lock with lock_status=unlocked emits UNLOCK NODE."""
        from sp_mcp_server.commands.clients.node import SetClientLock

        cli = _cli()
        cmd = SetClientLock(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "LEGACY01_NODE", "lock_status": "unlocked"})

        assert "UNLOCK NODE" in cli.calls[0]

    def test_rename_node(self):
        """rename_client emits RENAME NODE with old and new names."""
        from sp_mcp_server.commands.clients.node import RenameClient

        cli = _cli()
        cmd = RenameClient(cli)  # type: ignore[arg-type]
        cmd.execute({
            "current_name": "APPSVR01_NODE",
            "new_name": "APPSVR01_RHEL9",
        })

        assert "RENAME NODE" in cli.calls[0]
        assert "APPSVR01_NODE" in cli.calls[0]
        assert "APPSVR01_RHEL9" in cli.calls[0]

    def test_query_client_list(self):
        """query_client with no filter returns all nodes."""
        from sp_mcp_server.commands.clients.node import QueryClient

        cli = _cli()
        cmd = QueryClient(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert "QUERY NODE" in cli.calls[0]

    def test_query_client_by_domain(self):
        """query_client filtered by domain_name scopes the QUERY NODE call."""
        from sp_mcp_server.commands.clients.node import QueryClient

        cli = _cli()
        cmd = QueryClient(cli)  # type: ignore[arg-type]
        cmd.execute({"domain_name": "DOM_GENERAL"})

        assert "QUERY NODE" in cli.calls[0]
        assert "DOM_GENERAL" in cli.calls[0]


class TestR01StoragePoolConfiguration:
    """Prompts:
    - 'Create a PRIMARY container storage pool POOL_DISK_EXT01 …'
    - 'Add a new storage pool directory /tsm/containers/ext02 …'
    - 'Show DB backup volumes using query_volume_history TYPE=DBBACKUP'
    """

    def test_define_storage_pool(self):
        """define_storage_pool emits DEFINE STGPOOL with device class."""
        from sp_mcp_server.commands.storage.stgpool import DefineStoragePool

        cli = _cli()
        cmd = DefineStoragePool(cli)  # type: ignore[arg-type]
        cmd.execute({
            "pool_name": "POOL_DISK_EXT01",
            "device_class_name": "DCLASS_DISK",
            "description": "Extended primary deduplicated disk pool",
        })

        assert "DEFINE STGPOOL" in cli.calls[0]
        assert "POOL_DISK_EXT01" in cli.calls[0]
        assert "DCLASS_DISK" in cli.calls[0]

    def test_define_storage_pool_directory(self):
        """define_storage_pool_directory emits DEFINE STGPOOLDIRECTORY."""
        from sp_mcp_server.commands.storage.stgpool import DefineStoragePoolDirectory

        cli = _cli()
        cmd = DefineStoragePoolDirectory(cli)  # type: ignore[arg-type]
        cmd.execute({
            "pool_name": "POOL_DISK_PRIMARY",
            "directory": "/tsm/containers/ext02",
        })

        assert "DEFINE STGPOOLDIRECTORY" in cli.calls[0]
        assert "POOL_DISK_PRIMARY" in cli.calls[0]
        assert "/tsm/containers/ext02" in cli.calls[0]

    def test_query_volume_history_dbbackup(self):
        """query_volume_history TYPE=DBBACKUP filters to DB backup volumes."""
        from sp_mcp_server.commands.storage.volume import QueryVolumeHistory

        cli = _cli()
        cmd = QueryVolumeHistory(cli)  # type: ignore[arg-type]
        cmd.execute({"type": "DBBACKUP"})

        assert "QUERY VOLHISTORY" in cli.calls[0]
        assert "DBBACKUP" in cli.calls[0]

    def test_define_volume(self):
        """define_volume emits DEFINE VOLUME in the target pool."""
        from sp_mcp_server.commands.storage.volume import DefineVolume

        cli = _cli()
        cmd = DefineVolume(cli)  # type: ignore[arg-type]
        cmd.execute({
            "pool_name": "POOL_DISK_PRIMARY",
            "volume_name": "/data/tsm/vol003",
        })

        assert "DEFINE VOLUME" in cli.calls[0]
        assert "POOL_DISK_PRIMARY" in cli.calls[0]
        assert "/data/tsm/vol003" in cli.calls[0]


# ---------------------------------------------------------------------------
# R-02 · Data Protection Administrator
# ---------------------------------------------------------------------------

class TestR02PerformanceTuning:
    """Prompts:
    - 'Retrieve TXNGROUPMAX, MOVEBATCHSIZE, RESOURCEUTILIZATION, MAXSESSIONS …'
    - 'What is the current TXNGROUPMAX value on SPSVR01?'
    """

    def test_query_server_option_all(self):
        """query_server_option with no filter lists all options."""
        from sp_mcp_server.commands.system.server import QueryServerOption

        cli = _cli()
        cmd = QueryServerOption(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert "QUERY OPTION" in cli.calls[0]

    def test_query_server_option_specific(self):
        """query_server_option for TXNGROUPMAX targets that option."""
        from sp_mcp_server.commands.system.server import QueryServerOption

        cli = _cli()
        cmd = QueryServerOption(cli)  # type: ignore[arg-type]
        cmd.execute({"option_name": "TXNGROUPMAX"})

        assert "QUERY OPTION" in cli.calls[0]
        assert "TXNGROUPMAX" in cli.calls[0]


class TestR02DatabaseDiagnostics:
    """Prompts:
    - 'The SPSVR01 active log is reported at 78% utilisation …'
    - 'Run a full database diagnostic check on SPSVR01 …'
    """

    def test_query_recovery_log_standard(self):
        """query_recovery_log standard format returns log space info."""
        from sp_mcp_server.commands.system.logs import QueryRecoveryLog

        cli = _cli()
        cmd = QueryRecoveryLog(cli)  # type: ignore[arg-type]
        cmd.execute({"format": "standard"})

        assert "QUERY LOG" in cli.calls[0]

    def test_query_recovery_log_detailed(self):
        """query_recovery_log detailed returns extended log diagnostics."""
        from sp_mcp_server.commands.system.logs import QueryRecoveryLog

        cli = _cli()
        cmd = QueryRecoveryLog(cli)  # type: ignore[arg-type]
        cmd.execute({"format": "detailed"})

        assert "QUERY LOG" in cli.calls[0]
        assert "DETAILED" in cli.calls[0].upper()


class TestR02OperationalAudit:
    """Prompts:
    - 'Identify all nodes across DOM_GENERAL and DOM_DATABASE that have not
       completed a successful backup in the last 30 days …'
    - 'Check schedule miss rate for SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY
       over the last 7 days …'
    """

    def test_query_occupancy_for_node(self):
        """query_occupancy for a specific node shows its data distribution."""
        from sp_mcp_server.commands.storage.stgpool import QueryOccupancy

        cli = _cli()
        cmd = QueryOccupancy(cli)  # type: ignore[arg-type]
        cmd.execute({"node_name": "LEGACY01_NODE"})

        assert "QUERY OCCUPANCY" in cli.calls[0]
        assert "LEGACY01_NODE" in cli.calls[0]

    def test_query_scheduled_event_with_date_range(self):
        """query_scheduled_event with date range shows 7-day miss history."""
        from sp_mcp_server.commands.policies.schedule import QueryScheduledEvent

        cli = _cli()
        cmd = QueryScheduledEvent(cli)  # type: ignore[arg-type]
        cmd.execute({
            "schedule_name": "SCHED_DB_NIGHTLY",
            "begindate": "09/30/2026",
            "enddate": "10/07/2026",
        })

        assert "QUERY EVENT" in cli.calls[0]
        assert "SCHED_DB_NIGHTLY" in cli.calls[0]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# R-03 · Infrastructure Solution Architect
# ---------------------------------------------------------------------------

class TestR03EnvironmentAndSizing:
    """Prompt: 'What is the deduplication ratio and space savings on POOL_DISK_PRIMARY?'
               'Show device classes and tape libraries available for offsite storage'
               'Add directory /storage/primary/dir02 to container storage pool POOL_DISK_PRIMARY'
               'Are we compliant with our IBM Storage Protect server licenses?'
    """

    def test_query_deduplication_stats(self):
        """query_deduplication_stats returns deduplication and savings information."""
        from sp_mcp_server.commands.storage.content import QueryDeduplicationStats

        cli = _cli()
        cmd = QueryDeduplicationStats(cli)  # type: ignore[arg-type]
        cmd.execute({"container_name": "POOL_DISK_PRIMARY"})

        assert "QUERY DEDUPSTATS" in cli.calls[0]
        assert "POOL_DISK_PRIMARY" in cli.calls[0]

    def test_query_device_type(self):
        """query_device_type queries device class configuration."""
        from sp_mcp_server.commands.storage.device import QueryDeviceType

        cli = _cli()
        cmd = QueryDeviceType(cli)  # type: ignore[arg-type]
        cmd.execute({"device_type_name": "DCLASS_DISK"})

        assert "QUERY DEVCLASS" in cli.calls[0]
        assert "DCLASS_DISK" in cli.calls[0]

    def test_define_storage_pool_directory(self):
        """define_storage_pool_directory expands directory space for a container pool."""
        from sp_mcp_server.commands.storage.stgpool import DefineStoragePoolDirectory

        cli = _cli()
        cmd = DefineStoragePoolDirectory(cli)  # type: ignore[arg-type]
        cmd.execute({
            "pool_name": "POOL_DISK_PRIMARY",
            "directory": "/storage/primary/dir02",
        })

        assert "DEFINE STGPOOLDIRECTORY" in cli.calls[0]
        assert "POOL_DISK_PRIMARY" in cli.calls[0]
        assert "/storage/primary/dir02" in cli.calls[0]

    def test_query_license_info(self):
        """query_license_info emits QUERY LICENSE."""
        from sp_mcp_server.commands.system.admin import QueryLicenseInfo

        cli = _cli()
        cmd = QueryLicenseInfo(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY LICENSE"]


# ---------------------------------------------------------------------------
# R-04 · Workload & Application Owner
# ---------------------------------------------------------------------------

class TestR04WorkloadBackupIntegration:
    """Prompt: 'Check filespace backup status for database node DBSQL01_NODE'
               'Define copy group for SAP archive log retention in DOM_SAP'
               'Inspect occupancy distribution for Oracle database host DBORA01_NODE'
    """

    def test_query_client_backup_volume(self):
        """query_client_backup_volume lists filespaces for client node."""
        from sp_mcp_server.commands.clients.info import QueryClientBackupVolume

        cli = _cli()
        cmd = QueryClientBackupVolume(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "DBSQL01_NODE"})

        assert "QUERY FILESPACE" in cli.calls[0]
        assert "DBSQL01_NODE" in cli.calls[0]

    def test_define_copy_group_sap_archive(self):
        """define_copy_group emits DEFINE COPYGROUP for SAP archive retention."""
        from sp_mcp_server.commands.policies.copy import DefineCopyGroup

        cli = _cli()
        cmd = DefineCopyGroup(cli)  # type: ignore[arg-type]
        cmd.execute({
            "domain_name": "DOM_SAP",
            "policy_set_name": "PSET_SAP",
            "class_name": "MC_SAP_ARCHIVE",
            "type": "BACKUP",
            "destination": "POOL_DISK_PRIMARY",
        })

        assert "DEFINE COPYGROUP" in cli.calls[0]
        assert "DOM_SAP" in cli.calls[0]
        assert "MC_SAP_ARCHIVE" in cli.calls[0]

    def test_query_data_occupancy_oracle(self):
        """query_data_occupancy lists occupancy for Oracle database node."""
        from sp_mcp_server.commands.clients.info import QueryDataOccupancy

        cli = _cli()
        cmd = QueryDataOccupancy(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "DBORA01_NODE"})

        assert "QUERY OCCUPANCY" in cli.calls[0]
        assert "DBORA01_NODE" in cli.calls[0]

# R-05 · Security & Compliance Officer
# ---------------------------------------------------------------------------

class TestR05SecurityHardening:
    """Prompts:
    - 'Audit all SP administrator accounts … session security, SSL requirements'
    - 'Show license compliance status …'
    """

    def test_query_admin_user_all(self):
        """query_admin_user with no filter audits all SP administrator accounts."""
        from sp_mcp_server.commands.system.admin import QueryAdminUser

        cli = _cli()
        cmd = QueryAdminUser(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert "QUERY ADMIN" in cli.calls[0]

    def test_query_admin_user_specific(self):
        """query_admin_user for a named account returns detailed security info."""
        from sp_mcp_server.commands.system.admin import QueryAdminUser

        cli = _cli()
        cmd = QueryAdminUser(cli)  # type: ignore[arg-type]
        cmd.execute({"admin_name": "mcp-svc-system"})

        assert "QUERY ADMIN" in cli.calls[0]
        assert "mcp-svc-system" in cli.calls[0]

    def test_query_license_info(self):
        """query_license_info emits QUERY LICENSE."""
        from sp_mcp_server.commands.system.admin import QueryLicenseInfo

        cli = _cli()
        cmd = QueryLicenseInfo(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert "QUERY LICENSE" in cli.calls[0]

    def test_lock_admin_account(self):
        """set_user_lock with lock_status=locked emits LOCK ADMIN."""
        from sp_mcp_server.commands.system.admin import SetUserLock

        cli = _cli()
        cmd = SetUserLock(cli)  # type: ignore[arg-type]
        cmd.execute({"user_name": "OPS_READER", "lock_status": "locked"})

        assert "LOCK ADMIN" in cli.calls[0]
        assert "OPS_READER" in cli.calls[0]

    def test_grant_authority(self):
        """grant_authority emits GRANT AUTHORITY with privilege class."""
        from sp_mcp_server.commands.system.admin import GrantAuthority

        cli = _cli()
        cmd = GrantAuthority(cli)  # type: ignore[arg-type]
        cmd.execute({"user_name": "OPS_READER", "classes": "OPERATOR"})

        assert "GRANT AUTHORITY" in cli.calls[0]
        assert "OPS_READER" in cli.calls[0]
        assert "OPERATOR" in cli.calls[0]

    def test_revoke_authority(self):
        """revoke_authority emits REVOKE AUTHORITY."""
        from sp_mcp_server.commands.system.admin import RevokeAuthority

        cli = _cli()
        cmd = RevokeAuthority(cli)  # type: ignore[arg-type]
        cmd.execute({"user_name": "OPS_READER", "classes": "OPERATOR"})

        assert "REVOKE AUTHORITY" in cli.calls[0]
        assert "OPS_READER" in cli.calls[0]


class TestR05PolicyAudit:
    """Prompts:
    - 'Show all policy domains and their active policy sets …'
    - 'Show all copy group retention settings for DOM_DATABASE …'
    """

    def test_query_policy_domain_all(self):
        """query_policy_group lists all policy domains."""
        from sp_mcp_server.commands.policies.domain import QueryPolicyGroup

        cli = _cli()
        cmd = QueryPolicyGroup(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert "QUERY DOMAIN" in cli.calls[0]

    def test_query_policy_domain_specific(self):
        """query_policy_group filtered by domain_name returns that domain."""
        from sp_mcp_server.commands.policies.domain import QueryPolicyGroup

        cli = _cli()
        cmd = QueryPolicyGroup(cli)  # type: ignore[arg-type]
        cmd.execute({"domain_name": "DOM_DATABASE"})

        assert "QUERY DOMAIN" in cli.calls[0]
        assert "DOM_DATABASE" in cli.calls[0]

    def test_query_copy_group_retention(self):
        """query_retention_rule_config scoped to DOM_DATABASE shows its copy groups."""
        from sp_mcp_server.commands.policies.copy import QueryRetentionRuleConfig

        cli = _cli()
        cmd = QueryRetentionRuleConfig(cli)  # type: ignore[arg-type]
        cmd.execute({
            "policy_group": "DOM_DATABASE",
            "policy_set": "PSET_DATABASE",
            "policy_name": "MC_DB_90",
        })

        assert "QUERY COPYGROUP" in cli.calls[0]
        assert "DOM_DATABASE" in cli.calls[0]

    def test_query_protection_policy(self):
        """query_protection_policy lists management classes for a domain."""
        from sp_mcp_server.commands.policies.mgmt import QueryProtectionPolicy

        cli = _cli()
        cmd = QueryProtectionPolicy(cli)  # type: ignore[arg-type]
        cmd.execute({"domain_name": "DOM_GENERAL"})

        assert "QUERY MGMTCLASS" in cli.calls[0]
        assert "DOM_GENERAL" in cli.calls[0]


# ---------------------------------------------------------------------------
# Tool type and privilege annotations
# ---------------------------------------------------------------------------

    def test_query_retention_set(self):
        """query_retention_set emits QUERY RETSET."""
        from sp_mcp_server.commands.policies.copy import QueryRetentionSet

        cli = _cli()
        cmd = QueryRetentionSet(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY RETSET"]


# ---------------------------------------------------------------------------
# R-06 · Resilience Operations Manager
# ---------------------------------------------------------------------------

class TestR06ResilienceOperations:
    """Prompt: 'Isolate suspected ransomware host WEB01_NODE with client lock'
               'Invoke disaster recovery database restore'
               'Query disaster recovery plan file status'
               'Track offsite disaster recovery media'
    """

    def test_query_dr_media(self):
        """query_dr_media emits QUERY DRMEDIA."""
        from sp_mcp_server.commands.operations.disaster_recovery import QueryDRMedia

        cli = _cli()
        cmd = QueryDRMedia(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY DRMEDIA"]

    def test_query_recovery_plan_file(self):
        """query_recovery_plan_file emits QUERY RPFILE."""
        from sp_mcp_server.commands.operations.disaster_recovery import QueryRecoveryPlanFile

        cli = _cli()
        cmd = QueryRecoveryPlanFile(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY RPFILE"]

    def test_restore_db_command(self):
        """restore_db emits RESTORE DB with target parameters."""
        from sp_mcp_server.commands.operations.disaster_recovery import RestoreDB

        cli = _cli()
        cmd = RestoreDB(cli)  # type: ignore[arg-type]
        cmd.execute({"source": "DBBACKUP"})

        assert "RESTORE DB" in cli.calls[0]
        assert "SOURCE=DBBACKUP" in cli.calls[0]

    def test_set_client_lock_ransomware(self):
        """set_client_lock isolates client node via LOCK NODE."""
        from sp_mcp_server.commands.clients.node import SetClientLock

        cli = _cli()
        cmd = SetClientLock(cli)  # type: ignore[arg-type]
        cmd.execute({"client_name": "WEB01_NODE", "lock_status": "lock"})

        assert cli.calls == ["LOCK NODE WEB01_NODE"]


# ---------------------------------------------------------------------------
# R-07 · Storage Protect Service Engineer
# ---------------------------------------------------------------------------

class TestR07ServiceEngineerDiagnostics:
    """Prompt: 'Execute servermon diagnostic utility'
               'Check for running background processes before maintenance window'
               'Triage activity log defect ANR0406E'
               'Audit frequency of warning ANR8468W'
    """

    def test_query_activity_log_anr8468w(self):
        """query_activity_log searches for warning code ANR8468W."""
        from sp_mcp_server.commands.operations.misc import QueryActivityLog

        cli = _cli()
        cmd = QueryActivityLog(cli)  # type: ignore[arg-type]
        cmd.execute({"search": "ANR8468W"})

        assert "QUERY ACTLOG" in cli.calls[0]
        assert "SEARCH=ANR8468W" in cli.calls[0]

    def test_query_activity_log_defect_anr0406e(self):
        """query_activity_log searches for defect error code ANR0406E."""
        from sp_mcp_server.commands.operations.misc import QueryActivityLog

        cli = _cli()
        cmd = QueryActivityLog(cli)  # type: ignore[arg-type]
        cmd.execute({"search": "ANR0406E"})

        assert "QUERY ACTLOG" in cli.calls[0]
        assert "SEARCH=ANR0406E" in cli.calls[0]

    def test_run_servermon_execution(self):
        """run_servermon executes diagnostic collector."""
        from sp_mcp_server.commands.servermon import RunServerMon
        from tests.fixtures import FakeServermonCli

        cli = FakeServermonCli(stdout="SERVERMON DIAGNOSTIC COMPLETE")
        cmd = RunServerMon(cli)
        result = cmd.execute({"args": ["-standard"]})

        assert result == "SERVERMON DIAGNOSTIC COMPLETE"
        assert cli.calls == [["-standard"]]

    def test_query_background_job(self):
        """query_background_job emits QUERY PROCESS."""
        from sp_mcp_server.commands.operations.data_movement import QueryBackgroundJob

        cli = _cli()
        cmd = QueryBackgroundJob(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY PROCESS"]


# ---------------------------------------------------------------------------
# R-08 · Multi-Server Replication & Data Management
# ---------------------------------------------------------------------------

class TestR08MultiServerReplication:
    """Prompt: 'Discover replication servers and topology'
               'Query replication rules and failures'
               'Monitor replication status for client nodes'
               'Verify storage pool protection status'
               'Update node domain after failover'
    """

    def test_query_protection_status(self):
        """query_protection_status emits QUERY PROTECTSTATUS."""
        from sp_mcp_server.commands.operations.replication import QueryProtectionStatus

        cli = _cli()
        cmd = QueryProtectionStatus(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY PROTECTSTATUS"]

    def test_query_replication_failures(self):
        """query_replication_failures emits QUERY REPLFAILURES."""
        from sp_mcp_server.commands.operations.replication import QueryReplicationFailures

        cli = _cli()
        cmd = QueryReplicationFailures(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY REPLFAILURES"]

    def test_query_replication_rule(self):
        """query_replication_rule emits QUERY REPLRULE."""
        from sp_mcp_server.commands.operations.replication import QueryReplicationRule

        cli = _cli()
        cmd = QueryReplicationRule(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY REPLRULE"]

    def test_query_replication_server(self):
        """query_replication_server emits QUERY REPLSERVER."""
        from sp_mcp_server.commands.operations.replication import QueryReplicationServer

        cli = _cli()
        cmd = QueryReplicationServer(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY REPLSERVER"]

    def test_query_replication_status_node(self):
        """query_replication_status emits QUERY REPLICATION for target node."""
        from sp_mcp_server.commands.operations.replication import QueryReplicationStatus

        cli = _cli()
        cmd = QueryReplicationStatus(cli)  # type: ignore[arg-type]
        cmd.execute({"node_name": "WEB01_NODE"})

        assert cli.calls == ["QUERY REPLICATION WEB01_NODE"]

    def test_query_replication_client_all_nodes(self):
        """query_replication_client emits QUERY REPLNODE * for all nodes."""
        from sp_mcp_server.commands.clients.node import QueryReplicationClient

        cli = _cli()
        cmd = QueryReplicationClient(cli)  # type: ignore[arg-type]
        cmd.execute({"node_name": "*"})

        assert cli.calls == ["QUERY REPLNODE *"]

    def test_query_replication_client_single_node(self):
        """query_replication_client emits QUERY REPLNODE for specific node and server."""
        from sp_mcp_server.commands.clients.node import QueryReplicationClient

        cli = _cli()
        cmd = QueryReplicationClient(cli)  # type: ignore[arg-type]
        cmd.execute({"node_name": "WEB01_NODE", "target_server_name": "SPSVR02"})

        assert cli.calls == ["QUERY REPLNODE WEB01_NODE SPSVR02"]

    def test_query_storage_rule(self):
        """query_storage_rule emits QUERY STGRULE."""
        from sp_mcp_server.commands.operations.rules import QueryStorageRule

        cli = _cli()
        cmd = QueryStorageRule(cli)  # type: ignore[arg-type]
        cmd.execute({})

        assert cli.calls == ["QUERY STGRULE"]

    def test_update_node_replication_domain(self):
        """update_node updates node domain during failover."""
        from sp_mcp_server.commands.clients.node import UpdateNode

        cli = _cli()
        cmd = UpdateNode(cli)  # type: ignore[arg-type]
        cmd.execute({"node_name": "WEB01_NODE", "domain_name": "DOM_GENERAL"})

        assert "UPDATE NODE WEB01_NODE" in cli.calls[0]
        assert "DOMAIN=DOM_GENERAL" in cli.calls[0]

# ---------------------------------------------------------------------------
# Tool type and privilege annotations
# ---------------------------------------------------------------------------

class TestPromptToolPrivilegeAnnotations:
    """Verify that tools referenced in read-only sample prompts are annotated
    read-only, and write tools that require confirmation are annotated full."""

    @pytest.mark.parametrize("cls_path,expected_type", [
        ("sp_mcp_server.commands.clients.info.QueryActiveSession",       "read-only"),
        ("sp_mcp_server.commands.clients.info.QueryClientBackupVolume",  "read-only"),
        ("sp_mcp_server.commands.clients.node.QueryClient",              "read-only"),
        ("sp_mcp_server.commands.operations.misc.QueryActivityLog",      "read-only"),
        ("sp_mcp_server.commands.operations.replication.QueryProtectionStatus", "read-only"),
        ("sp_mcp_server.commands.operations.replication.QueryReplicationFailures", "read-only"),
        ("sp_mcp_server.commands.operations.replication.QueryReplicationServer", "read-only"),
        ("sp_mcp_server.commands.policies.schedule.QuerySchedule",       "read-only"),
        ("sp_mcp_server.commands.policies.schedule.QueryScheduledEvent",  "read-only"),
        ("sp_mcp_server.commands.storage.content.QueryDeduplicationStats", "read-only"),
        ("sp_mcp_server.commands.storage.device.QueryDeviceType",         "read-only"),
        ("sp_mcp_server.commands.storage.stgpool.QueryStorageContainer",  "read-only"),
        ("sp_mcp_server.commands.storage.volume.QueryVolumeHistory",     "read-only"),
        ("sp_mcp_server.commands.system.admin.QueryAdminUser",           "read-only"),
        ("sp_mcp_server.commands.system.admin.QueryLicenseInfo",         "read-only"),
        ("sp_mcp_server.commands.system.logs.QueryRecoveryLog",          "read-only"),
        ("sp_mcp_server.commands.system.server.QueryServerOption",       "read-only"),
        ("sp_mcp_server.commands.system.server.QueryServerStatus",       "read-only"),
    ])
    def test_read_only_tool_type(self, cls_path: str, expected_type: str):
        import importlib
        module_path, class_name = cls_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        cli = _cli()
        instance = cls(cli)  # type: ignore[arg-type]
        assert instance.tool_type == expected_type, (
            f"{class_name}.tool_type should be '{expected_type}', got '{instance.tool_type}'"
        )

    @pytest.mark.parametrize("cls_path,expected_priv", [
        ("sp_mcp_server.commands.clients.node.RegisterNode",              "policy"),
        ("sp_mcp_server.commands.clients.node.RenameClient",              "policy"),
        ("sp_mcp_server.commands.clients.node.SetClientLock",             "operator"),
        ("sp_mcp_server.commands.operations.disaster_recovery.RestoreDB", "system"),
        ("sp_mcp_server.commands.policies.copy.DefineCopyGroup",          "policy"),
        ("sp_mcp_server.commands.policies.mgmt.DefineManagementClass",    "policy"),
        ("sp_mcp_server.commands.policies.schedule.DefineSchedule",       "policy"),
        ("sp_mcp_server.commands.storage.stgpool.DefineStoragePool",      "storage"),
        ("sp_mcp_server.commands.storage.stgpool.DefineStoragePoolDirectory", "storage"),
        ("sp_mcp_server.commands.storage.volume.DefineVolume",            "storage"),
        ("sp_mcp_server.commands.system.admin.GrantAuthority",            "system"),
        ("sp_mcp_server.commands.system.admin.SetUserLock",               "system"),
    ])
    def test_write_tool_privilege(self, cls_path: str, expected_priv: str):
        import importlib
        module_path, class_name = cls_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        cli = _cli()
        instance = cls(cli)  # type: ignore[arg-type]
        assert instance.required_privilege == expected_priv, (
            f"{class_name}.required_privilege should be '{expected_priv}', "
            f"got '{instance.required_privilege}'"
        )



# ===========================================================================
# Part 2: Live Integration Tests (against real SP server)
# ===========================================================================

import os

_MISSING_ENV = not (
    os.environ.get("TCPSERVERADDRESS")
    or os.environ.get("SP_ADMIN_ID_READONLY")
    or os.environ.get("SP_ADMIN_ID_SYSTEM")
)

if _MISSING_ENV:
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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
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

@pytest.mark.integration
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
