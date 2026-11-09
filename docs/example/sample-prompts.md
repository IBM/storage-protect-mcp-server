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

## Prompt Anatomy

Every prompt below is written in plain English and follows the same structure, so that the model has
the information it needs and the answer is predictable and reviewable. Copy the structure when
writing your own.

| Part | Introduced by | Purpose | Example |
|---|---|---|---|
| **Role** | `You are a ...` (opening sentence) | Persona and responsibility the model should adopt | `You are a Data Protection Operator ...` |
| **Context** | Opening paragraph, after the role | Environment, MCP server, and the situation that triggered the request | `SPSVR01 ... DBSQL01_NODE missed its last three runs ...` |
| **Task** | `Do the following:` | Numbered, single-purpose actions, naming the exact MCP tools where known | `1. Retrieve ... using query_activity_log.` |
| **Constraints** | `The following constraints apply:` | Scope limits, safety rules, and whether changes may be executed | `Read-only: run queries only ...` |
| **Output Format** | `Generate the output with the following format:` | Shape of the answer: table columns, ordered steps, or ratings | `Table with columns: node, schedule, return code.` |

Three constraint profiles are used throughout:

- **Read-only** — queries only; no configuration change is made.
- **Change with confirmation** — commands are shown first and executed only after approval.
- **Advisory** — guidance only; nothing is executed.

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
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am starting a shift and need an inventory of what this MCP server
exposes.

Do the following:
- List the micro-MCP servers and tools available in sp-mcp-server-remote-tumbleweed.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: micro-MCP server, tool name, one-line purpose.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am auditing which server-side operations the MCP tools can
trigger.

Do the following:
- List all IBM Storage Protect commands called by the tools in sp-mcp-server-remote-tumbleweed.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table mapping each tool to the Storage Protect commands it issues.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I need a quick health read of the server before the backup window
opens.

Do the following:
1. Run run_servermon on sp-mcp-server-remote-tumbleweed.
2. Report how many threads are active and the DB status (almost full, fragmented, locked).
3. Highlight any immediate risks.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Short summary with a Risks list ordered by severity.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I need a live view of client activity on SPSVR01.

Do the following:
- Show all active client sessions on SPSVR01 right now.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node name, session type, bytes sent, start time.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am checking storage headroom ahead of tonight's backups.

Do the following:
1. Report current utilisation of all storage pools on SPSVR01.
2. Flag any pool above 80% capacity, specifically POOL_DISK_PRIMARY and POOL_CLOUD_TIER.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: pool, type, utilisation %, status (OK or Above 80%).
```

### Backup policy & scheduling

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Web workloads in DOM_GENERAL need a 60-day retention class.

Do the following:
1. Create management class MC_WEB_60 in policy domain DOM_GENERAL.
2. Add a backup copy group that keeps 5 versions for 60 days and sends data to POOL_DISK_PRIMARY.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The DEFINE MGMTCLASS and DEFINE COPYGROUP commands, then the verification query results.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The web servers need a nightly incremental backup in DOM_GENERAL.

Do the following:
1. Define daily incremental schedule SCHED_WEB_DAILY in policy domain DOM_GENERAL.
2. Start it at 22:30 with a one-hour duration window.
3. Associate it with nodes WEB01_NODE and WEB02_NODE.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The commands to be run, then the schedule and association details after execution.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am reviewing the database backup schedules for DOM_DATABASE.

Do the following:
- List the backup schedules defined for policy domain DOM_DATABASE.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: schedule name, type, start time, last result.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. DBSQL01_NODE missed its last three runs of SCHED_DB_NIGHTLY (23:30
window).

Do the following:
1. Retrieve the activity log for DBSQL01_NODE for the last 72 hours.
2. Narrow the search to +/-60 minutes around each missed window.
3. Categorise the likely root cause of each miss.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.
- Use query_activity_log with an exact node name and a bounded time window only.

Generate the output with the following format:
Table with columns: missed window, evidence message, root-cause category, next action.
```

### Storage pool configuration

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. POOL_DISK_PRIMARY is nearly full and I need a second deduplicated
container pool.

Do the following:
1. Create PRIMARY container storage pool POOL_DISK_EXT01 on device class DCLASS_DISK.
2. Enable deduplication and set the description to "Extended primary deduplicated disk pool".

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The DEFINE STGPOOL command before execution, then the pool details after creation.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. We plan to tier cold data from POOL_DISK_PRIMARY to POOL_CLOUD_TIER
on SPSVR01.

Do the following:
1. Explain the steps to tier data from POOL_DISK_PRIMARY to POOL_CLOUD_TIER.
2. Cover the migration policy configuration and the MOVE DATA trigger settings.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Numbered procedure with the commands for each step.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. POOL_DISK_PRIMARY is at 83% utilisation on SPSVR01.

Do the following:
1. Add storage pool directory /tsm/containers/ext02 to the pool using DEFINE STGPOOL DIRECTORY.
2. List the post-definition checks that confirm the directory is active.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The command to run, then a checklist of verification queries with expected results.
```

### Node lifecycle

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A new application server must be onboarded to DOM_GENERAL.

Do the following:
- Register client node APPSVR02_NODE in policy domain DOM_GENERAL on SPSVR01.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The REGISTER NODE command before execution, then the node details after registration.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. LEGACY01_NODE has been decommissioned and must stop sending data.

Do the following:
1. Lock node LEGACY01_NODE immediately.
2. Confirm the node is locked and that no active sessions remain on SPSVR01.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Confirmation of lock state and the active-session check result.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. APPSVR01_NODE is being renamed as part of a RHEL 9 rebuild.

Do the following:
1. Rename node APPSVR01_NODE to APPSVR01_RHEL9.
2. List the Storage Protect commands required.
3. Identify schedule associations under DOM_GENERAL or SCHED_GENERAL_DAILY that need updating.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Ordered command list plus a table of associations to update.
```

### Backup & restore operations

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am preparing the morning failure report for SPSVR01.

Do the following:
1. List all failed backup operations from the last 24 hours.
2. Explain the likely cause of each failure from its ANS error code.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, schedule, return code, one-line likely cause.
```

```text
You are a Data Protection Operator responsible for the day-to-day operation, monitoring, and failure
triage of an IBM Storage Protect environment.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A manual database backup is needed outside the normal
SCHED_DBBACKUP_DAILY run.

Do the following:
1. Run a server-side database backup on SPSVR01 to POOL_DBBACKUP.
2. Confirm completion with query_volume_history using TYPE=DBBACKUP.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Backup command issued, completion status, and the volume history record as evidence.
```

---

## R-02 · Data Protection Administrator

> Advanced administration: performance tuning, capacity expansion, anti-pattern audits, database diagnostics, tape library management, VTL integration, and NDMP NAS backup.

### Performance tuning

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Migration from POOL_DISK_PRIMARY to POOL_CLOUD_TIER completes below
200 MB/s.

Do the following:
1. Retrieve TXNGROUPMAX, MOVEBATCHSIZE, RESOURCEUTILIZATION, and MAXSESSIONS using
   query_server_option.
2. Compare them with IBM recommended values for a deduplicated disk-to-cloud path.
3. Recommend specific tuning changes with justification.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Table with columns: option, current value, recommended value, justification.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 shows high CPU from 22:00 to 01:00 when SCHED_GENERAL_DAILY
and SCHED_DB_NIGHTLY overlap.

Do the following:
1. Analyse active session counts using query_active_session.
2. Read MAXSESSIONS from query_server_option.
3. Recommend MAXSESSIONS and RESOURCEUTILIZATION changes that reduce CPU contention without lowering
   throughput.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Findings, then a table of recommended changes with expected impact.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am considering raising TXNGROUPMAX on SPSVR01 to 4096.

Do the following:
1. Report the current TXNGROUPMAX value.
2. Explain the impact of 4096 on deduplicated backup performance to POOL_DISK_PRIMARY versus memory
   consumption.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Current value, trade-off table (benefit versus cost), and a go/no-go recommendation.
```

### Capacity expansion

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. POOL_DISK_PRIMARY is at 91% utilisation on SPSVR01.

Do the following:
1. Add volumes /data/tsm/vol003 and /data/tsm/vol004 using DEFINE VOLUME.
2. Confirm pool utilisation drops below 80% after the expansion.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Commands before execution, then before and after utilisation figures.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. POOL_DISK_PRIMARY needs more capacity through a container
directory.

Do the following:
1. Add storage pool directory /tsm/containers/ext01 to POOL_DISK_PRIMARY using DEFINE STGPOOL
   DIRECTORY.
2. List the post-definition checks that confirm the directory is active and deduplication is
   enabled.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The command, then a verification checklist with expected results.
```

### Operational anti-pattern audit

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am running a periodic operational health review of SPSVR01.

Do the following:
1. Check when SCHED_DBBACKUP_DAILY last ran successfully.
2. Calculate the miss rate for SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY over the last 7 days.
3. Check activity log utilisation.
4. List nodes with no backup activity in 30 days, starting with LEGACY01_NODE.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Findings table with columns: check, result, severity (High, Medium, Low), recommended action.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Stale nodes may be consuming licences and hiding protection gaps in
DOM_GENERAL and DOM_DATABASE.

Do the following:
1. Identify nodes in both domains with no successful backup in the last 30 days.
2. Use the last access date from query_client.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, policy domain, last access date, recommended remediation.
```

### Database diagnostics

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The SPSVR01 active log is reported at 78% utilisation.

Do the following:
1. Retrieve the log space allocation using query_recovery_log.
2. Retrieve active-log-related options using query_server_option.
3. State how close the server is to the threshold.
4. List the manual steps needed outside the MCP server to extend capacity.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Short status summary followed by a numbered list of manual steps.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 (v8.1.22) protects 45 registered nodes and I need a full
database diagnostic.

Do the following:
1. Retrieve DB and log space using query_recovery_log and query_server_option.
2. Report the log pool percentage used and the archive log directory status.
3. Flag any value that exceeds IBM-recommended thresholds.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: metric, value, IBM threshold, status.
```

### Tape library management

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A second tape library is being added to SPSVR01.

Do the following:
1. Define SCSI tape library LIB_LTO8_02 with device /dev/sg4.
2. Define drives DRIVE_LTO8_05 and DRIVE_LTO8_06 in that library.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The complete DEFINE LIBRARY and DEFINE DRIVE commands before execution.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A new LTO-8 drive DRIVE_LTO8_04 is being added to existing library
LIB_LTO8_01.

Do the following:
1. Walk through the configuration on SPSVR01: DEFINE DRIVE and DEFINE PATH.
2. Provide verification steps proving the drive is online and usable by POOL_TAPE_COPY.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Numbered procedure with commands and expected output for each verification step.
```

### VTL & NDMP

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. An IBM ProtecTIER VTL will become an additional copy target on
SPSVR01.

Do the following:
1. List the DEFINE LIBRARY, DEFINE DRIVE, and DEFINE DEVCLASS commands required.
2. Explain which VTL-specific parameters differ from physical library LIB_LTO8_01.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Comparison table (parameter, physical library, VTL) followed by the command list.
```

```text
You are a Data Protection Administrator responsible for advanced administration, tuning, capacity
expansion, and diagnostics of IBM Storage Protect servers.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The NetApp filer behind NASSVR01_NODE must be backed up with NDMP.

Do the following:
1. Update the NAS_MOVER_01 datamover configuration if needed.
2. Confirm the filespace definition.
3. Explain the NDMP topology SPSVR01 uses to move data into POOL_DISK_PRIMARY.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Configuration steps with commands, plus a short data-flow description.
```

---

## R-03 · Infrastructure Solution Architect

> Environment sizing, solution architecture, server deployment, upgrade planning, cloud tiering strategy, licensing, and TCO optimisation. Operates at Day-0 design through Day-2 cost review.

### Environment sizing & architecture

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 protects 45 nodes and 28 TB front-end data; we will add 80
database nodes in 12 months and reach 120 TB.

Do the following:
1. Determine the CPU, RAM, database size, and network bandwidth changes to plan for.
2. Base the sizing on IBM Blueprint guidelines.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Sizing table (resource, current, target, rationale) followed by assumptions.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The planned environment will protect 125 nodes with Oracle, SQL
Server, SAP HANA, and VMware workloads.

Do the following:
1. Compare single-server, scale-out, and container-based deployment topologies.
2. List pros, cons, and recommended use case for each.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Comparison table plus a one-paragraph recommendation.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. We will protect 120 TB of front-end data with deduplication across
POOL_DISK_PRIMARY and POOL_CLOUD_TIER.

Do the following:
- State the IBM Storage Protect Blueprint recommendations for database sizing.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Recommended DB size, active log and archive log sizes, and the calculation behind them.
```

### Server installation & upgrade

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A second server named SPSVR02 will be built on Red Hat Enterprise
Linux 9, aligned with SPSVR01.

Do the following:
1. Provide the pre-installation checklist.
2. Cover kernel parameters, filesystem layout, user and group setup, and ulimit settings.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Checklist table with columns: item, required value, how to verify.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 runs 8.1.17 and must reach 8.1.22.

Do the following:
1. Identify the supported upgrade path.
2. List the pre-upgrade checks to run.
3. Define the sequence of server and client upgrades that minimises risk to SCHED_DB_NIGHTLY and
   SCHED_SAP_LOG_HOURLY.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Ordered upgrade plan with checks, sequence, and rollback considerations.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A fix pack will be applied to SPSVR01.

Do the following:
1. Retrieve the server version using query_server_status.
2. Retrieve active log utilisation using query_recovery_log.
3. Retrieve active sessions using query_active_session.
4. Retrieve in-progress migration or maintenance jobs using query_background_job.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Pre-upgrade checklist with columns: check, result, pass or fail.
```

### Cloud tiering strategy

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 must extend POOL_DISK_PRIMARY into IBM Cloud Object Storage
at cos.us-south.example.com.

Do the following:
1. Design the cloud tiering strategy.
2. Include DEFINE DEVCLASS for DCLASS_COS, DEFINE STGPOOL for POOL_CLOUD_TIER, and the migration
   threshold configuration.
3. State the credential configuration required in the MCP server's connection store.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Design summary followed by the commands in execution order.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. DOM_DATABASE nodes need a third copy in a deep archive tier on S3
Glacier Deep Archive, sourced from POOL_TAPE_COPY.

Do the following:
1. Specify the DEFINE DEVCLASS parameters, DEFINE COPYGROUP settings, and migration thresholds.
2. Provide a worked example aligned to MC_DB_90.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Worked example with commands and a short explanation of each parameter.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Cold data on SPSVR01 should automatically move to the cloud tier.

Do the following:
1. Give the complete steps to tier data from POOL_DISK_PRIMARY to POOL_CLOUD_TIER.
2. Show the MOVE DATA trigger configuration.
3. Show the storage rule that automates migration when POOL_DISK_PRIMARY exceeds 80%.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Numbered procedure with commands.
```

### Copy strategy & gap analysis

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. DOM_DATABASE nodes on SPSVR01 require a 3-2-1-1-0 copy strategy.

Do the following:
1. Map each copy to an existing pool: POOL_DISK_PRIMARY, POOL_DISK_COPY, POOL_TAPE_COPY,
   POOL_CLOUD_TIER.
2. Define any missing copy groups in MC_DB_90.
3. Identify gaps in the current configuration.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Mapping table (copy, pool, media type, location) followed by a gap list.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am auditing copy groups against a 3-2-1 strategy.

Do the following:
1. Review all policy domains on sp-mcp-server-remote-tumbleweed.
2. List each domain's active copy groups and destination pool types.
3. Flag domains with fewer than two distinct physical copy destinations.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: domain, copy groups, destination pool types, 3-2-1 status.
```

### Licensing & TCO

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 protects 28 TB front-end data across 45 nodes (Oracle, SQL
Server, SAP HANA, VMware) and will grow to 120 TB.

Do the following:
1. Explain the difference between front-end TB and processor-based licensing.
2. State which model is likely more cost-effective at 120 TB.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Comparison table and a recommendation with the assumptions it depends on.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A licence consumption audit is due for
sp-mcp-server-remote-tumbleweed.

Do the following:
1. Retrieve total protected front-end capacity using query_occupancy.
2. Retrieve the number of licensed nodes using query_client.
3. Retrieve licence status using query_license_info.
4. Identify compliance gaps.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: metric, value, entitlement, gap.
```

```text
You are an Infrastructure Solution Architect responsible for sizing, designing, upgrading, and
costing IBM Storage Protect deployments.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am presenting a TCO optimisation analysis for SPSVR01.

Do the following:
1. Retrieve storage pool utilisation for POOL_DISK_PRIMARY and POOL_CLOUD_TIER.
2. Retrieve deduplication ratios using query_deduplication_stats.
3. Retrieve the active node count using query_client.
4. Identify the top three cost levers across storage capacity, licensing, and cloud egress.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Ranked list of three levers with evidence, estimated saving direction, and effort.
```

---

## R-04 · Workload & Application Owner

> Application-specific backup integration for databases, virtualised workloads, and NDMP NAS. Collaborates with R-01 and R-02 to integrate a specific workload into the backup environment.

### Database backup integration

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am the DBA for Oracle 19c on DBORA01_NODE, bound to policy domain
DOM_DATABASE.

Do the following:
1. Identify the agent or API method for application-consistent RMAN backint backup.
2. State which parameters control the backup channel count.
3. Explain how to bind the node to MC_DB_90.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Numbered setup guide with parameter names and sample values.
```

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SQL Server 2022 on DBSQL01_NODE must be protected with the VSS
agent.

Do the following:
1. Specify the DEFINE SCHEDULE parameters under SCHED_DB_NIGHTLY for a daily full plus transaction
   log backup chain.
2. Identify the server-side policy settings in MC_DB_90 that govern retention.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Parameter table (setting, value, purpose) plus a short note on the retention settings.
```

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The Db2 11.5 database on DBDB201_NODE must be protected with
API-based backup.

Do the following:
1. Show the Db2 BACKUP DATABASE syntax using the IBM Storage Protect API.
2. Identify the DOM_DATABASE policy parameters that govern retention of the backup objects.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Sample command with annotated options, then the retention parameters.
```

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SAP HANA 2.0 on SAPHANA01_NODE uses backint with domain DOM_SAP.

Do the following:
1. Show the relevant hdbbackint profile parameters.
2. Explain how they map to MC_SAP_FULL and MC_SAP_LOG.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Mapping table with columns: profile parameter, value, management class, effect.
```

### SAP & ERP backup

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SAP S/4HANA ABAP on SAPABAP01_NODE uses BRTOOLS with backint.

Do the following:
1. Explain the initSAPSID.utl parameter file.
2. Describe redo-log archiving bound to MC_SAP_LOG.
3. Explain how to verify that a BRBACKUP run is recorded against SPSVR01.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Numbered procedure with example parameter lines and a verification query.
```

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SAP redo-log archiving on SAPABAP01_NODE must meet a 15-minute RPO.

Do the following:
1. Recommend management class and copy group settings.
2. Show the DEFINE COPYGROUP command for MC_SAP_LOG in DOM_SAP with destination pool
   POOL_DISK_PRIMARY.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Recommended settings table and the command, shown but not executed.
```

### Hypervisor VM backup

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. VMPROXY01_NODE is the SPVE proxy for vSphere 8 and protects 120
VMs.

Do the following:
1. List the prerequisites for VADP-based backup.
2. Explain how to enable changed block tracking (CBT) at scale.
3. Compare instant access restore and full VM restore policy under MC_VM_14.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Prerequisite checklist, CBT steps, and a comparison table for the two restore types.
```

```text
You are a Workload and Application Owner (database, SAP, or virtualisation administrator)
integrating an application workload with IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A production VM must be restored to its 2024-11-10 03:00 state
using VMPROXY01_NODE.

Do the following:
1. Describe the server-side checks that confirm the backup exists.
2. Explain when instant access restore is preferred over a full VM restore.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Checks as a numbered list, then a decision table for the restore method.
```

---

## R-05 · Security & Compliance Officer

> Security hardening, immutability and retention controls, verified recovery, configuration drift detection, and regulatory compliance mapping (NIST SP 800-53, EU DORA, BSI C5, ISO 27001).

### Security hardening

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am reviewing transport security on SPSVR01.

Do the following:
1. Retrieve SSL-related server options using query_server_option.
2. Identify the configured protocol versions and cipher suites.
3. Flag deviations from IBM hardening guidance.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: option, value, guidance, status.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am performing a privileged-access review.

Do the following:
1. Audit administrator accounts using query_admin_user: ADMIN, mcp-svc-system, mcp-svc-operator,
   OPS_READER, DBA_ADMIN.
2. Report each account's privilege class and last login date.
3. Flag accounts holding more privilege than their stated role needs.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: admin ID, privilege class, last login, finding.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Policy requires 90-day password rotation with complexity across all
45 registered nodes.

Do the following:
1. Retrieve password-related server options using query_server_option.
2. Report the current node password expiry policy.
3. Recommend changes to enforce the policy.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Current versus required settings table and the recommended commands (not executed).
```

### WORM & immutable backup

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Regulation requires WORM retention on POOL_TAPE_WORM for 7 years.

Do the following:
1. Specify the DEFINE COPYGROUP RETMIN and RETMAX values for MC_WORM_7YR in PSET_WORM of
   DOM_GENERAL.
2. Explain how to verify that a volume in LIB_LTO8_01 is WORM-protected after data is written.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Recommended parameter values and a verification procedure.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. We need an immutable backup target in addition to POOL_TAPE_WORM
for a 7-year hold.

Do the following:
1. Design an immutable configuration using IBM Cloud Object Storage object lock at
   cos.us-south.example.com.
2. Compare hardware WORM tape with object-lock cloud on retention enforcement, tamper evidence, and
   audit trail suitability.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Comparison table followed by a recommended design.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Retention sets are being considered for DOM_DATABASE on SPSVR01.

Do the following:
1. Explain what a retention set is and how it relates to a retention pool.
2. Show how to define a retention set for DOM_DATABASE nodes and assign DBORA01_NODE data.
3. Show how to verify enforcement using query_retention_set.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Concept summary, then an example command sequence with expected verification output.
```

### Verified recovery

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. We must prove DOM_DATABASE can be recovered within a 4-hour RTO.

Do the following:
1. Design a verified recovery test procedure.
2. Define pass and fail criteria.
3. Specify server-side checks using query_scheduled_event for SCHED_DB_NIGHTLY and
   query_client_backup_volume for DBORA01_NODE.
4. Recommend a test cadence.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Test plan with columns: step, check, pass criterion, fail criterion.
```

### Configuration drift detection

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am checking SPSVR01 against the approved security baseline.

Do the following:
1. Check SSL options via query_server_option.
2. Check privilege classes for all five admin IDs via query_admin_user.
3. Check node lock status for LEGACY01_NODE via query_client.
4. Check RETMIN and RETMAX for MC_WORM_7YR via query_protection_policy.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Deviation table with columns: item, expected, actual, severity (High, Medium, Low).
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am detecting drift in storage pool and policy definitions on
SPSVR01.

Do the following:
1. Flag pools missing a copy destination, starting with POOL_DISK_PRIMARY.
2. Flag management classes with RETONLY incorrectly set.
3. Flag schedules in DOM_DATABASE with no active node associations.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: object, issue, expected, actual, recommended fix.
```

### Regulatory compliance mapping

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. An audit requires mapping SPSVR01 to NIST SP 800-53 CP-9 and CP-10.

Do the following:
1. Gather evidence from query_protection_policy and query_volume_history.
2. For each control, state the evidence, any gap, and a remediation recommendation.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: control, evidence, gap, remediation.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. An EU DORA resilience assessment is due for the SPSVR01
environment.

Do the following:
1. Map capabilities to Articles 9, 12, and 17.
2. For Article 12, cite SCHED_DB_NIGHTLY, SCHED_SAP_LOG_HOURLY, and the copy groups on
   POOL_DISK_PRIMARY, POOL_TAPE_COPY, POOL_CLOUD_TIER.
3. List the evidence artefacts needed and flag gaps.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: article, capability, evidence artefact, gap.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A BSI C5 and ISO 27001 checklist is required for SPSVR01.

Do the following:
1. Map OPS-09 and OPS-10 (BSI C5) and A.12.3 and A.12.4 (ISO 27001) to configuration items.
2. Use management classes, copy groups, MC_WORM_7YR, POOL_TAPE_WORM, and SCHED_DBBACKUP_DAILY.
3. Rate each control as met, partially met, or not met.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Checklist table with columns: control, configuration item, status, note.
```

```text
You are a Security and Compliance Officer responsible for hardening, immutability, recovery
verification, and regulatory mapping of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I need a security hardening gap analysis of SPSVR01.

Do the following:
1. Retrieve SSL options and admin account data via query_server_option and query_admin_user.
2. Retrieve lock status of inactive nodes via query_client.
3. Retrieve WORM retention for MC_WORM_7YR via query_protection_policy.
4. Map each finding to its NIST SP 800-53 control.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: finding, NIST control, severity, recommended action.
```

---

## R-06 · Resilience Operations Manager

> Schedule compliance monitoring, application-aware backup scope, ITIL incident/problem/change management, disaster recovery execution, and ransomware incident response.

### Schedule compliance monitoring

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am preparing the weekly compliance report for SPSVR01 (last 7
days, all nodes).

Do the following:
1. Report total scheduled events, completed, failed, missed, and percentage compliance per policy
   domain.
2. Flag any domain below 95%, specifically DOM_DATABASE and DOM_SAP.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: domain, scheduled, completed, failed, missed, compliance %, flag.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Nightly database and SAP log schedules are under review.

Do the following:
1. List nodes with missed events for SCHED_DB_NIGHTLY or SCHED_SAP_LOG_HOURLY in the last 48 hours.
2. Show whether a subsequent retry succeeded.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, domain, scheduled time, retry result.
```

### Application-aware backup scope

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A 4-hour RPO applies to DOM_DATABASE and DOM_SAP on SPSVR01.

Do the following:
1. Retrieve all nodes in both domains using query_client.
2. Cross-reference with query_scheduled_event for SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY.
3. Highlight nodes whose last successful backup falls outside the RPO.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, application, last success, age, RPO status.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I need to confirm database coverage on SPSVR01.

Do the following:
1. Check DBORA01_NODE, DBSQL01_NODE, and DBDB201_NODE.
2. Confirm the last SCHED_DB_NIGHTLY event completed within its schedule window using
   query_scheduled_event.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, last event time, status, within window (Yes or No).
```

### ITIL incident triage

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 backup jobs stopped completing at about 23:45. Treat this
as a P1 incident.

Do the following:
1. Check active sessions via query_active_session.
2. Check DB and log space via query_recovery_log.
3. Check missed SCHED_DB_NIGHTLY events in the last 2 hours via query_scheduled_event.
4. Check recent ANR-class errors via query_activity_log.
5. Classify priority and list the diagnostic steps for IBM Support escalation.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.
- Bound every activity log query with a specific search term and a narrow time window.

Generate the output with the following format:
Incident summary, priority, findings table, and a numbered escalation checklist.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A P2 incident is open: DBSQL01_NODE has not completed
SCHED_DB_NIGHTLY in 18 hours.

Do the following:
1. Check node status via query_client.
2. Check the last backup result via query_scheduled_event.
3. Check activity log errors +/-60 minutes around the 23:30 window via query_activity_log.
4. Check open session state via query_active_session.
5. Summarise findings and recommend the next escalation step.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Findings summary and a single recommended next step with rationale.
```

### ITIL problem management

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. DBORA01_NODE and DBDB201_NODE each missed two consecutive
SCHED_DB_NIGHTLY runs this week.

Do the following:
1. Retrieve schedule event history via query_scheduled_event.
2. Retrieve activity log errors per node via query_activity_log, +/-60 minutes around each miss.
3. Retrieve POOL_DISK_PRIMARY utilisation via query_storage_container at each failure time.
4. Build a causal chain and recommend a permanent fix.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Causal chain, evidence table per miss, and a permanent-fix recommendation.
```

### ITIL change risk assessment

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I plan to raise MAXSESSIONS from 25 to 40 on SPSVR01 during
Saturday's maintenance window.

Do the following:
1. Retrieve the active session load via query_active_session.
2. Check for in-progress POOL_DISK_PRIMARY to POOL_CLOUD_TIER migration via query_background_job.
3. Confirm SCHED_GENERAL_DAILY and SCHED_DB_NIGHTLY are not running.
4. Provide a rollback procedure.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Risk rating (Low, Medium, High) with evidence, go/no-go, and rollback steps.
```

### Disaster recovery execution

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The SPSVR01 database must be recovered after a failure.

Do the following:
1. Confirm the last successful SCHED_DBBACKUP_DAILY run via query_volume_history with TYPE=DBBACKUP.
2. Verify no active sessions remain via query_active_session.
3. Then initiate RESTORE DB with the restore_db tool.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.
- Do not call restore_db until both pre-checks pass and I have confirmed.

Generate the output with the following format:
Pre-checks with results, then the restore command and its outcome.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The SPSVR01 database has been restored.

Do the following:
1. Describe the steps to reconnect the 45 registered nodes, especially DBORA01_NODE, DBSQL01_NODE,
   and DBDB201_NODE.
2. Explain how to re-register nodes if node records were lost.

The following constraints apply:
- Advisory: do not execute any change; ground guidance in IBM documentation and the sample topology.

Generate the output with the following format:
Ordered recovery procedure with a per-node verification check.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The volume history file for SPSVR01 was not replicated to the DR
site before the failure.

Do the following:
1. Use query_dr_media and query_recovery_plan_file to assess available recovery information.
2. Summarise what data is at risk, particularly POOL_TAPE_COPY volumes in LIB_LTO8_01.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table of available recovery artefacts, missing artefacts, and data-at-risk summary.
```

### Ransomware & cyber incident response

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Ransomware is suspected on DBSQL01_NODE since about 2024-11-12
14:00.

Do the following:
1. Lock the node immediately using set_client_lock.
2. Use query_client_backup_volume and query_data_occupancy to find the last successful backup
   versions before the infection window.
3. Quantify the data-at-risk period.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.
- Lock the node first; every later step is read-only.

Generate the output with the following format:
Lock confirmation, last clean backup version, and data-at-risk window in hours.
```

```text
You are a Resilience Operations Manager responsible for schedule compliance, ITIL incident, problem,
and change management, and disaster recovery of IBM Storage Protect.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Ransomware is confirmed on DBSQL01_NODE with an infection timestamp
of 2024-11-12 14:00.

Do the following:
1. Retrieve all backup versions from the last 14 days via query_client_backup_volume.
2. Identify the last backup set that predates the infection.
3. State which SQL Server databases are recoverable from POOL_DISK_PRIMARY and what is at risk.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: backup version, timestamp, predates infection (Yes or No), databases.
```

---

## R-07 · Storage Protect Service Engineer

> IBM field and remote service professional: deployment health assessment, Blueprint-based resizing, upgrade and fix-pack planning, performance and cost optimisation, security vulnerability analysis, and defect investigation using Servermon and IBM Support tooling.

### Deployment health assessment

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am performing a full deployment health assessment of SPSVR01.

Do the following:
1. Retrieve the server version via query_server_status.
2. Retrieve DB and log space via query_recovery_log and query_server_option.
3. Retrieve utilisation of POOL_DISK_PRIMARY and POOL_CLOUD_TIER via query_storage_container.
4. Retrieve 7-day schedule compliance for SCHED_DB_NIGHTLY via query_scheduled_event.
5. Retrieve the last SCHED_DBBACKUP_DAILY run via query_volume_history.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Health report with a red, amber, or green status per area and a prioritised action list.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I need a Servermon analysis of SPSVR01.

Do the following:
1. Run run_servermon on sp-mcp-server-remote-tumbleweed.
2. Identify customer-impacting issues, bottlenecks (DB, log space, session backlog), and ANR error
   spikes.
3. Map each finding to a likely root cause and recommended resolution.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: finding, impact, likely root cause, resolution, priority.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. SPSVR01 has 45 nodes and 28 TB front-end data and must be checked
against IBM Blueprint.

Do the following:
- Compare DB sizing, log sizing, pool hierarchy (POOL_DISK_PRIMARY, POOL_TAPE_COPY,
  POOL_CLOUD_TIER), MAXSESSIONS, TXNGROUPMAX, and RESOURCEUTILIZATION with the Blueprint.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: area, current, Blueprint, severity, corrective action.
```

### Upgrade & fix-pack planning

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. The customer wants to upgrade SPSVR01 from 8.1.17 to 8.1.22.

Do the following:
1. Identify the supported upgrade path and any interim fix packs.
2. Build a pre-upgrade checklist covering SCHED_DBBACKUP_DAILY recency, active log space, active
   sessions, in-progress migration jobs, and BA client compatibility for DBORA01_NODE and
   SAPHANA01_NODE.
3. Use query_volume_history, query_recovery_log, query_active_session, and query_background_job.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Upgrade path, then a checklist table with columns: check, result, pass or fail.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. A fix pack addressing a known deduplication processing defect is
available for SPSVR01.

Do the following:
1. Retrieve the server version, active log utilisation, active session count, and in-progress
   reclamation or migration jobs on POOL_DISK_PRIMARY.
2. Confirm safe conditions for the fix-pack window.
3. Produce a rollback procedure.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Safe-to-apply verdict with evidence, then a rollback procedure.
```

### Performance optimisation

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Nightly throughput to POOL_DISK_PRIMARY dropped 40% after
DBDB201_NODE and SAPHANA01_NODE were added three weeks ago; sessions in SCHED_DB_NIGHTLY now exceed
30.

Do the following:
1. Retrieve MAXSESSIONS, TXNGROUPMAX, and MOVEBATCHSIZE using query_server_option.
2. Identify the likely bottleneck.
3. Recommend tuning changes with expected throughput impact.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Bottleneck analysis and a table of recommended changes with expected impact.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Migration to POOL_CLOUD_TIER at cos.us-south.example.com runs at
150 MB/s but the WAN supports 800 MB/s.

Do the following:
1. Retrieve migration concurrency settings and MOVEBATCHSIZE via query_server_option.
2. Identify the limiting parameter.
3. Recommend a change that uses the available bandwidth.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Limiting parameter, recommended change, and expected throughput.
```

### Security vulnerability analysis

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. I am assessing known-vulnerability exposure of SPSVR01.

Do the following:
1. Retrieve SSL-related options via query_server_option.
2. Retrieve the status of ADMIN, mcp-svc-system, mcp-svc-operator, OPS_READER, and DBA_ADMIN via
   query_admin_user.
3. Flag deviations from IBM hardening guidance with the IBM Security Bulletin reference.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: finding, evidence, bulletin reference, severity, fix.
```

### Defect investigation & IBM Support tooling

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. DBORA01_NODE and DBDB201_NODE show intermittent ANR0406E errors
during SCHED_DB_NIGHTLY.

Do the following:
1. Filter query_activity_log to ANR0406E for the last 24 hours.
2. Correlate with query_active_session counts and query_recovery_log utilisation.
3. Decide whether the pattern matches a known deduplication or session-limit defect.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Failure pattern summary, correlation table, and a defect-match verdict.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. An IBM Support case is open for SPSVR01 and needs diagnostic data.

Do the following:
1. Collect the server version, DB and log space, and ANR-class errors for the last 48 hours.
2. Collect SCHED_DB_NIGHTLY miss events, run_servermon output, and POOL_DISK_PRIMARY utilisation.
3. Use query_server_status, query_recovery_log, query_server_option, query_activity_log,
   query_scheduled_event, and query_storage_container.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Structured case summary with one section per data item and a list of attachments.
```

```text
You are an IBM Storage Protect Service Engineer responsible for health assessment, upgrade planning,
performance tuning, and defect investigation.
IBM Storage Protect server SPSVR01 (v8.1.22, RHEL 9), reached through the MCP server
sp-mcp-server-remote-tumbleweed. Recurring ANR8468W warnings occur during POOL_DISK_PRIMARY to
POOL_CLOUD_TIER migration.

Do the following:
1. Filter query_activity_log to ANR8468W for the last 14 days.
2. Cross-reference SCHED_DB_NIGHTLY miss events and query_recovery_log trends.
3. Recommend the appropriate fix pack or MOVEBATCHSIZE change.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Frequency table, correlation findings, and one recommended fix with rationale.
```

---

## Context-Optimised Investigation Blueprint

Unconstrained multi-schedule troubleshooting queries can exhaust context windows or hit API rate limits. Use the structured blueprint below for large-scale schedule failure analysis — shown here for the SPSVR01 environment.

### Problematic unconstrained prompt

> *"SPSVR01 had multiple backup failures last night. Identify all failed or missed backup schedules across DOM_GENERAL, DOM_DATABASE, and DOM_SAP in the last 24 hours. Categorise failures by root cause."*

### Refined context-preserving prompt

```text
You are a Backup Engineer troubleshooting IBM Storage Protect backup schedule failures.
IBM Storage Protect server SPSVR01, reached through the MCP server
sp-mcp-server-remote-tumbleweed.

Do the following:
Identify all failed or missed client backup schedule events across DOM_GENERAL, DOM_DATABASE, and
DOM_SAP in the last 24 hours and categorise each by likely root cause.

Follow these query success rules:
1. Prefer the most constrained query possible before expanding scope.
2. Never call query_scheduled_event without specifying a valid policy domain and exact schedule
   name.
3. Never call query_activity_log without both a specific search term and a narrow date/time window.
4. If a query fails, retry once with a simpler but still constrained parameter set.
5. If a query still fails, state the exact failed query pattern and move to the next best
   constrained query.

Follow this execution sequence:

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
- Search using the most specific discriminator: exact node name (e.g. DBSQL01_NODE), exact schedule
  name, or specific IBM message code.
- Always include a narrow time window around the event. Start with ±60 minutes; expand once to ±180
  minutes if no evidence is found.
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
- If it still fails, continue schedule-by-schedule using query_schedule, query_client, and
  query_active_session.
- Mark findings as Likely instead of Confirmed.

Step 7 — If query_activity_log Fails
- Retry once with a single exact node name and a smaller time window.
- If it still fails, do not broaden the query.
- Use operational evidence from query_client and query_active_session.

Generate the output with the following format:
- Executive Summary: total confirmed failed, missed, and likely abnormal events; count by root cause
  category; domains affected.
- Confirmed Failed or Missed Schedules Table: Node · Domain · Schedule · Scheduled Time · Status ·
  Result Code · Root Cause · Evidence Summary · Recommended Action.
- Likely Failed or Abnormal Schedules Table: Node · Domain · Schedule · Scheduled Time · Why Flagged
  · Likely Root Cause · Recommended Validation Step.
- Top Recurring Failure Patterns.
- Environmental Risks (e.g. POOL_DISK_PRIMARY utilisation, active log space).
- Items Requiring Immediate Attention.
- Limitations.

The following constraints apply:
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
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am validating the
replication partner definitions on the primary and DR servers.

Do the following:
1. On sp-mcp-spsvr01 and sp-mcp-spsvr02, run query_replication_server.
2. List each server's replication partners, network addresses, and SSL setting.
3. Confirm SPSVR02 is a registered target on SPSVR01.
4. Confirm SPSVR03 is a registered target on both SPSVR01 and SPSVR02.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: server, partner, address, SSL, role (source or target), status.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am verifying the
replication rules on the primary server.

Do the following:
1. On sp-mcp-spsvr01, run query_replication_rule.
2. List each rule's name, action type, target server, and enabled status.
3. Confirm REPL_RULE_PRIMARY_DR targets SPSVR02 and REPL_RULE_PRIMARY_ARCHIVE targets SPSVR03, and
   that both are active.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: rule, action type, target, enabled, matches expected (Yes or No).
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am verifying the
DR-to-archive replication leg.

Do the following:
1. On sp-mcp-spsvr02, retrieve REPL_RULE_DR_ARCHIVE using query_replication_rule.
2. Confirm the action type is REPLICATE, the target is SPSVR03, and the rule is enabled.
3. On sp-mcp-spsvr03, run query_replication_server and verify SPSVR02 is a registered source.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Pass or fail per check, with the evidence value for each.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I need one summary of the
full replication mesh.

Do the following:
1. On sp-mcp-spsvr01 and sp-mcp-spsvr02, run query_replication_rule and query_replication_server.
2. On sp-mcp-spsvr03, run query_replication_server.
3. Summarise which server replicates what scope to which target.
4. Flag missing or disabled rules.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Mesh table with columns: source, target, scope, rule, status, followed by a findings list.
```

---

### Replication health monitoring & failure triage

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am checking replication
health across all three servers at once.

Do the following:
1. On each of sp-mcp-spsvr01, sp-mcp-spsvr02, and sp-mcp-spsvr03, run query_protection_status and
   query_replication_failures.
2. Summarise protection status per server.
3. List all failures with node name, file space, and failure date.
4. Rate replication health green, amber, or red per server.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Per-server health rating followed by a failure table.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). DBORA01_NODE has not
replicated from SPSVR01 to SPSVR02 in the last 6 hours.

Do the following:
1. On sp-mcp-spsvr01, run query_replication_status for DBORA01_NODE to check for an active
   replication process.
2. Run query_replication_failures to find a failure record.
3. Run query_storage_container for POOL_DISK_PRIMARY; a full source pool is the most common cause of
   stalled replication.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Likely cause with the supporting evidence and one recommended next step.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). A replication failure
alert fired for SAPHANA01_NODE on SPSVR01.

Do the following:
1. On sp-mcp-spsvr01, run query_replication_failures to retrieve the failure record.
2. Run query_activity_log for SAPHANA01_NODE for +/-60 minutes around the failure time.
3. Confirm REPLSTATE=ENABLED with query_replication_client and node_name=SAPHANA01_NODE.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Failure record, relevant log messages, REPLSTATE value, and a root-cause statement.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am checking DOM_DATABASE
replication status on the primary server.

Do the following:
1. On sp-mcp-spsvr01, run query_replication_client with node_name=* and keep DBORA01_NODE,
   DBSQL01_NODE, and DBDB201_NODE.
2. Show each node's target server, file spaces, and files sent and received.
3. Flag nodes whose replication to SPSVR02 or SPSVR03 has not completed in 24 hours.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, target, file spaces, files sent, files received, flag.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I need to confirm the
replica pool is in sync with the primary pool.

Do the following:
1. Run query_protection_status on sp-mcp-spsvr01 and sp-mcp-spsvr02.
2. Confirm POOL_DISK_REPLICA on SPSVR02 is in sync with POOL_DISK_PRIMARY on SPSVR01.
3. If out of sync, retrieve failure records via query_replication_failures on sp-mcp-spsvr01 and
   recommend remediation.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Sync status, failure evidence if any, and remediation steps.
```

---

### Node replication enablement & configuration

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am looking for
production nodes that are not covered by replication on SPSVR01.

Do the following:
1. On sp-mcp-spsvr01, run query_replication_client with node_name=*.
2. List nodes with REPLSTATE=DISABLED or an empty target server column.
3. Provide the UPDATE NODE command that sets REPLSTATE=ENABLED for each.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.
- Do not execute any UPDATE NODE command; list them only.

Generate the output with the following format:
Table with columns: node, policy domain, REPLSTATE, recommended UPDATE NODE command.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). New node APPSVR10_NODE was
registered in DOM_GENERAL on SPSVR01.

Do the following:
1. On sp-mcp-spsvr01, use update_node to set REPLSTATE=ENABLED so it falls under
   REPL_RULE_PRIMARY_DR.
2. Confirm it appears in query_replication_client output with SPSVR02 as target server.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
The command before execution, then the confirmation query result.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). VMPROXY01_NODE must join
the remote archive replication to SPSVR03 under REPL_RULE_PRIMARY_ARCHIVE, which currently covers
only DOM_DATABASE and DOM_SAP.

Do the following:
1. On sp-mcp-spsvr01, determine the commands needed to add VMPROXY01_NODE to the scope.
2. Preserve existing REPL_RULE_PRIMARY_DR coverage to SPSVR02.
3. Show the UPDATE NODE and any UPDATE REPLRULE or DEFINE SUBRULE commands.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Ordered command list with the purpose of each and a rollback command.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am verifying that
REPL_RULE_PRIMARY_DR covers every enabled node.

Do the following:
1. On sp-mcp-spsvr01, run query_storage_rule and query_replication_rule.
2. Confirm REPL_RULE_PRIMARY_DR has ACTIONTYPE=REPLICATE and covers all nodes with
   REPLSTATE=ENABLED.
3. On sp-mcp-spsvr02, run query_replication_client with node_name=* and confirm every enabled
   SPSVR01 node appears as a replicated target.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, enabled on SPSVR01, present on SPSVR02, status.
```

---

### Cross-server backup data consistency checks

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I need to verify that
DOM_DATABASE backup data on SPSVR02 matches SPSVR01.

Do the following:
1. On sp-mcp-spsvr01 and sp-mcp-spsvr02, run query_data_occupancy for DBORA01_NODE, DBSQL01_NODE,
   and DBDB201_NODE.
2. Compare backup object counts and physical bytes per node.
3. Flag nodes where SPSVR02 is more than 5% below SPSVR01.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, SPSVR01 objects, SPSVR02 objects, difference %, flag.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am checking file space
replication for SAPHANA01_NODE.

Do the following:
1. On sp-mcp-spsvr01, list backup file spaces using query_client_backup_volume.
2. On sp-mcp-spsvr02, run query_replication_client with node_name=SAPHANA01_NODE.
3. Report file spaces missing from the replica, with their last-modified dates.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: file space, on SPSVR01, replicated to SPSVR02, last modified.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am auditing SAP node
occupancy across all three servers.

Do the following:
1. On each of sp-mcp-spsvr01, sp-mcp-spsvr02, and sp-mcp-spsvr03, run query_data_occupancy for
   SAPHANA01_NODE and SAPABAP01_NODE.
2. Flag any server deviating by more than 10% from the primary.
3. State whether the gap is in backup objects, archive objects, or both.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Side-by-side table with columns: node, object type, SPSVR01, SPSVR02, SPSVR03, deviation %.
```

---

### Archive data lifecycle across servers

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). Long-term archive objects
for DOM_DATABASE should have replicated from SPSVR01 to SPSVR03.

Do the following:
1. On sp-mcp-spsvr03, run query_data_occupancy for DBORA01_NODE and DBDB201_NODE.
2. Compare archive object counts with the MC_DB_90 archive copy group retention on sp-mcp-spsvr01,
   using query_protection_policy.
3. Flag discrepancies suggesting archive objects were not replicated.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, archive objects on SPSVR03, expected, discrepancy.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). POOL_DISK_ARCHIVE on
SPSVR03 may be nearing capacity.

Do the following:
1. On sp-mcp-spsvr03, run query_storage_container for POOL_DISK_ARCHIVE.
2. Report utilisation, available capacity, and whether deduplication is active.
3. If utilisation exceeds 75%, estimate how many more archive objects fit before migration to
   POOL_TAPE_ARCHIVE, using the average object size from query_data_occupancy for DOM_DATABASE and
   DOM_SAP nodes.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Pool status summary and, if triggered, the capacity estimate with its assumptions.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). SAP archive log objects
for SAPHANA01_NODE under MC_SAP_LOG approach the 90-day retention boundary.

Do the following:
1. On sp-mcp-spsvr03, run query_data_occupancy for SAPHANA01_NODE filtered to archive objects.
2. Report how many objects expire in 14 days and their total size.
3. Assess whether expiration frees enough space in POOL_DISK_ARCHIVE before new replication from
   SPSVR01 arrives.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Expiry table (count, size) and a space-sufficiency verdict.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). Aged archive data on
SPSVR03 must move to tape after 180 days.

Do the following:
1. On sp-mcp-spsvr03, run query_storage_rule to confirm no conflicting tiering rule exists.
2. Show the DEFINE STGRULE command with ACTIONTYPE=TIEBYAGE and TIERDAYS=180 that moves data from
   POOL_DISK_ARCHIVE to POOL_TAPE_ARCHIVE.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Conflict check result and the command, shown before any execution.
```

---

### Multi-server schedule compliance & RPO monitoring

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am producing the
last-24-hour schedule compliance report for all three servers.

Do the following:
1. On sp-mcp-spsvr01, run query_scheduled_event for SCHED_DB_NIGHTLY (DOM_DATABASE) and
   SCHED_SAP_LOG_HOURLY (DOM_SAP).
2. On sp-mcp-spsvr02, verify the same nodes replicated within 2 hours of each backup using
   query_protection_status and query_replication_failures.
3. On sp-mcp-spsvr03, run query_protection_status.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Three-column summary: backup status on SPSVR01, replication to SPSVR02, archive replication to
SPSVR03.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). A 4-hour RPO applies to
DOM_DATABASE nodes across the three-server chain.

Do the following:
1. On sp-mcp-spsvr01, find the last successful SCHED_DB_NIGHTLY event for DBORA01_NODE via
   query_scheduled_event.
2. On sp-mcp-spsvr02 and sp-mcp-spsvr03, find the last successful replication via
   query_replication_client.
3. Calculate end-to-end data age from the SPSVR01 backup to the SPSVR03 replica.
4. Flag if it exceeds 4 hours.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Timeline table with columns: server, last success time, age; then the RPO verdict.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). SAPHANA01_NODE has a
15-minute RPO for archive logs under SCHED_SAP_LOG_HOURLY.

Do the following:
1. On sp-mcp-spsvr01, confirm the last five archive events completed within the schedule window via
   query_scheduled_event.
2. On sp-mcp-spsvr02, run query_replication_client for SAPHANA01_NODE.
3. Assess whether replication lag could push the effective RPO above 15 minutes.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Event table, observed replication lag, and an RPO verdict.
```

---

### Disaster recovery failover readiness

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). We are assessing readiness
to fail over from SPSVR01 to SPSVR02.

Do the following:
1. On sp-mcp-spsvr02, run query_protection_status to confirm POOL_DISK_REPLICA is in sync.
2. Run query_replication_client with node_name=* to verify all production nodes replicated.
3. Run query_server_status to confirm SPSVR02 is running and not degraded.
4. Run query_recovery_log to confirm DB and log space are healthy.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
DR readiness scorecard with columns: check, result, red, amber, or green.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). SPSVR01 is offline after a
site incident and failover to SPSVR02 has been approved.

Do the following:
1. On sp-mcp-spsvr02, confirm DBORA01_NODE, DBSQL01_NODE, DBDB201_NODE, SAPHANA01_NODE, and
   SAPABAP01_NODE exist with valid data using query_client and query_data_occupancy.
2. Find each node's most recent backup version via query_client_backup_volume.
3. Flag nodes whose coverage could cause data loss beyond the 4-hour RTO.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: node, latest backup version, data present, RTO risk.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). Failover to SPSVR02
succeeded and three DOM_DATABASE nodes must now use it as primary.

Do the following:
1. List the commands on sp-mcp-spsvr02 to update DBORA01_NODE, DBSQL01_NODE, and DBDB201_NODE.
2. Re-bind them to policy domain DOM_DATABASE.
3. Ensure SCHED_DB_NIGHTLY runs against SPSVR02.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.
- Do not execute anything until I approve the whole sequence.

Generate the output with the following format:
Full ordered command sequence with the purpose of each step.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). A planned DR drill from
SPSVR01 to SPSVR02 is scheduled for this weekend.

Do the following:
1. On sp-mcp-spsvr01, list nodes with REPLSTATE=ENABLED via query_replication_client.
2. On sp-mcp-spsvr02, confirm each node has data via query_data_occupancy.
3. Identify nodes missing or at zero occupancy on SPSVR02.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Gap table with columns: node, enabled on SPSVR01, occupancy on SPSVR02, gap (Yes or No).
```

---

### Multi-server security & audit

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am auditing MCP service
accounts for a consistent security posture.

Do the following:
1. On each of sp-mcp-spsvr01, sp-mcp-spsvr02, and sp-mcp-spsvr03, run query_admin_user for
   mcp-svc-system, mcp-svc-policy, mcp-svc-storage, mcp-svc-operator, and mcp-svc-readonly.
2. Verify each account exists, has SESSIONSECURITY=Strict, and carries the correct privilege class.
3. Report accounts that are missing, misconfigured, or unused for 30 days.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: server, account, exists, SESSIONSECURITY, privilege class, last used.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I am reviewing MCP write
operations from the last 7 days on all three servers.

Do the following:
1. On each server, run query_activity_log with search term MCP_AUDIT and a 7-day window.
2. Aggregate into one audit table.
3. Flag write operations on SPSVR02 or SPSVR03 with no originating operation on SPSVR01, as they may
   indicate out-of-band changes.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: operation, tool, privilege class, correlation ID, server, timestamp.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). An auditor needs the
multi-server topology mapped to NIST SP 800-53 CP-9 and CP-6.

Do the following:
1. For CP-9, cite the SPSVR01 schedules SCHED_DB_NIGHTLY and SCHED_SAP_LOG_HOURLY and
   query_protection_status on all three servers.
2. For CP-6, cite the separation between SPSVR01 and SPSVR02 (on-site) and SPSVR03 (remote).
3. Identify control gaps and the evidence artefacts needed.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Table with columns: control, evidence, gap, artefact needed.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). DOM_DATABASE archive data
on SPSVR03 must be protected from deletion for 7 years.

Do the following:
1. On sp-mcp-spsvr01, retrieve the MC_DB_90 archive copy group settings via query_protection_policy.
2. On sp-mcp-spsvr03, retrieve REPL_RULE_PRIMARY_ARCHIVE via query_replication_rule to confirm
   archive objects are in scope.
3. Confirm whether POOL_TAPE_ARCHIVE has WORM volumes enforcing immutability independent of
   replication policy.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Pass or fail per requirement with evidence, and an overall retention-protection verdict.
```

---

### Multi-server capacity planning & storage management

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). I need a unified capacity
view of the three-server topology.

Do the following:
1. On sp-mcp-spsvr01, run query_storage_container for POOL_DISK_PRIMARY and POOL_CLOUD_TIER.
2. On sp-mcp-spsvr02, run it for POOL_DISK_REPLICA.
3. On sp-mcp-spsvr03, run it for POOL_DISK_ARCHIVE and POOL_TAPE_ARCHIVE.
4. Flag any pool above 80%.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Dashboard table with columns: pool, server, total, used, available, utilisation %, flag.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). POOL_DISK_ARCHIVE on
SPSVR03 is at 78% and may pass 90% within 30 days.

Do the following:
1. On sp-mcp-spsvr03, retrieve DOM_DATABASE and DOM_SAP archive occupancy via query_data_occupancy.
2. On sp-mcp-spsvr01, review 7 days of SCHED_SAP_LOG_HOURLY and SCHED_DB_NIGHTLY events via
   query_scheduled_event to estimate daily inflow.
3. Project whether the pool is exhausted within 30 days.
4. Recommend adding capacity or accelerating migration to POOL_TAPE_ARCHIVE.

The following constraints apply:
- Read-only: run queries only and do not change any configuration.
- Prefer exact object names and narrow time windows over broad or unbounded scans.

Generate the output with the following format:
Projection table (day, projected utilisation %), assumptions, and one recommendation.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). POOL_DISK_REPLICA on
SPSVR02 needs more capacity for growing inflow from SPSVR01.

Do the following:
1. On sp-mcp-spsvr02, retrieve the current POOL_DISK_REPLICA configuration via
   query_storage_container.
2. Show the DEFINE STGPOOL DIRECTORY command to add /tsm/replica/ext01.
3. List post-definition checks to confirm the directory is active before the next replication cycle.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Current configuration, the command before execution, and a verification checklist.
```

---

### Multi-server replication rule management (operator / administrator)

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). Remote archive site
maintenance runs this Saturday 02:00 to 06:00.

Do the following:
1. On sp-mcp-spsvr01, confirm the enabled state of REPL_RULE_PRIMARY_ARCHIVE via
   query_replication_rule.
2. Show the UPDATE REPLRULE commands to disable it before the window and re-enable it after.
3. Include the pre-window check that no replication is in progress, using query_replication_status
   for DBORA01_NODE.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Pre-window check, disable command, and re-enable command, in execution order.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). New policy domain
DOM_COMPLIANCE on SPSVR01 must replicate to both SPSVR02 and SPSVR03.

Do the following:
1. On sp-mcp-spsvr01, review existing rules via query_replication_rule.
2. Show DEFINE STGRULE commands for REPL_RULE_COMPLIANCE_DR (target SPSVR02) and
   REPL_RULE_COMPLIANCE_ARCHIVE (target SPSVR03), both scoped to DOM_COMPLIANCE nodes.
3. Confirm they do not breach the limit of two active target replication servers per source.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.

Generate the output with the following format:
Rule structure review, the two commands, and the limit check result.
```

```text
You are a Data Protection Administrator responsible for replication and data lifecycle management
across a three-server IBM Storage Protect topology.
Three-server topology reached through MCP servers sp-mcp-spsvr01 (primary production),
sp-mcp-spsvr02 (on-site DR replica), and sp-mcp-spsvr03 (remote archive). IBM Storage Protect allows
only one target server per replication storage rule.

Do the following:
1. On sp-mcp-spsvr01, run query_storage_rule and query_replication_rule.
2. Verify no rule defines both SPSVR02 and SPSVR03 as targets.
3. Flag any misconfiguration and show the DEFINE STGRULE or UPDATE REPLRULE commands that split them
   into independent rules.

The following constraints apply:
- Show every command and wait for my confirmation before executing it.
- Verify the current state with a query before and after any change.
- Show corrective commands only; do not execute them.

Generate the output with the following format:
Per-rule pass or fail, with corrective commands for any failing rule.
```

---

### Context-optimised multi-server replication investigation blueprint

Replication health queries across multiple servers can exhaust context windows if run without scope constraints. Use the structured blueprint below when investigating a replication lag or failure across the three-server topology.

```text
You are a Backup Engineer investigating an IBM Storage Protect replication health issue.
Three-server topology: SPSVR01 (primary, sp-mcp-spsvr01), SPSVR02 (on-site DR replica,
sp-mcp-spsvr02), SPSVR03 (remote archive, sp-mcp-spsvr03).

Do the following:
Identify which nodes have failed or lagging replication on each replication leg (SPSVR01→SPSVR02,
SPSVR01→SPSVR03, SPSVR02→SPSVR03), determine root cause for each failure, and classify the risk to
DR and archive data coverage.

Follow these query success rules:
1. Prefer the most constrained query possible before expanding scope.
2. Never run query_replication_client with node_name=* unless targeted per-server.
3. Never run query_activity_log without a specific node name and narrow time window (±60 minutes).
4. Address each MCP server separately and in order: SPSVR01, then SPSVR02, then SPSVR03.
5. If a query returns no match, retry once with a simpler parameter set before moving on.

Follow this execution sequence:

Step 1 — Source Server Health (sp-mcp-spsvr01)
- Run query_protection_status to get POOL_DISK_PRIMARY protection state.
- Run query_replication_failures to retrieve all failure records.
- Run query_replication_rule to confirm REPL_RULE_PRIMARY_DR and REPL_RULE_PRIMARY_ARCHIVE are
  active.
- Run query_storage_container for POOL_DISK_PRIMARY — a pool above 80% is a common replication stall
  cause.

Step 2 — DR Replica Health (sp-mcp-spsvr02)
- Run query_protection_status to confirm POOL_DISK_REPLICA is in sync.
- Run query_replication_failures to retrieve any inbound failure records.
- Run query_replication_rule to confirm REPL_RULE_DR_ARCHIVE is active.
- Run query_server_status to confirm SPSVR02 is operational.

Step 3 — Remote Archive Health (sp-mcp-spsvr03)
- Run query_protection_status to confirm POOL_DISK_ARCHIVE is in sync.
- Run query_replication_failures to retrieve any inbound failure records.
- Run query_storage_container for POOL_DISK_ARCHIVE — a full archive pool will reject new
  replication.

Step 4 — Per-Node Replication Validation (sp-mcp-spsvr01)
- For each node flagged in failure records from Steps 1–3, run query_replication_client with the
  specific node name.
- Confirm REPLSTATE=ENABLED and review the target server and files-sent count.
- For each failed node, run query_activity_log with a ±60-minute window around the failure
  timestamp.

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
- Run query_replication_client with node_name=* on sp-mcp-spsvr01 and manually inspect files-sent
  versus files-received for key nodes.
- Mark findings as Likely instead of Confirmed.

Generate the output with the following format:
- Executive Summary: replication health status per server leg (green / amber / red); total failure
  records; nodes at risk.
- Replication Failure Table: Node · Source Server · Target Server · Failure Date · File Space · Root
  Cause · Recommended Action.
- Lagging Nodes Table: Node · Source Server · Target Server · Files Sent · Files Received ·
  Estimated Lag · Risk to RPO.
- Pool Capacity Risk: server, pool, utilisation %, and whether the pool is a blocker.
- Immediate Actions Required.
- Limitations.

The following constraints apply:
- Address one MCP server at a time.
- Do not run broad unbounded queries against all nodes simultaneously.
- Clearly distinguish Confirmed failures (from query_replication_failures) from Likely failures
  (inferred from query_replication_client).
```
