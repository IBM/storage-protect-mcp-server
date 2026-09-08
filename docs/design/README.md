# Design

Security design specifications for the IBM Storage Protect MCP Server, one document per security domain. Each document defines the design changes required to close identified security gaps, the rationale, and the mapping to implementation specifications.

---

## Documents

| Document | Domain | Gaps closed |
|---|---|---|
| [`security-network.md`](security-network.md) | Network Security | NET-1, NET-2, NET-3 — session security validation, SSH key auth, TLS enforcement |
| [`security-identity-credentials.md`](security-identity-credentials.md) | Identity & Credentials | CRED-1 through CRED-4 — 5-tier service accounts, stash auth, `.env` permission check |
| [`security-access.md`](security-access.md) | Access Management | ACC-1 through ACC-4 — per-tool privilege annotation, self-narrowing registry, `sudo` execution |
| [`security-policy.md`](security-policy.md) | Policy Management | POL-1 through POL-4 — command approval, password pre-validation, ACTLOG audit attribution |
| [`security-integrations.md`](security-integrations.md) | Secure Integrations | INT-1 through INT-4 — OAuth 2.1 / OIDC, HTTP TLS, keyring secret resolution |

---

## How to Read These Documents

Each design document follows the same structure:

1. **Overview** — the original gap and why the existing code was insufficient
2. **Change table** — each design change with its ID, description, and gaps closed
3. **Detailed design** — the specific approach for each change, including IBM SP native controls referenced
4. **Security considerations** — residual risk, assumptions, and boundary conditions

Design documents are the bridge between the audit findings in [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md) and the implementation notes in [`../implement/`](../implement/).

---

## Cross-References

- Audit findings: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Implementation specs: [`../implement/`](../implement/)
- Traceability: [`../traceability/traceability-matrix.md`](../traceability/traceability-matrix.md)
