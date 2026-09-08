# Documentation

This directory contains the complete documentation for the IBM Storage Protect MCP Server, organised by purpose. Start with the [guides](guides/) for installation and day-to-day use, then consult the architecture and design documents for a deeper understanding of how the system is built and secured.

---

## Directory Map

| Folder | Purpose |
|---|---|
| [`guides/`](guides/) | End-user guides: installation, configuration, usage, and troubleshooting |
| [`example/`](example/) | Sample prompts for all personas, with a reference deployment topology |
| [`architecture/`](architecture/) | System architecture, module designs, and component diagrams |
| [`design/`](design/) | Security design specifications per domain |
| [`implement/`](implement/) | Implementation notes per security domain, tracing design to code |
| [`analysis/`](analysis/) | Security design analysis and audit findings |
| [`traceability/`](traceability/) | Requirements traceability matrix and gap analysis |
| [`reference/`](reference/) | External IBM reference material (IBM SP Administrator's Reference) |

---

## Suggested Reading Order

### Getting started

1. [`guides/install-guide.md`](guides/install-guide.md) — Install the MCP server on the IBM SP host
2. [`guides/configure-guide.md`](guides/configure-guide.md) — Configure your MCP client (stdio/SSH or HTTP/OIDC)
3. [`guides/user-guide.md`](guides/user-guide.md) — Understand privilege tiers, tool access, and the `--mode` flag
4. [`example/sample-prompts.md`](example/sample-prompts.md) — Try ready-made prompts against the sample deployment topology
5. [`guides/troubleshoot.md`](guides/troubleshoot.md) — Diagnose startup and runtime errors

### Understanding the system

6. [`architecture/architecture.md`](architecture/architecture.md) — System architecture and core design principles
7. [`architecture/module-*.md`](architecture/) — Per-module architecture for clients, storage, policies, operations, and system
8. [`analysis/security-design-analysis.md`](analysis/security-design-analysis.md) — Security audit findings and resolved controls

### Security governance

9. [`design/`](design/) — Security design specs per domain (network, credentials, access, policy, integrations)
10. [`implement/`](implement/) — Implementation specs per domain, tracing design decisions to source files
11. [`traceability/traceability-matrix.md`](traceability/traceability-matrix.md) — End-to-end requirements traceability
12. [`traceability/gap-analysis.md`](traceability/gap-analysis.md) — Security gap status (all 27 gaps closed)
