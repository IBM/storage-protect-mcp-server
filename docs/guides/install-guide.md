# Installation Guide

> **Before installing:** Complete [`planning-guide.md`](planning-guide.md) to choose your deployment topology (co-located or centralised), inventory your SP servers, and verify prerequisites. The steps in this guide assume those decisions have already been made.

This guide covers the topology-specific installation steps for the IBM Storage Protect MCP Server. Complete this guide before proceeding to [`configure-guide.md`](configure-guide.md).

---

## Part 1 — OS User Setup

### Topology A — Co-located

Run as `root` on **each SP server host**:

```bash
useradd -m -d /opt/sp-mcp-server -s /bin/bash mcp-runner
mkdir -p /opt/sp-mcp-server/.ssh
chmod 700 /opt/sp-mcp-server/.ssh
chown -R mcp-runner:mcp-runner /opt/sp-mcp-server
```

### Topology B — Centralised

Run as `root` on the **control host once**. Create a shared base directory and per-SP-server working directories:

```bash
useradd -m -d /opt/sp-mcp -s /bin/bash mcp-runner
mkdir -p /opt/sp-mcp/.ssh
chmod 700 /opt/sp-mcp/.ssh
chown -R mcp-runner:mcp-runner /opt/sp-mcp

# Create a working directory for each SP server
mkdir -p /opt/sp-mcp/spsvr01
mkdir -p /opt/sp-mcp/spsvr02
# ... repeat for each SP server
chown -R mcp-runner:mcp-runner /opt/sp-mcp
```

> Each SP server gets its own subdirectory because `secure_startup()` looks for `.env` relative to the **current working directory** at process launch. Launching from `/opt/sp-mcp/spsvr01` loads `/opt/sp-mcp/spsvr01/.env`, and from `/opt/sp-mcp/spsvr02` loads `/opt/sp-mcp/spsvr02/.env`.

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

**Topology A** — run as `mcp-runner` on each SP server host:

```bash
su - mcp-runner
cd /opt/sp-mcp-server
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

**Topology B** — run as `mcp-runner` on the control host once, in a shared location:

```bash
su - mcp-runner
cd /opt/sp-mcp
python3.11 -m venv shared/.venv
source shared/.venv/bin/activate
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

**Topology A:**
```bash
git clone https://github.com/IBM/ibm-storage-protect-mcp-server.git /opt/sp-mcp-server
cd /opt/sp-mcp-server
pip install -e ".[dev]"
```

**Topology B:**
```bash
git clone https://github.com/IBM/ibm-storage-protect-mcp-server.git /opt/sp-mcp/shared/src
cd /opt/sp-mcp/shared/src
pip install -e ".[dev]"
```

### Verify

```bash
python3 -m sp_mcp_server.main --help
```

Expected output includes `--mode`, `--enable-servers`, `--transport`, and `--port` arguments.

---

## Part 4 — `.env` Configuration File

> **How `.env` loading works:** `secure_startup()` resolves `.env` as a path **relative to the current working directory** of the process. There is no `--env-file` flag. In Topology B, each process is launched with `cd /opt/sp-mcp/<servername>` so it reads its own `.env` in that directory.

### Topology A — one `.env` per SP server host

On each SP server host, create `/opt/sp-mcp-server/.env`:

```bash
touch /opt/sp-mcp-server/.env
chmod 600 /opt/sp-mcp-server/.env
chown mcp-runner:mcp-runner /opt/sp-mcp-server/.env
```

The only variable that differs between hosts is `TCPSERVERADDRESS`. All other variables are structurally identical.

### Topology B — one `.env` per SP server subdirectory, on the control host

On the control host, create a separate `.env` for each SP server:

```bash
# For each SP server (repeat for spsvr02, spsvr03, ...)
touch /opt/sp-mcp/spsvr01/.env
chmod 600 /opt/sp-mcp/spsvr01/.env
chown mcp-runner:mcp-runner /opt/sp-mcp/spsvr01/.env
```

> **Security note:** All `.env` files reside on the control host. Apply strict OS controls — only `mcp-runner` should be able to read the base directory. The CRED-3 permission check still enforces `0600` on each file at startup.

### Minimum `.env` for a single read-only service account

```dotenv
# .env  — permissions 600

# ── Connection ──────────────────────────────────────────────────
TCPSERVERADDRESS=your-sp-server.example.com   # set per SP server
SP_SERVER_PORT=1500

# ── Legacy single credential (simplest setup) ───────────────────
# Deprecated: migrate to per-privilege credentials for production.
SP_ADMIN_ID=mcp-svc-readonly
SP_ADMIN_PASSWORD=<strong-password>
```

### Full `.env` — per-privilege service accounts (recommended for production)

```dotenv
# .env  — permissions 600

# ── Connection ──────────────────────────────────────────────────
TCPSERVERADDRESS=your-sp-server.example.com   # set per SP server
SP_SERVER_PORT=1500

# ── Per-privilege credentials (CRED-1 / least-privilege model) ──
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
SP_MCP_USE_PASSWORD_STASH=0   # set to 1 after populating the stash

# ── Production environment marker (RG-1) ────────────────────────
SP_MCP_ENV=production

# ── Offline command support — Topology A only ───────────────────
# Remove or leave blank in Topology B (centralised).
SP_INSTANCE_USER=tsminst1
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/home/tsminst1/srvmon

# ── Dynamic & Delegated User Authentication (optional) ──────────
# Set to 'dynamic' to challenge interactive chat users for credentials
# at runtime instead of relying solely on static service accounts.
SP_MCP_AUTH_MODE=service_account   # 'service_account' (default) or 'dynamic'
SP_MCP_SESSION_TTL=900             # Inactivity lease timeout in seconds (default: 15m)
SP_MCP_SESSION_MAX_TTL=3600        # Hard session cap in seconds (default: 60m)

# ── HTTP transport with OIDC (optional — INT-2) ─────────────────
# SP_OIDC_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0
# SP_OIDC_AUDIENCE=sp-mcp-server
# SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
# SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
```

### Complete environment variable reference

| Variable | Required | Topology | Description |
|----------|----------|----------|-------------|
| `TCPSERVERADDRESS` | Yes | Both | IBM SP server hostname or IP |
| `SP_SERVER_PORT` | No (default `1500`) | Both | IBM SP admin port |
| `SP_ADMIN_ID` | Legacy | Both | Single-account ID (deprecated) |
| `SP_ADMIN_PASSWORD` | Legacy | Both | Single-account password (deprecated) |
| `SP_ADMIN_ID_SYSTEM` | Per-privilege | Both | System-privilege service account ID |
| `SP_ADMIN_PASSWORD_SYSTEM` | Per-privilege | Both | Password (omit when stash active) |
| `SP_ADMIN_ID_POLICY` | Per-privilege | Both | Policy-privilege service account ID |
| `SP_ADMIN_PASSWORD_POLICY` | Per-privilege | Both | Password |
| `SP_ADMIN_ID_STORAGE` | Per-privilege | Both | Storage-privilege service account ID |
| `SP_ADMIN_PASSWORD_STORAGE` | Per-privilege | Both | Password |
| `SP_ADMIN_ID_OPERATOR` | Per-privilege | Both | Operator-privilege service account ID |
| `SP_ADMIN_PASSWORD_OPERATOR` | Per-privilege | Both | Password |
| `SP_ADMIN_ID_READONLY` | Per-privilege | Both | Read-only service account ID |
| `SP_ADMIN_PASSWORD_READONLY` | Per-privilege | Both | Password |
| `SP_MCP_USE_PASSWORD_STASH` | No (default `0`) | Both | `1` = omit `-PA=`; use `dsm.sys` stash |
| `SP_MCP_ENV` | No | Both | Set to `production` to enforce RG-1 production guard |
| `DSM_CONFIG` | No | Both | Full path to `dsm.sys` file |
| `SP_MCP_AUTH_MODE` | No (default `service_account`) | Both | `service_account` (static) or `dynamic` (challenge-response) |
| `SP_MCP_SESSION_TTL` | No (default `900`) | Both | Ephemeral session sliding timeout (seconds) |
| `SP_MCP_SESSION_MAX_TTL` | No (default `3600`) | Both | Ephemeral session maximum hard lifetime (seconds) |
| `SP_MCP_STRICT_AUDIT` | No (default `0`) | Both | `1` = fail-closed mode: abort tool if ACTLOG audit write fails |
| `SP_INSTANCE_USER` | Offline cmds | **A only** | OS user for `dsmserv` / `servermon` |
| `SP_DSMSERV_PATH` | Offline cmds | **A only** | Full path to `dsmserv` binary |
| `SP_SERVER_INSTANCE_DIR` | Offline cmds | **A only** | SP server instance directory |
| `SP_SERVERMON_PATH` | Offline cmds | **A only** | Full path to `servermon` binary |
| `SP_SERVERMON_XML_DIR` | Offline cmds | **A only** | Directory where `servermon` writes XML output |
| `SP_OIDC_ISSUER` | HTTP transport | Both | OIDC discovery URL |
| `SP_OIDC_AUDIENCE` | HTTP transport | Both | Expected `aud` claim (default `sp-mcp-server`) |
| `SP_TLS_CERT` | HTTP transport | Both | Path to PEM TLS certificate |
| `SP_TLS_KEY` | HTTP transport | Both | Path to PEM TLS private key |
| `SP_MCP_ALLOW_HTTP_PLAINTEXT` | No (default `0`) | Both | `1` = allow HTTP without TLS (loopback test only) |
| `SP_MCP_LOG_DIR` | No | Both | Log directory (default `/var/log/ibm-sp-mcp-server`) |

---

## Part 5 — IBM SP Service Account Provisioning

The MCP server startup check (NET-1) validates that every configured service account has `SESSIONSECURITY=STRICT`. Create accounts on the IBM SP server before first run.

> **Both topologies:** Service accounts live on the IBM SP server itself — not on the MCP server host. Provisioning is the same regardless of topology. Run `scripts/provision-sp-service-accounts.sh` on each SP server to create all five tiers in one step. Encode the SP server's own hostname in each `CONTACT=` field so audit attribution is clear.

### Minimum setup (single read-only account)

```
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
```

### Full least-privilege setup (recommended for production)

Run these commands as a System-privileged IBM SP administrator on **each SP server**:

```
* Read-only account (QUERY tools only)
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-readonly CONTACT="MCP Server | host:<this-sp-host> | role:readonly"

* Operator account
REGISTER ADMIN mcp-svc-operator PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-operator CONTACT="MCP Server | host:<this-sp-host> | role:operator"

* Storage account
REGISTER ADMIN mcp-svc-storage PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE
UPDATE ADMIN mcp-svc-storage SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-storage CONTACT="MCP Server | host:<this-sp-host> | role:storage"

* Policy account
REGISTER ADMIN mcp-svc-policy PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY
UPDATE ADMIN mcp-svc-policy SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30
UPDATE ADMIN mcp-svc-policy CONTACT="MCP Server | host:<this-sp-host> | role:policy"

* System account (broadest privilege — also designated as command approver)
REGISTER ADMIN mcp-svc-system PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM
UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSWORDEXPIRATION=30 CMDAPPROVER=YES
UPDATE ADMIN mcp-svc-system CONTACT="MCP Server | host:<this-sp-host> | role:system"
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

### Topology A — one `dsm.sys` per SP server host

On each SP server host, the `dsm.sys` contains a single stanza pointing at the local SP server:

```bash
mkdir -p /opt/sp-mcp-server/config
cat > /opt/sp-mcp-server/config/dsm.sys << 'EOF'
SERVERNAME          SP_SPSVR01
TCPSERVERADDRESS    spsvr01.corp.example.com
TCPPORT             1500
COMMMETHOD          TCPIP
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE
EOF
chmod 600 /opt/sp-mcp-server/config/dsm.sys
echo "DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys" >> /opt/sp-mcp-server/.env
```

### Topology B — one `dsm.sys` on the control host, one stanza per SP server

On the control host, a single `dsm.sys` holds one stanza per remote SP server. Each stanza has a unique `SERVERNAME` — the password stash is keyed by `SERVERNAME` + account ID, so names must not collide:

```bash
mkdir -p /opt/sp-mcp/config
cat > /opt/sp-mcp/config/dsm.sys << 'EOF'
* Stanza for SPSVR01
SERVERNAME          SP_SPSVR01
TCPSERVERADDRESS    spsvr01.corp.example.com
TCPPORT             1500
COMMMETHOD          TCPIP
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE

* Stanza for SPSVR02
SERVERNAME          SP_SPSVR02
TCPSERVERADDRESS    spsvr02.corp.example.com
TCPPORT             1500
COMMMETHOD          TCPIP
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE
EOF
chmod 600 /opt/sp-mcp/config/dsm.sys

# Point all per-server .env files at this shared dsm.sys
echo "DSM_CONFIG=/opt/sp-mcp/config/dsm.sys" >> /opt/sp-mcp/spsvr01/.env
echo "DSM_CONFIG=/opt/sp-mcp/config/dsm.sys" >> /opt/sp-mcp/spsvr02/.env
```

### Populate the password stash (one-time per account, per SP server)

**Topology A** — run on each SP server host:

```bash
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys

dsmadmc -id=mcp-svc-readonly   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy     -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-system     -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
```

**Topology B** — run on the control host for each SP server stanza:

```bash
export DSM_CONFIG=/opt/sp-mcp/config/dsm.sys

# Populate for SPSVR01 (use its unique SERVERNAME)
dsmadmc -id=mcp-svc-readonly   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy     -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-system     -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"

# Populate for SPSVR02
dsmadmc -id=mcp-svc-readonly   -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator   -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage    -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy     -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
dsmadmc -id=mcp-svc-system     -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
```

After each command the password is stored in the encrypted stash (`~mcp-runner/.tsm/`). Once all accounts are stashed, enable stash mode in each `.env`:

```bash
# Topology A
sed -i 's/SP_MCP_USE_PASSWORD_STASH=0/SP_MCP_USE_PASSWORD_STASH=1/' /opt/sp-mcp-server/.env

# Topology B — for each server subdirectory
sed -i 's/SP_MCP_USE_PASSWORD_STASH=0/SP_MCP_USE_PASSWORD_STASH=1/' /opt/sp-mcp/spsvr01/.env
sed -i 's/SP_MCP_USE_PASSWORD_STASH=0/SP_MCP_USE_PASSWORD_STASH=1/' /opt/sp-mcp/spsvr02/.env
```

---

## Part 7 — sudoers Rule for Offline Commands (Topology A only)

> **Topology B:** Skip this part. The offline `dsmserv` and `servermon` tools require the SP server binaries to be present locally — they are not available in the centralised topology.

If the `dsmserv` and `servermon` offline tools are needed (Topology A only), add a sudoers rule on each SP server host so `mcp-runner` can run those binaries as the SP instance user:

```bash
cat > /etc/sudoers.d/mcp-server << 'EOF'
# Allow mcp-runner to run dsmserv and servermon as the SP instance user
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/dsmserv
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/servermon
EOF
chmod 440 /etc/sudoers.d/mcp-server
visudo -c   # validate syntax before relying on it
```

Replace `tsminst1` with the actual SP instance OS username and adjust binary paths to match your installation.

---

## Part 8 — Verify the Installation

### Topology A — on each SP server host

```bash
# As mcp-runner, with .venv active
cd /opt/sp-mcp-server
source .venv/bin/activate

# 1. Confirm dsmadmc is reachable
dsmadmc -id=mcp-svc-readonly "QUERY STATUS"

# 2. Dry-run the server
SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -20
# Expected: NET-1 check passed, tool registration logged, waiting on stdin
# Note: remove SP_MCP_SKIP_SECURITY_CHECKS and set SP_MCP_ENV=production before going live.
```

### Topology B — on the control host, once per SP server subdirectory

```bash
su - mcp-runner
source /opt/sp-mcp/shared/.venv/bin/activate

# Test for SPSVR01
cd /opt/sp-mcp/spsvr01
dsmadmc -id=mcp-svc-readonly -se=SP_SPSVR01 "QUERY STATUS"

SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -20

# Test for SPSVR02
cd /opt/sp-mcp/spsvr02
dsmadmc -id=mcp-svc-readonly -se=SP_SPSVR02 "QUERY STATUS"

SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -20
```

---

## Post-Install Checklist

### Topology A — repeat on each SP server host

```
[ ] mcp-runner OS user created; /opt/sp-mcp-server owned by mcp-runner
[ ] Python 3.10+ installed; .venv created and package installed
[ ] .env created at /opt/sp-mcp-server/.env with permissions 600
[ ] TCPSERVERADDRESS set to this SP server's address in .env
[ ] SP service accounts registered with SESSIONSECURITY=STRICT on this SP server
[ ] dsm.sys at /opt/sp-mcp-server/config/dsm.sys (permissions 600)
[ ] dsm.sys SERVERNAME is unique for this host (e.g. SP_SPSVR01)
[ ] Password stash populated for each account using correct -se=<servername>
[ ] SP_MCP_USE_PASSWORD_STASH=1 set in .env
[ ] SP_MCP_ENV=production set in .env
[ ] sudoers rule deployed (if offline dsmserv/servermon tools are needed)
[ ] SSH public key deployed to mcp-runner@<this-host> (see configure-guide.md)
```

### Topology B — run on the control host

```
[ ] mcp-runner OS user created; /opt/sp-mcp owned by mcp-runner
[ ] Python 3.10+ installed; shared/.venv created and package installed
[ ] dsmadmc installed on the control host and in mcp-runner's PATH
[ ] TCP 1500 reachable from control host to each SP server (verify with nc -zv)
[ ] Per-server subdirectory created: /opt/sp-mcp/<servername>/
[ ] Per-server .env created in each subdirectory with permissions 600
[ ] TCPSERVERADDRESS set correctly in each per-server .env
[ ] SP service accounts registered with SESSIONSECURITY=STRICT on each SP server
[ ] dsm.sys at /opt/sp-mcp/config/dsm.sys (permissions 600) with one stanza per SP server
[ ] Each stanza has a unique SERVERNAME (e.g. SP_SPSVR01, SP_SPSVR02)
[ ] Password stash populated for each account on each SP server using correct -se=<servername>
[ ] SP_MCP_USE_PASSWORD_STASH=1 set in each per-server .env
[ ] SP_MCP_ENV=production set in each per-server .env
[ ] SSH public key deployed to mcp-runner@ctrl-host (see configure-guide.md)
[ ] Offline tools (dsmserv/servermon) NOT expected — not supported in Topology B
```

---

## Related Documentation

- Deployment planning: [`planning-guide.md`](planning-guide.md)
- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security — Network: [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Security — Identity & Credentials: [`../implement/impl-security-identity-credentials.md`](../implement/impl-security-identity-credentials.md)
