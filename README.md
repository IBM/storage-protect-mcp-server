# IBM Storage Protect MCP Server

The IBM Storage Protect Model Context Protocol (MCP) server enables natural language administration of IBM Storage Protect systems through AI-powered automation. Transform complex `dsmadmc` command-line operations into simple conversational interactions with any MCP-compatible AI agent.

## Table of Contents

- [What It Does](#what-it-does)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

---

## What It Does

The MCP server exposes IBM Storage Protect administrative operations as structured tools that any MCP-compatible client (Claude Desktop, VS Code Copilot, an automated pipeline) can invoke. Instead of composing `dsmadmc` commands manually, you describe what you want in natural language and the AI agent translates that into the appropriate tool call.

| Category | Examples |
|---|---|
| Monitoring | Check server status, review active sessions, query storage pool utilisation |
| Investigation | Find failed operations, search activity logs, check alert history |
| Client management | Register or update nodes, manage node groups, review policy assignments |
| Storage operations | Define or update storage pools, check volume usage, manage device classes |
| Policy management | Create or activate policy sets, manage management classes and copy groups |
| System administration | Manage administrators, licences, and server-to-server connections |
| Offline diagnostics | Run `servermon`, check DB space and recovery logs |

**Two operating modes:**

- **Unified MCP server** — a single process exposing all or selected functional groups over `stdio` or HTTP/SSE
- **Micro-MCP servers** — fine-grained, isolated server processes optimised for LLM context-window efficiency and least-privilege scoping

---

## Prerequisites

| Requirement | Minimum |
|---|---|
| IBM Storage Protect server | Running, reachable on TCP 1500 |
| Python | 3.10 or higher (3.11 recommended) |
| `dsmadmc` CLI | Available in `PATH` on the MCP server host |
| OS user | Dedicated non-root `mcp-runner` account |
| SP admin credentials | Administrator ID and password with appropriate privilege class |

---

## Quick Start

1. **Install** — follow [`docs/guides/install-guide.md`](docs/guides/install-guide.md) to set up the OS user, Python environment, and wheel package on the IBM SP host.

2. **Configure** — follow [`docs/guides/configure-guide.md`](docs/guides/configure-guide.md) to set up your MCP client (stdio/SSH or HTTP/OIDC) and create the `.env` credential file.

3. **Run** — the MCP client launches the server automatically. For manual testing:

   ```bash
   cd /opt/sp-mcp-server
   source .venv/bin/activate
   python3 -m sp_mcp_server.main --mode full
   ```

4. **Try prompts** — see [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md) for ready-made prompts across seven administrator personas.

---

## Documentation

Full documentation is in [`docs/`](docs/). The table below lists the key documents.

| Document | Purpose |
|---|---|
| [`docs/guides/install-guide.md`](docs/guides/install-guide.md) | OS setup, Python environment, `dsmadmc` prerequisites |
| [`docs/guides/configure-guide.md`](docs/guides/configure-guide.md) | MCP client configuration for stdio/SSH and HTTP/OIDC transports |
| [`docs/guides/user-guide.md`](docs/guides/user-guide.md) | Privilege tiers, tool access control, `--mode` flag, audit behaviour |
| [`docs/guides/troubleshoot.md`](docs/guides/troubleshoot.md) | Startup failures, credential errors, and runtime error reference |
| [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md) | 60+ sample prompts across seven personas with a reference deployment topology |
| [`docs/architecture/architecture.md`](docs/architecture/architecture.md) | System architecture, operating models, and security design principles |
| [`docs/analysis/security-design-analysis.md`](docs/analysis/security-design-analysis.md) | Security audit — all 27 gaps resolved, 56/56 tests passing |
| [`docs/traceability/traceability-matrix.md`](docs/traceability/traceability-matrix.md) | End-to-end requirements traceability (NET, CRED, ACC, POL, INT) |
| [`docs/traceability/gap-analysis.md`](docs/traceability/gap-analysis.md) | Security gap status — 0 open gaps |

---

## Environment Variables

### Service Account Credentials (CRED-1)

The MCP server uses **five tiered service accounts**, one per IBM SP privilege class. Each account is configured independently so the MCP server invokes the narrowest privilege tier each tool requires. See [`docs/design/security-identity-credentials.md`](docs/design/security-identity-credentials.md) for the full design and [`docs/implement/impl-security-identity-credentials.md`](docs/implement/impl-security-identity-credentials.md) for provisioning steps.

| Variable | Privilege class | SP commands accessible | Example value |
|---|---|---|---|
| `SP_ADMIN_ID_SYSTEM` | System | All commands | `mcp-svc-system` |
| `SP_ADMIN_PASSWORD_SYSTEM` | System | — | *(omit when stash active)* |
| `SP_ADMIN_ID_POLICY` | Policy | Policy + read-only tools | `mcp-svc-policy` |
| `SP_ADMIN_PASSWORD_POLICY` | Policy | — | *(omit when stash active)* |
| `SP_ADMIN_ID_STORAGE` | Storage | Storage + read-only tools | `mcp-svc-storage` |
| `SP_ADMIN_PASSWORD_STORAGE` | Storage | — | *(omit when stash active)* |
| `SP_ADMIN_ID_OPERATOR` | Operator | Operations + read-only tools | `mcp-svc-operator` |
| `SP_ADMIN_PASSWORD_OPERATOR` | Operator | — | *(omit when stash active)* |
| `SP_ADMIN_ID_READONLY` | Any (read-only) | `QUERY` tools only | `mcp-svc-readonly` |
| `SP_ADMIN_PASSWORD_READONLY` | Any (read-only) | — | *(omit when stash active)* |

> **Credential resolution** — `credential_for(tier)` walks from the requested tier down to `any` and returns the first configured credential. A minimal deployment that only sets `SP_ADMIN_ID_SYSTEM` / `SP_ADMIN_PASSWORD_SYSTEM` will serve all tools using the system account. A full deployment configures all five tiers and invokes the narrowest one per tool call.

> **`SP_ADMIN_ID` / `SP_ADMIN_PASSWORD`** — The original single-credential variables are still accepted as a **legacy fallback** but are deprecated. The server emits a `CRED-1` warning at startup when only these are configured. Migrate to the per-tier variables above.

### Server Connection

| Variable | Description | Default | Example |
|---|---|---|---|
| `TCPSERVERADDRESS` | SP server hostname or IP | — | `spsvr01.corp.example.com` |
| `SP_SERVER_PORT` / `TCPPORT` | SP server TCP port | `1500` | `1500` |

### Offline & Diagnostic Commands

| Variable | Description | Default | Example |
|---|---|---|---|
| `SP_DSMSERV_PATH` | Path to `dsmserv` executable | — | `/opt/tivoli/tsm/server/bin/dsmserv` |
| `SP_SERVER_INSTANCE_DIR` | Server instance directory | — | `/tsminst1` |
| `SP_SERVERMON_PATH` | Path to `servermon` executable | — | `/opt/tivoli/tsm/server/bin/servermon` |
| `SP_SERVERMON_XML_DIR` | Directory for servermon XML output | — | `/tmp/servermon` |
| `SP_INSTANCE_USER` | IBM SP instance OS user for `dsmserv` / `servermon` | — | `tsminst1` |

> **`SP_INSTANCE_USER` is required for offline commands.** Without it, `dsmserv` fails to load shared libraries. The MCP server uses `sudo -u <SP_INSTANCE_USER>` to run these commands — a `sudoers` entry for `mcp-runner` is required.

### Security Controls

| Variable | Description | Default | Example |
|---|---|---|---|
| `SP_MCP_USE_PASSWORD_STASH` | `1` = omit `-PA=`; read password from `dsm.sys` encrypted stash (`PASSWORDACCESS GENERATE`) | `0` | `1` |
| `SP_MCP_ENV` | Set to `production` to enforce all security controls and block bypass flags | — | `production` |

> **`SP_MCP_USE_PASSWORD_STASH=1` is the recommended production setting.** In this mode the password is never passed on the command line and is never visible in `/proc/<pid>/cmdline`. Once the stash is active the `SP_ADMIN_PASSWORD_*` variables can be removed from `.env` entirely. See the stash population steps in [`docs/implement/impl-security-identity-credentials.md § CRED-2`](docs/implement/impl-security-identity-credentials.md).

### Example `.env` files

**Minimum — read-only monitoring deployment:**

```bash
# .env — chmod 600, chown mcp-runner:mcp-runner
TCPSERVERADDRESS=spsvr01.corp.example.com
SP_SERVER_PORT=1500

SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_ADMIN_PASSWORD_READONLY=<strong-password>

SP_MCP_ENV=production
```

**Full — all five tiers with stash mode (recommended for production):**

```bash
# .env — chmod 600, chown mcp-runner:mcp-runner
TCPSERVERADDRESS=spsvr01.corp.example.com
SP_SERVER_PORT=1500

SP_ADMIN_ID_SYSTEM=mcp-svc-system
SP_ADMIN_ID_POLICY=mcp-svc-policy
SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_ID_OPERATOR=mcp-svc-operator
SP_ADMIN_ID_READONLY=mcp-svc-readonly

# Passwords omitted — read from dsm.sys encrypted stash
SP_MCP_USE_PASSWORD_STASH=1

SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/tmp/servermon
SP_INSTANCE_USER=tsminst1

SP_MCP_ENV=production
```

> The `.env` file **must** have `0600` POSIX permissions (`chmod 600 .env`). The server exits immediately at startup (`sys.exit(1)`) if the file is group- or world-readable — before any secret is read. Run [`scripts/provision-sp-service-accounts.sh`](scripts/provision-sp-service-accounts.sh) to create the five service accounts on the SP server before populating `.env`.

---

## Contributing

Contributions are welcome through Pull Requests.

1. Fork the repository and create a new branch for your feature or bug fix.
2. Follow the existing code style and conventions.
3. Test your changes thoroughly.
4. Submit a pull request with a clear description of your changes.
5. Sign the Developer's Certificate of Origin (DCO) by adding your name and email to `DCO.md` in your pull request.

---

## Disclaimer

This software is provided "as is" without any warranties of any kind, including, but not limited to, warranties related to installation, use, or performance. IBM is not responsible for any damage, charges, or data loss incurred with the use of this software. You are responsible for reviewing and testing any scripts you run thoroughly before use in any production environment. This content is subject to change without notice.
