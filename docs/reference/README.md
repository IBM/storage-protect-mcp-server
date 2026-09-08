# Reference

External IBM reference material for the IBM Storage Protect MCP Server.

---

## Documents

| Document | Description |
|---|---|
| [`b_srv_admin_ref_linux.pdf`](b_srv_admin_ref_linux.pdf) | IBM Storage Protect — Administrator's Reference for Linux, version 8.1.26. The authoritative reference for all IBM SP server commands, option names, privilege classes, session security controls, and retention/policy parameters used in the MCP server implementation. |

---

## How This Document Is Used

The Administrator's Reference is the primary IBM source consulted throughout the MCP server project for:

- **Command syntax** — exact parameter names and values for all `DEFINE`, `UPDATE`, `QUERY`, and operational commands implemented as MCP tools
- **Privilege classes** — definitions of `SYSTEM`, `POLICY`, `STORAGE`, `OPERATOR`, and `ANY` privilege classes referenced in the access management design
- **Session security** — `SESSIONSECURITY=STRICT` behaviour, `QUERY ADMIN FORMAT=DETAILED` output fields, and TLS requirements
- **Policy constructs** — management class parameters (`VEREXISTS`, `RETEXTRA`, `RETMIN`, `RETMAX`), copy group types, and retention set behaviour
- **Security controls** — `SET COMMANDAPPROVAL`, `APPROVE PENDINGCMD`, `SET INVALIDPWLIMIT`, `QUERY OPTION MINPWLENGTH`, and `DEFINE SCRATCHPADENTRY`

Specific section references from this document appear throughout [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md) and the design specs in [`../design/`](../design/).

---

## Cross-References

- Security analysis: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Architecture: [`../architecture/architecture.md`](../architecture/architecture.md)
