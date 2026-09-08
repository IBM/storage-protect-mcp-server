# Architecture

System architecture documentation for the IBM Storage Protect MCP Server. These documents describe how the server is structured, how its modules interact, and the design decisions behind the security and operational model.

---

## Documents

| Document | Description |
|---|---|
| [`architecture.md`](architecture.md) | Full system architecture: operating models (unified vs micro-MCP), layered architecture diagram, component descriptions, transport security, privilege model, and module registry |
| [`module-clients.md`](module-clients.md) | Clients module: node lifecycle, node groups, client option sets, session diagnostics, proxy and replication queries |
| [`module-operations.md`](module-operations.md) | Operations module: data movement, disaster recovery, retention rules, replication status, schedule events, alerts, and approval workflows |
| [`module-policies.md`](module-policies.md) | Policies module: policy domains, policy sets, management classes, copy groups, schedules, and subscriber management |
| [`module-storage.md`](module-storage.md) | Storage module: storage pools, device classes, libraries, drives, volumes, datamover/NDMP, paths, and content integrity |
| [`module-system.md`](module-system.md) | System module: server administration, admin accounts, license management, server options, connection management, recovery logs, and scripting |

---

## Key Concepts

**Two operating models** — The server can run as a single unified process (`main.py`) exposing all or selected functional groups, or as fine-grained micro-MCP servers (`main_<module>_*.py`) for LLM context-window efficiency and least-privilege scoping.

**Privilege gate** — Every tool declares a `required_privilege` property. At startup, `mcp_factory.py` queries the configured service account's actual IBM SP privilege class via `QUERY ADMIN` and registers only the tools that account is authorised to invoke.

**Two transport modes** — `stdio` over SSH (Ed25519 key auth, `StrictHostKeyChecking=yes`) for local/single-client deployments; HTTP/SSE with TLS and OAuth 2.1 / OIDC bearer token authentication for enterprise multi-client deployments.

---

## Cross-References

- Security controls implemented: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Per-domain design specs: [`../design/`](../design/)
- End-to-end traceability: [`../traceability/traceability-matrix.md`](../traceability/traceability-matrix.md)
- Source code: [`../../src/sp_mcp_server/`](../../src/sp_mcp_server/)
