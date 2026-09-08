# Implementation

Implementation specifications for each security domain of the IBM Storage Protect MCP Server. These documents trace each design decision to the specific source files, functions, and test cases that implement it.

---

## Documents

| Document | Domain | Source files |
|---|---|---|
| [`impl-security-network.md`](impl-security-network.md) | Network Security | `mcp_factory.py`, `config/dsm.sys.template`, `configure-guide.md` |
| [`impl-security-identity-credentials.md`](impl-security-identity-credentials.md) | Identity & Credentials | `config.py`, `cli_wrapper.py`, all `main*.py` entry points |
| [`impl-security-access.md`](impl-security-access.md) | Access Management | `commands/base.py`, `mcp_factory.py`, all `commands/**/*.py` |
| [`impl-security-policy.md`](impl-security-policy.md) | Policy Management | `mcp_factory.py`, `commands/operations/approval.py`, `commands/operations/misc.py` |
| [`impl-security-integrations.md`](impl-security-integrations.md) | Secure Integrations | `http_server.py`, `system/conn.py`, `config.py` |
| [`impl-security-non-repudiation.md`](impl-security-non-repudiation.md) | Non-Repudiation & Forensics | `mcp_factory.py`, `http_server.py`, `tests/test_security_controls.py` |

---

## Relationship to Design Documents

Each implementation document corresponds directly to a design document in [`../design/`](../design/). The implementation documents add:

- The exact files and functions changed
- Code-level rationale for decisions made during implementation
- Test coverage references (`tests/test_security_controls.py`, `tests/test_cli_wrapper.py`)
- Residual risk notes and assumptions

---

## Cross-References

- Security design specs: [`../design/`](../design/)
- Audit findings: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Traceability matrix: [`../traceability/traceability-matrix.md`](../traceability/traceability-matrix.md)
- Source code: [`../../src/sp_mcp_server/`](../../src/sp_mcp_server/)
- Tests: [`../../tests/`](../../tests/)
