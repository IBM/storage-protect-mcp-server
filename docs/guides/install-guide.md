# Installation Guide

> **Before installing:** Complete [`planning-guide.md`](planning-guide.md) to choose your deployment topology (Step 1 — co-located or centralised) **and** your transport protocol (Step 1.5 — stdio over SSH or streamable-http with TLS), inventory your SP servers, and verify prerequisites. The steps in this guide assume those decisions have already been made.

This guide covers the topology-specific installation steps for the IBM Storage Protect MCP Server. Complete this guide before proceeding to [`configure-guide.md`](configure-guide.md).

---

## Table of Contents

- [Part 1 — Pre-Installation Checks](#part-1--pre-installation-checks)
  - [Step 1.1 — Identify your host type](#step-11--identify-your-host-type)
  - [Step 1.2 — Confirm `dsmadmc` is available](#step-12--confirm-dsmadmc-is-available)
  - [Step 1.3 — Confirm the SP server TLS certificate is trusted](#step-13--confirm-the-sp-server-tls-certificate-is-trusted)
  - [Step 1.4 — Confirm `LD_LIBRARY_PATH` includes GSKit](#step-14--confirm-ld_library_path-includes-gskit)
  - [Transport B — TLS certificate provisioning](#transport-b--tls-certificate-provisioning)
- [Part 2 — OS User Setup](#part-2--os-user-setup)
  - [Topology A — Co-located](#topology-a--co-located)
  - [Topology B — Centralised](#topology-b--centralised)
- [Part 3 — Python Environment](#part-3--python-environment)
- [Part 4 — Install the Package](#part-4--install-the-package)
- [Part 5 — `.env` Configuration File](#part-5---env-configuration-file)
  - [Topology A — one `.env` per SP server host](#topology-a--one-env-per-sp-server-host)
  - [Topology B — one `.env` per SP server subdirectory, on the control host](#topology-b--one-env-per-sp-server-subdirectory-on-the-control-host)
  - [Minimum `.env` for a single read-only service account](#minimum-env-for-a-single-read-only-service-account)
  - [Full `.env` — per-privilege service accounts (recommended for production)](#full-env--per-privilege-service-accounts-recommended-for-production)
  - [Complete environment variable reference](#complete-environment-variable-reference)
- [Part 6 — IBM SP Service Account Provisioning](#part-6--ibm-sp-service-account-provisioning)
  - [Minimum setup (single read-only account)](#minimum-setup-single-read-only-account)
  - [Full least-privilege setup (recommended for production)](#full-least-privilege-setup-recommended-for-production)
- [Part 7 — `dsm.sys` TLS Configuration (NET-3)](#part-7--dsmsys-tls-configuration-net-3)
  - [Topology A — one `dsm.sys` per SP server host](#topology-a--one-dsmsys-per-sp-server-host)
  - [Topology B — one `dsm.sys` on the control host, one stanza per SP server](#topology-b--one-dsmsys-on-the-control-host-one-stanza-per-sp-server)
  - [Populate the password stash (one-time per account, per SP server)](#populate-the-password-stash-one-time-per-account-per-sp-server)
- [Part 8 — sudoers Rule for Offline Commands (Topology A only)](#part-8--sudoers-rule-for-offline-commands-topology-a-only)
- [Part 9 — Verify the Installation](#part-9--verify-the-installation)
  - [Topology A — on each SP server host](#topology-a--on-each-sp-server-host)
  - [Topology B — on the control host, once per SP server subdirectory](#topology-b--on-the-control-host-once-per-sp-server-subdirectory)
- [Post-Install Checklist](#post-install-checklist)
  - [Topology A — repeat on each SP server host](#topology-a--repeat-on-each-sp-server-host)
  - [Topology B — run on the control host](#topology-b--run-on-the-control-host)
- [Related Documentation](#related-documentation)

---

## Part 1 — Pre-Installation Checks

Before creating any users or installing packages, confirm that `dsmadmc` is reachable and the SP server TLS certificate is trusted from the host where the MCP server process will run. Skipping these checks is the most common source of `ANS1592E Failed to initialize SSL protocol` errors later.

### Step 1.1 — Identify your host type

Answer these two questions before continuing:

> **Question 1 — Topology:** Is the host where you will install the MCP server the same machine as the IBM SP server?

| Answer | Topology | `dsmadmc` situation |
|---|---|---|
| **Yes** — same machine | Topology A (co-located) | `dsmadmc` is already installed; cert is already on-host |
| **No** — separate machine | Topology B (centralised) | You must install the IBM SP admin client package and register the cert separately |

> **Question 2 — Transport:** Will the MCP client connect over stdio/SSH (Transport A) or streamable-http with TLS (Transport B)?

| Answer | Transport | Extra installation requirements |
|---|---|---|
| **stdio over SSH** | Transport A | None beyond what this guide already covers — SSH key deployment is handled in [`configure-guide.md`](configure-guide.md) |
| **streamable-http with TLS** | Transport B | TLS certificate and key must be provisioned before first run (see [Transport B — TLS certificate provisioning](#transport-b--tls-certificate-provisioning) below); an enterprise IdP with `mcp:*` scopes is required |

> Both answers are independent. You may combine any topology with either transport.

---

### Step 1.2 — Confirm `dsmadmc` is available

Run this as the OS user you will install under (or as root):

```bash
which dsmadmc
dsmadmc -help 2>&1 | head -3
```

**Expected:** path printed (e.g. `/usr/bin/dsmadmc`) and version line shown.

**If `dsmadmc` is not found:**
- **Topology A (co-located):** The SP server installation includes `dsmadmc`. Check `/opt/tivoli/tsm/client/ba/bin/dsmadmc` and ensure it is in `PATH`, or add it:
  ```bash
  export PATH=$PATH:/opt/tivoli/tsm/client/ba/bin
  ```
- **Topology B (separate host):** Install the IBM Storage Protect administrative client package from IBM Passport Advantage / Fix Central (search for *IBM Storage Protect Client — Administrative Client*). Do not proceed until `dsmadmc` is available.

---

### Step 1.3 — Confirm the SP server TLS certificate is trusted

`dsmadmc` uses TLS for all connections. The SP server's self-signed certificate must be registered in the client keystore **on the host running the MCP server process** before any connection attempt — otherwise you will get `ANS1592E Failed to initialize SSL protocol` regardless of credentials or `dsm.sys` content.

#### Topology A — co-located (MCP process on the SP server host)

The certificate files are already present in the SP instance user's home directory. Use IBM's `dsmcert` tool to register the cert into the system-wide client keystore, then make it readable by `mcp-runner`:

```bash
# Run as root on the SP server host
# Replace tsminst1 and the cert256.arm path with your SP instance user and cert location
/opt/tivoli/tsm/client/ba/bin/dsmcert -add \
  -server <SERVERNAME-from-dsm.sys> \
  -file /home/tsminst1/cert256.arm

# Make the system cert.kdb readable by mcp-runner (and any non-root user running dsmadmc)
chmod 644 /opt/tivoli/tsm/client/ba/bin/cert.kdb
chmod 644 /opt/tivoli/tsm/client/ba/bin/cert.sth
```

> **Why `dsmcert` and not `gsk8capicmd_64`?** IBM's `dsmcert` tool registers the certificate in the format that `dsmadmc` trusts. Raw GSKit imports with `gsk8capicmd_64` produce a keystore that `dsmadmc` cannot use, resulting in `ANS1592E` even when the certificate appears to be present and trusted.

> **Why `chmod 644`?** The system `cert.kdb` is created with mode `600` owned by the SP instance user. The `mcp-runner` account (a separate non-root user) cannot read it until permissions are relaxed. `644` allows all local users to read the public certificate — this is safe since keystores contain only public certificates, not private keys.

Verify the cert is registered:

```bash
/usr/local/ibm/gsk8_64/bin/gsk8capicmd_64 -cert -list all \
  -db /opt/tivoli/tsm/client/ba/bin/cert.kdb -stashed
```

Expected output includes `! "TSM Server SelfSigned SHA Key"` (the `!` flag means trusted).

Test `dsmadmc` connectivity as `mcp-runner` after the OS user is created (Part 1):

```bash
su - mcp-runner -c "dsmadmc -id=<admin-id> -pa=<password> -se=<SERVERNAME> 'QUERY STATUS'"
```

Expected: `Session established with server <name>`.

#### Topology B — separate control host

On the control host you must:

1. Obtain the SP server's certificate file (`cert256.arm`) — copy it from the SP server host or export it using `gsk8capicmd_64` on the SP server.
2. Run `dsmcert -add` on the control host to register it.
3. Apply `chmod 644` on the control host's `cert.kdb` / `cert.sth`.

```bash
# On the SP server host — export the cert
/usr/local/ibm/gsk8_64/bin/gsk8capicmd_64 -cert -extract \
  -db /home/tsminst1/cert.kdb -stashed \
  -label "TSM Server SelfSigned SHA Key" \
  -target /tmp/sp_server.arm -format ascii

# Copy the cert to the control host
scp /tmp/sp_server.arm mcp-runner@control-host:/tmp/sp_server.arm

# On the control host — register it (as root)
/opt/tivoli/tsm/client/ba/bin/dsmcert -add \
  -server <SERVERNAME-from-dsm.sys> \
  -file /tmp/sp_server.arm

chmod 644 /opt/tivoli/tsm/client/ba/bin/cert.kdb
chmod 644 /opt/tivoli/tsm/client/ba/bin/cert.sth
```

---

### Step 1.4 — Confirm `LD_LIBRARY_PATH` includes GSKit

On some RHEL/Rocky systems the GSKit SSL libraries are not in the default linker path. If `dsmadmc` fails with SSL errors despite the certificate being registered, add this to the `mcp-runner` shell profile and to the `.env` file:

```bash
# Check what the SP instance user has set
su - tsminst1 -c "echo \$LD_LIBRARY_PATH"

# Add the same paths for mcp-runner — edit /opt/sp-mcp-server/.bash_profile
export LD_LIBRARY_PATH=/usr/local/ibm/gsk8_64/lib64:/opt/ibm/lib:/opt/ibm/lib64
```

Also add it to `.env` so it is inherited by the MCP server process:

```dotenv
LD_LIBRARY_PATH=/usr/local/ibm/gsk8_64/lib64:/opt/ibm/lib:/opt/ibm/lib64
```

> If the SP instance user's `LD_LIBRARY_PATH` also includes DB2 sqllib paths (e.g. `/home/tsminst1/sqllib/lib64/icc`), include those as well — they contain ICC crypto libraries that `dsmadmc` requires for TLS on DB2-backed SP installations.

---

### Transport B — TLS certificate provisioning

> **Skip if using Transport A (stdio over SSH).** This section applies only if you chose Transport B in [`planning-guide.md`](planning-guide.md) Step 1.5.

The MCP server process exits at startup with `SECURITY [RG-5]` if `SP_TLS_CERT` or `SP_TLS_KEY` are missing or unreadable. Provision the certificate before enabling the HTTP transport.

**Option 1 — Enterprise PKI or Let's Encrypt (production):**

Issue a certificate signed by your internal CA or by Let's Encrypt for the MCP server's hostname. Place the PEM-encoded files where `mcp-runner` can read them:

```bash
# Topology A — one cert per SP server host
mkdir -p /opt/sp-mcp-server/certs
# Copy your cert and key into place:
cp /path/to/server.crt /opt/sp-mcp-server/certs/server.crt
cp /path/to/server.key /opt/sp-mcp-server/certs/server.key
chmod 640 /opt/sp-mcp-server/certs/server.key
chown root:mcp-runner /opt/sp-mcp-server/certs/server.key

# Topology B — one cert for the control host (or a SAN cert covering all MCP endpoints)
mkdir -p /opt/sp-mcp/certs
cp /path/to/server.crt /opt/sp-mcp/certs/server.crt
cp /path/to/server.key /opt/sp-mcp/certs/server.key
chmod 640 /opt/sp-mcp/certs/server.key
chown root:mcp-runner /opt/sp-mcp/certs/server.key
```

**Option 2 — Self-signed certificate (lab / testing only):**

```bash
# Generate a self-signed cert valid for 365 days (replace CN with your hostname)
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout /opt/sp-mcp-server/certs/server.key \
  -out    /opt/sp-mcp-server/certs/server.crt \
  -subj "/CN=sp-mcp-01.corp.example.com" \
  -addext "subjectAltName=DNS:sp-mcp-01.corp.example.com"

chmod 640 /opt/sp-mcp-server/certs/server.key
chown root:mcp-runner /opt/sp-mcp-server/certs/server.key
```

> **Self-signed certs in production** require MCP clients to trust the CA. For enterprise deployments always use a PKI-issued or Let's Encrypt certificate. Never disable TLS verification on the client side.

Add the paths to `.env` once the files are in place (Part 5 covers the full `.env` — add these there):

```dotenv
SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
```

Verify the key is readable by `mcp-runner` before starting the server:

```bash
su - mcp-runner -c "openssl x509 -noout -subject -in /opt/sp-mcp-server/certs/server.crt"
su - mcp-runner -c "openssl rsa  -noout -check   -in /opt/sp-mcp-server/certs/server.key"
# Both commands should succeed without errors.
```

---

## Part 2 — OS User Setup

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

## Part 3 — Python Environment

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

## Part 4 — Install the Package

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

## Part 5 — `.env` Configuration File

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

# ── streamable-http transport with TLS (Transport B — INT-2) ────
# Required only when --transport http is used (see planning-guide.md Step 1.5).
# Ensure cert/key files are provisioned first (Part 1 above).
# SP_OIDC_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0
# SP_OIDC_AUDIENCE=sp-mcp-server
# SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
# SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
# SP_MCP_PUBLIC_URL=https://sp-mcp-01.corp.example.com:8443
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
| `SP_MCP_PUBLIC_URL` | No | Both | Externally reachable MCP server URL — included in RFC 9470 `/.well-known/oauth-protected-resource` and `WWW-Authenticate` header (OA-6) |
| `SP_OIDC_JWKS_TTL` | No (default `3600`) | Both | JWKS cache lifetime in seconds; set to match IdP key-rotation policy (OA-2) |
| `SP_OIDC_INTROSPECTION_ENDPOINT` | No | Both | RFC 7662 token introspection URL; leave unset to disable (OA-5) |
| `SP_OIDC_INTROSPECTION_CLIENT_ID` | No (default `SP_OIDC_AUDIENCE`) | Both | Client ID for introspection Basic auth (OA-5) |
| `SP_OIDC_INTROSPECTION_CLIENT_SECRET` | No | Both | Client secret for introspection — set in `.env` (0600) or inject via secrets manager (OA-5) |
| `SP_OIDC_INTROSPECT_BELOW_TTL` | No (default `300`) | Both | Introspect tokens with less than N seconds remaining lifetime (OA-5) |
| `SP_MCP_ALLOW_HTTP_PLAINTEXT` | No (default `0`) | Both | `1` = allow HTTP without TLS (loopback test only) |
| `SP_MCP_LOG_DIR` | No | Both | Log directory (default `/var/log/ibm-sp-mcp-server`) |

> For full descriptions and usage examples for all HTTP transport variables, see [`configure-guide.md` — Part 2 Complete `.env` reference](configure-guide.md#complete-env-reference--http-transport-variables).

---

## Part 6 — IBM SP Service Account Provisioning

The MCP server startup check (NET-1) validates that every configured service account has `SESSIONSECURITY=STRICT`. Create accounts on the IBM SP server before first run.

> **Both topologies:** Service accounts live on the IBM SP server itself — not on the MCP server host. Provisioning is the same regardless of topology. Run `scripts/provision-sp-service-accounts.sh` on each SP server to create all five tiers in one step. Encode the SP server's own hostname in each `CONTACT=` field so audit attribution is clear.

### Minimum setup (single read-only account)

```
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30
```

### Full least-privilege setup (recommended for production)

Run these commands as a System-privileged IBM SP administrator on **each SP server**:

```
* Read-only account (QUERY tools only)
REGISTER ADMIN mcp-svc-readonly PASSWORD=<strong-password>
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30
UPDATE ADMIN mcp-svc-readonly CONTACT="MCP Server | host:<this-sp-host> | role:readonly"

* Operator account
REGISTER ADMIN mcp-svc-operator PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30
UPDATE ADMIN mcp-svc-operator CONTACT="MCP Server | host:<this-sp-host> | role:operator"

* Storage account
REGISTER ADMIN mcp-svc-storage PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE
UPDATE ADMIN mcp-svc-storage SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30
UPDATE ADMIN mcp-svc-storage CONTACT="MCP Server | host:<this-sp-host> | role:storage"

* Policy account
REGISTER ADMIN mcp-svc-policy PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY
UPDATE ADMIN mcp-svc-policy SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30
UPDATE ADMIN mcp-svc-policy CONTACT="MCP Server | host:<this-sp-host> | role:policy"

* System account (broadest privilege — also designated as command approver)
REGISTER ADMIN mcp-svc-system PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM
UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT MFAREQUIRED=NO PASSEXP=30 CMDAPPROVER=YES
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

## Part 7 — `dsm.sys` TLS Configuration (NET-3)

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

## Part 8 — sudoers Rule for Offline Commands (Topology A only)

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

## Part 9 — Verify the Installation

### Topology A — on each SP server host

```bash
# As mcp-runner, with .venv active
cd /opt/sp-mcp-server
source .venv/bin/activate

# 1. Confirm dsmadmc is reachable
dsmadmc -id=mcp-svc-readonly "QUERY STATUS"

# 2. Dry-run the server (Transport A — stdio)
SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --mode read-only --enable-servers system 2>&1 | head -20
# Expected: NET-1 check passed, tool registration logged, waiting on stdin
# Note: remove SP_MCP_SKIP_SECURITY_CHECKS and set SP_MCP_ENV=production before going live.
```

**Transport B only — verify HTTP transport startup:**

```bash
# As mcp-runner, with .venv active (SP_TLS_CERT / SP_TLS_KEY must be set in .env)
cd /opt/sp-mcp-server
source .venv/bin/activate

SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --transport http --port 8443 \
    --mode read-only --enable-servers system 2>&1 | head -30
# Expected startup lines (no SECURITY [RG-5] error):
#   INFO:  RG-5: TLS configured — cert=/opt/sp-mcp-server/certs/server.crt
#   INFO:  OA-1: AS metadata cached from https://...
#   INFO:  Uvicorn running on https://0.0.0.0:8443

# Confirm port is open from a second terminal or from the client workstation:
curl --cacert /opt/sp-mcp-server/certs/server.crt \
  https://$(hostname -f):8443/health
# Expected: {"status":"ok"}
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

**Transport B only — verify HTTP transport startup (Topology B):**

```bash
# Each process uses its own port; test each SP server subdirectory in turn
cd /opt/sp-mcp/spsvr01
SP_MCP_SKIP_SECURITY_CHECKS=1 \
  python3 -m sp_mcp_server.main --transport http --port 8443 \
    --mode read-only --enable-servers system 2>&1 | head -30
# Expected: RG-5 TLS configured, Uvicorn running on https://0.0.0.0:8443

curl --cacert /opt/sp-mcp/certs/server.crt \
  https://$(hostname -f):8443/health
# Expected: {"status":"ok"}
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
[ ] — Transport A only — SSH public key deployed to mcp-runner@<this-host> (see configure-guide.md)
[ ] — Transport B only — TLS cert/key provisioned in /opt/sp-mcp-server/certs/ (permissions 640, owner root:mcp-runner)
[ ] — Transport B only — SP_TLS_CERT, SP_TLS_KEY, SP_OIDC_ISSUER, SP_MCP_PUBLIC_URL set in .env
[ ] — Transport B only — TCP 8443 (or chosen port) open inbound from MCP client hosts
[ ] — Transport B only — MCP server host can reach IdP OIDC discovery URL outbound
[ ] — Transport B only — HTTP transport smoke-test passed (Part 9 above)
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
[ ] Offline tools (dsmserv/servermon) NOT expected — not supported in Topology B
[ ] — Transport A only — SSH public key deployed to mcp-runner@ctrl-host (see configure-guide.md)
[ ] — Transport B only — TLS cert/key provisioned in /opt/sp-mcp/certs/ (permissions 640, owner root:mcp-runner)
[ ] — Transport B only — SP_TLS_CERT, SP_TLS_KEY, SP_OIDC_ISSUER, SP_MCP_PUBLIC_URL set in each per-server .env
[ ] — Transport B only — Each MCP process port (e.g. :8443, :8444) open inbound from MCP client hosts
[ ] — Transport B only — Control host can reach IdP OIDC discovery URL outbound
[ ] — Transport B only — HTTP transport smoke-test passed per SP server subdirectory (Part 9 above)
```

---

## Related Documentation

- Deployment planning (topology + transport choice): [`planning-guide.md`](planning-guide.md)
- MCP client configuration (stdio + HTTP transport): [`configure-guide.md`](configure-guide.md)
- Local IdP / OAuth 2 test environment (Transport B): [`local-idp-oauth2-guide.md`](local-idp-oauth2-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Troubleshooting: [`troubleshoot.md`](troubleshoot.md)
- Security — Network & TLS: [`../design/security-network.md`](../design/security-network.md)
- Security — OAuth 2 / OIDC (Transport B): [`../design/security-oauth2.md`](../design/security-oauth2.md)
- Security — Identity & Credentials: [`../design/security-identity-credentials.md`](../design/security-identity-credentials.md)
