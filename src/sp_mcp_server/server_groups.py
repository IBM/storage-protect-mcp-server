import sp_mcp_server.commands.system as sys_cmd
import sp_mcp_server.commands.operations as ops
import sp_mcp_server.commands.clients as cli_cmd
import sp_mcp_server.commands.policies as pol_cmd
import sp_mcp_server.commands.storage as stg_cmd
import sp_mcp_server.commands.offline as off_cmd
import sp_mcp_server.commands.servermon as mon_cmd

# ==========================================
# GROUP 1: CLIENT MANAGEMENT
# ==========================================

# 1. mcp-server-clients-core (~12 tools)
# Focus: Node lifecycle.
ISP_CLIENTS_CORE = [
    cli_cmd.RegisterNode,       # NEW
    cli_cmd.UpdateNode,
    cli_cmd.DeleteNode,
    cli_cmd.RenameClient,       # NEW (RenameNode)
    cli_cmd.SetClientLock,      # NEW (LockNode/UnlockNode)
    cli_cmd.QueryClient,
    cli_cmd.QueryActiveSession,
    cli_cmd.QueryDataOccupancy,
    cli_cmd.QueryAuditDataOccupancy,
    cli_cmd.QueryClientBackupVolume,
    cli_cmd.QueryVirtualMountPoint,
    cli_cmd.QueryClientDataPlacement,
    cli_cmd.DefineNodeGroup,
    cli_cmd.UpdateNodeGroup,
    cli_cmd.DeleteNodeGroup,
    cli_cmd.QueryClientGroup,
    cli_cmd.DefineNodeGroupMember,
    cli_cmd.RemoveClientFromGroup,
    cli_cmd.QueryProxyClient,
    cli_cmd.QueryReplicationClient
]

# 2. mcp-server-clients-config (~10 tools)
# Focus: Client options and schedules.
ISP_CLIENTS_CONFIG = [
    cli_cmd.DefineClientOptSet,
    cli_cmd.UpdateClientOptSet,
    cli_cmd.DeleteClientOptSet,
    cli_cmd.DefineClientOpt,
    cli_cmd.UpdateClientOpt,
    cli_cmd.DeleteClientOpt,
    cli_cmd.QueryClientOptionSet,
    # Client Actions / Schedules often related to client config
    ops.DefineClientAction,
    cli_cmd.DefineAssociation,
    cli_cmd.DeleteAssociation
]

# ==========================================
# GROUP 2: STORAGE MANAGEMENT
# ==========================================

# 3. mcp-server-storage-pools (~14 tools)
# Focus: Storage Pools and Volumes.
ISP_STORAGE_POOLS = [
    stg_cmd.DefineStoragePool,
    stg_cmd.UpdateStoragePool,
    stg_cmd.DeleteStoragePool,
    stg_cmd.DefineStoragePoolDirectory,
    stg_cmd.QueryContainerDirectory,
    stg_cmd.DeleteStoragePoolDirectory,
    stg_cmd.QueryStorageContainer,
    stg_cmd.QueryOccupancy,
    stg_cmd.DefineVolume,
    stg_cmd.UpdateVolume,
    stg_cmd.DeleteVolume,
    stg_cmd.QueryMediaVolume,
    stg_cmd.UpdateVolumeHistory,
    stg_cmd.QueryMountedVolumes,
    stg_cmd.QueryVolumeHistory
]

# 4. mcp-server-storage-hardware (~15 tools)
# Focus: Libraries, Drives, Paths.
ISP_STORAGE_HARDWARE = [
    stg_cmd.DefineLibrary,
    stg_cmd.UpdateLibrary,
    stg_cmd.DeleteLibrary,
    stg_cmd.QueryTapeLibrary,
    stg_cmd.DefineDrive,
    stg_cmd.UpdateDrive,
    stg_cmd.DeleteDrive,
    stg_cmd.QueryTapeDrive,
    stg_cmd.DefinePath,
    stg_cmd.UpdatePath,
    stg_cmd.DeletePath,
    stg_cmd.QueryDataPath,
    # Extras
    stg_cmd.QueryTapeAlerts,
    stg_cmd.QuerySanDevices
    # CheckinLibVol if implemented
]

# 5. mcp-server-storage-device (~12 tools)
# Focus: Device Classes and Data Movers.
ISP_STORAGE_DEVICE = [
    stg_cmd.DefineDeviceClass,
    stg_cmd.UpdateDeviceClass,
    stg_cmd.DeleteDeviceClass,
    stg_cmd.QueryDeviceType,
    stg_cmd.DefineDataMover,
    stg_cmd.UpdateDataMover,
    stg_cmd.DeleteDataMover,
    stg_cmd.QueryDataMover,
    # Related storage ops
    ops.MigrateStorageTarget,
    #stg_cmd.QueryStorageTarget
]

# ==========================================
# GROUP 3: POLICY MANAGEMENT
# ==========================================

# 6. mcp-server-policies-lifecycle (~14 tools)
# Focus: Policy Domains, Sets, and Activation.
ISP_POLICIES_LIFECYCLE = [
    pol_cmd.DefinePolicyDomain,
    pol_cmd.UpdatePolicyDomain,
    pol_cmd.DeletePolicyDomain,
    pol_cmd.QueryPolicyGroup,
    pol_cmd.DefinePolicySet,
    pol_cmd.UpdatePolicySet,
    pol_cmd.DeletePolicySet,
    pol_cmd.QueryPolicySet,
    pol_cmd.ActivatePolicySet,  # NEW
    pol_cmd.ValidatePolicySet   # NEW
]

# 7. mcp-server-policies-management (~12 tools)
# Focus: Management Classes and Copy Groups.
ISP_POLICIES_MANAGEMENT = [
    pol_cmd.DefineManagementClass,
    pol_cmd.UpdateManagementClass,
    pol_cmd.DeleteManagementClass,
    pol_cmd.QueryProtectionPolicy,
    pol_cmd.DefineCopyGroup,
    pol_cmd.UpdateCopyGroup,
    pol_cmd.DeleteCopyGroup,
    pol_cmd.QueryRetentionRuleConfig,
    # Schedules
    pol_cmd.DefineSchedule,
    pol_cmd.UpdateSchedule,
    pol_cmd.DeleteSchedule,
    pol_cmd.QuerySchedule,
    pol_cmd.QueryScheduledEvent
]

# ==========================================
# GROUP 4: SYSTEM & SECURITY
# ==========================================

# 8. mcp-server-system-admin (~15 tools)
# Focus: Administrators and Permissions.
ISP_SYSTEM_ADMIN = [
    sys_cmd.DefineAdmin,
    sys_cmd.UpdateUser,         # UpdateAdmin
    sys_cmd.DeleteAdmin,
    sys_cmd.QueryAdminUser,
    sys_cmd.SetUserLock,        # Lock/Unlock Admin
    sys_cmd.GrantAuthority,     # NEW
    sys_cmd.RevokeAuthority,    # NEW
    sys_cmd.RegisterLicense,    # NEW
    sys_cmd.QueryLicenseInfo,
    sys_cmd.DefineMachine,
    sys_cmd.UpdateMachine,
    sys_cmd.DeleteMachine
]

# 9. mcp-server-system-config (~12 tools)
# Focus: Global server configuration and monitoring.
ISP_SYSTEM_CONFIG = [
    sys_cmd.DefineServer,
    sys_cmd.UpdateServer,
    sys_cmd.DeleteServer,
    sys_cmd.QueryServerStatus,
    sys_cmd.QuerySystemInfo,
    sys_cmd.QueryServerOption,  # Check import name
    sys_cmd.DefineScript,
    sys_cmd.UpdateScript,
    sys_cmd.DeleteScript,
    sys_cmd.QueryAutomationScript, # Check import name
    sys_cmd.DefineConnection,
    sys_cmd.UpdateConnection,
    sys_cmd.DeleteConnection
]

# ==========================================
# GROUP 5: OPERATIONS
# ==========================================

# 10. mcp-server-ops-protection (~10 tools)
# Focus: DB Backup, Replication, Disaster Recovery.
ISP_OPS_PROTECTION = [
    ops.BackupDB,               # NEW
    ops.RestoreDB,              # NEW
    ops.QueryDRStatus,
    ops.QueryDRMedia,
    ops.QueryRecoveryPlanFile,
    ops.QueryRecoveryPlanFileContent,
    ops.QueryReplicationStatus,
    ops.QueryReplicationRule,
    ops.QueryProtectionStatus,
    ops.QueryReplicationFailures
]

# 11. mcp-server-ops-maintenance (~12 tools)
# Focus: Data movement and cleanup.
ISP_OPS_MAINTENANCE = [
    ops.MoveDataContainer,
    ops.MoveClientData,
    ops.ReclaimStorageSpace,
    ops.DefineRecoveryMedia,
    ops.UpdateRecoveryMedia,
    ops.DeleteRecoveryMedia,
    ops.DefineBackupSet,
    ops.UpdateBackupSet,
    ops.DeleteBackupSet,
    # Diag / Offline
    off_cmd.QueryOfflineDBSpace,
    off_cmd.QueryOfflineLog,
    mon_cmd.RunServerMon,
    # Logs and Events
    ops.QueryActivityLog,
    sys_cmd.QueryRecoveryLog,
    sys_cmd.QueryEnabledEvents,
    sys_cmd.QueryEventRules,
    sys_cmd.QueryEventReceiver,
    # Jobs
    ops.QueryBackgroundJob,
    ops.QueryExportJob,
    ops.QueryMaintenanceJob,
    ops.QueryRestoreJob
]

# 12. mcp-server-ops-rules (~18 tools)
# Focus: Automation rules and alerts, subrules, retention rules, and holds.
# NOTE: DeleteHold removed - IBM SP has no DELETE HOLD command (holds auto-deactivate when all retsets released)
ISP_OPS_RULES = [
    ops.DefineAlertTrigger,
    ops.UpdateAlertTrigger,
    ops.DeleteAlertTrigger,
    ops.UpdateAlertStatus,
    ops.QueryAlertTrigger,
    ops.DefineStorageRule,
    ops.UpdateStorageRule,
    ops.DeleteStorageRule,
    ops.QueryStorageRule,
    ops.DefineSpaceTrigger,
    ops.UpdateSpaceTrigger,
    ops.DeleteSpaceTrigger,
    ops.DefineStatusThreshold,
    ops.UpdateStatusThreshold,
    ops.DeleteStatusThreshold,
    ops.DefineSubRule,
    ops.UpdateSubRule,
    ops.DeleteSubRule,
    pol_cmd.QuerySubRule,
    ops.DefineHold,
    ops.DefineRetentionRule
]



# ==========================================
# ADDITIONAL OPERATION GROUPS (for main_ops.py)
# ==========================================

# ISP_LOGS - Log and event management
ISP_LOGS = [
    ops.QueryActivityLog,
    sys_cmd.QueryRecoveryLog,
    sys_cmd.QueryEnabledEvents,
    sys_cmd.QueryEventRules,
    sys_cmd.QueryEventReceiver
]

# ISP_JOBS - Background job monitoring
ISP_JOBS = [
    ops.QueryBackgroundJob,
    ops.QueryExportJob,
    ops.QueryMaintenanceJob,
    ops.QueryRestoreJob
]

# ISP_ALERTS - Alert management
ISP_ALERTS = [
    ops.DefineAlertTrigger,
    ops.UpdateAlertTrigger,
    ops.DeleteAlertTrigger,
    ops.UpdateAlertStatus,
    ops.QueryAlertTrigger,
    ops.QueryAlertStatus
]

# ISP_BACKUPSET - Backup set management
ISP_BACKUPSET = [
    ops.DefineBackupSet,
    ops.UpdateBackupSet,
    ops.DeleteBackupSet
]

# ISP_CATALOG - Catalog operations
ISP_CATALOG = [
    ops.ProtectCatalog,
    ops.RestoreCatalog
]

# ISP_DATA_MOVEMENT - Data movement operations
ISP_DATA_MOVEMENT = [
    ops.MoveDataContainer,
    ops.MoveClientData,
    ops.MigrateStorageTarget,
    ops.ReclaimStorageSpace
]

# ISP_DR - Disaster recovery operations
ISP_DR = [
    ops.BackupDB,
    ops.RestoreDB,
    ops.QueryDRStatus,
    ops.QueryDRMedia,
    ops.QueryRecoveryPlanFile,
    ops.QueryRecoveryPlanFileContent
]

# ISP_FILESYSTEM - Filesystem and virtual mapping
ISP_FILESYSTEM = [
    ops.DefineObjectDomain,
    ops.DefineVirtualFSMapping,
    ops.UpdateVirtualFSMapping,
    ops.DeleteVirtualFSMapping
]

# ISP_MEDIA - Recovery media management
ISP_MEDIA = [
    ops.DefineRecoveryMedia,
    ops.UpdateRecoveryMedia,
    ops.DeleteRecoveryMedia
]

# ISP_REPLICATION - Replication monitoring
ISP_REPLICATION = [
    ops.QueryProtectionStatus,
    ops.QueryReplicationFailures,
    ops.QueryReplicationStatus,
    ops.QueryReplicationRule,
    ops.QueryReplicationServer
]

# ISP_RULES - Storage and automation rules
ISP_RULES = [
    ops.DefineStorageRule,
    ops.UpdateStorageRule,
    ops.DeleteStorageRule,
    ops.QueryStorageRule,
    ops.DefineSpaceTrigger,
    ops.UpdateSpaceTrigger,
    ops.DeleteSpaceTrigger,
    ops.DefineStatusThreshold,
    ops.UpdateStatusThreshold,
    ops.DeleteStatusThreshold,
    ops.DefineSubRule,
    ops.UpdateSubRule,
    ops.DeleteSubRule,
    ops.DefineHold,
    ops.DeleteHold,
    ops.DefineRetentionRule
]

# ISP_MISC_OPS - Miscellaneous operations
ISP_MISC_OPS = [
    ops.DefineScratchPadEntry,
    ops.UpdateScratchPadEntry,
    ops.DeleteScratchPadEntry,
    ops.QueryPendingCommand,
    ops.QueryProfile,
    ops.QueryUserRequest,
    ops.UpdateCollocationGroup,
    ops.DefineClientAction
]
