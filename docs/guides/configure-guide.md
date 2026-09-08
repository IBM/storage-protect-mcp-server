# Configuration Guide

This guide contains MCP client configuration examples for connecting to the IBM Storage Protect MCP Server, covering all supported transports and deployment scenarios.

> **Security note**: All configurations use SSH key authentication with a dedicated non-root `mcp-runner` OS user (NET-2). The legacy `sshpass`/`StrictHostKeyChecking=no`/`root` pattern has been removed. See [`install-guide.md`](install-guide.md) for SSH key setup steps.

---

## Transport Options

The MCP server supports two transport modes:

| Transport | Flag | Authentication | Typical use |
|-----------|------|---------------|-------------|
| `stdio` (default) | `--transport stdio` | SSH key / process isolation | Local or single-client deployments |
| `http` | `--transport http` | OIDC bearer token (OAuth 2.1) | Enterprise / multi-client deployments |

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

## Part 3 — Privilege-Aware Tool Registration

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

## Part 4 — Command Approval (Optional but Recommended)

IBM SP's command-approval workflow queues destructive operations for human review before execution. The MCP server provides `approve_pending_command`, `reject_pending_command`, and `withdraw_pending_command` tools to complete the approval cycle.

Enable on the IBM SP server:

```
SET COMMANDAPPROVAL ON
SET APPROVERSREQUIREAPPROVAL ON
UPDATE ADMIN mcp-svc-system CMDAPPROVER=YES
```

With `SET APPROVERSREQUIREAPPROVAL ON`, even the `mcp-svc-system` account's own commands require a second approver — enforcing two-person integrity for the most destructive SP operations.

---

## Related Documentation

- Installation steps: [`install-guide.md`](install-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security — Network: [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Security — Integrations: [`../implement/impl-security-integrations.md`](../implement/impl-security-integrations.md)
