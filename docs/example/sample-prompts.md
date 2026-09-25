# Sample Prompts

A collection of naturalistic, task-oriented prompts for the IBM Storage Protect MCP Server, organised by persona. Each prompt carries **intent** (what the user wants to accomplish), **context** (the environment or scope), and **form** (how the answer should be delivered). All prompts use the [Sample Deployment Topology](#sample-deployment-topology) defined below — substitute your own server names, node names, pool names, and dates when adapting them.

---

## Related Guides

| Guide | Purpose |
|---|---|
| [Installation Guide](../guides/install-guide.md) | OS user setup, Python environment, virtual environment, and `dsmadmc` prerequisites |
| [Configuration Guide](../guides/configure-guide.md) | MCP client configuration for stdio (SSH) and HTTP (OIDC) transports |
| [User Guide](../guides/user-guide.md) | Privilege tiers, tool access control, `--mode` flag, starting and stopping the server |
| [Troubleshooting Guide](../guides/troubleshoot.md) | Error markers, startup failures, credential errors, offline command failures, and Python import errors |

---

## Guidelines for Effective Prompts

- **Keep scope constrained.** Ask for specific entities or time windows rather than unbounded global scans.
- **Prefer exact object names.** When known, supply node names, pool names, or schedule names to minimise exploratory tool calls.
- **Single-task focus.** Break complex automation workflows into distinct sequential steps.
- **Constrain log queries.** Specify narrow time windows (±60 minutes) and exact search strings instead of broad `QUERY ACTLOG` sweeps.
- **Summary first.** Request high-level status summaries before asking for granular diagnostic drill-downs.

---

## Sample Deployment Topology

All prompts in this document are written against the following named environment. Use this topology as a reference when adapting prompts to your own infrastructure.

### IBM Storage Protect Server

| Attribute | Value |
|---|---|
| MCP server identifier | `sp-mcp-server-remote-tumbleweed` |
| SP server hostname | `spsvr01.corp.example.com` |
| SP server name (internal) | `SPSVR01` |
| SP server version | 8.1.22 |
| OS | Red Hat Enterprise Linux 9 |
| DB allocated | 512 GB |
| Active log | 32 GB |
| Archive log | 128 GB |

### BA Client Nodes

| Node name | Hostname | OS | Policy domain | Workload |
|---|---|---|---|---|
| `WEB01_NODE` | `web01.corp.example.com` | RHEL 9 | `DOM_GENERAL` | Apache HTTP Server |
| `WEB02_NODE` | `web02.corp.example.com` | RHEL 9 | `DOM_GENERAL` | Apache HTTP Server |
| `APPSVR01_NODE` | `appsvr01.corp.example.com` | RHEL 9 | `DOM_GENERAL` | Java application server |
| `DBORA01_NODE` | `dbora01.corp.example.com` | RHEL 9 | `DOM_DATABASE` | Oracle 19c (RMAN/backint) |
| `DBSQL01_NODE` | `dbsql01.corp.example.com` | Windows Server 2022 | `DOM_DATABASE` | SQL Server 2022 (VSS agent) |
| `DBDB201_NODE` | `dbdb201.corp.example.com` | RHEL 9 | `DOM_DATABASE` | Db2 11.5 (API backup) |
| `SAPHANA01_NODE` | `saphana01.corp.example.com` | SLES 15 | `DOM_SAP` | SAP HANA 2.0 (backint) |
| `SAPABAP01_NODE` | `sapabap01.corp.example.com` | SLES 15 | `DOM_SAP` | SAP S/4HANA ABAP (BRTOOLS/backint) |
| `VMPROXY01_NODE` | `vmproxy01.corp.example.com` | RHEL 9 | `DOM_VIRTUAL` | SPVE proxy for VMware vSphere 8 |
| `NASSVR01_NODE` | `nassvr01.corp.example.com` | — | `DOM_GENERAL` | NetApp NAS (NDMP datamover) |
| `LEGACY01_NODE` | `legacy01.corp.example.com` | RHEL 7 | `DOM_GENERAL` | Decommissioned — pending removal |

### Policy Domains, Management Classes, and Copy Groups

| Domain | Policy set | Management class | Copy group type | VEREXISTS | RETEXTRA | Destination pool |
|---|---|---|---|---|---|---|
| `DOM_GENERAL` | `PSET_GENERAL` | `MC_STD_30` (default) | Backup | 3 | 30 days | `POOL_DISK_PRIMARY` |
| `DOM_GENERAL` | `PSET_GENERAL` | `MC_STD_30` | Archive | 1 | 365 days | `POOL_DISK_PRIMARY` |
| `DOM_DATABASE` | `PSET_DATABASE` | `MC_DB_90` (default) | Backup | 5 | 90 days | `POOL_DISK_PRIMARY` |
| `DOM_DATABASE` | `PSET_DATABASE` | `MC_DB_90` | Archive | 1 | 2555 days | `POOL_TAPE_COPY` |
| `DOM_SAP` | `PSET_SAP` | `MC_SAP_LOG` | Archive | 1 | 90 days | `POOL_DISK_PRIMARY` |
| `DOM_SAP` | `PSET_SAP` | `MC_SAP_FULL` | Backup | 5 | 180 days | `POOL_DISK_PRIMARY` |
| `DOM_VIRTUAL` | `PSET_VIRTUAL` | `MC_VM_14` (default) | Backup | 14 | 14 days | `POOL_DISK_PRIMARY` |
| `DOM_GENERAL` | `PSET_WORM` | `MC_WORM_7YR` | Backup | 1 | 2555 days | `POOL_TAPE_WORM` |

### Backup Schedules

| Schedule name | Domain | Type | Start time | Period | Action | Associated nodes |
|---|---|---|---|---|---|---|
| `SCHED_GENERAL_DAILY` | `DOM_GENERAL` | Client | 22:00 | Daily | Incremental | `WEB01_NODE`, `WEB02_NODE`, `APPSVR01_NODE`, `NASSVR01_NODE` |
| `SCHED_DB_NIGHTLY` | `DOM_DATABASE` | Client | 23:30 | Daily | Incremental | `DBORA01_NODE`, `DBSQL01_NODE`, `DBDB201_NODE` |
| `SCHED_SAP_LOG_HOURLY` | `DOM_SAP` | Client | 00:00 | Hourly | Archive | `SAPHANA01_NODE`, `SAPABAP01_NODE` |
| `SCHED_SAP_FULL_WEEKLY` | `DOM_SAP` | Client | 01:00 Saturday | Weekly | Selective | `SAPHANA01_NODE`, `SAPABAP01_NODE` |
| `SCHED_VM_DAILY` | `DOM_VIRTUAL` | Client | 21:00 | Daily | Incremental | `VMPROXY01_NODE` |
| `SCHED_DBBACKUP_DAILY` | — | Administrative | 04:00 | Daily | DB backup | — |

### Storage Pools and Device Classes

| Pool name | Type | Device class | Role | Max utilisation |
|---|---|---|---|---|
| `POOL_DISK_PRIMARY` | PRIMARY (container) | `DCLASS_DISK` (DISK) | Primary deduplicated disk pool | 80% trigger migration |
| `POOL_DISK_COPY` | COPY | `DCLASS_DISK` (DISK) | On-site disk copy | — |
| `POOL_TAPE_COPY` | COPY | `DCLASS_LTO8` (LTO8, library `LIB_LTO8_01`) | Off-site tape copy | — |
| `POOL_TAPE_WORM` | PRIMARY | `DCLASS_LTO8_WORM` (LTO8, WORM) | Regulatory WORM retention | — |
| `POOL_CLOUD_TIER` | PRIMARY (cloud) | `DCLASS_COS` (CLOUD, IBM COS `cos.us-south.example.com`) | Active cloud object tier | — |
| `POOL_DBBACKUP` | PRIMARY | `DCLASS_DISK` (DISK) | DB backup target | — |

### Storage Devices

| Name | Type | Device / connection |
|---|---|---|
| `LIB_LTO8_01` | SCSI tape library | FC-attached, device `/dev/sg2`, 4 drives |
| `DRIVE_LTO8_01` through `DRIVE_LTO8_04` | LTO-8 tape drives | In `LIB_LTO8_01` |
| `NAS_MOVER_01` | NDMP datamover | NetApp NAS filer `nassvr01.corp.example.com` |
| IBM Cloud Object Storage | Cloud endpoint | `cos.us-south.example.com`, bucket `sp-backup-primary` |

### Administrative Accounts (SP server-side)

| Admin ID | Privilege class | Role |
|---|---|---|
| `ADMIN` | System | Break-glass system admin |
| `mcp-svc-system` | System | MCP server service account (full tools) |
| `mcp-svc-operator` | Operator | MCP server service account (operations + read-only) |
| `OPS_READER` | Operator | Read-only operations monitoring |
| `DBA_ADMIN` | Policy | Database policy management |

---

## Multi-Server Deployment Topology

The prompts in the [R-08 section](#r-08--multi-server-replication--data-management) below are written against the following extended three-server environment. SPSVR01 is the primary production server (also used for all single-server prompts above). SPSVR02 is an on-site DR replica that receives node replication from SPSVR01. SPSVR03 is a remote archive server at a second data-centre site.

### SP Servers in the Multi-Server Topology

| MCP server identifier | SP server name | Hostname | Role |
|---|---|---|---|
| `sp-mcp-spsvr01` | `SPSVR01` | `spsvr01.corp.example.com` | Primary production server |
| `sp-mcp-spsvr02` | `SPSVR02` | `spsvr02.corp.example.com` | On-site DR replica (replication target from SPSVR01) |
| `sp-mcp-spsvr03` | `SPSVR03` | `spsvr03.corp.example.com` | Remote archive server (replication target from SPSVR01 and SPSVR02) |

Each server has an independent MCP server process registered in the MCP client configuration with a dedicated SSH Ed25519 key, its own `.env`, and its own five tiered service accounts (`mcp-svc-system`, `mcp-svc-policy`, `mcp-svc-storage`, `mcp-svc-operator`, `mcp-svc-readonly`). See [configure-guide.md — Part 5](../guides/configure-guide.md) for the full per-process architecture.

### Replication Topology

```
SPSVR01 (primary)
 ├── Replicates all production nodes ──▶  SPSVR02 (on-site DR replica)   [REPL_RULE_PRIMARY_DR]
 └── Replicates DOM_DATABASE + DOM_SAP ──▶  SPSVR03 (remote archive)     [REPL_RULE_PRIMARY_ARCHIVE]

SPSVR02 (DR replica)
 └── Replicates DOM_DATABASE + DOM_SAP ──▶  SPSVR03 (remote archive)     [REPL_RULE_DR_ARCHIVE]
```

| Replication storage rule | Source server | Target server | Scope | Action type |
|---|---|---|---|---|
| `REPL_RULE_PRIMARY_DR` | SPSVR01 | SPSVR02 | All nodes (`REPLSTATE=ENABLED`) | `REPLICATE` |
| `REPL_RULE_PRIMARY_ARCHIVE` | SPSVR01 | SPSVR03 | DOM_DATABASE + DOM_SAP nodes | `REPLICATE` |
| `REPL_RULE_DR_ARCHIVE` | SPSVR02 | SPSVR03 | DOM_DATABASE + DOM_SAP nodes | `REPLICATE` |

### Additional Storage Pools on Replica Servers

| Pool name | Server | Type | Role |
|---|---|---|---|
| `POOL_DISK_REPLICA` | SPSVR02 | PRIMARY (container) | Replication target pool receiving from SPSVR01 |
| `POOL_DISK_ARCHIVE` | SPSVR03 | PRIMARY (container) | Archive replication target from SPSVR01 and SPSVR02 |
| `POOL_TAPE_ARCHIVE` | SPSVR03 | COPY | Long-term tape copy of archive data (LTO-8 library at remote site) |

---

## R-01 · Data Protection Operator

> Day-to-day operation and monitoring of the IBM Storage Protect environment: client deployment, backup policy, storage pools, scheduling, node lifecycle, and failure triage.

### Discovery & status

```text
What micro-MCP servers and tools are available in sp-mcp-server-remote-tumbleweed?
```

```text
List all IBM Storage Protect commands called by the tools in sp-mcp-server-remote-tumbleweed.
```

```text
On sp-mcp-server-remote-tumbleweed, run run_servermon and tell me how many threads are active, what the DB status is (almost full, fragmented, locked), and highlight any immediate risks.
```

```text
Show me all active client sessions on SPSVR01 right now — node name, session type, bytes sent, and start time.
```

```text
What is the current utilisation of all storage pools on SPSVR01? Flag any pool above 80% capacity — specifically check POOL_DISK_PRIMARY and POOL_CLOUD_TIER.
```

### Backup policy & scheduling

```text
Create a management class named MC_WEB_60 in policy domain DOM_GENERAL with a backup copy group that retains 5 versions and 60 days of data, sending data to POOL_DISK_PRIMARY. Show me the DEFINE MGMTCLASS and DEFINE COPYGROUP commands before executing them.
```

```text
Define a daily incremental backup schedule named SCHED_WEB_DAILY in policy domain DOM_GENERAL, starting at 22:30 with a one-hour duration window, and associate it with nodes WEB01_NODE and WEB02_NODE.
```

```text
What backup schedules are currently defined for policy domain DOM_DATABASE? Show the schedule name, type, start time, and last result for each.
```

```text
Node DBSQL01_NODE missed its last three runs of SCHED_DB_NIGHTLY. Pull the activity log for that node over the last 72 hours, narrow to ±60 minutes around each missed window, and categorise the likely root cause for each miss.
```

### Storage pool configuration

```text
Create a PRIMARY container storage pool named POOL_DISK_EXT01 using DCLASS_DISK with deduplication enabled and a description of "Extended primary deduplicated disk pool". Show me the DEFINE STGPOOL command before executing.
```

```text
What are the steps to tier data from POOL_DISK_PRIMARY to POOL_CLOUD_TIER on SPSVR01? Walk me through the migration policy configuration and MOVE DATA trigger settings.
```

```text
POOL_DISK_PRIMARY is at 83% utilisation on SPSVR01. Add a new storage pool directory /tsm/containers/ext02 to the pool using DEFINE STGPOOL DIRECTORY. What post-definition checks should I run to confirm the directory is active?
```

### Node lifecycle

```text
Register a new client node named APPSVR02_NODE in policy domain DOM_GENERAL on SPSVR01. Show the REGISTER NODE command.
```

```text
Lock node LEGACY01_NODE immediately — it has been decommissioned. Confirm the node is locked and no active sessions remain on SPSVR01.
```

```text
Rename node APPSVR01_NODE to APPSVR01_RHEL9. What IBM Storage Protect commands are required, and are there any schedule associations under DOM_GENERAL or SCHED_GENERAL_DAILY that I need to update?
```

### Backup & restore operations

```text
Show me all failed backup operations on SPSVR01 from the last 24 hours. For each failure include the node name, schedule name, return code, and a one-line description of the likely cause based on the ANS error code.
```

```text
Run a server-side database backup on SPSVR01 to POOL_DBBACKUP using SCHED_DBBACKUP_DAILY and confirm it completed successfully using query_volume_history with TYPE=DBBACKUP.
```

---

## R-02 · Data Protection Administrator

> Advanced administration: performance tuning, capacity expansion, anti-pattern audits, database diagnostics, tape library management, VTL integration, and NDMP NAS backup.

### Performance tuning

```text
On sp-mcp-server-remote-tumbleweed, migration from POOL_DISK_PRIMARY to POOL_CLOUD_TIER is completing below 200 MB/s. Retrieve the current TXNGROUPMAX, MOVEBATCHSIZE, RESOURCEUTILIZATION, and MAXSESSIONS settings using query_server_option. Compare against IBM recommended values for a deduplicated disk-to-cloud migration path and suggest specific tuning changes with justification.
```

```text
I am seeing high CPU on SPSVR01 during the 22:00–01:00 backup window when SCHED_GENERAL_DAILY and SCHED_DB_NIGHTLY overlap. Analyse current active session counts using query_active_session and MAXSESSIONS from query_server_option. Recommend MAXSESSIONS and RESOURCEUTILIZATION changes to reduce CPU contention without degrading throughput.
```

```text
What is the current TXNGROUPMAX value on SPSVR01, and what impact does increasing it to 4096 have on deduplicated backup performance to POOL_DISK_PRIMARY versus memory consumption?
```

### Capacity expansion

```text
POOL_DISK_PRIMARY is at 91% utilisation on SPSVR01. Add two new volumes — /data/tsm/vol003 and /data/tsm/vol004 — using DEFINE VOLUME and confirm the pool utilisation drops below 80% after expansion.
```

```text
Add a new storage pool directory /tsm/containers/ext01 to POOL_DISK_PRIMARY on SPSVR01 using DEFINE STGPOOL DIRECTORY. What post-definition checks should I run to confirm the directory is active and deduplication is enabled?
```

### Operational anti-pattern audit

```text
Audit SPSVR01 for operational anti-patterns. Check: (1) when SCHED_DBBACKUP_DAILY last ran successfully, (2) schedule miss rate for SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY over the last 7 days, (3) activity log utilisation, and (4) nodes with no backup activity in 30 days — starting with LEGACY01_NODE. Present findings as a table with severity ratings.
```

```text
Identify all nodes across DOM_GENERAL and DOM_DATABASE on SPSVR01 that have not completed a successful backup in the last 30 days. For each, show the node name, policy domain, last access date from query_client, and recommended remediation action.
```

### Database diagnostics

```text
The SPSVR01 active log is reported at 78% utilisation. Retrieve the current log space allocation using query_recovery_log and retrieve active log-related server options using query_server_option. Identify how close the server is to the threshold and what manual steps are needed outside the MCP server to extend capacity.
```

```text
Run a full database diagnostic check on SPSVR01: retrieve DB and log space using query_recovery_log and query_server_option. Report log pool percentage used, archive log directory status, and flag any values that exceed IBM-recommended thresholds for an 8.1.22 server protecting 45 registered nodes.
```

### Tape library management

```text
Define a tape library named LIB_LTO8_02 of type SCSI with device /dev/sg4 on SPSVR01, then define drives DRIVE_LTO8_05 and DRIVE_LTO8_06 in that library. Show the complete DEFINE LIBRARY and DEFINE DRIVE commands before executing.
```

```text
Walk me through the complete IBM Storage Protect configuration on SPSVR01 to add a new LTO-8 drive DRIVE_LTO8_04 to existing library LIB_LTO8_01: DEFINE DRIVE, DEFINE PATH, and the verification steps to confirm the drive is online and usable by POOL_TAPE_COPY.
```

### VTL & NDMP

```text
I am integrating an IBM ProtecTIER VTL as an additional copy target on SPSVR01. What DEFINE LIBRARY, DEFINE DRIVE, and DEFINE DEVCLASS commands do I need, and what VTL-specific parameters differ from the physical LIB_LTO8_01 configuration already in place?
```

```text
Configure NDMP backup for the NetApp NAS filer on NASSVR01_NODE: update the datamover NAS_MOVER_01 configuration if needed, confirm the filespace definition, and explain the NDMP topology SPSVR01 uses to move data into POOL_DISK_PRIMARY.
```

---

## R-03 · Infrastructure Solution Architect

> Environment sizing, solution architecture, server deployment, upgrade planning, cloud tiering strategy, licensing, and TCO optimisation. Operates at Day-0 design through Day-2 cost review.

### Environment sizing & architecture

```text
The SPSVR01 environment currently protects 45 nodes and 28 TB of front-end data. We are planning to add 80 database nodes over the next 12 months, growing front-end data to 120 TB. What CPU, RAM, database size, and network bandwidth changes should I plan for? Use IBM Blueprint guidelines and show the sizing rationale.
```

```text
Compare single-server (like current SPSVR01), scale-out, and container-based IBM Storage Protect deployment topologies for the planned 125-node environment. For each topology list the pros, cons, and recommended use case given our mix of Oracle, SQL Server, SAP HANA, and VMware workloads.
```

```text
What are the IBM Storage Protect Blueprint recommendations for database sizing when protecting 120 TB of front-end data with deduplication enabled across POOL_DISK_PRIMARY and POOL_CLOUD_TIER?
```

### Server installation & upgrade

```text
Walk me through the pre-installation checklist for a second IBM Storage Protect server on Red Hat Enterprise Linux 9 to be named SPSVR02: kernel parameters, filesystem layout, user and group setup, and ulimit settings aligned to our existing SPSVR01 configuration.
```

```text
SPSVR01 is currently on version 8.1.17 and needs to be upgraded to 8.1.22 to match target. What is the supported upgrade path, what pre-upgrade checks must I run, and in what order should server and client upgrades be sequenced to minimise risk to SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY?
```

```text
What pre-upgrade checks should I run on sp-mcp-server-remote-tumbleweed before applying the next fix pack? Retrieve current server version via query_server_status, active log utilisation via query_recovery_log, active sessions via query_active_session, and any in-progress migration or maintenance jobs via query_background_job.
```

### Cloud tiering strategy

```text
Design a cloud tiering strategy for SPSVR01 to extend POOL_DISK_PRIMARY to POOL_CLOUD_TIER using IBM Cloud Object Storage at cos.us-south.example.com. Include the DEFINE DEVCLASS for DCLASS_COS, DEFINE STGPOOL for POOL_CLOUD_TIER, and the migration threshold configuration. What credential configuration is required in the MCP server's connection store?
```

```text
I want to archive data from POOL_TAPE_COPY to a deep archive cloud tier backed by S3 Glacier Deep Archive as a third copy for DOM_DATABASE nodes. What IBM Storage Protect DEFINE DEVCLASS parameters, DEFINE COPYGROUP settings, and migration thresholds should I configure? Show a worked example aligned to MC_DB_90.
```

```text
What are the complete steps to tier data from POOL_DISK_PRIMARY to POOL_CLOUD_TIER on SPSVR01? Show the MOVE DATA trigger configuration and the storage rule that automates migration when POOL_DISK_PRIMARY exceeds 80%.
```

### Copy strategy & gap analysis

```text
I need to implement a 3-2-1-1-0 copy strategy for DOM_DATABASE nodes on SPSVR01. Map each copy to an existing storage pool (POOL_DISK_PRIMARY, POOL_DISK_COPY, POOL_TAPE_COPY, POOL_CLOUD_TIER), define any missing copy groups in MC_DB_90, and identify any gaps in the current configuration.
```

```text
Audit the copy group configuration for all policy domains on sp-mcp-server-remote-tumbleweed against a 3-2-1 strategy. List each domain, its active copy groups, destination pool types, and any domains where fewer than two distinct physical copy destinations exist.
```

### Licensing & TCO

```text
SPSVR01 currently protects 28 TB front-end data across 45 nodes including Oracle, SQL Server, SAP HANA, and VMware workloads. Explain the difference between front-end TB and processor-based IBM Storage Protect licensing for this workload mix. Which model is likely more cost-effective as we grow to 120 TB?
```

```text
Prepare a licence consumption audit for sp-mcp-server-remote-tumbleweed: retrieve total protected front-end capacity using query_occupancy, number of licensed nodes using query_client, and licence status using query_license_info. Identify any compliance gaps.
```

```text
I am presenting a TCO optimisation analysis for SPSVR01. Retrieve current storage pool utilisation across POOL_DISK_PRIMARY and POOL_CLOUD_TIER, deduplication ratios using query_deduplication_stats, and active node count using query_client. Identify the top three cost optimisation levers across storage capacity, licensing, and cloud egress.
```

---

## R-04 · Workload & Application Owner

> Application-specific backup integration for databases, virtualised workloads, and NDMP NAS. Collaborates with R-01 and R-02 to integrate a specific workload into the backup environment.

### Database backup integration

```text
I am the DBA responsible for Oracle 19c on DBORA01_NODE. What IBM Storage Protect agent or API method should I use for application-consistent Oracle backup via RMAN backint, what IBM Storage Protect parameters control the backup channel count, and how should the node be bound to MC_DB_90 in DOM_DATABASE?
```

```text
Configure IBM Storage Protect backup for SQL Server 2022 on DBSQL01_NODE using the VSS agent. What DEFINE SCHEDULE parameters should I set under SCHED_DB_NIGHTLY for a daily full plus transaction log backup chain, and what server-side policy settings in MC_DB_90 govern retention?
```

```text
I need to protect the Db2 11.5 database on DBDB201_NODE using IBM Storage Protect API-based backup. Walk me through the Db2 BACKUP DATABASE command syntax using the IBM Storage Protect API, and what server-side policy parameters in DOM_DATABASE govern retention of these backup objects?
```

```text
What is the IBM Storage Protect configuration for SAP HANA backint integration on SAPHANA01_NODE? Show the relevant parameters in the hdbbackint profile and how they map to MC_SAP_FULL and MC_SAP_LOG in DOM_SAP.
```

### SAP & ERP backup

```text
Walk me through the IBM Storage Protect BRTOOLS/backint configuration for SAP S/4HANA on SAPABAP01_NODE: the initSAPSID.utl parameter file, redo-log archiving bound to MC_SAP_LOG, and how to verify a successful BRBACKUP run is recorded against SPSVR01.
```

```text
What IBM Storage Protect management class and copy group settings are recommended for SAP redo-log archiving on SAPABAP01_NODE to meet a 15-minute RPO? Show the DEFINE COPYGROUP command for MC_SAP_LOG in DOM_SAP, specifying destination pool POOL_DISK_PRIMARY.
```

### Hypervisor VM backup

```text
VMPROXY01_NODE is the SPVE proxy for our VMware vSphere 8 environment protecting 120 VMs. What are the prerequisites for VADP-based backup, how do I enable changed block tracking (CBT) at scale, and what is the recommended policy difference between instant access restore and full VM restore under MC_VM_14?
```

```text
One of our VMware production VMs needs to be restored to its state at 2024-11-10 03:00 using IBM Storage Protect for Virtual Environments via VMPROXY01_NODE. Walk me through the server-side checks to confirm the backup exists and the conditions under which instant access restore is preferred over a full VM restore.
```

---

## R-05 · Security & Compliance Officer

> Security hardening, immutability and retention controls, verified recovery, configuration drift detection, and regulatory compliance mapping (NIST SP 800-53, EU DORA, BSI C5, ISO 27001).

### Security hardening

```text
Review the TLS/SSL configuration on sp-mcp-server-remote-tumbleweed: retrieve the current SSL-related server options using query_server_option. Identify which protocol versions and cipher suites are configured on SPSVR01, and flag any that deviate from IBM hardening guidance.
```

```text
Audit administrator account privilege classes on sp-mcp-server-remote-tumbleweed using query_admin_user. List each admin ID (ADMIN, mcp-svc-system, mcp-svc-operator, OPS_READER, DBA_ADMIN), its privilege class, last login date, and flag any accounts with more privileges than their stated role requires.
```

```text
What is the current node password expiry policy on SPSVR01? Retrieve password-related server options using query_server_option and recommend changes to enforce 90-day rotation with complexity requirements across all 45 registered nodes.
```

### WORM & immutable backup

```text
I need to configure WORM retention on POOL_TAPE_WORM for regulatory compliance. What DEFINE COPYGROUP RETMIN and RETMAX parameters should be set in MC_WORM_7YR under DOM_GENERAL's PSET_WORM policy set, and how do I verify that a volume in LIB_LTO8_01 is WORM-protected after data is written?
```

```text
Design an immutable backup configuration using IBM Cloud Object Storage object lock at cos.us-south.example.com as the WORM target in addition to POOL_TAPE_WORM. Compare hardware WORM tape versus object-lock cloud — list the trade-offs for each in terms of retention enforcement, tamper evidence, and audit trail suitability for a 7-year compliance hold.
```

```text
What is retset and how is it related to a retention pool in IBM Storage Protect? Show me an example of how to define a retention set for DOM_DATABASE nodes on SPSVR01, assign DBORA01_NODE data to it, and verify the retention hold is enforced using query_retention_set.
```

### Verified recovery

```text
Design a verified recovery test procedure for DOM_DATABASE on SPSVR01. Define pass/fail criteria, the server-side checks to run using query_scheduled_event for SCHED_DB_NIGHTLY and query_client_backup_volume for DBORA01_NODE, and a recommended test cadence aligned to a 4-hour RTO.
```

### Configuration drift detection

```text
Compare the current SPSVR01 configuration against our approved security baseline using sp-mcp-server-remote-tumbleweed. Check: SSL options via query_server_option, admin privilege classes for all five admin IDs via query_admin_user, node lock status for LEGACY01_NODE via query_client, and RETMIN/RETMAX values for MC_WORM_7YR via query_protection_policy. Present deviations as a table with severity ratings.
```

```text
Detect configuration drift in storage pool and policy definitions on SPSVR01: flag any pool missing a copy destination (check POOL_DISK_PRIMARY for a COPY pool link), any management class with RETONLY incorrectly set, and any schedule in DOM_DATABASE with no active node associations.
```

### Regulatory compliance mapping

```text
Map the current SPSVR01 configuration on sp-mcp-server-remote-tumbleweed to NIST SP 800-53 controls CP-9 (information system backup) and CP-10 (recovery and reconstitution). For each control, state: current configuration evidence drawn from query_protection_policy and query_volume_history, any gap, and a remediation recommendation.
```

```text
Produce an EU DORA resilience assessment for the SPSVR01 environment. Map current capabilities to Articles 9 (ICT risk management), 12 (backup policies), and 17 (ICT-related incident response). For Article 12, reference the active schedule set (SCHED_DB_NIGHTLY, SCHED_SAP_LOG_HOURLY) and copy group configuration (POOL_DISK_PRIMARY, POOL_TAPE_COPY, POOL_CLOUD_TIER). List the evidence artefacts needed and flag any gaps.
```

```text
Generate a BSI C5 and ISO 27001 compliance checklist for SPSVR01. Map OPS-09, OPS-10 (BSI C5) and A.12.3, A.12.4 (ISO 27001) to specific IBM Storage Protect configuration items — management classes, copy groups, WORM policy (MC_WORM_7YR, POOL_TAPE_WORM), and DB backup schedule (SCHED_DBBACKUP_DAILY). For each control, indicate whether it is met, partially met, or not met.
```

```text
Produce a security hardening gap analysis for sp-mcp-server-remote-tumbleweed: retrieve SSL options and admin account data via query_server_option and query_admin_user, node lock status for inactive nodes via query_client, and WORM retention settings for MC_WORM_7YR via query_protection_policy. Map each finding to its NIST SP 800-53 control and rate its severity.
```

---

## R-06 · Resilience Operations Manager

> Schedule compliance monitoring, application-aware backup scope, ITIL incident/problem/change management, disaster recovery execution, and ransomware incident response.

### Schedule compliance monitoring

```text
Show me the backup schedule compliance report for SPSVR01 over the last 7 days across all nodes: total scheduled events, completed, failed, missed, and percentage compliance per policy domain. Flag any domain below 95% compliance — specifically check DOM_DATABASE and DOM_SAP.
```

```text
Which nodes had missed events for SCHED_DB_NIGHTLY or SCHED_SAP_LOG_HOURLY in the last 48 hours? For each, show the node name, domain, scheduled time, and whether a subsequent retry succeeded.
```

### Application-aware backup scope

```text
Map the application inventory to IBM Storage Protect nodes on SPSVR01 to identify RPO gaps. Retrieve all nodes in DOM_DATABASE and DOM_SAP using query_client. Cross-reference with query_scheduled_event for SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY to highlight any node where the last successful backup event falls outside the required RPO of 4 hours.
```

```text
Identify all nodes in DOM_DATABASE on SPSVR01 — DBORA01_NODE, DBSQL01_NODE, DBDB201_NODE. For each, confirm whether the last scheduled event for SCHED_DB_NIGHTLY completed successfully within the defined schedule window using query_scheduled_event.
```

### ITIL incident triage

```text
SPSVR01 backup jobs have stopped completing since approximately 23:45. Run a structured P1 incident triage: check active sessions using query_active_session, DB and log space using query_recovery_log, missed schedule events for SCHED_DB_NIGHTLY in the last 2 hours using query_scheduled_event, and recent ANR-class errors using query_activity_log. Classify priority and list recommended diagnostic steps for IBM Support escalation.
```

```text
A P2 incident has been raised — DBSQL01_NODE has not completed SCHED_DB_NIGHTLY successfully in 18 hours. Run the diagnostic sequence: query node status via query_client, last backup result via query_scheduled_event, activity log errors (±60 minutes around the last scheduled 23:30 window) via query_activity_log, and open session state via query_active_session. Summarise findings and recommend the next escalation step.
```

### ITIL problem management

```text
DBORA01_NODE and DBDB201_NODE in DOM_DATABASE have each missed two consecutive SCHED_DB_NIGHTLY runs this week. Perform root cause analysis: retrieve schedule event history via query_scheduled_event, activity log errors per node via query_activity_log (±60 minutes around each miss), and POOL_DISK_PRIMARY utilisation via query_storage_container at the time of each failure. Produce a causal chain and recommend a permanent fix.
```

### ITIL change risk assessment

```text
I am planning to increase MAXSESSIONS from 25 to 40 on SPSVR01 during Saturday's maintenance window. Assess the change risk: retrieve current active session load using query_active_session, check for any in-progress migration jobs from POOL_DISK_PRIMARY to POOL_CLOUD_TIER using query_background_job, and confirm that SCHED_GENERAL_DAILY and SCHED_DB_NIGHTLY are not running. Provide a rollback procedure.
```

### Disaster recovery execution

```text
The SPSVR01 database needs to be recovered after a failure. Use the restore_db tool to initiate RESTORE DB. Before invoking it, confirm the last successful SCHED_DBBACKUP_DAILY run using query_volume_history with TYPE=DBBACKUP and verify no active sessions remain using query_active_session.
```

```text
After restoring the SPSVR01 database, what steps do I need to take to reconnect the 45 registered nodes — especially DOM_DATABASE nodes DBORA01_NODE, DBSQL01_NODE, and DBDB201_NODE — to the recovered server, or re-register them if node records were lost?
```

```text
The volume history file for SPSVR01 was not replicated to the DR site before the failure. Use query_dr_media and query_recovery_plan_file to assess what recovery information is available on sp-mcp-server-remote-tumbleweed, and summarise what data is at risk — particularly for POOL_TAPE_COPY volumes in LIB_LTO8_01.
```

### Ransomware & cyber incident response

```text
We suspect ransomware has encrypted data on DBSQL01_NODE since approximately 2024-11-12 14:00. Lock the node immediately using set_client_lock to prevent further backup activity. Then use query_client_backup_volume and query_data_occupancy for DBSQL01_NODE to identify the last successful backup versions that predate the infection window and quantify the data-at-risk period.
```

```text
A ransomware incident has been confirmed on DBSQL01_NODE. Use query_client_backup_volume to retrieve all backup versions from the last 14 days and identify the last backup set that predates the infection timestamp of 2024-11-12 14:00. Summarise which SQL Server databases can be recovered from POOL_DISK_PRIMARY and what data is at risk.
```

---

## R-07 · Storage Protect Service Engineer

> IBM field and remote service professional: deployment health assessment, Blueprint-based resizing, upgrade and fix-pack planning, performance and cost optimisation, security vulnerability analysis, and defect investigation using Servermon and IBM Support tooling.

### Deployment health assessment

```text
Perform a full deployment health assessment of sp-mcp-server-remote-tumbleweed (SPSVR01): retrieve server version via query_server_status, DB and log space via query_recovery_log and query_server_option, storage pool utilisation for POOL_DISK_PRIMARY and POOL_CLOUD_TIER via query_storage_container, schedule compliance for SCHED_DB_NIGHTLY over the last 7 days via query_scheduled_event, and last SCHED_DBBACKUP_DAILY run via query_volume_history. Present findings as a structured health report with red/amber/green status indicators.
```

```text
Run run_servermon on sp-mcp-server-remote-tumbleweed and analyse the Servermon output for SPSVR01. Identify customer-impacting issues, bottlenecks (DB utilisation, log space, session backlog), error spikes (ANR codes), and the most critical findings. Map each finding to a likely root cause and recommended resolution step.
```

```text
Compare the current SPSVR01 configuration against IBM Storage Protect Blueprint recommendations for a 45-node environment with 28 TB front-end data: DB sizing, log sizing, storage pool hierarchy (POOL_DISK_PRIMARY, POOL_TAPE_COPY, POOL_CLOUD_TIER), MAXSESSIONS, TXNGROUPMAX, and RESOURCEUTILIZATION. List each deviation with severity and the recommended corrective action.
```

### Upgrade & fix-pack planning

```text
SPSVR01 is on version 8.1.17 and the customer wants to upgrade to 8.1.22. Identify the supported upgrade path, list any interim fix packs required, and produce a pre-upgrade checklist covering: SCHED_DBBACKUP_DAILY recency via query_volume_history, active log space via query_recovery_log, active sessions via query_active_session, in-progress migration jobs via query_background_job, and BA client version compatibility for DBORA01_NODE and SAPHANA01_NODE.
```

```text
A fix pack addressing a known deduplication processing defect is available for SPSVR01. Before recommending application, retrieve server version via query_server_status, active log utilisation via query_recovery_log, active session count via query_active_session, and any in-progress reclamation or migration jobs from POOL_DISK_PRIMARY via query_background_job. Confirm safe conditions for the fix-pack window and produce a rollback procedure.
```

### Performance optimisation

```text
The customer reports that nightly backup throughput to POOL_DISK_PRIMARY dropped by 40% after DBDB201_NODE and SAPHANA01_NODE were added three weeks ago, pushing the total session count during SCHED_DB_NIGHTLY above 30. Retrieve current MAXSESSIONS, TXNGROUPMAX, and MOVEBATCHSIZE using query_server_option. Analyse the likely bottleneck and recommend specific tuning changes with expected throughput impact.
```

```text
Migration from POOL_DISK_PRIMARY to POOL_CLOUD_TIER at cos.us-south.example.com is completing at 150 MB/s but the customer's WAN link supports 800 MB/s. Retrieve the current POOL_CLOUD_TIER migration concurrency settings and MOVEBATCHSIZE from query_server_option. Identify the limiting parameter and recommend the change to better utilise available bandwidth.
```

### Security vulnerability analysis

```text
Analyse the security posture of sp-mcp-server-remote-tumbleweed (SPSVR01) for known IBM Storage Protect vulnerabilities: retrieve SSL-related server options using query_server_option and the status of all five admin accounts (ADMIN, mcp-svc-system, mcp-svc-operator, OPS_READER, DBA_ADMIN) using query_admin_user. Identify configuration values that deviate from IBM hardening guidance and flag each finding with its IBM Security Bulletin reference where applicable.
```

### Defect investigation & IBM Support tooling

```text
DBORA01_NODE and DBDB201_NODE are experiencing intermittent ANR0406E errors during SCHED_DB_NIGHTLY sessions. Use query_activity_log filtered to ANR0406E over the last 24 hours, identify the affected nodes and session IDs, correlate with active session counts from query_active_session and active log utilisation from query_recovery_log, and summarise the failure pattern to determine whether this matches a known deduplication or session-limit defect.
```

```text
Collect diagnostic data for an open IBM Support case on SPSVR01: retrieve server version via query_server_status, DB and log space via query_recovery_log and query_server_option, activity log errors from the last 48 hours filtered to ANR-class messages via query_activity_log, SCHED_DB_NIGHTLY miss events via query_scheduled_event, Servermon output via run_servermon, and POOL_DISK_PRIMARY utilisation via query_storage_container. Format the output as a structured case summary.
```

```text
Recurring ANR8468W warnings have been reported on SPSVR01 during POOL_DISK_PRIMARY to POOL_CLOUD_TIER migration windows. Use query_activity_log filtered to ANR8468W over the last 14 days to identify frequency and affected operations. Cross-reference with query_scheduled_event for SCHED_DB_NIGHTLY miss events and query_recovery_log for log utilisation trends at the time of each warning. Summarise the pattern and recommend the appropriate fix-pack or MOVEBATCHSIZE configuration change.
```

---

## Context-Optimised Investigation Blueprint

Unconstrained multi-schedule troubleshooting queries can exhaust context windows or hit API rate limits. Use the structured blueprint below for large-scale schedule failure analysis — shown here for the SPSVR01 environment.

### Problematic unconstrained prompt

> *"SPSVR01 had multiple backup failures last night. Identify all failed or missed backup schedules across DOM_GENERAL, DOM_DATABASE, and DOM_SAP in the last 24 hours. Categorise failures by root cause."*

### Refined context-preserving prompt

```text
You are assisting a Backup Engineer troubleshooting IBM Storage Protect server SPSVR01 via sp-mcp-server-remote-tumbleweed.

Goal:
Identify all failed or missed client backup schedule events across DOM_GENERAL, DOM_DATABASE, and DOM_SAP in the last 24 hours and categorise each by likely root cause.

Query Success Rules:
1. Prefer the most constrained query possible before expanding scope.
2. Never call query_scheduled_event without specifying a valid policy domain and exact schedule name.
3. Never call query_activity_log without both a specific search term and a narrow date/time window.
4. If a query fails, retry once with a simpler but still constrained parameter set.
5. If a query still fails, state the exact failed query pattern and move to the next best constrained query.

Required Execution Sequence:

Step 1 — Discover Valid Scope
- Use query_policy_group to confirm the three domains: DOM_GENERAL, DOM_DATABASE, DOM_SAP.
- Use query_schedule with domain_name and type="client" to list active schedules per domain:
  - DOM_GENERAL: SCHED_GENERAL_DAILY
  - DOM_DATABASE: SCHED_DB_NIGHTLY
  - DOM_SAP: SCHED_SAP_LOG_HOURLY, SCHED_SAP_FULL_WEEKLY
- Focus only on schedules whose scheduled start time falls within the last 24 hours.

Step 2 — Query Scheduled Events Using Narrow Scope
- Run query_scheduled_event for one domain and one schedule at a time.
- Use date filters in MM/DD/YYYY format.
- Do not issue broad, all-domain event queries.

Step 3 — Keep Only Abnormal Events
- Retain only events with status Failed, Missed, Incomplete, or abnormal non-success result codes.

Step 4 — Validate Each Abnormal Event With Targeted Log Search
- Use query_activity_log only for one failed event at a time.
- Search using the most specific discriminator: exact node name (e.g. DBSQL01_NODE), exact schedule name, or specific IBM message code.
- Always include a narrow time window around the event. Start with ±60 minutes; expand once to ±180 minutes if no evidence is found.
- Never run broad searches such as all ANR*, or unbounded 24-hour log scans.

Step 5 — Root Cause Classification
Classify each event as one of:
- Communication error
- Locked file / file in use
- Out of space / storage pool full (check POOL_DISK_PRIMARY utilisation via query_storage_container)
- Authentication / node locked / password issue (check node lock via query_client)
- Schedule window / timeout / missed window
- Other / unknown

Step 6 — If query_scheduled_event Fails
- Retry once with exact domain, exact schedule name, and date only (no time filters).
- If it still fails, continue schedule-by-schedule using query_schedule, query_client, and query_active_session.
- Mark findings as Likely instead of Confirmed.

Step 7 — If query_activity_log Fails
- Retry once with a single exact node name and a smaller time window.
- If it still fails, do not broaden the query.
- Use operational evidence from query_client and query_active_session.

Output Format:
- Executive Summary: total confirmed failed, missed, and likely abnormal events; count by root cause category; domains affected.
- Confirmed Failed or Missed Schedules Table: Node · Domain · Schedule · Scheduled Time · Status · Result Code · Root Cause · Evidence Summary · Recommended Action.
- Likely Failed or Abnormal Schedules Table: Node · Domain · Schedule · Scheduled Time · Why Flagged · Likely Root Cause · Recommended Validation Step.
- Top Recurring Failure Patterns.
- Environmental Risks (e.g. POOL_DISK_PRIMARY utilisation, active log space).
- Items Requiring Immediate Attention.
- Limitations.

Constraints:
- Limit analysis to the last 24 hours only.
- Query one schedule and one failed event at a time.
- Do not include raw log dumps unless a single short message is essential as evidence.
- Clearly distinguish Confirmed from Likely findings.
```

---

## R-08 · Multi-Server Replication & Data Management

> Cross-server replication topology management, DR readiness, archive data lifecycle across SPSVR01, SPSVR02, and SPSVR03, and multi-server backup compliance. Relevant to Data Protection Operators, Administrators, Resilience Operations Managers, Security & Compliance Officers, and Infrastructure Solution Architects working in an environment where multiple IBM SP servers replicate data between themselves.

All prompts in this section address the [Multi-Server Deployment Topology](#multi-server-deployment-topology) above. The MCP client has three registered MCP server processes — `sp-mcp-spsvr01`, `sp-mcp-spsvr02`, and `sp-mcp-spsvr03` — each independently connected to its respective SP server.

---

### Replication topology discovery

```text
Query the replication server definitions on sp-mcp-spsvr01 using query_replication_server and on sp-mcp-spsvr02 using query_replication_server. List each server's configured replication partners, their network addresses, and the SSL setting. Confirm that SPSVR02 is registered as a target on SPSVR01 and that SPSVR03 is registered as a target on both SPSVR01 and SPSVR02.
```

```text
On sp-mcp-spsvr01, retrieve all replication storage rules using query_replication_rule. List each rule name, action type, target server, and enabled status. Confirm that REPL_RULE_PRIMARY_DR and REPL_RULE_PRIMARY_ARCHIVE are active and their target servers match SPSVR02 and SPSVR03 respectively.
```

```text
On sp-mcp-spsvr02, retrieve the replication storage rule REPL_RULE_DR_ARCHIVE using query_replication_rule. Confirm the action type is REPLICATE, the target server is SPSVR03, and the rule is enabled. Then repeat the check on sp-mcp-spsvr03 using query_replication_server to verify SPSVR02 is a registered source.
```

```text
Give me a cross-server replication topology summary for the three-server environment. On sp-mcp-spsvr01, run query_replication_rule and query_replication_server. On sp-mcp-spsvr02, run query_replication_rule and query_replication_server. On sp-mcp-spsvr03, run query_replication_server. Summarise the full replication mesh — which server replicates what scope to which target — and flag any missing or disabled rules.
```

---

### Replication health monitoring & failure triage

```text
Check replication health across all three servers simultaneously. On sp-mcp-spsvr01, run query_protection_status and query_replication_failures. On sp-mcp-spsvr02, run query_protection_status and query_replication_failures. On sp-mcp-spsvr03, run query_protection_status and query_replication_failures. Summarise the protection status for each server, list all replication failures with node name, file space, and failure date, and rate overall replication health as green, amber, or red per server.
```

```text
On sp-mcp-spsvr01, DBORA01_NODE has not replicated to SPSVR02 in the last 6 hours. Use query_replication_status for DBORA01_NODE to check for an active replication process. Then use query_replication_failures on sp-mcp-spsvr01 to confirm whether a replication failure record exists. Cross-check POOL_DISK_PRIMARY utilisation on sp-mcp-spsvr01 using query_storage_container — a full source pool is the most common cause of stalled node replication.
```

```text
A replication failure alert has fired for SAPHANA01_NODE on SPSVR01. Run query_replication_failures on sp-mcp-spsvr01 to retrieve the failure record. Then query the activity log on sp-mcp-spsvr01 using query_activity_log filtered to SAPHANA01_NODE for a ±60-minute window around the reported failure time. Cross-check that SAPHANA01_NODE has REPLSTATE=ENABLED using query_replication_client with node_name=SAPHANA01_NODE.
```

```text
On sp-mcp-spsvr01, retrieve replication status for all DOM_DATABASE nodes — DBORA01_NODE, DBSQL01_NODE, DBDB201_NODE — using query_replication_client with node_name=* and filter results to those three nodes. For each node, show the target server, file spaces, and files sent/received. Flag any node where replication to SPSVR02 or SPSVR03 has not completed in the last 24 hours.
```

```text
Compare storage pool protection status between sp-mcp-spsvr01 and sp-mcp-spsvr02 using query_protection_status on each. Confirm that POOL_DISK_REPLICA on SPSVR02 is in sync with POOL_DISK_PRIMARY on SPSVR01. If protection status shows out-of-sync, retrieve the last replication failure records from query_replication_failures on sp-mcp-spsvr01 and recommend remediation steps.
```

---

### Node replication enablement & configuration

```text
On sp-mcp-spsvr01, check which production nodes do NOT have replication enabled. Use query_replication_client with node_name=* to list all nodes and their REPLSTATE. List any node with REPLSTATE=DISABLED or where the target server column is empty. For each, show the node name, policy domain, and recommended UPDATE NODE command to set REPLSTATE=ENABLED.
```

```text
A new node APPSVR10_NODE has been registered in DOM_GENERAL on SPSVR01. Enable replication for this node so it is covered by REPL_RULE_PRIMARY_DR. On sp-mcp-spsvr01, use update_node to set REPLSTATE=ENABLED for APPSVR10_NODE. Then confirm the node appears in query_replication_client output with the target server set to SPSVR02.
```

```text
On sp-mcp-spsvr01, a decision has been made to include VMPROXY01_NODE in the remote archive replication to SPSVR03 under REPL_RULE_PRIMARY_ARCHIVE. The rule currently covers only DOM_DATABASE and DOM_SAP nodes. What IBM Storage Protect commands are needed to add VMPROXY01_NODE to the replication scope without disrupting the existing REPL_RULE_PRIMARY_DR coverage to SPSVR02? Show the UPDATE NODE and any required UPDATE REPLRULE or DEFINE SUBRULE commands before executing.
```

```text
On sp-mcp-spsvr01, retrieve the current replication storage rules using query_storage_rule and query_replication_rule. I want to verify that REPL_RULE_PRIMARY_DR has ACTIONTYPE=REPLICATE and covers all nodes with REPLSTATE=ENABLED. Then on sp-mcp-spsvr02, run query_replication_client with node_name=* and confirm that all nodes present on SPSVR01 with REPLSTATE=ENABLED appear as replicated targets on SPSVR02.
```

---

### Cross-server backup data consistency checks

```text
Verify that the DOM_DATABASE node backup data on SPSVR02 is consistent with SPSVR01. On sp-mcp-spsvr01, use query_data_occupancy for DBORA01_NODE, DBSQL01_NODE, and DBDB201_NODE to get the total backup objects and physical bytes per node. On sp-mcp-spsvr02, run query_data_occupancy for the same three nodes. Compare the object counts and flag any node where the replica on SPSVR02 is more than 5% below the primary on SPSVR01.
```

```text
On sp-mcp-spsvr01, retrieve the backup file space list for SAPHANA01_NODE using query_client_backup_volume. On sp-mcp-spsvr02, run query_replication_client with node_name=SAPHANA01_NODE to confirm the same file spaces have been replicated. Report any file spaces present on SPSVR01 that are absent from the replication record on SPSVR02, with the last-modified date of each missing file space.
```

```text
Run a cross-server occupancy audit for all SAP nodes (SAPHANA01_NODE, SAPABAP01_NODE) across the three servers. On sp-mcp-spsvr01, run query_data_occupancy for both nodes. On sp-mcp-spsvr02, run query_data_occupancy for both nodes. On sp-mcp-spsvr03, run query_data_occupancy for both nodes. Present results in a side-by-side comparison table. Flag any server where the occupancy deviates by more than 10% from the primary, and identify whether the gap is in backup objects, archive objects, or both.
```

---

### Archive data lifecycle across servers

```text
On sp-mcp-spsvr03, I need to verify that the long-term archive objects for DOM_DATABASE nodes have replicated correctly from SPSVR01. Use query_data_occupancy on sp-mcp-spsvr03 for DBORA01_NODE and DBDB201_NODE. Compare the archive object counts against the archive copy group retention settings in MC_DB_90 on sp-mcp-spsvr01 using query_protection_policy. Flag any discrepancy that suggests archive objects were not replicated.
```

```text
On sp-mcp-spsvr03, query the storage pool POOL_DISK_ARCHIVE using query_storage_container. Report current utilisation, available capacity, and whether deduplication is active. If utilisation exceeds 75%, estimate how many additional archive objects the pool can absorb before migration to POOL_TAPE_ARCHIVE is required, based on the average object size derived from query_data_occupancy for DOM_DATABASE and DOM_SAP nodes.
```

```text
On sp-mcp-spsvr03, SAP archive log objects for SAPHANA01_NODE managed under MC_SAP_LOG are approaching the 90-day retention boundary. Use query_data_occupancy on sp-mcp-spsvr03 for SAPHANA01_NODE filtered to archive objects. Identify how many archive objects expire in the next 14 days, their collective size, and whether the automatic expiration process will free sufficient space in POOL_DISK_ARCHIVE before new archive replication from SPSVR01 arrives.
```

```text
I need to implement a policy on SPSVR03 to move aged archive data from POOL_DISK_ARCHIVE to POOL_TAPE_ARCHIVE after 180 days. On sp-mcp-spsvr03, retrieve the current storage rules using query_storage_rule to confirm no conflicting tiering rule exists. Then show me the DEFINE STGRULE command with ACTIONTYPE=TIEBYAGE and TIERDAYS=180 that migrates data from POOL_DISK_ARCHIVE to POOL_TAPE_ARCHIVE. Show the command before executing.
```

---

### Multi-server schedule compliance & RPO monitoring

```text
Produce a schedule compliance report across all three servers for the last 24 hours. On sp-mcp-spsvr01, query SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY using query_scheduled_event for DOM_DATABASE and DOM_SAP. On sp-mcp-spsvr02, verify that replication of the same nodes completed within 2 hours of each backup event using query_protection_status and query_replication_failures. On sp-mcp-spsvr03, run query_protection_status. Present a three-column compliance summary: backup status on SPSVR01, replication status to SPSVR02, and archive replication status to SPSVR03.
```

```text
We have an RPO target of 4 hours for DOM_DATABASE nodes across the three-server topology. On sp-mcp-spsvr01, retrieve the last successful backup event for DBORA01_NODE under SCHED_DB_NIGHTLY using query_scheduled_event. On sp-mcp-spsvr02, confirm the last successful replication of DBORA01_NODE using query_replication_client. On sp-mcp-spsvr03, confirm the same. Calculate the end-to-end data age — from last backup on SPSVR01 to last replica on SPSVR03 — and flag if the chain exceeds 4 hours.
```

```text
SAPHANA01_NODE on SPSVR01 has a 15-minute RPO for SAP HANA archive logs under SCHED_SAP_LOG_HOURLY. On sp-mcp-spsvr01, confirm the last five archive events completed within the schedule window using query_scheduled_event. On sp-mcp-spsvr02, run query_replication_client for SAPHANA01_NODE to confirm the archive file spaces are being replicated. Report whether the current replication lag between SPSVR01 and SPSVR02 for SAPHANA01_NODE could place the effective RPO above 15 minutes.
```

---

### Disaster recovery failover readiness

```text
Assess DR readiness for a failover from SPSVR01 to SPSVR02. On sp-mcp-spsvr02, run the following checks: (1) query_protection_status to confirm POOL_DISK_REPLICA is in sync; (2) query_replication_client with node_name=* to verify all production nodes have replicated; (3) query_server_status to confirm SPSVR02 is running and not degraded; (4) query_recovery_log to confirm DB and log space are healthy. Produce a DR readiness scorecard with red/amber/green status per check.
```

```text
A failover decision has been made — SPSVR01 is offline following a site incident. On sp-mcp-spsvr02, verify that DBORA01_NODE, DBSQL01_NODE, DBDB201_NODE, SAPHANA01_NODE, and SAPABAP01_NODE are all present and have valid backup data using query_client and query_data_occupancy for each node. Identify the most recent backup version available for each node from query_client_backup_volume. Summarise recovery point and any nodes where data coverage on SPSVR02 may result in data loss exceeding the 4-hour RTO.
```

```text
After a successful failover to SPSVR02, we need to re-register the three DOM_DATABASE nodes — DBORA01_NODE, DBSQL01_NODE, DBDB201_NODE — to point to SPSVR02 as their primary server. What IBM Storage Protect commands are required to update the node definitions, re-bind them to the correct policy domain DOM_DATABASE, and ensure SCHED_DB_NIGHTLY runs against SPSVR02? Show the full sequence of commands on sp-mcp-spsvr02 before executing anything.
```

```text
We want to test a planned DR drill from SPSVR01 to SPSVR02 this weekend. On sp-mcp-spsvr01, retrieve the current list of all nodes with REPLSTATE=ENABLED using query_replication_client. On sp-mcp-spsvr02, confirm each of those nodes has data present using query_data_occupancy. Identify any nodes that exist on SPSVR01 but are missing or have zero occupancy on SPSVR02 — these represent DR coverage gaps that must be resolved before the drill.
```

---

### Multi-server security & audit

```text
Audit the MCP service account configuration across all three servers to confirm consistent security posture. On sp-mcp-spsvr01, run query_admin_user for mcp-svc-system, mcp-svc-policy, mcp-svc-storage, mcp-svc-operator, mcp-svc-readonly. Repeat on sp-mcp-spsvr02 and sp-mcp-spsvr03. For each server, verify that all five accounts exist, have SESSIONSECURITY=Strict, and carry the correct privilege class. Report any account that is missing, incorrectly configured, or has not been used in 30 days.
```

```text
Retrieve the MCP audit trail from all three servers for write operations performed in the last 7 days. On sp-mcp-spsvr01, use query_activity_log with search term MCP_AUDIT and a 7-day window. Repeat on sp-mcp-spsvr02 and sp-mcp-spsvr03. Aggregate the results into a cross-server audit table showing the operation, tool, privilege class, correlation ID, server, and timestamp. Flag any write operations on SPSVR02 or SPSVR03 that do not have a corresponding originating operation on SPSVR01 — these may indicate out-of-band administrative changes.
```

```text
Map the multi-server IBM Storage Protect topology (SPSVR01, SPSVR02, SPSVR03) to NIST SP 800-53 CP-9 (information system backup) and CP-6 (alternate storage site). For CP-9, reference the backup schedules on SPSVR01 (SCHED_DB_NIGHTLY, SCHED_SAP_LOG_HOURLY) and query_protection_status on all three servers. For CP-6, reference the geographic separation between SPSVR01/SPSVR02 (on-site) and SPSVR03 (remote site). Identify any control gaps and list the evidence artefacts needed to satisfy an auditor.
```

```text
On sp-mcp-spsvr03, confirm that the long-term archive data for DOM_DATABASE nodes is protected from deletion for the required 7-year retention period. Retrieve the archive copy group settings for MC_DB_90 in DOM_DATABASE using query_protection_policy on sp-mcp-spsvr01. Then on sp-mcp-spsvr03, retrieve the replication rule REPL_RULE_PRIMARY_ARCHIVE using query_replication_rule to confirm archive objects are included in scope. Confirm whether POOL_TAPE_ARCHIVE has WORM volumes configured that would enforce immutability independent of the replication policy.
```

---

### Multi-server capacity planning & storage management

```text
Produce a cross-server storage capacity report for the three-server topology. On sp-mcp-spsvr01, retrieve utilisation for POOL_DISK_PRIMARY and POOL_CLOUD_TIER using query_storage_container. On sp-mcp-spsvr02, retrieve utilisation for POOL_DISK_REPLICA using query_storage_container. On sp-mcp-spsvr03, retrieve utilisation for POOL_DISK_ARCHIVE and POOL_TAPE_ARCHIVE using query_storage_container. Present a unified capacity dashboard — pool name, server, total capacity, used, available, utilisation % — and flag any pool above 80%.
```

```text
On sp-mcp-spsvr03, POOL_DISK_ARCHIVE is at 78% utilisation. We need to understand whether the growth rate from replication will push it above 90% within the next 30 days. Retrieve the current occupancy for DOM_DATABASE and DOM_SAP archive objects on sp-mcp-spsvr03 using query_data_occupancy. On sp-mcp-spsvr01, retrieve the archive schedule event history for SCHED_SAP_LOG_HOURLY and SCHED_DB_NIGHTLY over the last 7 days using query_scheduled_event to estimate the daily inflow. Project whether POOL_DISK_ARCHIVE will be exhausted within 30 days and recommend whether to add capacity or accelerate migration to POOL_TAPE_ARCHIVE.
```

```text
I need to add a new storage pool directory to POOL_DISK_REPLICA on SPSVR02 to accommodate growing replication inflow from SPSVR01 as we add more DOM_DATABASE nodes. On sp-mcp-spsvr02, retrieve the current POOL_DISK_REPLICA configuration using query_storage_container. Show me the DEFINE STGPOOL DIRECTORY command to add /tsm/replica/ext01 to POOL_DISK_REPLICA on SPSVR02. What post-definition checks should I run on sp-mcp-spsvr02 to confirm the directory is active before the next replication cycle?
```

---

### Multi-server replication rule management (operator / administrator)

```text
On sp-mcp-spsvr01, I need to temporarily suspend replication to SPSVR03 during a scheduled maintenance window on the remote archive site this Saturday 02:00–06:00. Retrieve REPL_RULE_PRIMARY_ARCHIVE using query_replication_rule to confirm its current enabled state. Show me the UPDATE REPLRULE command to disable it before the window and re-enable it after. Include the pre-window check to confirm no active replication is in progress using query_replication_status for DBORA01_NODE.
```

```text
A new policy domain DOM_COMPLIANCE has been created on SPSVR01 for regulated workloads that require replication to both SPSVR02 and SPSVR03. On sp-mcp-spsvr01, retrieve the existing replication storage rules using query_replication_rule to understand the current rule structure. Show me the DEFINE STGRULE commands to create two new replication storage rules — REPL_RULE_COMPLIANCE_DR targeting SPSVR02 and REPL_RULE_COMPLIANCE_ARCHIVE targeting SPSVR03 — both scoped to DOM_COMPLIANCE nodes. Confirm these do not conflict with the existing rule limit of two active target replication servers from a single source.
```

```text
On sp-mcp-spsvr01, retrieve all storage rules and replication rules using query_storage_rule and query_replication_rule. I need to verify that no replication storage rule has both SPSVR02 and SPSVR03 defined as the target in the same rule (IBM SP only supports one target server per replication storage rule). Flag any misconfiguration and show the corrective DEFINE STGRULE or UPDATE REPLRULE commands needed to separate them into independent rules.
```

---

### Context-optimised multi-server replication investigation blueprint

Replication health queries across multiple servers can exhaust context windows if run without scope constraints. Use the structured blueprint below when investigating a replication lag or failure across the three-server topology.

```text
You are assisting a Backup Engineer investigating an IBM Storage Protect replication health issue across a three-server topology: SPSVR01 (primary, sp-mcp-spsvr01), SPSVR02 (on-site DR replica, sp-mcp-spsvr02), SPSVR03 (remote archive, sp-mcp-spsvr03).

Goal:
Identify which nodes have failed or lagging replication on each replication leg (SPSVR01→SPSVR02, SPSVR01→SPSVR03, SPSVR02→SPSVR03), determine root cause for each failure, and classify the risk to DR and archive data coverage.

Query Success Rules:
1. Prefer the most constrained query possible before expanding scope.
2. Never run query_replication_client with node_name=* unless targeted per-server.
3. Never run query_activity_log without a specific node name and narrow time window (±60 minutes).
4. Address each MCP server separately and in order: SPSVR01, then SPSVR02, then SPSVR03.
5. If a query returns no match, retry once with a simpler parameter set before moving on.

Required Execution Sequence:

Step 1 — Source Server Health (sp-mcp-spsvr01)
- Run query_protection_status to get POOL_DISK_PRIMARY protection state.
- Run query_replication_failures to retrieve all failure records.
- Run query_replication_rule to confirm REPL_RULE_PRIMARY_DR and REPL_RULE_PRIMARY_ARCHIVE are active.
- Run query_storage_container for POOL_DISK_PRIMARY — a pool above 80% is a common replication stall cause.

Step 2 — DR Replica Health (sp-mcp-spsvr02)
- Run query_protection_status to confirm POOL_DISK_REPLICA is in sync.
- Run query_replication_failures to retrieve any inbound failure records.
- Run query_replication_rule to confirm REPL_RULE_DR_ARCHIVE is active.
- Run query_server_status to confirm SPSVR02 is operational.

Step 3 — Remote Archive Health (sp-mcp-spsvr03)
- Run query_protection_status to confirm POOL_DISK_ARCHIVE is in sync.
- Run query_replication_failures to retrieve any inbound failure records.
- Run query_storage_container for POOL_DISK_ARCHIVE — a full archive pool will reject new replication.

Step 4 — Per-Node Replication Validation (sp-mcp-spsvr01)
- For each node flagged in failure records from Steps 1–3, run query_replication_client with the specific node name.
- Confirm REPLSTATE=ENABLED and review the target server and files-sent count.
- For each failed node, run query_activity_log with a ±60-minute window around the failure timestamp.

Step 5 — Root Cause Classification
Classify each replication failure as one of:
- Source pool full (POOL_DISK_PRIMARY > 80%)
- Target pool full (POOL_DISK_REPLICA or POOL_DISK_ARCHIVE > 80%)
- Network / connectivity error between servers
- Node REPLSTATE=DISABLED
- Replication rule disabled or misconfigured
- Concurrent replication conflict (>2 active target servers from same source)
- Other / unknown

Step 6 — If query_replication_failures Returns No Results
- Treat absence of failure records as a potential false-negative.
- Run query_replication_client with node_name=* on sp-mcp-spsvr01 and manually inspect files-sent versus files-received for key nodes.
- Mark findings as Likely instead of Confirmed.

Output Format:
- Executive Summary: replication health status per server leg (green / amber / red); total failure records; nodes at risk.
- Replication Failure Table: Node · Source Server · Target Server · Failure Date · File Space · Root Cause · Recommended Action.
- Lagging Nodes Table: Node · Source Server · Target Server · Files Sent · Files Received · Estimated Lag · Risk to RPO.
- Pool Capacity Risk: server, pool, utilisation %, and whether the pool is a blocker.
- Immediate Actions Required.
- Limitations.

Constraints:
- Address one MCP server at a time.
- Do not run broad unbounded queries against all nodes simultaneously.
- Clearly distinguish Confirmed failures (from query_replication_failures) from Likely failures (inferred from query_replication_client).
```
