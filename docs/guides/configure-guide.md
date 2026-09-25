# Configuration Guide

> **Before configuring:** Complete [`planning-guide.md`](planning-guide.md) to choose your deployment topology and plan your SP server inventory, service accounts, and SSH keys. Complete [`install-guide.md`](install-guide.md) to install the MCP server software. The steps in this guide assume both are done.

This guide contains MCP client configuration examples for connecting to the IBM Storage Protect MCP Server, covering all supported transports and deployment scenarios.

> **Security note**: All configurations use SSH key authentication with a dedicated non-root `mcp-runner` OS user (NET-2). The legacy `sshpass`/`StrictHostKeyChecking=no`/`root` pattern has been removed. See [`install-guide.md`](install-guide.md) for SSH key setup steps.

---

## Transport Options

The MCP server supports two transport modes:

| Transport | Flag | Authentication | Typical use |
|-----------|------|---------------|-------------|
| `stdio` (default) | `--transport stdio` | SSH key / Tiered Service Accounts or Dynamic Challenge-Response | Local or single-client deployments (e.g. Claude Desktop) |
| `http` | `--transport http` | OIDC bearer token (OAuth 2.1) / Dynamic session tokens | Enterprise / multi-client deployments (e.g. Web UIs, REST gateways) |

---

## Part 1 — stdio Transport (SSH)

The stdio transport runs the MCP server as a subprocess launched over an SSH connection. The MCP client's stdin/stdout tunnel becomes the MCP protocol channel. No network port is opened by the MCP server itself.

### Step 1 — SSH key setup (one-time, from the MCP client workstation)

**Linux / macOS:**

```bash
# Generate a dedicated Ed25519 key
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_sp_mcp -C "mcp-server-access" -N ""

# Deploy the public key to the mcp-runner account on the SP server
ssh-copy-id -i ~/.ssh/id_ed25519_sp_mcp.pub mcp-runner@your-sp-server

# Pin the host key to prevent future MITM attacks
ssh-keyscan -H your-sp-server >> ~/.ssh/known_hosts

# Verify — must succeed without a password prompt
ssh -i ~/.ssh/id_ed25519_sp_mcp -o StrictHostKeyChecking=yes \
    -o BatchMode=yes mcp-runner@your-sp-server echo "OK"
```

**Windows (PowerShell):**

```powershell
ssh-keygen -t ed25519 -f "$HOME\.ssh\id_ed25519_sp_mcp" -C "mcp-server-access"
ssh-copy-id -i "$HOME\.ssh\id_ed25519_sp_mcp.pub" mcp-runner@your-sp-server
ssh-keyscan -H your-sp-server >> "$HOME\.ssh\known_hosts"
```

### Step 2 — MCP client configuration

Replace `your-sp-server` and the path to your virtual environment throughout.

#### Linux / macOS — full access

```json
{
  "mcpServers": {
    "sp-mcp-server": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@your-sp-server",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

#### Linux / macOS — read-only (monitoring and reporting)

```json
{
  "mcpServers": {
    "sp-mcp-readonly": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@your-sp-server",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode read-only"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

#### Linux / macOS — scoped to specific modules

Use `--enable-servers` to register only the tool groups you need. Available modules: `system`, `operations`, `clients`, `policy`, `storage`.

```json
{
  "mcpServers": {
    "sp-mcp-storage-only": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@your-sp-server",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

#### Windows — remote access to a Linux SP server

```json
{
  "mcpServers": {
    "sp-mcp-server": {
      "command": "ssh",
      "args": [
        "-i", "C:\\Users\\<your-username>\\.ssh\\id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@your-sp-server",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

#### Windows — remote access to a Windows SP server

```json
{
  "mcpServers": {
    "sp-mcp-server-windows": {
      "command": "ssh",
      "args": [
        "-i", "C:\\Users\\<your-username>\\.ssh\\id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@<windows-sp-server-ip>",
        "powershell -NoProfile -Command \"cd C:\\sp-mcp-server; .\\.venv\\Scripts\\Activate.ps1; python -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage\""
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

### `sshd_config` hardening on the SP server (recommended)

On the Linux SP server, restrict the `mcp-runner` account to key-only auth with no TTY or port-forwarding. Add to `/etc/ssh/sshd_config.d/mcp-runner.conf`:

```
Match User mcp-runner
    PasswordAuthentication no
    PubkeyAuthentication   yes
    PermitTTY              no
    AllowTcpForwarding     no
    X11Forwarding          no
```

> Do **not** add `ForceCommand` — the MCP server needs to exec arbitrary Python commands through the SSH session.

```bash
systemctl reload sshd
```

---

## Part 2 — HTTP Transport (OIDC Bearer Token)

The HTTP transport starts a local HTTPS/SSE server. Each MCP client authenticates with an OIDC bearer token issued by your enterprise identity provider. Token scopes map to IBM SP privilege tiers so each client only accesses the tools its token authorizes.

### Token scope → privilege mapping

| OIDC scope in token | SP privilege tier | Tools accessible |
|---------------------|------------------|-----------------|
| `mcp:read` | `any` | All `QUERY` / read-only tools |
| `mcp:operator` | `operator` | Operator tools + read-only |
| `mcp:storage` | `storage` | Storage tools + read-only |
| `mcp:policy` | `policy` | Policy tools + read-only |
| `mcp:system` | `system` | All tools |

### Required `.env` additions

```dotenv
# OIDC issuer — the IdP discovery URL
SP_OIDC_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0

# Audience claim the token must carry
SP_OIDC_AUDIENCE=sp-mcp-server

# TLS certificate and private key (required — server refuses to start without them)
SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
```

### Starting the HTTP transport

```bash
cd /opt/sp-mcp-server
source .venv/bin/activate
python3 -m sp_mcp_server.main \
  --transport http \
  --port 8443 \
  --mode full \
  --enable-servers system,operations,clients,policy,storage
```

> **TLS is mandatory.** The server exits with `SECURITY [RG-5]` if `SP_TLS_CERT` or `SP_TLS_KEY` are missing or the files do not exist. Set `SP_MCP_ALLOW_HTTP_PLAINTEXT=1` **only** for loopback-only test deployments (emits an `ERROR` log).

### Verify the HTTP transport

```bash
# Health check (no token required)
curl -k https://sp-mcp-01.example.com:8443/health
# Expected: {"status":"ok"}

# Tool call with a valid bearer token
curl -k -H "Authorization: Bearer <oidc-access-token>" \
  https://sp-mcp-01.example.com:8443/mcp/sse
```

### MCP client configuration for HTTP transport

```json
{
  "mcpServers": {
    "sp-mcp-http": {
      "url": "https://sp-mcp-01.example.com:8443/mcp/sse",
      "headers": {
        "Authorization": "Bearer <oidc-access-token>"
      }
    }
  }
}
```

> Replace `<oidc-access-token>` with a token obtained from your IdP with the appropriate `mcp:*` scope. Tokens are short-lived — automate refresh in your deployment tooling.

---

## Part 3 — Dynamic & Delegated User Authentication (Challenge-Response)

When the MCP server is deployed for interactive AI chat environments (e.g. Claude Desktop, OpenWebUI, or IDE extensions), human administrators interact with tools directly. Instead of embedding static passwords in shared daemon configurations, the server can be configured in **Dynamic Authentication Mode**.

### Enabling Dynamic Authentication

In your `.env` file (or environment):

```dotenv
# Enable Dynamic Challenge-Response mode
SP_MCP_AUTH_MODE=dynamic

# Sliding inactivity timeout in seconds (default: 15 minutes)
SP_MCP_SESSION_TTL=900

# Maximum hard session lease duration in seconds (default: 60 minutes)
SP_MCP_SESSION_MAX_TTL=3600
```

### How Challenge-Response Works in Chat

```mermaid
sequenceDiagram
    autonumber
    participant User as Human Operator
    participant AI as AI Assistant (Claude / Chat UI)
    participant MCP as MCP Server
    participant SP as IBM Storage Protect (dsmadmc)

    User->>AI: "List all registered nodes and their storage usage."
    AI->>MCP: call_tool("query_node", {})
    Note over MCP: SP_MCP_AUTH_MODE=dynamic: No active session lease found
    MCP-->>AI: AUTHENTICATION_REQUIRED (JSON Challenge Schema)
    AI-->>User: "To access IBM Storage Protect, please provide your administrator username and password."
    User->>AI: Provides credentials (admin_alice / password)
    AI->>MCP: call_tool("authenticate_session", {username: "admin_alice", password: "***"})
    Note over MCP: Zero-trace verification via execute_silent (passwords not logged)
    MCP->>SP: dsmadmc QUERY STATUS / QUERY ADMIN
    SP-->>MCP: Authenticated (ANR0000I)
    Note over MCP: Mint ephemeral lease (TTL=15m) & bind current_audit_user
    MCP-->>AI: {"success": true, "username": "admin_alice", "expires_in_seconds": 900}
    AI->>MCP: Re-calls original tool: "query_node", {}
    MCP->>SP: dsmadmc QUERY NODE
    SP-->>MCP: Node records
    MCP-->>AI: Tool result payload
    AI-->>User: Formatted node listing
```

### Security Properties of Dynamic Authentication
1. **Zero-Trace Credential Verification**: Passwords provided to `authenticate_session` are verified via [`cli_wrapper.DsmAdmcWrapper.execute_silent()`](../../src/sp_mcp_server/cli_wrapper.py) and are **never** logged to `/var/log/ibm-sp-mcp-server/mcp-server.log` or shell process trees.
2. **Ephemeral In-Memory Leases**: Session leases are kept only in memory with a sliding inactivity window (`SP_MCP_SESSION_TTL`, default 15 minutes) and are destroyed upon process restart or explicit timeout.
3. **Forensic Attribution (Non-Repudiation)**: Once authenticated, the user's verified identity is stored in `current_audit_user` ContextVar and emitted to the IBM Storage Protect Activity Log (`DEFINE SCRATCHPADENTRY MCP_AUDIT user=<username> ...`) for every modifying operation.

---

## Part 4 — Privilege-Aware Tool Registration

The MCP server automatically narrows the registered tool set at startup based on the IBM SP privilege class of the configured service account. This is the primary access control gate and operates independently of `--mode`.

| Configured account privilege | Tools registered |
|------------------------------|-----------------|
| `system` | All tools (100%) |
| `policy` | Policy + read-only tools |
| `storage` | Storage + read-only tools |
| `operator` | Operator + read-only tools |
| `any` (read-only) | Query/read-only tools only |

### Combining `--mode` and service account privilege

| Scenario | `--mode` | Account | Net effect |
|----------|----------|---------|-----------|
| Full monitoring + admin | `full` | `system` credential | All tools registered |
| Monitoring only | `read-only` | any | Only query tools, even if account is `system` |
| Storage management only | `full` | `storage` credential | Storage + query tools; no policy or system tools |
| Read-only by account | `full` | `any` (readonly) credential | Only query tools (mode filter redundant) |

---

## Part 5 — Command Approval (Optional but Recommended)

IBM SP's command-approval workflow queues destructive operations for human review before execution. The MCP server provides `approve_pending_command`, `reject_pending_command`, and `withdraw_pending_command` tools to complete the approval cycle.

Enable on the IBM SP server:

```
SET COMMANDAPPROVAL ON
SET APPROVERSREQUIREAPPROVAL ON
UPDATE ADMIN mcp-svc-system CMDAPPROVER=YES
```

With `SET APPROVERSREQUIREAPPROVAL ON`, even the `mcp-svc-system` account's own commands require a second approver — enforcing two-person integrity for the most destructive SP operations.

---

## Part 6 — Managing Multiple SP Servers

The MCP server is a **one-process-to-one-SP-server** deployment unit. A single MCP server process connects to exactly one IBM SP server defined by `TCPSERVERADDRESS` in its `.env`. To manage multiple SP servers from a single AI agent session, run one MCP server process per SP server and register each as a separate named entry in the MCP client configuration.

Two deployment topologies are supported — see [`planning-guide.md`](planning-guide.md) for diagrams, a comparison table, pros/cons, and the full pre-installation checklist. Follow only the section matching your chosen topology.

> **`isp_server_name` parameter note:** Many tools expose an `isp_server_name` optional parameter in their schema. This parameter is documented ahead of a planned multi-server registry feature and is **not yet wired into command execution** — it is currently ignored at runtime. Until that feature is implemented, use the per-process pattern below to target a specific SP server.

---

### Topology A — Co-located (MCP Server on each SP Server host)

Each MCP server process runs on the same host as the IBM SP server it manages. The MCP client SSH-es to each SP server host independently. See [`planning-guide.md`](planning-guide.md) for the full topology diagram and comparison.

#### Step A-1 — Install on each SP server host

Follow [`install-guide.md` — Topology A](install-guide.md) on every SP server host. Each host gets:

- `mcp-runner` OS user and `.venv` under `/opt/sp-mcp-server/`
- Its own `/opt/sp-mcp-server/.env` with `TCPSERVERADDRESS` pointing at that host's SP server
- Five service accounts provisioned via `scripts/provision-sp-service-accounts.sh`
- Its own `dsm.sys` with a unique `SERVERNAME` stanza and stash populated per account

#### Step A-2 — SSH key setup (one-time, from the MCP client workstation)

Generate a **dedicated key per SP server host** so a compromised key for one server does not expose the others:

```bash
# Key for SPSVR01
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_spsvr01 -C "mcp-spsvr01" -N ""
ssh-copy-id -i ~/.ssh/id_ed25519_spsvr01.pub mcp-runner@spsvr01.corp.example.com
ssh-keyscan -H spsvr01.corp.example.com >> ~/.ssh/known_hosts

# Key for SPSVR02
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_spsvr02 -C "mcp-spsvr02" -N ""
ssh-copy-id -i ~/.ssh/id_ed25519_spsvr02.pub mcp-runner@spsvr02.corp.example.com
ssh-keyscan -H spsvr02.corp.example.com >> ~/.ssh/known_hosts

# Verify — each must succeed without a password prompt
ssh -i ~/.ssh/id_ed25519_spsvr01 -o StrictHostKeyChecking=yes \
    -o BatchMode=yes mcp-runner@spsvr01.corp.example.com echo "OK"
ssh -i ~/.ssh/id_ed25519_spsvr02 -o StrictHostKeyChecking=yes \
    -o BatchMode=yes mcp-runner@spsvr02.corp.example.com echo "OK"
```

#### Step A-3 — MCP client configuration

Register each SP server host as a separate named MCP server entry. The MCP client SSH-es to each host and starts the process there.

```json
{
  "mcpServers": {
    "sp-mcp-spsvr01": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_spsvr01",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@spsvr01.corp.example.com",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    },
    "sp-mcp-spsvr02": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_spsvr02",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@spsvr02.corp.example.com",
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

> Each entry launches an independent process. The MCP client connects to all entries simultaneously. Each process runs its own NET-1 session security check and registers only the tools the configured service accounts permit.

#### Step A-4 — Per-server `.env` layout

The only variable that changes between hosts is `TCPSERVERADDRESS`.

**`/opt/sp-mcp-server/.env` on `spsvr01.corp.example.com`:**
```dotenv
# chmod 600, chown mcp-runner:mcp-runner
TCPSERVERADDRESS=spsvr01.corp.example.com
SP_SERVER_PORT=1500
SP_ADMIN_ID_SYSTEM=mcp-svc-system
SP_ADMIN_ID_POLICY=mcp-svc-policy
SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_ID_OPERATOR=mcp-svc-operator
SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_MCP_USE_PASSWORD_STASH=1
DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/tmp/servermon
SP_INSTANCE_USER=tsminst1
SP_MCP_ENV=production
```

**`/opt/sp-mcp-server/.env` on `spsvr02.corp.example.com`:** — identical except:
```dotenv
TCPSERVERADDRESS=spsvr02.corp.example.com
```

#### Step A-5 — Provisioning checklist (repeat per SP server host)

```
[ ] mcp-runner OS user created; /opt/sp-mcp-server owned by mcp-runner
[ ] Python venv at /opt/sp-mcp-server/.venv; package installed
[ ] dsmadmc available in PATH for mcp-runner
[ ] scripts/provision-sp-service-accounts.sh run on this SP server
[ ] QUERY ADMIN mcp-svc-* shows SESSIONSECURITY=Strict for all 5 accounts
[ ] dsm.sys at /opt/sp-mcp-server/config/dsm.sys; SERVERNAME unique (e.g. SP_SPSVR01)
[ ] Password stash populated per account; SP_MCP_USE_PASSWORD_STASH=1 confirmed working
[ ] .env at /opt/sp-mcp-server/.env; chmod 600; TCPSERVERADDRESS set to this SP server
[ ] SP_MCP_ENV=production set in .env
[ ] sudoers rule deployed for dsmserv/servermon (if offline tools needed)
[ ] Dedicated Ed25519 key generated and deployed to mcp-runner@<this-host>
[ ] Host key pinned in known_hosts on the MCP client workstation
[ ] MCP client config entry added; StrictHostKeyChecking=yes; correct key per host
[ ] Startup verified via SSH: NET-1 check passes, tools registered
[ ] sshd_config hardened: PasswordAuthentication no, PermitTTY no, AllowTcpForwarding no
```

---

### Topology B — Centralised (all MCP Servers on one Control Host)

All MCP server processes run on a single dedicated control host. The MCP client SSH-es only to that one host. Each process runs from its own subdirectory (`/opt/sp-mcp/<servername>/`) and loads its own `.env` pointing remotely at its respective SP server over TCP 1500. See [`planning-guide.md`](planning-guide.md) for the full topology diagram, pros/cons, and comparison.

> **How `.env` isolation works in Topology B:** `secure_startup()` resolves `.env` relative to the **current working directory** of the process. Each MCP client config entry uses `cd /opt/sp-mcp/<servername>` before launching Python, so that process loads its own `.env` — with no `--env-file` flag needed.

#### Step B-1 — Install on the control host (once)

Follow [`install-guide.md` — Topology B](install-guide.md) on the control host. This creates:

- `mcp-runner` OS user with home at `/opt/sp-mcp/`
- A shared Python venv at `/opt/sp-mcp/shared/.venv`
- One subdirectory per SP server: `/opt/sp-mcp/spsvr01/`, `/opt/sp-mcp/spsvr02/`, ...
- One `.env` per subdirectory, each with its own `TCPSERVERADDRESS`
- A single `dsm.sys` at `/opt/sp-mcp/config/dsm.sys` with one stanza per SP server

#### Step B-2 — SSH key setup (one-time, from the MCP client workstation)

A single key to the control host is sufficient. Generate a dedicated key for the control host:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_ctrl -C "mcp-ctrl-access" -N ""
ssh-copy-id -i ~/.ssh/id_ed25519_ctrl.pub mcp-runner@ctrl.corp.example.com
ssh-keyscan -H ctrl.corp.example.com >> ~/.ssh/known_hosts

# Verify
ssh -i ~/.ssh/id_ed25519_ctrl -o StrictHostKeyChecking=yes \
    -o BatchMode=yes mcp-runner@ctrl.corp.example.com echo "OK"
```

#### Step B-3 — MCP client configuration

Each entry SSH-es to the **same control host** but changes the working directory (`cd`) before starting Python, so each process loads a different `.env`.

```json
{
  "mcpServers": {
    "sp-mcp-spsvr01": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_ctrl",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@ctrl.corp.example.com",
        "cd /opt/sp-mcp/spsvr01 && source /opt/sp-mcp/shared/.venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    },
    "sp-mcp-spsvr02": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_ctrl",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "mcp-runner@ctrl.corp.example.com",
        "cd /opt/sp-mcp/spsvr02 && source /opt/sp-mcp/shared/.venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

> The `cd /opt/sp-mcp/<servername>` before `python3 -m sp_mcp_server.main` is what causes each process to load its own `.env`. This is the only mechanism — there is no `--env-file` flag.

#### Step B-4 — Per-server `.env` layout on the control host

```dotenv
# /opt/sp-mcp/spsvr01/.env  — chmod 600, chown mcp-runner:mcp-runner
TCPSERVERADDRESS=spsvr01.corp.example.com
SP_SERVER_PORT=1500
SP_ADMIN_ID_SYSTEM=mcp-svc-system
SP_ADMIN_ID_POLICY=mcp-svc-policy
SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_ID_OPERATOR=mcp-svc-operator
SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_MCP_USE_PASSWORD_STASH=1
DSM_CONFIG=/opt/sp-mcp/config/dsm.sys
SP_MCP_ENV=production
# SP_INSTANCE_USER / SP_DSMSERV_PATH / SP_SERVERMON_PATH — omit in Topology B
```

`/opt/sp-mcp/spsvr02/.env` — identical except `TCPSERVERADDRESS=spsvr02.corp.example.com`.

#### Step B-5 — Security controls in Topology B

Every security control applies, with the following Topology B-specific notes:

| Control | Topology B behaviour |
|---|---|
| **NET-1** `SESSIONSECURITY=STRICT` | Each process validates against its own remote SP server at startup. A failure on one process does not affect others. |
| **CRED-1** Five tiered accounts | Service accounts are on the remote SP servers — provisioned identically to Topology A. |
| **CRED-2** Password stash | All stash entries live in `~mcp-runner/.tsm/` on the control host. Each entry is keyed by `SERVERNAME` + account ID — stanza names in `dsm.sys` must be unique per SP server. |
| **CRED-3** `.env` `0600` permission check | Each process checks its own per-server `.env`. All `.env` files are on the control host — OS directory permissions on `/opt/sp-mcp/` must restrict access to `mcp-runner` only. |
| **NET-2** SSH key auth | One key to the control host. The control host's `sshd_config` should still enforce `PasswordAuthentication no`, `PermitTTY no`, `AllowTcpForwarding no` for the `mcp-runner` user. |
| **POL-4** ACTLOG audit | Audit records are on each remote SP server's ACTLOG. Run `QUERY ACTLOG SEARCH=MCP_AUDIT` on each SP server individually. |
| **RG-1** Production bypass guard | `SP_MCP_ENV=production` must be set in each per-server `.env`. |
| **Offline tools** | ❌ Not supported. `dsmserv` and `servermon` require local SP server binaries. |

#### Step B-6 — Provisioning checklist (control host)

```
[ ] mcp-runner OS user created; /opt/sp-mcp owned by mcp-runner; mode 700
[ ] Python venv at /opt/sp-mcp/shared/.venv; package installed
[ ] dsmadmc installed on control host and in mcp-runner's PATH
[ ] TCP 1500 verified open from control host to each SP server (nc -zv <host> 1500)
[ ] Per-server subdirectory created: /opt/sp-mcp/<servername>/
[ ] Per-server .env created; chmod 600; TCPSERVERADDRESS set per SP server
[ ] SP_MCP_ENV=production set in each per-server .env
[ ] scripts/provision-sp-service-accounts.sh run on each SP server
[ ] QUERY ADMIN mcp-svc-* shows SESSIONSECURITY=Strict on each SP server
[ ] dsm.sys at /opt/sp-mcp/config/dsm.sys; one unique SERVERNAME stanza per SP server
[ ] Password stash populated on control host for each account × each SP server stanza
[ ] SP_MCP_USE_PASSWORD_STASH=1 set in each per-server .env
[ ] Ed25519 key generated; deployed to mcp-runner@ctrl.corp.example.com
[ ] ctrl host key pinned in known_hosts on the MCP client workstation
[ ] MCP client config entries added; each uses cd /opt/sp-mcp/<servername> before python3
[ ] Startup verified per entry: NET-1 check passes, tools registered
[ ] sshd_config on ctrl host: PasswordAuthentication no, PermitTTY no, AllowTcpForwarding no
[ ] Offline tools (dsmserv/servermon) explicitly NOT configured — not supported in Topology B
```

---

### Common — Scoping tools per server (both topologies)

Different SP servers may need different tool scopes regardless of topology. Use `--mode` and `--enable-servers` per MCP client config entry:

```json
"sp-mcp-spsvr01-full":      { "args": ["...", "python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"] },
"sp-mcp-spsvr02-ops-only":  { "args": ["...", "python3 -m sp_mcp_server.main --mode full --enable-servers operations,clients"] },
"sp-mcp-spsvr03-readonly":  { "args": ["...", "python3 -m sp_mcp_server.main --mode read-only"] }
```

### Common — Addressing multiple servers in prompts (both topologies)

The registered MCP server name becomes the routing key the AI agent uses to target a specific SP server:

```text
On sp-mcp-spsvr01, show me all failed backup operations from the last 24 hours.
```

```text
Compare storage pool utilisation on sp-mcp-spsvr01 and sp-mcp-spsvr02.
```

```text
Register node APPSVR10_NODE in policy domain DOM_GENERAL on sp-mcp-spsvr02.
```

### Common — Security controls applicable to both topologies

Every security control applies independently per MCP server process regardless of topology:

| Control | Scope | Notes |
|---|---|---|
| **NET-1** `SESSIONSECURITY=STRICT` | Per process at startup | Each process validates its own SP server. A failure on one does not affect others. |
| **CRED-1** Five tiered service accounts | Per SP server | Accounts are on the IBM SP server — provisioned identically in both topologies. |
| **CRED-3** `.env` `0600` check | Per process at startup | Each process checks its own `.env` before reading any secret. |
| **POL-4** ACTLOG audit attribution | Per SP server | Run `QUERY ACTLOG SEARCH=MCP_AUDIT` on each SP server to retrieve its own audit trail. |
| **RG-1** Production bypass guard | Per process | `SP_MCP_ENV=production` required in each `.env`. |

---

## Related Documentation

- Deployment planning: [`planning-guide.md`](planning-guide.md)
- Installation steps: [`install-guide.md`](install-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security — Identity & Credentials: [`../design/security-identity-credentials.md`](../design/security-identity-credentials.md)
- Security — Network: [`../design/security-network.md`](../design/security-network.md)
- Security — Implementation (Credentials): [`../implement/impl-security-identity-credentials.md`](../implement/impl-security-identity-credentials.md)
- Security — Implementation (Network): [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Security — Integrations: [`../implement/impl-security-integrations.md`](../implement/impl-security-integrations.md)
