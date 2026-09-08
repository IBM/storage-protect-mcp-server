# Troubleshooting Guide

This guide covers every error condition the IBM Storage Protect MCP Server can produce, organized from startup failures through runtime issues. Each section includes the exact log message, root cause, and the remediation steps grounded in IBM SP's own security controls.

> **Before troubleshooting:** If you have not yet completed [`planning-guide.md`](planning-guide.md), do so first. Many issues arise from skipping planning steps — wrong `SERVERNAME` labels, missing TCP 1500 access, or offline tools configured in Topology B.

**Log file location:**
- **Topology A (co-located):** `/var/log/ibm-sp-mcp-server/mcp-server.log` on each SP server host (override with `SP_MCP_LOG_DIR`)
- **Topology B (centralised):** `/var/log/ibm-sp-mcp-server/mcp-server.log` on the control host — all processes write here; filter by process or timestamp to isolate a specific SP server entry

---

## Quick Reference — Error Markers

| Log marker | Exit? | Topology | Section |
|-----------|-------|---------|---------|
| `SECURITY [CRED-3]` | Yes — `sys.exit(1)` | Both | [§1 `.env` permissions](#1-env-file-permission-errors-cred-3) |
| `SECURITY [RG-1]` | Yes — `sys.exit(1)` | Both | [§2 Production bypass guard](#2-production-bypass-guard-rg-1) |
| `SECURITY [NET-1]` | Yes — `sys.exit(1)` | Both | [§3 Session security check](#3-session-security-check-net-1) |
| `SECURITY [RG-5]` | Varies | Both | [§4 HTTP transport TLS](#4-http-transport-tls-rg-5) |
| `SECURITY [POL-3]` | No — warning only | Both | [§5 Account lockout advisory](#5-account-lockout-advisory-pol-3) |
| `SECURITY [POL-4 / RG-4]` | No — advisory | Both | [§6 Audit write failure](#6-audit-write-failure-pol-4--rg-4) |
| `dsmadmc executable not found` | Tool error | Both | [§7 dsmadmc not found](#7-dsmadmc-not-found) |
| `No credential available` | Tool error | Both | [§8 Missing credentials](#8-missing-credentials) |
| `ACC-2: Skipping tool` | No | Both | [§9 Tool not registered](#9-tool-not-registered--privilege-errors) |
| `sudo:` in stderr | Offline error | **A only** | [§10 Offline command failures](#10-offline-command-failures-dsmserv--servermon) |
| `ImportError` / `ModuleNotFoundError` | Immediate | Both | [§11 Python import errors](#11-python-and-import-errors) |
| Stash not populated / `ANR2034E` | Tool error | Both | [§12 Password stash issues](#12-password-stash-issues) |
| `ANR0521W` / connection refused | Startup / tool | Both | [§13 Connection to IBM SP Server Fails](#13-connection-to-ibm-sp-server-fails) |
| `Permission denied (publickey)` | Startup | Both | [§14 SSH connection issues](#14-ssh-connection-issues-stdio-transport) |
| One process fails; stash collision; wrong key | Startup | Both | [§15 Multi-server issues](#15-multi-server-deployment-issues) |
| `AUTHENTICATION_REQUIRED` / dynamic auth expiry | Tool challenge | Both | [§16 Dynamic authentication & session lease issues](#16-dynamic-authentication--session-lease-issues) |

---

## 1. `.env` File Permission Errors (CRED-3)

### Symptom

Server exits immediately at startup with:

```
ERROR: SECURITY [CRED-3]: '.env' has insecure permissions (0o644).
Restrict to owner-only: chmod 600 .env
```

### Cause

The `.env` file has group-readable or world-readable bits set. The server aborts **before** reading any secret from the file to prevent credentials from being exposed.

### Remediation

**Topology A** — fix on each SP server host:

```bash
chmod 600 /opt/sp-mcp-server/.env
chown mcp-runner:mcp-runner /opt/sp-mcp-server/.env

# Verify
ls -la /opt/sp-mcp-server/.env
# Expected: -rw------- 1 mcp-runner mcp-runner
```

**Topology B** — fix the affected per-server `.env` on the control host:

```bash
# Replace spsvr01 with the subdirectory name for the failing process
chmod 600 /opt/sp-mcp/spsvr01/.env
chown mcp-runner:mcp-runner /opt/sp-mcp/spsvr01/.env

# Verify all per-server .env files at once
ls -la /opt/sp-mcp/*/.env
# Expected: -rw------- 1 mcp-runner mcp-runner  (each)
```

> The CRED-3 check applies to each process's own `.env`, resolved relative to the working directory (`cwd`) at process launch. In Topology B each MCP client config entry uses `cd /opt/sp-mcp/<servername>` before starting Python — the check fires against that subdirectory's `.env`.

---

## 2. Production Bypass Guard (RG-1)

### Symptom

Server exits with:

```
ERROR: SECURITY [RG-1]: SP_MCP_SKIP_SECURITY_CHECKS=1 is set but
SP_MCP_ENV=production. PRODUCTION UNSAFE — all session security checks
are disabled. Unset SP_MCP_SKIP_SECURITY_CHECKS before running in production.
```

### Cause

Both `SP_MCP_SKIP_SECURITY_CHECKS=1` and `SP_MCP_ENV=production` are set. This combination is blocked — the bypass override must never reach a production host.

### Remediation

**Option A — remove the bypass variable** (correct fix for production):

```bash
# Remove or comment out the line in .env
sed -i '/SP_MCP_SKIP_SECURITY_CHECKS/d' /opt/sp-mcp-server/.env

# Confirm SP_MCP_ENV=production is still set
grep SP_MCP_ENV /opt/sp-mcp-server/.env
```

**Option B — this is a non-production host** (dev / CI):

```bash
# Remove SP_MCP_ENV=production from .env
sed -i '/SP_MCP_ENV=production/d' /opt/sp-mcp-server/.env
# SP_MCP_SKIP_SECURITY_CHECKS=1 is now allowed (warning only)
```

> `SP_MCP_SKIP_SECURITY_CHECKS=1` is for test/CI environments only. Never set it on any host that connects to a production IBM SP server.

---

## 3. Session Security Check (NET-1)

### Symptom A — Cannot query service account

```
ERROR: SECURITY [NET-1]: Cannot query service account 'mcp-svc-system'.
Verify credentials and SP server connectivity. stderr: ANR2034E ...
```

### Cause

`dsmadmc` returned non-zero when querying `QUERY ADMIN <id> FORMAT=DETAILED`. Most common causes: wrong password, SP server unreachable, or the account does not exist.

### Remediation

```bash
# 1. Test connectivity directly
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"

# 2. If connectivity fails, check the port
nc -zv your-sp-server.example.com 1500

# 3. If the account doesn't exist, register it on the SP server
REGISTER ADMIN mcp-svc-system PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM
UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT MFAREQUIRED=NO
```

> **Multi-server deployments:** Each MCP server process runs independently with its own log file on its own host. When a NET-1 failure occurs, check the log on the specific host whose process failed — a failure on one server does not affect the others. Use `SP_MCP_LOG_DIR` consistently across all hosts to make log collection uniform.

---

### Symptom B — Session Security not `Strict`

```
ERROR: SECURITY [NET-1]: Service account 'mcp-svc-system' has SESSIONSECURITY=Transitional.
Required value: Strict.
Remediate on the SP server: UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT
```

### Cause

The IBM SP administrator account has `SESSIONSECURITY=TRANSITIONAL` (the default for accounts created before SP v8.1.2) or has been explicitly set to `TRANSITIONAL`. The MCP server requires `STRICT` for all service accounts.

### Remediation

Run on the SP server as a System-privileged administrator:

```
UPDATE ADMIN mcp-svc-system   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-storage  SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-policy   SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT
UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT
```

> **Multi-server deployments:** Run these `UPDATE ADMIN` commands on **each SP server independently**. The accounts are distinct SP objects per server — updating them on SPSVR01 has no effect on SPSVR02.

Verify:

```
QUERY ADMIN mcp-svc-system FORMAT=DETAILED
```

Expected output includes:

```
  Session Security: Strict
  Transport Method: TLS 1.2
```

> **IBM SP note**: After an administrator successfully authenticates using SP v8.1.2 or later, it can no longer authenticate using earlier client versions or TLS 1.0/1.1. If you need a mixed-version environment, create a separate administrator account for legacy clients; do not revert `SESSIONSECURITY` on the MCP service accounts.

---

### Symptom C — Transport method not TLS

```
ERROR: SECURITY [NET-1]: Service account 'mcp-svc-system' transport method is 'SSL 3.0'.
TLS 1.2 or TLS 1.3 required.
```

### Cause

`dsmadmc` is connecting without TLS or using an obsolete SSL version. The `dsm.sys` file is missing `SSLREQUIRED=Yes` or `DSM_CONFIG` is not pointing to the correct file.

### Remediation

```bash
# Confirm DSM_CONFIG is set
echo $DSM_CONFIG
# Should point to /opt/sp-mcp-server/config/dsm.sys

# Confirm dsm.sys has SSL settings
cat /opt/sp-mcp-server/config/dsm.sys | grep -i ssl
# Expected: SSL Yes and SSLREQUIRED Yes

# If dsm.sys is missing, create it from the template
cat > /opt/sp-mcp-server/config/dsm.sys << 'EOF'
SERVERNAME          SP_SPSVR01
TCPSERVERADDRESS    your-sp-server.example.com
TCPPORT             1500
COMMMETHOD          TCPIP
SSL                 Yes
SSLREQUIRED         Yes
PASSWORDACCESS      GENERATE
EOF
chmod 600 /opt/sp-mcp-server/config/dsm.sys

# Add to .env
echo "DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys" >> /opt/sp-mcp-server/.env
```

> **Multi-server deployments:** The `SERVERNAME` value (e.g. `SP_SPSVR01`) must be unique per SP server host. Sharing the same `SERVERNAME` across hosts causes password stash key collisions — see [§12 Password Stash Issues](#12-password-stash-issues) for details.

---

## 4. HTTP Transport TLS (RG-5)

### Symptom A — TLS cert/key missing, no plaintext override

```
ERROR: SECURITY [RG-5]: --transport http requires both SP_TLS_CERT and SP_TLS_KEY
to be set. Bearer tokens and MCP traffic would be transmitted in cleartext without TLS.
```

Server exits with code 1.

### Remediation

```bash
# Generate a self-signed cert for testing (replace with a CA-signed cert in production)
mkdir -p /opt/sp-mcp-server/certs
openssl req -x509 -newkey rsa:4096 -keyout /opt/sp-mcp-server/certs/server.key \
  -out /opt/sp-mcp-server/certs/server.crt -days 365 -nodes \
  -subj "/CN=sp-mcp-server"
chmod 600 /opt/sp-mcp-server/certs/server.key

# Add to .env
cat >> /opt/sp-mcp-server/.env << 'EOF'
SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
EOF
```

---

### Symptom B — cert/key set but file not found

```
ERROR: SECURITY [RG-5]: SP_TLS_CERT path '/opt/certs/sp-mcp.crt' does not exist
or is not a file.
```

### Remediation

```bash
# Confirm paths
ls -la $SP_TLS_CERT $SP_TLS_KEY

# Fix path in .env if wrong
grep SP_TLS /opt/sp-mcp-server/.env
```

---

### Symptom C — plaintext HTTP allowed (test only)

```
ERROR: SECURITY [RG-5]: HTTP transport started WITHOUT TLS
(SP_MCP_ALLOW_HTTP_PLAINTEXT=1). PRODUCTION UNSAFE — bearer tokens
transmitted in cleartext. Do not use this in production.
```

This is logged as `ERROR` but startup continues. This is the expected behaviour when `SP_MCP_ALLOW_HTTP_PLAINTEXT=1` is set for a loopback-only test deployment.

> **Never use this in production.** Bearer tokens transmitted over plaintext HTTP expose the OIDC token to any network observer.

---

## 5. Account Lockout Advisory (POL-3)

### Symptom

```
WARNING: SECURITY [POL-3]: IBM SP account lockout is DISABLED
(Invalid Sign-on Attempt Limit = 0). Brute-force attacks on SP accounts
are unrestricted. Remediate on SP server: SET INVALIDPWLIMIT 5
```

Startup **continues** — this is advisory only.

### Cause

IBM SP defaults `INVALIDPWLIMIT` to `0` (unlimited) at installation. The MCP server warns because unlimited invalid password attempts allow brute-force attacks against the service accounts.

### Remediation

Run on the SP server as a System-privileged administrator:

```
SET INVALIDPWLIMIT 5
```

Verify:

```
QUERY STATUS
```

Expected: `Invalid Sign-on Attempt Limit: 5`

> **Multi-server deployments:** `SET INVALIDPWLIMIT` must be applied on **each SP server independently**. Each server maintains its own lockout counter — an account locked on SPSVR01 is not affected on SPSVR02 and vice versa.

> If a service account is subsequently locked out after too many failed attempts, unlock it with:
> ```
> UNLOCK ADMIN mcp-svc-system
> ```

---

## 6. Audit Write Failure (POL-4 / RG-4)

### Symptom

```
ERROR: SECURITY [POL-4 / RG-4]: Audit write FAILED for tool='delete_admin'
corr=a3f8b2c19d44 (SP returned code 2: ANR2034E ...). Write operation will
proceed but this event has no ACTLOG record. Verify SCRATCHPADENTRY write
permission for the service account.
```

Startup continues and the tool executes — audit mode is advisory.

### Cause

The `DEFINE SCRATCHPADENTRY MCP_AUDIT ...` command failed. Possible causes:

1. The service account does not have write access to `SCRATCHPADENTRY`.
2. The SP server is temporarily unreachable.
3. A network timeout occurred between audit write and tool execution.

### Remediation

**Verify scratchpad write permission** on the SP server:

```bash
# Test directly
dsmadmc -id=mcp-svc-system -pa=<password> \
  "DEFINE SCRATCHPADENTRY TEST_WRITE DESCRIPTION=\"audit-test\""
```

If this returns `ANR2034E` (not authorized), the account lacks the privilege to write scratchpad entries. By default, System-class administrators can write scratchpad entries. If the account is not System-class, a System admin must grant the right or configure a separate audit account.

**Verify existing audit entries**:

```
QUERY ACTLOG SEARCH=MCP_AUDIT
```

If no entries appear and the server has been running with write operations, the audit write has been failing silently and the gap should be investigated.

> **Multi-server deployments:** Audit records are distributed — each SP server's ACTLOG holds only the records for MCP operations that targeted it. Run `QUERY ACTLOG SEARCH=MCP_AUDIT` on **each SP server individually** to retrieve its own audit trail. There is no aggregated cross-server ACTLOG view.

---

## 7. `dsmadmc` Not Found

### Symptom

Tool call returns:

```
dsmadmc executable not found. Please ensure it is in your PATH.
```

Or at startup:

```
dsmadmc executable not found in PATH
```

### Cause

`shutil.which("dsmadmc")` returned `None` — the `dsmadmc` binary is not on the `PATH` of the `mcp-runner` OS user.

### Remediation

```bash
# Find dsmadmc
sudo find /opt/tivoli /usr/local -name dsmadmc 2>/dev/null
# Typical location: /opt/tivoli/tsm/client/ba/bin/dsmadmc

# Add to PATH permanently for mcp-runner
echo 'export PATH=$PATH:/opt/tivoli/tsm/client/ba/bin' >> /opt/sp-mcp-server/.profile

# Or add to the .env file (picked up before subprocess calls)
echo "PATH=$PATH:/opt/tivoli/tsm/client/ba/bin" >> /opt/sp-mcp-server/.env

# Verify as mcp-runner
su - mcp-runner -c "which dsmadmc"
```

---

## 8. Missing Credentials

### Symptom A — No credentials configured

```
Configuration incomplete. Missing required credentials.
```

### Cause

Neither `SP_ADMIN_ID` (legacy) nor any `SP_ADMIN_ID_*` (per-privilege) variable is set in the environment.

### Remediation

```bash
# Check .env is loaded and contains credentials
grep SP_ADMIN_ID /opt/sp-mcp-server/.env

# Minimum required entry
echo "SP_ADMIN_ID=mcp-svc-readonly" >> /opt/sp-mcp-server/.env
echo "SP_ADMIN_PASSWORD=<password>" >> /opt/sp-mcp-server/.env
chmod 600 /opt/sp-mcp-server/.env
```

---

### Symptom B — No credential for privilege tier

```
No credential available for privilege tier 'storage'. Configure
SP_ADMIN_ID_STORAGE (or another tier) in the environment.
```

### Cause

A tool requiring `storage` privilege was called, but no `storage`- or `system`-class credential is configured. The server registered the tool at startup using a higher-tier credential check, but the execution path cannot find a matching credential.

### Remediation

Add the missing credential to `.env`:

```bash
cat >> /opt/sp-mcp-server/.env << 'EOF'
SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_PASSWORD_STORAGE=<password>
EOF
chmod 600 /opt/sp-mcp-server/.env
```

Or, to use a single credential for all tiers, configure a System-class account under `SP_ADMIN_ID_SYSTEM` — the server will satisfy all tiers from that one credential.

---

## 9. Tool Not Registered / Privilege Errors

### Symptom A — Tool not visible to MCP client

The MCP client does not list a tool you expect (e.g. `delete_storage_pool`).

### Cause

The tool was excluded at registration time because the configured service account does not have sufficient SP privilege. The server logs `ACC-2: Skipping tool` at `DEBUG` level during startup.

### Diagnosis

```bash
# Enable debug logging temporarily and start the server
SP_MCP_LOG_DIR=/tmp/sp-mcp-debug \
  python3 -m sp_mcp_server.main --mode full 2>&1 | grep "ACC-2"

# Look for lines like:
# ACC-2: Skipping tool 'delete_storage_pool' — requires 'storage', account satisfies: {'any'}
```

### Remediation

**Add the required credential** to `.env` for the missing privilege tier (see §8B above), then restart.

**Or confirm the SP account has the right privilege class**:

```
QUERY ADMIN mcp-svc-storage FORMAT=DETAILED
```

Expected: `Storage Privilege: Yes`

If not:

```
GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE
```

---

### Symptom B — Tool call returns `Unknown tool: <name>`

```
Error: Unknown tool: delete_storage_pool
```

The MCP client sent a tool call for a tool that was not registered in the current session. Most likely the client's tool list is cached from a previous session with different credentials.

### Remediation

Disconnect and reconnect the MCP client to force a fresh tool list query (`list_tools`).

---

## 10. Offline Command Failures (`dsmserv` / `servermon`) — Topology A only

> **Topology B:** Offline tools (`dsmserv` / `servermon`) are **not supported** in the centralised topology. The SP server binaries are not present on the control host. If you receive errors from these tools in Topology B, the MCP client configuration entry is incorrectly attempting to use them. See [`planning-guide.md`](planning-guide.md) for the topology comparison and the offline tools limitation.

### Symptom A — `sudo` fails

Tool call returns an error containing:

```
sudo: mcp-runner is not allowed to run sudo on this host
```

or

```
sudo: /opt/tivoli/tsm/server/bin/dsmserv: command not found
```

### Cause

The `sudoers` rule for `mcp-runner` is missing or the binary path is wrong.

### Remediation

```bash
# Check current sudoers rules for mcp-runner
sudo -l -U mcp-runner

# Deploy the rule
cat > /etc/sudoers.d/mcp-server << 'EOF'
# Allow mcp-runner to run dsmserv and servermon as the SP instance user
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/dsmserv
mcp-runner ALL=(tsminst1) NOPASSWD: /opt/tivoli/tsm/server/bin/servermon
EOF
chmod 440 /etc/sudoers.d/mcp-server
visudo -c   # validate before reloading

# Test the rule
sudo -u tsminst1 -- /opt/tivoli/tsm/server/bin/servermon --version
```

Replace `tsminst1` with your actual SP instance OS user and adjust paths to match your installation.

---

### Symptom B — SP instance directory not set

Tool call returns:

```
SP_SERVER_INSTANCE_DIR is not configured. Cannot run dsmserv utility.
```

### Remediation

Add to `.env`:

```dotenv
SP_INSTANCE_USER=tsminst1
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
SP_SERVERMON_XML_DIR=/home/tsminst1/srvmon
```

---

## 11. Python and Import Errors

### Symptom A — Python version too old

```
ERROR: Python 3.10 or higher is required. Found: 3.8.x
```

### Remediation

```bash
# Check installed Python versions
ls /usr/bin/python3*

# Install Python 3.11 on RHEL/Rocky
sudo dnf install python3.11 python3.11-pip -y

# Recreate the venv with the correct interpreter
rm -rf /opt/sp-mcp-server/.venv
python3.11 -m venv /opt/sp-mcp-server/.venv
source /opt/sp-mcp-server/.venv/bin/activate
pip install -e .
```

---

### Symptom B — `No module named 'hatchling'` during install

```
error: No module named 'hatchling'
```

### Remediation

```bash
pip install --upgrade pip setuptools wheel hatchling
pip install -e .
```

---

### Symptom C — `No module named 'mcp'` or `No module named 'dotenv'`

```
ModuleNotFoundError: No module named 'mcp'
```

### Cause

The package was not installed in the active virtual environment, or the wrong Python interpreter is being used.

### Remediation

```bash
# Confirm the venv is active
which python3
# Expected: /opt/sp-mcp-server/.venv/bin/python3

# Reinstall
source /opt/sp-mcp-server/.venv/bin/activate
pip install -e .

# List installed packages to confirm
pip list | grep -E "mcp|dotenv|keyring"
```

---

## 12. Password Stash Issues

### Symptom

With `SP_MCP_USE_PASSWORD_STASH=1` set, `dsmadmc` commands fail with:

```
ANR2034E You are not authorized to perform this command.
```

or `dsmadmc` hangs waiting for interactive input.

### Cause

The password stash for this service account has not been populated, or was populated under a different `DSM_CONFIG` path or `SERVERNAME`.

### Remediation — Topology A

On the affected SP server host:

```bash
# Confirm DSM_CONFIG points to a file with PASSWORDACCESS GENERATE
cat $DSM_CONFIG | grep PASSWORDACCESS
# Expected: PASSWORDACCESS      GENERATE

# Populate the stash (use the SERVERNAME from this host's dsm.sys)
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"

# Verify stash works without -PA=
dsmadmc -id=mcp-svc-system -se=SP_SPSVR01 "QUERY STATUS"
```

### Remediation — Topology B

On the control host. The stash for all SP servers lives in `~mcp-runner/.tsm/` keyed by `SERVERNAME` + account ID. The shared `dsm.sys` at `/opt/sp-mcp/config/dsm.sys` must have one stanza per SP server with a unique `SERVERNAME`:

```bash
export DSM_CONFIG=/opt/sp-mcp/config/dsm.sys

# Populate for the affected SP server stanza (e.g. SP_SPSVR01)
dsmadmc -id=mcp-svc-readonly  -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator  -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-system    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"

# Verify stash works without -PA=
dsmadmc -id=mcp-svc-system -se=SP_SPSVR01 "QUERY STATUS"
```

> **Stash collision (both topologies):** If two SP servers share the same `SERVERNAME` in `dsm.sys`, their stash entries collide and authentication fails on one or both. To recover, delete `~mcp-runner/.tsm/` and repopulate all accounts with the corrected unique `SERVERNAME` values. See [`planning-guide.md` — Step 5](planning-guide.md) for the naming convention.

---

## 13. Connection to IBM SP Server Fails

### Symptom

`dsmadmc` returns a connection error or the NET-1 check logs:

```
SECURITY [NET-1]: Cannot query service account 'mcp-svc-system'.
```

### Diagnosis — Topology A

```bash
# 1. Check which SP server this process is targeting
grep TCPSERVERADDRESS /opt/sp-mcp-server/.env

# 2. Test raw TCP connectivity (local — SP server is on this host)
nc -zv localhost 1500

# 3. Test dsmadmc directly
dsmadmc -id=mcp-svc-system -pa=<password> \
        -tcpserveraddress=localhost -tcpport=1500 "QUERY STATUS"
```

### Diagnosis — Topology B

```bash
# 1. Check which SP server the failing process targets
grep TCPSERVERADDRESS /opt/sp-mcp/spsvr01/.env   # replace subdirectory as appropriate

# 2. Test TCP reachability from the control host to the remote SP server
nc -zv spsvr01.corp.example.com 1500
# Expected: succeeded
# If this fails: open TCP 1500 from the control host to that SP server

# 3. Test dsmadmc from the control host explicitly
dsmadmc -id=mcp-svc-system -pa=<password> \
        -tcpserveraddress=spsvr01.corp.example.com \
        -tcpport=1500 "QUERY STATUS"

# 4. Check firewall on the SP server host (run on the SP host, not the control host)
sudo firewall-cmd --list-all | grep 1500
```

### Common causes and fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` | SP server not running or wrong port | Confirm `TCPPORT` in `dsm.sys` matches SP admin port |
| `No route to host` | Network/firewall blocking port 1500 | Open port 1500 inbound on SP host |
| `ANR0521W` / auth failed | Wrong password or account locked | Check `QUERY ADMIN <id>` on SP; `UNLOCK ADMIN` if locked |
| Hangs with no output | `dsm.sys` specifying wrong server name | Confirm `SERVERNAME` in `dsm.sys` matches `-se=` arg |

---

## 14. SSH Connection Issues (stdio Transport)

### Symptom

MCP client reports the server is not available or times out during startup.

### Diagnosis — Topology A

Test the exact SSH command the MCP client would use. In Topology A each entry targets a different host with a dedicated key:

```bash
ssh -i ~/.ssh/id_ed25519_spsvr01 \
    -o StrictHostKeyChecking=yes \
    -o BatchMode=yes \
    mcp-runner@spsvr01.corp.example.com \
    "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --help"
```

### Diagnosis — Topology B

In Topology B all entries SSH to the **same control host** but use `cd` to change the working directory. A failure on one entry while others succeed almost always means the `cd` path or `.env` for that entry is wrong:

```bash
# Test the exact command the failing MCP client entry would run
ssh -i ~/.ssh/id_ed25519_ctrl \
    -o StrictHostKeyChecking=yes \
    -o BatchMode=yes \
    mcp-runner@ctrl.corp.example.com \
    "cd /opt/sp-mcp/spsvr01 && source /opt/sp-mcp/shared/.venv/bin/activate && python3 -m sp_mcp_server.main --help"
# Adjust the cd path for the specific failing entry
```

### Common causes

| Error | Cause | Topology A fix | Topology B fix |
|-------|-------|----------------|----------------|
| `Permission denied (publickey)` | Key not deployed or wrong key path | Re-run `ssh-copy-id -i ~/.ssh/id_ed25519_spsvr01.pub mcp-runner@spsvr01` | Re-run `ssh-copy-id -i ~/.ssh/id_ed25519_ctrl.pub mcp-runner@ctrl` |
| `Host key verification failed` | Host key changed or not in `known_hosts` | `ssh-keyscan -H spsvr01 >> ~/.ssh/known_hosts` | `ssh-keyscan -H ctrl >> ~/.ssh/known_hosts` |
| `Connection refused` | `sshd` not running or port blocked | `systemctl status sshd` on the SP server host | `systemctl status sshd` on the control host |
| Server exits immediately | `.env` permission error or missing credential | Check `mcp-server.log` on the SP host for `SECURITY [CRED-3]` | Check log on control host; confirm `cd /opt/sp-mcp/<servername>` path is correct and its `.env` exists with `chmod 600` |
| `Permission denied` on wrong server | Wrong key in MCP client config entry | Each entry must use its own `-i ~/.ssh/id_ed25519_<hostname>` | All entries share `-i ~/.ssh/id_ed25519_ctrl`; wrong-server errors from incorrect `cd` path, not key |

---

## 15. Multi-Server Deployment Issues

This section covers failure modes specific to multi-server deployments where multiple MCP server processes are registered in the MCP client configuration.

### Symptom A — One process fails to start; others remain up

One SP server entry in the MCP client config is unavailable while others connect successfully.

**Cause:** Each MCP server process starts, runs NET-1, and registers tools independently. A failure on one entry prevents only that process from starting — it does not affect others.

**Diagnosis — Topology A** (SSH to the failing SP server host):
```bash
ssh -i ~/.ssh/id_ed25519_<failing-host> mcp-runner@<failing-host> \
  "cd /opt/sp-mcp-server && source .venv/bin/activate && \
   python3 -m sp_mcp_server.main --mode read-only 2>&1 | head -30"
```

**Diagnosis — Topology B** (all processes on the control host; use `cd` to the failing entry's subdirectory):
```bash
ssh -i ~/.ssh/id_ed25519_ctrl mcp-runner@ctrl.corp.example.com \
  "cd /opt/sp-mcp/spsvr01 && source /opt/sp-mcp/shared/.venv/bin/activate && \
   python3 -m sp_mcp_server.main --mode read-only 2>&1 | head -30"
# Replace spsvr01 with the subdirectory for the failing entry
```

Check the output for `SECURITY [CRED-3]`, `SECURITY [NET-1]`, or `SECURITY [RG-1]` markers and follow the corresponding section in this guide.

---

### Symptom B — Password stash collisions (`SERVERNAME` not unique)

`dsmadmc` authenticates correctly for one SP server but fails with `ANR2034E` or hangs for another, despite `SP_MCP_USE_PASSWORD_STASH=1` being set.

**Cause:** Two SP server stanzas share the same `SERVERNAME` in `dsm.sys`. The stash key is `SERVERNAME` + account ID — duplicates cause entries to overwrite each other.
- **Topology A:** Two hosts each have their own `dsm.sys` but both used the same stanza name (e.g. `SP_SERVER_1`).
- **Topology B:** The shared `dsm.sys` on the control host has two stanzas with the same `SERVERNAME`.

**Remediation — Topology A:**
1. Assign a unique `SERVERNAME` in each host's `/opt/sp-mcp-server/config/dsm.sys`.
2. Update `DSM_CONFIG` in each host's `/opt/sp-mcp-server/.env`.
3. Delete the stale stash on each affected host and repopulate:
```bash
rm -rf ~mcp-runner/.tsm/
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys
dsmadmc -id=mcp-svc-readonly  -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-operator  -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-storage   -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-policy    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-system    -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
```

**Remediation — Topology B:**
1. Edit `/opt/sp-mcp/config/dsm.sys` on the control host and ensure every `SERVERNAME` is unique.
2. Delete the stash on the control host and repopulate for all SP server stanzas:
```bash
rm -rf ~mcp-runner/.tsm/
export DSM_CONFIG=/opt/sp-mcp/config/dsm.sys
# Repopulate for each stanza
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SPSVR01 "QUERY STATUS"
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SPSVR02 "QUERY STATUS"
# Repeat for all five accounts × all SP server stanzas
```

See [`planning-guide.md` — Step 5](planning-guide.md) for the recommended `SERVERNAME` naming convention.

---

### Symptom C — SSH key or working directory mismatch

**Topology A:** MCP client connects to the wrong SP server, or `Permission denied (publickey)` is returned for an entry that appears correctly configured.

**Cause (Topology A):** The `-i <keyfile>` in one MCP client config entry references the key for a different host. Using the wrong key fails authentication or silently targets the wrong server.

**Remediation (Topology A):**
1. Confirm each entry uses the correct per-host key: `sp-mcp-spsvr01` → `-i ~/.ssh/id_ed25519_spsvr01`.
2. Verify authorised keys on each host:
```bash
cat ~mcp-runner/.ssh/authorized_keys
```
3. Remove any incorrectly deployed key from `authorized_keys` and re-run `ssh-copy-id`.

---

**Topology B:** One MCP client config entry starts the correct process on the control host but talks to the wrong SP server, or fails immediately after SSH connects.

**Cause (Topology B):** The `cd /opt/sp-mcp/<servername>` path in the MCP client config entry is wrong (typo, wrong subdirectory name), so the process loads the `.env` for a different SP server, or fails if the directory does not exist.

**Remediation (Topology B):**
1. Confirm each entry's `cd` path matches its subdirectory:
   - `sp-mcp-spsvr01` → `cd /opt/sp-mcp/spsvr01`
   - `sp-mcp-spsvr02` → `cd /opt/sp-mcp/spsvr02`
2. Confirm the subdirectory and its `.env` exist on the control host:
```bash
ls -la /opt/sp-mcp/spsvr01/.env
# Expected: -rw------- 1 mcp-runner mcp-runner
```
3. Confirm `TCPSERVERADDRESS` in each `.env` matches the intended SP server.

---

## 16. Dynamic Authentication & Session Lease Issues

### Symptom A — Structured `AUTHENTICATION_REQUIRED` response

When calling an administrative tool (e.g. `query_node`, `define_admin`), the tool returns:

```json
{
  "is_error": true,
  "error_type": "AUTHENTICATION_REQUIRED",
  "message": "Authentication required. Please provide your IBM Storage Protect administrator credentials.",
  "challenge": {
    "server": "tsm_server_01",
    "required_fields": ["username", "password"],
    "supported_schemes": ["basic_delegated", "oidc_bearer"],
    "auth_tool": "authenticate_session"
  }
}
```

### Cause
The server is running in Dynamic Authentication Mode (`SP_MCP_AUTH_MODE=dynamic`) and no active session lease exists for the user or the previous session lease has expired due to inactivity.

### Remediation
1. Provide credentials to the AI assistant or invoke `authenticate_session` directly:
   ```json
   {
     "name": "authenticate_session",
     "arguments": {
       "username": "admin1",
       "password": "<admin-password>"
     }
   }
   ```
2. If you prefer static daemon execution without interactive prompt challenges, switch to service account mode in `.env`:
   ```dotenv
   SP_MCP_AUTH_MODE=service_account
   ```

---

### Symptom B — `Authentication failed: invalid administrator credentials`

Tool call to `authenticate_session` returns:

```json
{
  "success": false,
  "error": "Authentication failed: invalid administrator credentials.",
  "returncode": 1
}
```

### Cause
The provided username or password was rejected by the IBM Storage Protect server during the zero-trace verification query (`QUERY STATUS`), or the account is locked due to exceeding `INVALIDPWLIMIT`.

### Remediation
1. Check administrator status and lock state on the SP server:
   ```
   dsmadmc -id=admin -pa=<admin_pass> "QUERY ADMIN <username> FORMAT=DETAILED"
   ```
2. If the administrator is locked:
   ```
   UNLOCK ADMIN <username>
   ```
3. Verify password policy compliance (`SET INVALIDPWLIMIT 5`).

---

## 17. Log File Access

```bash
# View the live log
tail -f /var/log/ibm-sp-mcp-server/mcp-server.log

# Filter security events only
grep "SECURITY \[" /var/log/ibm-sp-mcp-server/mcp-server.log

# Filter audit correlation entries
grep "POL-4" /var/log/ibm-sp-mcp-server/mcp-server.log

# Filter startup checks
grep -E "NET-1|POL-3|ACC-2" /var/log/ibm-sp-mcp-server/mcp-server.log

# If /var/log is not writable, the server falls back to /tmp/ibm-sp-mcp-server/
ls /tmp/ibm-sp-mcp-server/mcp-server.log 2>/dev/null
```

---

## Related Documentation

- Deployment planning: [`planning-guide.md`](planning-guide.md)
- Installation: [`install-guide.md`](install-guide.md)
- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Security analysis: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Network security implementation: [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Identity & credentials implementation: [`../implement/impl-security-identity-credentials.md`](../implement/impl-security-identity-credentials.md)
