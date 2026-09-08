# User Guide

This guide helps operators and AI-assisted workflows get the most out of the IBM Storage Protect MCP Server after installation and configuration. It covers what the server does, how privilege tiers control access, how to interact with it safely, and how to audit what it does.

---

## What the MCP Server Does

The IBM Storage Protect MCP Server exposes IBM SP administrative operations as structured tools that any MCP-compatible client (Claude, VS Code Copilot, an automated pipeline) can invoke. Instead of composing `dsmadmc` commands manually, you describe what you want in natural language and the AI agent translates that into the appropriate tool call.

Typical use cases:

| Category | Examples |
|----------|---------|
| Monitoring | Check server status, review active sessions, query storage utilization |
| Investigation | Find failed operations, search activity logs, check alert history |
| Client management | Register or update nodes, manage node groups, review policy assignments |
| Storage operations | Define or update storage pools, check volume usage, manage device classes |
| Policy management | Create or activate policy sets, manage management classes and copy groups |
| System administration | Manage administrators, licenses, and server-to-server connections |
| Offline diagnostics | Run `servermon`, check DB space and recovery logs |

---

## Privilege Tiers and Tool Access

The MCP server automatically narrows the registered tool set based on the IBM SP privilege class of the configured service account. This happens at startup — tools that require a higher privilege than the configured account possesses are simply not registered and are invisible to MCP clients.

| Account | SP privilege class | Tools available |
|---------|-------------------|----------------|
| `mcp-svc-system` | System | All tools — full administrative scope |
| `mcp-svc-policy` | Policy | Policy management + all read-only tools |
| `mcp-svc-storage` | Storage | Storage management + all read-only tools |
| `mcp-svc-operator` | Operator | Operations (sessions, media, jobs) + read-only tools |
| `mcp-svc-readonly` | Any-admin (no class) | Read-only `QUERY` tools only |

The `--mode` flag applies an additional filter on top of the privilege gate:

| `--mode` | Effect |
|----------|--------|
| `full` (default) | All privilege-appropriate tools registered |
| `read-only` | Only `QUERY`/info tools, regardless of account privilege |

For a monitoring-only deployment, `--mode read-only` is the safest choice. For full administration, configure per-privilege accounts and let the privilege gate control scope automatically.

---

## Starting the Server

After completing [`install-guide.md`](install-guide.md) and [`configure-guide.md`](configure-guide.md), the MCP client launches the server automatically. For manual testing or scripting:

```bash
cd /opt/sp-mcp-server
source .venv/bin/activate

# Full access — all modules, privilege-gated by configured accounts
python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage

# Read-only — query tools only
python3 -m sp_mcp_server.main --mode read-only

# Scoped — only storage and operations modules
python3 -m sp_mcp_server.main --mode full --enable-servers storage,operations

# HTTP transport with OIDC (requires SP_OIDC_ISSUER, SP_TLS_CERT, SP_TLS_KEY in .env)
python3 -m sp_mcp_server.main --transport http --port 8443 --mode full
```

### Command-line arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | `full` | `full` = all privilege-appropriate tools; `read-only` = query/info only |
| `--enable-servers` | all | Comma-separated module names: `system`, `operations`, `clients`, `policy`, `storage` |
| `--transport` | `stdio` | `stdio` (SSH) or `http` (OIDC bearer token) |
| `--port` | `8443` | HTTP listen port (used only with `--transport http`) |

---

## Server Modules

The `--enable-servers` flag controls which IBM SP functional areas are exposed. Each module maps to a set of tool classes:

| Module name | SP areas covered | Typical account |
|-------------|-----------------|----------------|
| `system` | Administrators, licenses, server definitions, scripts, connections | `system` |
| `operations` | DB backup, replication, data movement, jobs, alerts, rules, retention | `operator` / `system` |
| `clients` | Nodes, node groups, associations, client option sets | `policy` / `system` |
| `policy` | Policy domains/sets, management classes, copy groups, schedules | `policy` / `system` |
| `storage` | Storage pools, volumes, libraries, drives, paths, device classes, data movers | `storage` / `system` |

Omit modules that are not needed for a given deployment. A storage-focused team can run with `--enable-servers storage` and avoid exposing system or policy tools entirely.

---

## How Passwords Are Protected

The MCP server handles credentials with several layered controls:

1. **`.env` permissions enforced at startup** — the server aborts if `.env` is group- or world-readable (CRED-3). Never set permissions wider than `600`.

2. **Keyring-first password resolution** — if the OS keyring (macOS Keychain, Linux Secret Service) contains the service account password, it is used instead of the env var. To migrate:
   ```python
   import keyring
   keyring.set_password("ibm-sp-mcp-server", "mcp-svc-system", "<password>")
   ```
   Then remove `SP_ADMIN_PASSWORD_SYSTEM` from `.env`.

3. **Password stash mode** — with `SP_MCP_USE_PASSWORD_STASH=1` in `.env` (after populating the `dsmadmc` stash), the `-PA=` argument is never passed to subprocess calls. Passwords do not appear in `/proc/<pid>/cmdline` or log files.

4. **Silent execution for credential-bearing commands** — `REGISTER ADMIN`, `UPDATE ADMIN`, `REGISTER NODE`, and `UPDATE NODE` commands that embed a password string use a silent execution path that suppresses command logging entirely (RG-3).

---

## Audit Trail

Every write operation (tools requiring `system`, `policy`, `storage`, or `operator` privilege) emits a correlation record to the IBM SP activity log before executing:

```
DEFINE SCRATCHPADENTRY MCP_AUDIT DESCRIPTION="MCP_AUDIT tool=delete_admin priv=system corr=a3f8b2c19d44"
```

The correlation ID appears in both `mcp-server.log` and the IBM SP `ACTLOG`. To cross-reference:

```
* Find all MCP-originated write operations
QUERY ACTLOG SEARCH=MCP_AUDIT

* Find a specific tool call by correlation ID
QUERY ACTLOG SEARCH=corr=a3f8b2c19d44
```

If the audit write fails (permission issue, SP connectivity), an `ERROR` with marker `SECURITY [POL-4 / RG-4]` is written to `mcp-server.log`. The write operation proceeds — audit mode is advisory, not blocking.

---

## Command Approval Workflow

When `SET COMMANDAPPROVAL ON` is active on the IBM SP server, destructive commands are held in a pending queue instead of executing immediately. The MCP server provides three tools to manage this queue:

| Tool | SP command | Required privilege |
|------|------------|-------------------|
| `approve_pending_command` | `APPROVE PENDINGCMD <id>` | `system` |
| `reject_pending_command` | `REJECT PENDINGCMD <id>` | `system` |
| `withdraw_pending_command` | `WITHDRAW PENDINGCMD <id>` | `any` (issuing admin) |

Typical workflow via an AI agent:

1. AI issues a destructive command (e.g. `delete_node`) → SP queues it, returns the Command ID.
2. Operator asks the agent: *"Show me pending commands"* → `query_pending_command` lists them.
3. Operator approves or rejects: *"Approve command 42"* → `approve_pending_command {command_id: "42"}`.

With `SET APPROVERSREQUIREAPPROVAL ON`, even the approval administrator's own commands require a second approver — enforcing two-person integrity for the most sensitive operations.

---

## Example Prompts

These are examples of natural-language requests you can make through an MCP client:

**Monitoring**
```
What is the current server status?
Show me all active client sessions.
Which storage pools are above 85% utilization?
List all failed backup operations in the last 24 hours.
```

**Investigation**
```
Find all ANR error messages in the activity log from the last hour.
Which nodes have not backed up in the last 7 days?
Show the replication status for all rules.
Are there any tape alerts on the library?
```

**Administration**
```
Register a new node called PROD-SERVER-01 in the STANDARD domain.
Create an administrator account for alice with operator privilege.
Activate the STANDARD policy set on the PROD_DOMAIN policy domain.
Show me all administrators and their privilege classes.
```

**Storage**
```
Define a new disk storage pool named CLOUD_TIER of type cloud.
Show volume usage history for pool TAPE_PRIMARY.
List all libraries and their current status.
What device classes are defined?
```

**Approvals**
```
Show me all commands pending approval.
Approve pending command 42.
Withdraw pending command 17.
```

---

## Safe Usage Guidance

- **Start with read-only** when validating a new installation. Use `--mode read-only` or configure only a `mcp-svc-readonly` account until you are confident in the setup.
- **Review before confirming** — AI agents can misinterpret intent. When issuing write operations, read the generated tool call before confirming execution.
- **Use the narrowest account** — if only storage operations are needed, configure only `SP_ADMIN_ID_STORAGE` and omit system and policy accounts. The server registers only the tools the account can execute.
- **Enable command approval** in production — `SET COMMANDAPPROVAL ON` ensures no destructive command executes without human review, regardless of what the AI agent issues.
- **Never set `SP_MCP_SKIP_SECURITY_CHECKS=1` in production** — set `SP_MCP_ENV=production` in `.env` so the server aborts startup if this bypass is ever accidentally introduced.
- **Protect `.env`** — `chmod 600 /opt/sp-mcp-server/.env`. The server refuses to start if the file is group- or world-readable.

---

## Basic Validation Checklist

After installation, verify the server is working correctly:

```bash
# 1. Confirm the package is installed
cd /opt/sp-mcp-server && source .venv/bin/activate
python3 -m sp_mcp_server.main --help

# 2. Confirm dsmadmc is reachable
dsmadmc -id=mcp-svc-readonly "QUERY STATUS"

# 3. Confirm session security is STRICT on service accounts
dsmadmc -id=mcp-svc-readonly "QUERY ADMIN mcp-svc-readonly FORMAT=DETAILED" | grep -i "session security"
# Expected: Session Security: Strict

# 4. Start in read-only mode and confirm startup succeeds
python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -30
# Expected: NET-1 check passed, tool registration logged, waiting on stdin
```

---

## Log File

The MCP server writes a rotating log to `/var/log/ibm-sp-mcp-server/mcp-server.log` (or `$SP_MCP_LOG_DIR/mcp-server.log`). Key log markers:

| Log marker | Meaning |
|------------|---------|
| `NET-1: Session security check passed` | Startup security validation succeeded |
| `SECURITY [NET-1]` | Session security check failed — server will exit |
| `SECURITY [CRED-3]` | `.env` file has insecure permissions — server will exit |
| `SECURITY [RG-1]` | Production bypass attempted — server will exit |
| `SECURITY [RG-5]` | HTTP transport started without TLS — review immediately |
| `ACC-2: Registered N tools` | Confirms which tools were registered at startup |
| `POL-3: Account lockout threshold` | Advisory check result at startup |
| `POL-4: Emitting audit correlation` | Write operation is being audited |
| `SECURITY [POL-4 / RG-4]` | Audit write failed — write proceeded but has no ACTLOG record |

---

## Related Documentation

- Installation: [`install-guide.md`](install-guide.md)
- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security analysis: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
