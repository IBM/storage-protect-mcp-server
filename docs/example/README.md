# Examples

Sample prompts for the IBM Storage Protect MCP Server, organised by persona and grounded in a concrete reference deployment topology.

---

## Documents

| Document | Description |
|---|---|
| [`sample-prompts.md`](sample-prompts.md) | 60+ naturalistic, task-oriented prompts across seven personas, written against the sample deployment topology (SPSVR01, 11 BA client nodes, 6 storage pools, 6 backup schedules, 4 policy domains) |

---

## Sample Deployment Topology

All prompts in [`sample-prompts.md`](sample-prompts.md) use a consistent named environment:

| Component | Details |
|---|---|
| SP server | `SPSVR01` on `spsvr01.corp.example.com`, IBM SP 8.1.22, RHEL 9 |
| MCP server identifier | `sp-mcp-server-remote-tumbleweed` |
| BA client nodes | 11 nodes: web servers, app server, Oracle 19c, SQL Server 2022, Db2 11.5, SAP HANA 2.0, SAP S/4HANA ABAP, SPVE proxy (VMware), NDMP NAS, and one decommissioned node |
| Policy domains | `DOM_GENERAL`, `DOM_DATABASE`, `DOM_SAP`, `DOM_VIRTUAL` |
| Storage pools | `POOL_DISK_PRIMARY`, `POOL_DISK_COPY`, `POOL_TAPE_COPY`, `POOL_TAPE_WORM`, `POOL_CLOUD_TIER`, `POOL_DBBACKUP` |
| Backup schedules | `SCHED_GENERAL_DAILY`, `SCHED_DB_NIGHTLY`, `SCHED_SAP_LOG_HOURLY`, `SCHED_SAP_FULL_WEEKLY`, `SCHED_VM_DAILY`, `SCHED_DBBACKUP_DAILY` |
| Storage devices | FC-attached LTO-8 tape library (`LIB_LTO8_01`), IBM Cloud Object Storage (`cos.us-south.example.com`), NDMP datamover (`NAS_MOVER_01`) |

---

## Persona Coverage

| Persona | Focus |
|---|---|
| R-01 · Data Protection Operator | Discovery, backup policy, storage pool configuration, node lifecycle, backup operations |
| R-02 · Data Protection Administrator | Performance tuning, capacity expansion, anti-pattern audits, database diagnostics, tape/VTL/NDMP |
| R-03 · Infrastructure Solution Architect | Sizing, architecture, server upgrade, cloud tiering, copy strategy, licensing & TCO |
| R-04 · Workload & Application Owner | Oracle, SQL Server, Db2, SAP HANA, SAP ABAP, VMware SPVE integration |
| R-05 · Security & Compliance Officer | Hardening, WORM/immutability, verified recovery, drift detection, NIST/DORA/BSI C5/ISO 27001 |
| R-06 · Resilience Operations Manager | Schedule compliance, ITIL incident/problem/change, DR execution, ransomware response |
| R-07 · Storage Protect Service Engineer | Health assessment, fix-pack planning, performance optimisation, defect investigation |

---

## Cross-References

- Installation: [`../guides/install-guide.md`](../guides/install-guide.md)
- Configuration: [`../guides/configure-guide.md`](../guides/configure-guide.md)
- User guide: [`../guides/user-guide.md`](../guides/user-guide.md)
- Troubleshooting: [`../guides/troubleshoot.md`](../guides/troubleshoot.md)
