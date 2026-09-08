# Installation Guide

This guide covers installing and preparing the IBM Storage Protect MCP Server on the host where IBM Storage Protect is running. Complete this guide before proceeding to [`configure-guide.md`](configure-guide.md).

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Python | 3.10 or higher (3.11 recommended) |
| IBM Storage Protect server | Running, reachable on TCP 1500 |
| `dsmadmc` CLI | Available in `PATH` on the MCP server host |
| OS user | Non-root `mcp-runner` account (created in this guide) |

---

## Part 1 — OS User Setup

The MCP server must run as a dedicated non-root OS user. This is required by the SSH key authentication model (NET-2) and ensures the `dsmadmc` process arguments are isolated from other users.

```bash
# Run as root on the IBM SP server host
useradd -m -d /opt/sp-mcp-server -s /bin/bash mcp-runner
mkdir -p /opt/sp-mcp-server/.ssh
chmod 700 /opt/sp-mcp-server/.ssh
chown -R mcp-runner:mcp-runner /opt/sp-mcp-server
```

---

## Part 2 — Python Environment

### Linux (RHEL / Rocky / CentOS)

```bash
sudo dnf install python3.11 python3.11-pip -y
python3.11 --version
```

### Linux (Ubuntu / Debian)

```bash
sudo apt update && sudo apt install python3.11 python3.11-venv -y
python3.11 --version
```

### Create the virtual environment

Run as `mcp-runner`:

```bash
su - mcp-runner
cd /opt/sp-mcp-server
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

---

## Part 3 — Install the Package

### From a wheel file

```bash
# With the virtual environment active
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

### From source (development)

```bash
git clone https://github.com/IBM/ibm-storage-protect-mcp-server.git /opt/sp-mcp-server
cd /opt/sp-mcp-server
pip install -e ".[dev]"
```

### Verify

```bash
python3 -m sp_mcp_server.main --help
```

Expected output includes `--mode`, `--enable-servers`, `--transport`, and `--port` arguments.

---

## Part 4 — `.env` Configuration File

The server reads all credentials and paths from `/opt/sp-mcp-server/.env`. The file **must** have permissions `600` — the server aborts at startup if group or world read/write bits are set.

```bash
touch /opt/sp-mcp-server/.env
chmod 600 /opt/sp-mcp-server/.env
chown mcp-runner:mcp-runner /opt/sp-mcp-server/.env
```

### Minimum `.env` for a single read-only service account

```dotenv
# /opt/sp-mcp-server/.env  — permissions 600

# ── Connection ──────────────────────────────────────────────────
TCPSERVERADDRESS=your-sp-server.example.com
SP_SERVER_PORT=1500

# ── Legacy single credential (simplest setup) ───────────────────
# Deprecated: migrate to per-privilege credentials below for
# production deployments.
SP_ADMIN_ID=mcp-svc-readonly
SP_ADMIN_PASSWORD=<strong-password>

# ── Optional: offline command support ───────────────────────────
SP_INSTANCE_USER=tsminst1
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/home/tsminst1/srvmon
```

### Full `.env` — per-privilege service accounts (recommended for production)

```dotenv
# /opt/sp-mcp-server/.env  — permissions 600

# ── Connection ──────────────────────────────────────────────────
TCPSERVERADDRESS=your-sp-server.example.com
SP_SERVER_PORT=1500

# ── Per-privilege credentials (CRED-1 / least-privilege model) ──
# The server selects the narrowest credential that satisfies each
# tool's required privilege tier at registration time.
SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_ADMIN_PASSWORD_READONLY=<readonly-password>

SP_ADMIN_ID_OPERATOR=mcp-svc-operator
SP_ADMIN_PASSWORD_OPERATOR=<operator-password>

SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_PASSWORD_STORAGE=<storage-password>

SP_ADMIN_ID_POLICY=mcp-svc-policy
SP_ADMIN_PASSWORD_POLICY=<policy-password>

SP_ADMIN_ID_SYSTEM=mcp-svc-system
SP_ADMIN_PASSWORD_SYSTEM=<system-password>

# ── Password stash mode (CRED-2) ────────────────────────────────
# Set to 1 after populating the dsmadmc password stash.
# Eliminates -PA= from subprocess arguments (recommended).
SP_MCP_USE_PASSWORD_STASH=0

# ── Production environment marker (RG-1) ────────────────────────
# Required on all production hosts. Prevents SP_MCP_SKIP_SECURITY_CHECKS
# from being used accidentally in production.
SP_MCP_ENV=production

# ── Offline command support ──────────────────────────────────────
SP_INSTANCE_USER=tsminst1
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/home/tsminst1/srvmon

# ── HTTP transport with OIDC (optional — INT-2) ─────────────────
# Only needed when starting with --transport http
# SP_OIDC_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0
# SP_OIDC_AUDIENCE=sp-mcp-server
# SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
# SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
```

### Complete environment variable reference

| Variable | Required | Description |
|----------|----------|-------------|
| `TCPSERVERADDRESS` | Yes | IBM SP server hostname or IP |
| `SP_SERVER_PORT` | No (default `1500`) | IBM SP admin port |
| `SP_ADMIN_ID` | Legacy | Single-account ID (deprecated) |
| `SP_ADMIN_PASSWORD` | Legacy | Single-account password (deprecated) |
| `SP_ADMIN_ID_SYSTEM` | Per-privilege | System-privilege service account ID |
| `SP_ADMIN_PASSWORD_SYSTEM` | Per-privilege | Password (omit when keyring or stash active) |
| `SP_ADMIN_ID_POLICY` | Per-privilege | Policy-privilege service account ID |
| `SP_ADMIN_PASSWORD_POLICY` | Per-privilege | Password |
| `SP_ADMIN_ID_STORAGE` | Per-privilege | Storage-privilege service account ID |
| `SP_ADMIN_PASSWORD_STORAGE` | Per-privilege | Password |
| `SP_ADMIN_ID_OPERATOR` | Per-privilege | Operator-privilege service account ID |
| `SP_ADMIN_PASSWORD_OPERATOR` | Per-privilege | Password |
| `SP_ADMIN_ID_READONLY` | Per-privilege | Read-only (any-admin) service account ID |
| `SP_ADMIN_PASSWORD_READONLY` | Per-privilege | Password |
| `SP_MCP_USE_PASSWORD_STASH` | No (default `0`) | `1` = omit `-PA=`; use `dsm.sys` stash |
| `SP_MCP_ENV` | No | Set to `production` to enforce RG-1 production guard |
| `SP_INSTANCE_USER` | Offline cmds | OS user for `dsmserv` / `servermon` |
| `SP_DSMSERV_PATH` | Offline cmds | Full path to `dsmserv` binary |
| `SP_SERVER_INSTANCE_DIR` | Offline cmds | SP server instance directory |
| `SP_SERVERMON_PATH` | Offline cmds | Full path to `servermon` binary |
| `SP_SERVERMON_XML_DIR` | Offline cmds | Directory where `servermon` writes XML output |
| `SP_OIDC_ISSUER` | HTTP transport | OIDC discovery URL (e.g. Azure AD tenant URL) |
| `SP_OIDC_AUDIENCE` | HTTP transport | Expected `aud` claim (default `sp-mcp-server`) |
| `SP_TLS_CERT` | HTTP transport | Path to PEM TLS certificate file |
| `SP_TLS_KEY` | HTTP transport | Path to PEM TLS private key file |
| `SP_MCP_ALLOW_HTTP_PLAINTEXT` | No (default `0`) | `1` = allow HTTP without TLS (loopback test only) |
| `SP_MCP_LOG_DIR` | No | Log directory (default `/var/log/ibm-sp-mcp-server`) |

---

## Part 5 — IBM SP Service Account Provisioning

The MCP server startup check (NET-1) validates that every configured service account has `SESSIONSECURITY=STRICT`. Create accounts on the IBM SP server before first run.

### Minimum setup (single read-only account)

```
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
```

### Full least-privilege setup (recommended for production)

Run these commands as a System-privileged IBM SP administrator:

```
* Read-only account (QUERY tools only)
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-readonly CONTACT="MCP Server | host:sp-mcp-01 | role:readonly"

* Operator account
REGISTER ADMIN mcp-svc-operator PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-operator CONTACT="MCP Server | host:sp-mcp-01 | role:operator"

* Storage account
REGISTER ADMIN mcp-svc-storage PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE
UPDATE ADMIN mcp-svc-storage SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-storage CONTACT="MCP Server | host:sp-mcp-01 | role:storage"

* Policy account
REGISTER ADMIN mcp-svc-policy PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY
UPDATE ADMIN mcp-svc-policy SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-policy CONTACT="MCP Server | host:sp-mcp-01 | role:policy"

* System account (broadest privilege — also designated as command approver)
REGISTER ADMIN mcp-svc-system PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM
UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30 CMDAPPROVER=YES
UPDATE ADMIN mcp-svc-system CONTACT="MCP Server | host:sp-mcp-01 | role:system"
```

Verify all accounts:

```
QUERY ADMIN mcp-svc-system FORMAT=DETAILED
```

Expected lines in output:

```
  Session Security: Strict
  Transport Method: TLS 1.2
```

---

## Part 6 — `dsm.sys` TLS Configuration (NET-3)

Create a `dsm.sys` that forces TLS for every `dsmadmc` session and enables the password stash:

```bash
mkdir -p /opt/sp-mcp-server/config
cat > /opt/sp-mcp-server/config/dsm.sys << 'EOF'
SERVERNAME          SP_SERVER_1
TCPSERVERADDRESS    your-sp-server.example.com
TCPPORT             1500
COMMMETHOD          TCPIP
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE
EOF
chmod 600 /opt/sp-mcp-server/config/dsm.sys
```

Set the environment variable so `dsmadmc` picks up this file:

```bash
echo "DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys" >> /opt/sp-mcp-server/.env
```

### Populate the password stash (one-time per account)

Once `dsm.sys` is in place, populate the stash interactively so the server no longer needs `-PA=` on the command line:

```bash
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys

dsmadmc -id=mcp-svc-readonly   -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator   -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage    -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy     -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
dsmadmc -id=mcp-svc-system     -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
```

After each command the password is stored in an encrypted stash (`~mcp-runner/.tsm/`). Once all accounts are stashed:

```bash
# Enable stash mode — passwords no longer passed via -PA=
sed -i 's/SP_MCP_USE_PASSWORD_STASH=0/SP_MCP_USE_PASSWORD_STASH=1/' /opt/sp-mcp-server/.env

# Remove plaintext passwords from .env (now sourced from stash)
# (manually remove SP_ADMIN_PASSWORD_* lines that are no longer needed)
```

---

## Part 7 — sudoers Rule for Offline Commands

If the `dsmserv` and `servermon` offline tools are needed, add a sudoers rule so `mcp-runner` can run those binaries as the SP instance user (`tsminst1`):

```bash
cat > /etc/sudoers.d/mcp-server << 'EOF'
# Allow mcp-runner to run dsmserv and servermon as the SP instance user
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/dsmserv
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/servermon
EOF
chmod 440 /etc/sudoers.d/mcp-server
visudo -c   # validate syntax before relying on it
```

Replace `tsminst1` with the actual SP instance OS username, and adjust the binary paths to match your installation.

---

## Part 8 — Verify the Installation

```bash
# As mcp-runner, with .venv active
cd /opt/sp-mcp-server
source .venv/bin/activate

# 1. Confirm dsmadmc is reachable
dsmadmc -id=mcp-svc-readonly "QUERY STATUS"

# 2. Dry-run the server (will run NET-1 session security check and exit)
#    Expected: NET-1 OK log lines, then wait for MCP protocol input on stdin
SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -20
# Note: SP_MCP_SKIP_SECURITY_CHECKS is only for this connectivity test.
# Remove it (and set SP_MCP_ENV=production in .env) before going live.
```

---

## Post-Install Checklist

```
[ ] mcp-runner OS user created; /opt/sp-mcp-server owned by mcp-runner
[ ] Python 3.10+ installed; .venv created and package installed
[ ] .env created with permissions 600 and owned by mcp-runner
[ ] SP service accounts registered with SESSIONSECURITY=STRICT
[ ] dsm.sys deployed to /opt/sp-mcp-server/config/dsm.sys (permissions 600)
[ ] Password stash populated for each service account
[ ] SP_MCP_USE_PASSWORD_STASH=1 set in .env
[ ] SP_MCP_ENV=production set in .env (production hosts)
[ ] sudoers rule deployed if offline (dsmserv/servermon) tools are needed
[ ] SSH public key deployed (see configure-guide.md)
```

---

## Related Documentation

- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security — Network: [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Security — Identity & Credentials: [`../implement/impl-security-identity-credentials.md`](../implement/impl-security-identity-credentials.md)
