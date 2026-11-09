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
| [`test/`](test/) | Test engineering: test specifications, test case catalog, execution procedures, and fault/load test-bed |
| [`traceability/`](traceability/) | Requirements traceability matrix, gap analysis, and independent audit report |
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
8. [`analysis/security-design-analysis.md`](analysis/security-design-analysis.md) — Security architecture and active controls across all eight domains
8a. [`analysis/security-dynamic-authn-analysis.md`](analysis/security-dynamic-authn-analysis.md) — Dynamic & delegated authentication design analysis
8b. [`analysis/security-oauth2-analysis.md`](analysis/security-oauth2-analysis.md) — OAuth 2 gap analysis (OA-1–OA-7, all closed)

### Security governance & traceability

9. [`design/`](design/) — Security design specs per domain (network, credentials, access, policy, integrations, dynamic authentication, non-repudiation, OAuth 2)
10. [`implement/`](implement/) — Implementation specs per domain, tracing design decisions to source files
11. [`traceability/traceability-matrix.md`](traceability/traceability-matrix.md) — End-to-end requirements traceability (51 security requirements + 50 resilience tests)
12. [`traceability/gap-analysis.md`](traceability/gap-analysis.md) — Consolidated security, prompt & documentation gap status (all closed, 248 tests collected)
13. [`traceability/audit-report.md`](traceability/audit-report.md) — Comprehensive independent audit and verification report (all code, runtime, and documentation findings remediated)

### Verification and testing

14. [`test/test-specifications.md`](test/test-specifications.md) — Testing strategy, scope, quality gates, and test levels
15. [`test/test-cases.md`](test/test-cases.md) — Comprehensive test case catalog (all 248 tests, negative, failure, and stress cases)
16. [`test/test-procedures.md`](test/test-procedures.md) — Test execution procedures, runbooks, fault injection, and load testing
17. [`test/test-bed.md`](test/test-bed.md) — Fault injection, network chaos, load simulation, and security test-bed architecture


