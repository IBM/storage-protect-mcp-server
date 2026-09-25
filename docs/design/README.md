# Design

Security design specifications for the IBM Storage Protect MCP Server, one document per security domain. Each document defines the design changes required to close identified security gaps, the rationale, and the mapping to implementation specifications.

---

## Documents

| Document | Domain | Requirements |
|---|---|---|
| [`security-network.md`](security-network.md) | Network Security | NET-1 through NET-3 — session security validation, SSH key auth, TLS enforcement |
| [`security-identity-credentials.md`](security-identity-credentials.md) | Identity & Credentials | CRED-1 through CRED-5 — 5-tier service accounts, stash auth, `.env` permission check, provisioning script |
| [`security-dynamic-authn.md`](security-dynamic-authn.md) | Dynamic Authentication | DAUTH-1 through DAUTH-9 — challenge-response, ephemeral leases, privilege enforcement, target-server binding, credential lifecycle |
| [`security-access.md`](security-access.md) | Access Management | ACC-1 through ACC-4 — per-tool privilege annotation, self-narrowing registry, `sudo` execution |
| [`security-policy.md`](security-policy.md) | Policy Management | POL-1 through POL-4 — command approval, password pre-validation, lockout audit, ACTLOG attribution |
| [`security-integrations.md`](security-integrations.md) | Secure Integrations | INT-1 through INT-4 — OAuth 2.1 / OIDC, HTTP TLS, keyring secret resolution |
| [`security-non-repudiation.md`](security-non-repudiation.md) | Non-Repudiation & Forensics | NR-1 through NR-5 — user identity binding, strict audit fail-closed, ISO 8601 UTC timestamps |

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
