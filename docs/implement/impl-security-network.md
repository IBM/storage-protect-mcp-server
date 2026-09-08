# Implementation: Network Security

* **Domain**: Network Security
* **Analysis reference**: [`docs/analysis/security-design-analysis.md § 1`](../analysis/security-design-analysis.md)
* **Gaps addressed**: N1, N2, N3, RG-1
* **Files changed**: `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/config.py`, `docs/guides/configure-guide.md`, new `dsm.sys` deployment artifact

---

## Overview

Three changes close all network-layer gaps:

| ID | Change | Gaps closed |
|----|--------|-------------|
| NET-1 | Startup `SESSIONSECURITY=STRICT` validation in `mcp_factory.py` | N1 |
| NET-2 | Replace `sshpass` in `configure-guide.md` with SSH key auth | N2 |
| NET-3 | Ship a hardened `dsm.sys` template that enforces `SSLREQUIRED=YES` | N3 |
| RG-1 | Production guard: `SP_MCP_SKIP_SECURITY_CHECKS=1` blocked when `SP_MCP_ENV=production` | RG-1 |

---

## NET-1 — Startup Session Security Validation

### What to change

**File**: [`src/sp_mcp_server/mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py)

Add a `_validate_session_security(admc_cli, config)` function called immediately after the CLI wrappers are initialised, before any tool classes are registered. If the account is not on `STRICT` TLS, the server refuses to start.

### Implementation

```python
# src/sp_mcp_server/mcp_factory.py

def _validate_session_security(admc_cli: DsmAdmcWrapper, config) -> None:
    """
    Assert that the configured SP service account has SESSIONSECURITY=STRICT.
    Refuses server startup if the check fails.
    Called once per create_mcp_server() invocation before tool registration.
    """
    stdout, stderr, code = admc_cli.execute(
        f"QUERY ADMIN {config.admin_id} FORMAT=DETAILED"
    )
    if code != 0:
        logger.error(
            "SECURITY [NET-1]: Cannot query service account '%s'. "
            "Verify SP_ADMIN_ID and connectivity. stderr: %s",
            config.admin_id, stderr
        )
        sys.exit(1)

    # IBM SP QUERY ADMIN FORMAT=DETAILED output contains:
    #   Session Security: Strict
    #   Transport Method: TLS 1.2
    lines = {
        line.split(":")[0].strip(): line.split(":", 1)[1].strip()
        for line in stdout.splitlines()
        if ":" in line
    }

    session_security = lines.get("Session Security", "").strip()
    transport_method = lines.get("Transport Method", "").strip()

    if session_security.lower() != "strict":
        logger.error(
            "SECURITY [NET-1]: Service account '%s' has SESSIONSECURITY=%s. "
            "Required: STRICT. Run on SP server: "
            "UPDATE ADMIN %s SESSIONSECURITY=STRICT",
            config.admin_id, session_security or "(unknown)", config.admin_id
        )
        sys.exit(1)

    if transport_method and "TLS" not in transport_method.upper():
        logger.error(
            "SECURITY [NET-1]: Service account '%s' transport is '%s'. "
            "TLS 1.2 or TLS 1.3 required.",
            config.admin_id, transport_method
        )
        sys.exit(1)

    logger.info(
        "NET-1: Session security OK — account '%s': %s / %s",
        config.admin_id, session_security, transport_method
    )
```

Insert the call in `create_mcp_server()` right after the wrappers are created:

```python
def create_mcp_server(server_name: str, tool_classes: List[Any], allowed_modes: List[str] = None):
    config = load_config()

    admc_cli = DsmAdmcWrapper(config)
    serv_cli = DsmServWrapper(config)
    mon_cli  = ServermonWrapper(config)

    # ── NEW: network security check before any tool registration ──
    _validate_session_security(admc_cli, config)
    # ──────────────────────────────────────────────────────────────

    commands = {}
    # ... rest of existing function unchanged
```

### SP server prerequisite

Run once on each IBM SP server for every MCP service account before deploying the MCP server:

```
UPDATE ADMIN mcp-svc-system   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-storage  SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-policy   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT
```

Verify with:
```
QUERY ADMIN mcp-svc-system FORMAT=DETAILED
```
Expected output excerpt:
```
  Session Security: Strict
  Transport Method: TLS 1.2
```

### Behaviour matrix

| Account `SESSIONSECURITY` | `Transport Method` | MCP server startup |
|--------------------------|--------------------|--------------------|
| `Strict` | `TLS 1.2` or `TLS 1.3` | ✅ Allowed |
| `Strict` | (blank / unknown) | ✅ Allowed (TLS check is advisory warning only) |
| `Transitional` | any | ❌ `sys.exit(1)` with remediation message |
| Query fails (wrong creds, SP unreachable) | — | ❌ `sys.exit(1)` with connectivity message |

### Env-var override for testing

To disable the check in unit tests where no live SP server is available, honour an environment variable:

```python
if os.environ.get("SP_MCP_SKIP_SECURITY_CHECKS") == "1":
    logger.warning("NET-1: SESSIONSECURITY check SKIPPED (SP_MCP_SKIP_SECURITY_CHECKS=1)")
    return
```

> **Never set `SP_MCP_SKIP_SECURITY_CHECKS=1` in production.**

---

## NET-2 — SSH Key Authentication for Remote Access

### What to change

**File**: [`docs/guides/configure-guide.md`](../guides/configure-guide.md)

Remove the `sshpass` block entirely. Replace with the key-based pattern below. The change is documentation-only; no source code modification is required.

### OS setup steps (one-time, on the operator's workstation)

```bash
# 1. Generate a dedicated Ed25519 key for MCP server access
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_sp_mcp -C "mcp-server-access" -N ""

# 2. Create the dedicated non-root OS user on the SP server (run on server)
#    Replace 'your-sp-server' and adjust the home dir as needed
ssh root@your-sp-server \
  "useradd -m -d /opt/sp-mcp-server -s /bin/bash mcp-runner && \
   mkdir -p /opt/sp-mcp-server/.ssh && \
   chmod 700 /opt/sp-mcp-server/.ssh"

# 3. Deploy the public key
ssh-copy-id -i ~/.ssh/id_ed25519_sp_mcp.pub mcp-runner@your-sp-server

# 4. Verify — should open a shell without a password prompt
ssh -i ~/.ssh/id_ed25519_sp_mcp mcp-runner@your-sp-server echo "OK"
```

### Replacement MCP client config (Linux)

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
        "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --mode read-only"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

### Replacement MCP client config (Windows)

```json
{
  "mcpServers": {
    "sp-mcp-server-windows": {
      "command": "ssh",
      "args": [
        "-i", "C:\\Users\\<your-username>\\.ssh\\id_ed25519_sp_mcp",
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

### `sshd_config` hardening on the SP server (recommended)

Add to `/etc/ssh/sshd_config` (or a drop-in under `/etc/ssh/sshd_config.d/`):

```
# Restrict mcp-runner to key auth only, no TTY, no port-forwarding
Match User mcp-runner
    PasswordAuthentication no
    PubkeyAuthentication   yes
    PermitTTY              no
    AllowTcpForwarding     no
    X11Forwarding          no
    ForceCommand           /usr/sbin/nologin
```

> Remove the `ForceCommand` line if the MCP server must be able to run commands via SSH. The `mcp-runner` account's shell (`/bin/bash`) is sufficient; `ForceCommand` is only appropriate if you want to lock the account to a specific command.

### `known_hosts` pinning for production

After the first successful connection, pin the server's host key:

```bash
ssh-keyscan -H your-sp-server >> ~/.ssh/known_hosts
```

With `StrictHostKeyChecking=yes`, any subsequent connection to a different host key (indicating MITM or host replacement) will fail closed.

---

## NET-3 — `dsm.sys` TLS Certificate Trust

### What to add

**New file**: `config/dsm.sys.template` (shipped with the MCP server package)

This file is used by the `mcp-runner` OS account's `dsmadmc` invocations to enforce TLS independently of the SP account `SESSIONSECURITY` setting.

```
* dsm.sys — IBM Storage Protect dsmadmc client options
* Used by the MCP server's OS user (mcp-runner).
* Place at: /opt/sp-mcp-server/config/dsm.sys
* Set env: DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys

SERVERNAME          SP_SERVER_1

* ── Connection ────────────────────────────────
TCPSERVERADDRESS    your-sp-server
TCPPORT             1500
COMMMETHOD          TCPIP

* ── TLS ───────────────────────────────────────
* SSL=Yes: use TLS for authentication only (default from v8.1.2+)
* SSLREQUIRED=Yes: refuse to connect if TLS negotiation fails
SSL                 Yes
SSLREQUIRED         Yes

* ── Password storage ──────────────────────────
* PASSWORDACCESS GENERATE stores the password in an encrypted stash.
* Run dsmadmc once interactively to populate the stash, then the
* MCP server no longer needs -PA= on the command line.
PASSWORDACCESS      GENERATE
```

### Deployment steps

```bash
# 1. Copy the template to the deployment directory
cp config/dsm.sys.template /opt/sp-mcp-server/config/dsm.sys
sed -i "s/your-sp-server/${SP_SERVER_ADDRESS}/" /opt/sp-mcp-server/config/dsm.sys
chmod 600 /opt/sp-mcp-server/config/dsm.sys

# 2. Point dsmadmc to this config file
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys

# 3. Populate the encrypted password stash (interactive — one-time per account)
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
# After this run, dsmadmc reads the password from the stash automatically.

# 4. Verify TLS is in use
dsmadmc -id=mcp-svc-system "QUERY ADMIN mcp-svc-system FORMAT=DETAILED" | grep -i transport
# Expected: Transport Method: TLS 1.2
```

### `DsmAdmcWrapper` integration

Once `PASSWORDACCESS GENERATE` is configured, remove `-PA=` from the argument list in [`cli_wrapper.py`](../../src/sp_mcp_server/cli_wrapper.py). See **impl-security-identity-credentials.md § CRED-2** for the matching code change.

### `dsm.sys` for multiple SP servers

For multi-server deployments, add one `SERVERNAME` stanza per SP server:

```
SERVERNAME          SP_SERVER_1
TCPSERVERADDRESS    sp-server-01.example.com
TCPPORT             1500
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE

SERVERNAME          SP_SERVER_2
TCPSERVERADDRESS    sp-server-02.example.com
TCPPORT             1500
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE
```

---

## Verification Checklist

After implementing all three changes, verify with:

```bash
# 1. NET-1: Attempt startup with a TRANSITIONAL account — must fail
SP_ADMIN_ID=mcp-svc-transitional-test python3 -m sp_mcp_server.main
# Expected: "SECURITY [NET-1]: ... SESSIONSECURITY=Transitional ... Refusing to start."

# 2. NET-1: Startup with STRICT account — must succeed
SP_ADMIN_ID=mcp-svc-readonly python3 -m sp_mcp_server.main --mode read-only
# Expected: "NET-1: Session security OK — ..."

# 3. NET-2: Remote connection without -PA= password flag
ssh -i ~/.ssh/id_ed25519_sp_mcp mcp-runner@your-sp-server \
  "cd /opt/sp-mcp-server && source .venv/bin/activate && \
   python3 -m sp_mcp_server.main --mode read-only &"
# Expected: server starts without any password prompt

# 4. NET-3: Confirm TLS in dsmadmc using dsm.sys
DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys \
  dsmadmc -id=mcp-svc-readonly -se=SP_SERVER_1 "QUERY STATUS" | head -5
# Expected: connects successfully; no unencrypted TCP fallback warning
```

---

## SP Server Commands Summary

```
* Apply once per SP server, per service account
UPDATE ADMIN mcp-svc-system   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-storage  SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-policy   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT

* Verify
QUERY ADMIN mcp-svc-system FORMAT=DETAILED
```

---

## RG-1 — Production Guard for `SP_MCP_SKIP_SECURITY_CHECKS`

### What changed

**File**: [`src/sp_mcp_server/mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py)

The existing bypass variable `SP_MCP_SKIP_SECURITY_CHECKS=1` now checks for a companion environment variable `SP_MCP_ENV`. When `SP_MCP_ENV=production` is set, using the bypass is a fatal error:

```python
if os.environ.get("SP_MCP_SKIP_SECURITY_CHECKS") == "1":
    if os.environ.get("SP_MCP_ENV", "").lower() == "production":
        logger.error(
            "SECURITY [RG-1]: SP_MCP_SKIP_SECURITY_CHECKS=1 is set but "
            "SP_MCP_ENV=production. PRODUCTION UNSAFE — all session security "
            "checks are disabled. Unset SP_MCP_SKIP_SECURITY_CHECKS."
        )
        sys.exit(1)
    logger.warning(
        "NET-1: SESSIONSECURITY check SKIPPED (SP_MCP_SKIP_SECURITY_CHECKS=1). "
        "Do not use this override in production. "
        "Set SP_MCP_ENV=production to prevent this bypass on production hosts."
    )
    return
```

### Deployment requirement

Add `SP_MCP_ENV=production` to `.env` on all production SP server hosts. This turns any accidental bypass into an immediate hard failure with a `SECURITY [RG-1]` error that is visible to both operators and SIEM tools.

### Verification

```bash
# On a production host: this must fail
SP_MCP_ENV=production SP_MCP_SKIP_SECURITY_CHECKS=1 python3 -m sp_mcp_server.main
# Expected: "SECURITY [RG-1]: ... PRODUCTION UNSAFE" → sys.exit(1)

# On a test host: this must warn and continue
SP_MCP_ENV=test SP_MCP_SKIP_SECURITY_CHECKS=1 python3 -m sp_mcp_server.main
# Expected: WARNING logged; startup continues
```

### Automated test coverage

[`tests/test_security_controls.py::TestProductionGuard`](../../tests/test_security_controls.py)

