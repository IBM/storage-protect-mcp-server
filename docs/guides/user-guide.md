# User Guide

> **Prerequisites:** Complete [`planning-guide.md`](planning-guide.md), [`install-guide.md`](install-guide.md), and [`configure-guide.md`](configure-guide.md) before using this guide. The steps here assume the server is installed, service accounts are provisioned, and the MCP client is configured.

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

After completing [`install-guide.md`](install-guide.md) and [`configure-guide.md`](configure-guide.md), the MCP client launches the server automatically via SSH. The commands below are for **manual testing only**.

### Topology A — manual test on an SP server host

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

### Topology B — manual test on the control host

Each process must be started from its SP-server-specific subdirectory so `secure_startup()` loads the correct `.env`:

```bash
source /opt/sp-mcp/shared/.venv/bin/activate

# Test the process that targets SPSVR01
cd /opt/sp-mcp/spsvr01
python3 -m sp_mcp_server.main --mode read-only

# Test the process that targets SPSVR02
cd /opt/sp-mcp/spsvr02
python3 -m sp_mcp_server.main --mode read-only
```

> In production, the MCP client starts each process automatically using the `cd /opt/sp-mcp/<servername>` command in each MCP client config entry — see [`configure-guide.md` — Part 5](configure-guide.md#part-5--managing-multiple-sp-servers).

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

## Managing Multiple SP Servers

The MCP server is a **one-process-to-one-SP-server** deployment unit. A single MCP server process connects to exactly one IBM SP server defined by `TCPSERVERADDRESS` in its `.env`. To manage multiple SP servers from a single AI agent session, run one MCP server process per SP server and register each as a separate named entry in the MCP client configuration.

Two deployment topologies are supported — see [`planning-guide.md`](planning-guide.md) for the full comparison:

**Topology A — Co-located:** each process runs on the SP server host it manages; the MCP client SSH-es to each host independently.
```
AI Agent  ──SSH──▶  mcp-runner@spsvr01  ──dsmadmc──▶  SPSVR01
          ──SSH──▶  mcp-runner@spsvr02  ──dsmadmc──▶  SPSVR02
```

**Topology B — Centralised:** all processes run on one control host; the MCP client SSH-es only there; each process targets its SP server remotely over TCP 1500.
```
AI Agent  ──SSH──▶  mcp-runner@ctrl  ──[cwd: /opt/sp-mcp/spsvr01]── dsmadmc ──▶  SPSVR01
                                      ──[cwd: /opt/sp-mcp/spsvr02]── dsmadmc ──▶  SPSVR02
```

Each process starts up independently, runs its own NET-1 session security check, and registers only the tools the configured service accounts permit. A failure on one process does not affect the others.

### Addressing a specific server in prompts

The registered MCP server name (e.g. `sp-mcp-spsvr01`) becomes the routing key the AI agent uses to target operations at a specific SP server:

```
On sp-mcp-spsvr01, show me all failed backup operations from the last 24 hours.
```

```
Compare storage pool utilisation on sp-mcp-spsvr01 and sp-mcp-spsvr02.
```

```
Register node APPSVR10_NODE in policy domain DOM_GENERAL on sp-mcp-spsvr02.
```

### `isp_server_name` parameter note

Many tools expose an optional `isp_server_name` parameter in their schema. This parameter is documented ahead of a planned multi-server registry feature and is **not yet wired into command execution** — it is currently ignored at runtime. Until that feature is implemented, use the per-process pattern above (one named MCP server entry per SP host) to target a specific SP server.

For full setup instructions — SSH key generation, MCP client JSON configuration, per-server `.env` files, and per-topology provisioning checklists — see [`configure-guide.md` — Part 5](configure-guide.md#part-5--managing-multiple-sp-servers). For pre-installation planning and topology selection, see [`planning-guide.md`](planning-guide.md).

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

> **Multi-server deployments:** Audit records are distributed across each server's own ACTLOG. Run `QUERY ACTLOG SEARCH=MCP_AUDIT` on **each SP server individually** — there is no aggregated cross-server view.

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

**Multi-server targeting**
```
On sp-mcp-spsvr01, show me all failed backup operations from the last 24 hours.
```

```
Compare storage pool utilisation on sp-mcp-spsvr01 and sp-mcp-spsvr02.
```

```
Register node APPSVR10_NODE in policy domain DOM_GENERAL on sp-mcp-spsvr02.
```

```
Which nodes have not backed up in the last 7 days on sp-mcp-spsvr03?
```

---

## Safe Usage Guidance

- **Start with read-only** when validating a new installation. Use `--mode read-only` or configure only a `mcp-svc-readonly` account until you are confident in the setup.
- **Review before confirming** — AI agents can misinterpret intent. When issuing write operations, read the generated tool call before confirming execution.
- **Use the narrowest account** — if only storage operations are needed, configure only `SP_ADMIN_ID_STORAGE` and omit system and policy accounts. The server registers only the tools the account can execute.
- **Enable command approval** in production — `SET COMMANDAPPROVAL ON` ensures no destructive command executes without human review, regardless of what the AI agent issues.
- **Never set `SP_MCP_SKIP_SECURITY_CHECKS=1` in production** — set `SP_MCP_ENV=production` in every `.env` so the server aborts startup if this bypass is ever accidentally introduced.
- **Protect `.env`** — `chmod 600` on every `.env` file (Topology A: `/opt/sp-mcp-server/.env` per host; Topology B: `/opt/sp-mcp/<servername>/.env` on the control host). The server refuses to start if the file is group- or world-readable.
- **SSH key discipline** — Topology A: use a dedicated Ed25519 key pair per SP server host so a compromised key for one server cannot access others. Topology B: use a dedicated key for the control host and protect it accordingly — a compromised control-host key exposes all SP server processes. See [`planning-guide.md` — Step 6](planning-guide.md).

---

## Basic Validation Checklist

After installation, verify the server is working correctly.

### Topology A — run on each SP server host

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

Verify via SSH from the MCP client workstation before registering the entry in the MCP client config:

```bash
# Replace key and hostname for each SP server host
ssh -i ~/.ssh/id_ed25519_spsvr01 \
    -o StrictHostKeyChecking=yes -o BatchMode=yes \
    mcp-runner@spsvr01.corp.example.com \
    "cd /opt/sp-mcp-server && source .venv/bin/activate && \
     python3 -m sp_mcp_server.main --mode read-only 2>&1 | head -20"
```

### Topology B — run on the control host, once per SP server subdirectory

```bash
source /opt/sp-mcp/shared/.venv/bin/activate

# Verify for SPSVR01
cd /opt/sp-mcp/spsvr01
dsmadmc -id=mcp-svc-readonly -se=SP_SPSVR01 "QUERY STATUS"
python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -30
# Expected: NET-1 check passed, tool registration logged, waiting on stdin

# Verify for SPSVR02
cd /opt/sp-mcp/spsvr02
dsmadmc -id=mcp-svc-readonly -se=SP_SPSVR02 "QUERY STATUS"
python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -30
```

Verify via SSH from the MCP client workstation before registering entries in the MCP client config:

```bash
# Replace subdirectory path for each SP server entry
ssh -i ~/.ssh/id_ed25519_ctrl \
    -o StrictHostKeyChecking=yes -o BatchMode=yes \
    mcp-runner@ctrl.corp.example.com \
    "cd /opt/sp-mcp/spsvr01 && source /opt/sp-mcp/shared/.venv/bin/activate && \
     python3 -m sp_mcp_server.main --mode read-only 2>&1 | head -20"
```

---

## Log File

The MCP server writes a rotating log to `/var/log/ibm-sp-mcp-server/mcp-server.log` (or `$SP_MCP_LOG_DIR/mcp-server.log`). Key log markers:

> **Topology A:** Each MCP process writes to the log on its own SP server host. Set `SP_MCP_LOG_DIR` to the same path on every host to make log collection uniform. Check each host's log independently when investigating issues.
>
> **Topology B:** All MCP processes run on the control host and write to the **same log file**. Filter by timestamp or process ID to distinguish entries from different SP server processes. Set `SP_MCP_LOG_DIR` consistently across all per-server `.env` files — or leave it at the default so all processes share `/var/log/ibm-sp-mcp-server/mcp-server.log`.

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

- Deployment planning: [`planning-guide.md`](planning-guide.md)
- Installation: [`install-guide.md`](install-guide.md)
- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security analysis: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
