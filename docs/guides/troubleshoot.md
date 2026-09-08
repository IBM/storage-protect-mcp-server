# Troubleshooting Guide

This guide covers every error condition the IBM Storage Protect MCP Server can produce, organized from startup failures through runtime issues. Each section includes the exact log message, root cause, and the remediation steps grounded in IBM SP's own security controls.

**Log file location**: `/var/log/ibm-sp-mcp-server/mcp-server.log` (override with `SP_MCP_LOG_DIR`).

---

## Quick Reference — Error Markers

| Log marker | Exit? | Section |
|-----------|-------|---------|
| `SECURITY [CRED-3]` | Yes — `sys.exit(1)` | [§1 `.env` permissions](#1-env-file-permission-errors-cred-3) |
| `SECURITY [RG-1]` | Yes — `sys.exit(1)` | [§2 Production bypass guard](#2-production-bypass-guard-rg-1) |
| `SECURITY [NET-1]` | Yes — `sys.exit(1)` | [§3 Session security check](#3-session-security-check-net-1) |
| `SECURITY [RG-5]` | Varies | [§4 HTTP transport TLS](#4-http-transport-tls-rg-5) |
| `SECURITY [POL-3]` | No — warning only | [§5 Account lockout advisory](#5-account-lockout-advisory-pol-3) |
| `SECURITY [POL-4 / RG-4]` | No — advisory | [§6 Audit write failure](#6-audit-write-failure-pol-4--rg-4) |
| `dsmadmc executable not found` | Tool error | [§7 dsmadmc not found](#7-dsmadmc-not-found) |
| `No credential available` | Tool error | [§8 Missing credentials](#8-missing-credentials) |
| `ACC-2: Skipping tool` | No | [§9 Tool not registered](#9-tool-not-registered--privilege-errors) |
| `sudo:` in stderr | Offline error | [§10 Offline command failures](#10-offline-command-failures-dsmserv--servermon) |
| `ImportError` / `ModuleNotFoundError` | Immediate | [§11 Python import errors](#11-python-and-import-errors) |

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

```bash
chmod 600 /opt/sp-mcp-server/.env
chown mcp-runner:mcp-runner /opt/sp-mcp-server/.env

# Verify
ls -la /opt/sp-mcp-server/.env
# Expected: -rw------- 1 mcp-runner mcp-runner
```

> If you use a custom path, pass it via `secure_startup(env_path="/path/to/.env")` in your entry point.

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
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"

# 2. If connectivity fails, check the port
nc -zv your-sp-server.example.com 1500

# 3. If the account doesn't exist, register it on the SP server
REGISTER ADMIN mcp-svc-system PASSWORD=<strong-password>
GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM
UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT MFAREQUIRED=NO
```

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
SERVERNAME          SP_SERVER_1
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

## 10. Offline Command Failures (`dsmserv` / `servermon`)

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

The password stash for this service account has not been populated, or was populated under a different `DSM_CONFIG` path.

### Remediation

```bash
# Confirm DSM_CONFIG points to a file with PASSWORDACCESS GENERATE
cat $DSM_CONFIG | grep PASSWORDACCESS
# Expected: PASSWORDACCESS      GENERATE

# Populate the stash interactively (one-time per account)
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys
dsmadmc -id=mcp-svc-system -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
# The password is now stored in ~/.tsm/

# Verify stash works without -PA=
dsmadmc -id=mcp-svc-system -se=SP_SERVER_1 "QUERY STATUS"
# If this prompts for a password, the stash was not populated correctly
```

If the stash was populated under a different `DSM_CONFIG`, the stash file location may differ. The stash is stored in `~mcp-runner/.tsm/` by default.

---

## 13. Connection to IBM SP Server Fails

### Symptom

`dsmadmc` returns a connection error or the NET-1 check logs:

```
SECURITY [NET-1]: Cannot query service account 'mcp-svc-system'.
```

### Diagnosis

```bash
# 1. Test raw TCP connectivity to SP admin port
nc -zv your-sp-server.example.com 1500
# Expected: Connection to your-sp-server.example.com 1500 port [tcp] succeeded

# 2. Test dsmadmc directly with explicit credentials
dsmadmc -id=mcp-svc-system -pa=<password> \
        -tcpserveraddress=your-sp-server.example.com \
        -tcpport=1500 "QUERY STATUS"

# 3. Check server-side firewall
# On the SP server host:
sudo firewall-cmd --list-all | grep 1500
# Or:
sudo iptables -L -n | grep 1500
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

### Diagnosis

```bash
# Test the exact SSH command the MCP client would use
ssh -i ~/.ssh/id_ed25519_sp_mcp \
    -o StrictHostKeyChecking=yes \
    -o BatchMode=yes \
    mcp-runner@your-sp-server \
    "cd /opt/sp-mcp-server && source .venv/bin/activate && python3 -m sp_mcp_server.main --help"
```

### Common causes

| Error | Cause | Fix |
|-------|-------|-----|
| `Permission denied (publickey)` | SSH key not deployed or wrong key path | Re-run `ssh-copy-id -i ~/.ssh/id_ed25519_sp_mcp.pub mcp-runner@your-sp-server` |
| `Host key verification failed` | Host key changed or not in `known_hosts` | Run `ssh-keyscan -H your-sp-server >> ~/.ssh/known_hosts` |
| `Connection refused` | `sshd` not running or port not open | `systemctl status sshd` on SP server |
| Server starts but exits immediately | `.env` permission error or missing credential | Check `mcp-server.log` on the SP host for `SECURITY [CRED-3]` or missing credentials |

---

## 15. Log File Access

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

- Installation: [`install-guide.md`](install-guide.md)
- MCP client configuration: [`configure-guide.md`](configure-guide.md)
- User guide: [`user-guide.md`](user-guide.md)
- Security analysis: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Network security implementation: [`../implement/impl-security-network.md`](../implement/impl-security-network.md)
- Identity & credentials implementation: [`../implement/impl-security-identity-credentials.md`](../implement/impl-security-identity-credentials.md)
