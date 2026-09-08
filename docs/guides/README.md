# Guides

End-user guides for the IBM Storage Protect MCP Server. Read these in order when setting up for the first time.

---

## Documents

| Document | When to read |
|---|---|
| [`install-guide.md`](install-guide.md) | **First** — OS user setup, Python virtual environment, `dsmadmc` prerequisites, and wheel package installation |
| [`configure-guide.md`](configure-guide.md) | **Second** — MCP client configuration for stdio/SSH and HTTP/OIDC transports, `.env` setup, and multi-server registry |
| [`user-guide.md`](user-guide.md) | **Third** — Privilege tiers, tool access control, `--mode` flag, starting and stopping the server, and audit behaviour |
| [`troubleshoot.md`](troubleshoot.md) | **When something goes wrong** — Error markers, startup failures, credential errors, offline command failures, and Python import errors |

---

## Quick Overview

### install-guide.md

Covers everything needed to get the server running on the IBM Storage Protect host:

- Creating the dedicated `mcp-runner` OS user
- Setting up the Python 3.11 virtual environment
- Installing the wheel package
- Configuring `dsmadmc` and verifying connectivity

### configure-guide.md

Covers MCP client configuration for both transport modes:

- **stdio over SSH** — SSH Ed25519 key generation and deployment, `StrictHostKeyChecking=yes`, MCP client JSON configuration snippets for Claude Desktop, VS Code, and custom agents
- **HTTP/SSE** — TLS certificate setup, OIDC provider configuration, and bearer token authentication
- **Multi-server registry** — configuring connections to multiple IBM SP servers from a single MCP server instance

### user-guide.md

Covers day-to-day operation:

- The five privilege tiers (`system`, `policy`, `storage`, `operator`, `readonly`) and which tools each tier exposes
- Using `--mode full` versus `--mode read-only`
- Understanding audit log attribution via `DEFINE SCRATCHPADENTRY MCP_AUDIT`
- Starting the server manually for testing

### troubleshoot.md

A quick-reference error guide keyed by log marker:

| Log marker | Issue |
|---|---|
| `SECURITY [CRED-3]` | `.env` file has insecure permissions — run `chmod 600 .env` |
| `SECURITY [RG-1]` | Production bypass guard triggered — `SP_MCP_SKIP_SECURITY_CHECKS=1` blocked in production |
| `SECURITY [NET-1]` | Session security check failed — `SESSIONSECURITY` is not `STRICT` on a service account |
| `SECURITY [RG-5]` | HTTP transport TLS not configured |
| `dsmadmc executable not found` | `dsmadmc` is not in `PATH` on the MCP server host |
| `No credential available` | Missing `.env` entry or keyring secret for the required privilege tier |

---

## Cross-References

- Sample prompts: [`../example/sample-prompts.md`](../example/sample-prompts.md)
- Architecture overview: [`../architecture/architecture.md`](../architecture/architecture.md)
- Security controls: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
