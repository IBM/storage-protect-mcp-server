# Implementation: Identity & Credentials Management

* **Domain**: Identity & Credentials Management
* **Analysis reference**: [`docs/analysis/security-design-analysis.md § 2`](../analysis/security-design-analysis.md)
* **Gaps addressed**: I1, I2, I3, I4, I5, RG-2, RG-3
* **Files changed**: `src/sp_mcp_server/config.py`, `src/sp_mcp_server/cli_wrapper.py`, `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/commands/base.py`, `src/sp_mcp_server/commands/system/admin.py`, `src/sp_mcp_server/commands/clients/node.py`, all `main_*.py` entry points

---

## Overview

Five changes close all identity and credential gaps:

| ID | Change | Gaps closed |
|----|--------|-------------|
| CRED-1 | Per-privilege-class `ServerConfig` with module-scoped credential env vars | I1, I5 |
| CRED-2 | Remove `-PA=` from `dsmadmc` subprocess; use `PASSWORDACCESS GENERATE` stash | I2 |
| CRED-3 | `.env` file permission check at startup | I3 |
| CRED-4 | MFA exemption policy — documented + enforced in `ServerConfig.validate()` | I4 |
| CRED-5 | SP server provisioning script — one account set per SP server instance | I1, I5 |
| RG-2 | `secure_startup()` atomic helper; applied to all `main_*.py` entry points | RG-2 |
| RG-3 | `_execute_silent_query()` in `BaseCommand`; all password-bearing commands use it | RG-3 |

---

## CRED-1 — Per-Privilege-Class `ServerConfig`

### What to change

**File**: [`src/sp_mcp_server/config.py`](../../src/sp_mcp_server/config.py)

The existing `ServerConfig` holds one `admin_id` / `admin_password` pair. Replace it with a per-module credential map so each enabled server group uses the narrowest possible privilege.

### Implementation

```python
# src/sp_mcp_server/config.py
import os
import stat
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Ordered from narrowest to broadest privilege.
# The MCP factory selects the credential whose privilege satisfies
# the required_privilege of the loaded tool set.
PRIVILEGE_TIERS = ("any", "operator", "storage", "policy", "system")


@dataclass
class ModuleCredential:
    """Credential pair for one SP privilege tier."""
    admin_id: str
    admin_password: str
    privilege: str  # 'system' | 'policy' | 'storage' | 'operator' | 'any'


@dataclass
class ServerConfig:
    # Connection
    server_address: Optional[str]
    server_port: str

    # Per-module credentials (keyed by privilege tier)
    credentials: Dict[str, ModuleCredential] = field(default_factory=dict)

    # Legacy single-credential fallback (used when per-module vars not set)
    admin_id: Optional[str] = None
    admin_password: Optional[str] = None

    # Optional paths
    dsmserv_path: Optional[str] = None
    server_instance_dir: Optional[str] = None
    servermon_path: Optional[str] = None
    servermon_xml_dir: Optional[str] = None
    instance_user: Optional[str] = None

    def credential_for(self, privilege: str) -> Optional[ModuleCredential]:
        """
        Return the narrowest available credential that satisfies 'privilege'.
        Falls back to the legacy single credential if no per-module creds are set.
        """
        # Walk from narrowest to the requested tier, return first match found
        search_order = PRIVILEGE_TIERS[: PRIVILEGE_TIERS.index(privilege) + 1]
        for tier in reversed(search_order):          # prefer the closest match
            if tier in self.credentials:
                return self.credentials[tier]

        # Legacy fallback
        if self.admin_id and self.admin_password:
            return ModuleCredential(
                admin_id=self.admin_id,
                admin_password=self.admin_password,
                privilege="system"   # assume worst-case for legacy config
            )
        return None

    def validate(self) -> bool:
        """At least one credential must be configured."""
        return bool(self.credentials) or bool(self.admin_id and self.admin_password)


def _load_env_permission_check(env_path: str = ".env") -> None:
    """
    CRED-3: Fail fast if the .env file is readable by group or other.
    Called before any secrets are loaded from it.
    """
    if not os.path.exists(env_path):
        return
    mode = os.stat(env_path).st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError(
            f"SECURITY [CRED-3]: '{env_path}' has insecure permissions "
            f"({oct(mode & 0o777)}). Restrict to 600: chmod 600 {env_path}"
        )


def load_config(env_path: str = ".env") -> ServerConfig:
    """Load configuration from environment variables."""
    _load_env_permission_check(env_path)

    address = os.environ.get("TCPSERVERADDRESS")
    port    = os.environ.get("SP_SERVER_PORT") or os.environ.get("TCPPORT") or "1500"

    # ── Per-module credentials (CRED-1) ───────────────────────────────────
    credentials: Dict[str, ModuleCredential] = {}

    _module_map = {
        "system":   ("SP_ADMIN_ID_SYSTEM",   "SP_ADMIN_PASSWORD_SYSTEM"),
        "policy":   ("SP_ADMIN_ID_POLICY",   "SP_ADMIN_PASSWORD_POLICY"),
        "storage":  ("SP_ADMIN_ID_STORAGE",  "SP_ADMIN_PASSWORD_STORAGE"),
        "operator": ("SP_ADMIN_ID_OPERATOR", "SP_ADMIN_PASSWORD_OPERATOR"),
        "any":      ("SP_ADMIN_ID_READONLY", "SP_ADMIN_PASSWORD_READONLY"),
    }
    for privilege, (id_var, pw_var) in _module_map.items():
        admin_id  = os.environ.get(id_var)
        admin_pwd = os.environ.get(pw_var)
        if admin_id and admin_pwd:
            credentials[privilege] = ModuleCredential(
                admin_id=admin_id,
                admin_password=admin_pwd,
                privilege=privilege
            )

    # ── Legacy single-credential fallback ─────────────────────────────────
    legacy_id  = os.environ.get("SP_ADMIN_ID")
    legacy_pwd = os.environ.get("SP_ADMIN_PASSWORD")
    if legacy_id and legacy_pwd and not credentials:
        logger.warning(
            "CRED-1: Using legacy single-credential SP_ADMIN_ID/SP_ADMIN_PASSWORD. "
            "Migrate to per-module credentials (SP_ADMIN_ID_SYSTEM, etc.) "
            "for least-privilege operation."
        )

    return ServerConfig(
        server_address=address,
        server_port=port,
        credentials=credentials,
        admin_id=legacy_id,
        admin_password=legacy_pwd,
        dsmserv_path=os.environ.get("SP_DSMSERV_PATH"),
        server_instance_dir=os.environ.get("SP_SERVER_INSTANCE_DIR"),
        servermon_path=os.environ.get("SP_SERVERMON_PATH"),
        servermon_xml_dir=os.environ.get("SP_SERVERMON_XML_DIR"),
        instance_user=os.environ.get("SP_INSTANCE_USER"),
    )
```

### Environment variable reference

| Variable | Privilege tier | Example value |
|----------|---------------|---------------|
| `SP_ADMIN_ID_SYSTEM` | System | `mcp-svc-system` |
| `SP_ADMIN_PASSWORD_SYSTEM` | System | *(from stash or keyring)* |
| `SP_ADMIN_ID_POLICY` | Policy | `mcp-svc-policy` |
| `SP_ADMIN_PASSWORD_POLICY` | Policy | *(from stash or keyring)* |
| `SP_ADMIN_ID_STORAGE` | Storage | `mcp-svc-storage` |
| `SP_ADMIN_PASSWORD_STORAGE` | Storage | *(from stash or keyring)* |
| `SP_ADMIN_ID_OPERATOR` | Operator | `mcp-svc-operator` |
| `SP_ADMIN_PASSWORD_OPERATOR` | Operator | *(from stash or keyring)* |
| `SP_ADMIN_ID_READONLY` | Any (read-only) | `mcp-svc-readonly` |
| `SP_ADMIN_PASSWORD_READONLY` | Any (read-only) | *(from stash or keyring)* |
| `SP_ADMIN_ID` | Legacy fallback | *(deprecated)* |
| `SP_ADMIN_PASSWORD` | Legacy fallback | *(deprecated)* |

### `.env` file example (minimum read-only deployment)

```dotenv
# .env — permissions must be 600
TCPSERVERADDRESS=sp-server-01.example.com
SP_SERVER_PORT=1500

SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_ADMIN_PASSWORD_READONLY=<strong-password>
```

---

## CRED-2 — Remove `-PA=` from `dsmadmc` Subprocess Arguments

### What to change

**File**: [`src/sp_mcp_server/cli_wrapper.py`](../../src/sp_mcp_server/cli_wrapper.py)

With `PASSWORDACCESS GENERATE` configured in `dsm.sys` (see **impl-security-network.md § NET-3**), `dsmadmc` reads credentials from the encrypted stash. The `-PA=` argument must be removed to prevent the password appearing in `/proc/<pid>/cmdline`.

### Implementation

```python
# src/sp_mcp_server/cli_wrapper.py — DsmAdmcWrapper.execute()

def execute(self, command: str) -> Tuple[str, str, int]:
    """Execute a dsmadmc command. Returns (stdout, stderr, return_code)."""
    if not self.config.validate():
        return "", "Configuration incomplete. Missing required credentials.", 1

    cred = self.config.credential_for(self._privilege)

    # Build argument list.
    # -PA= is OMITTED when PASSWORDACCESS GENERATE is configured in dsm.sys.
    # The password is then read from the encrypted stash automatically.
    use_stash = os.environ.get("SP_MCP_USE_PASSWORD_STASH", "0") == "1"

    args = [
        self.executable,
        "-NOConfirm",
        "-DATAONLY=YES",
        f"-ID={cred.admin_id}",
        "-COMMAdelimited",
    ]

    if not use_stash:
        # Fallback: pass password on CLI (legacy mode; warns on startup)
        args.insert(4, f"-PA={cred.admin_password}")
        logger.debug(
            "CRED-2: Password passed via -PA= argument. "
            "Set SP_MCP_USE_PASSWORD_STASH=1 and configure dsm.sys "
            "PASSWORDACCESS=GENERATE to eliminate this exposure."
        )

    cmd_parts = command.split()
    args.extend(cmd_parts)

    logger.info("Executing dsmadmc command: %s", command)
    logger.debug(
        "Full command args: %s [credentials hidden] %s",
        " ".join(args[:5]), " ".join(cmd_parts)
    )

    try:
        process = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        # ... rest of existing error handling unchanged
        return process.stdout, process.stderr, process.returncode

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = e.stderr.decode() if e.stderr else ""
        logger.error("Command timed out after 30 seconds")
        return stdout, stderr or "Command execution timed out after 30 seconds", 124
    except FileNotFoundError:
        return "", "dsmadmc executable not found in PATH.", 127
    except Exception as e:
        logger.exception("Unexpected error executing command: %s", e)
        return "", str(e), 1
```

### Stash population (one-time, per account, per SP server)

```bash
# Set DSM_CONFIG to point at the hardened dsm.sys (see NET-3)
export DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys

# Run interactively once to store the password in the stash
dsmadmc -id=mcp-svc-readonly -pa=<password> -se=SP_SERVER_1 "QUERY STATUS"
# IBM SP writes an encrypted stash entry; subsequent calls need no -pa=

# Verify stash works without -pa=
dsmadmc -id=mcp-svc-readonly "QUERY STATUS"
```

### Enabling stash mode

Once the stash is populated for all accounts:

```dotenv
# .env — add this flag
SP_MCP_USE_PASSWORD_STASH=1
```

The `SP_ADMIN_PASSWORD_*` variables can then be removed from the `.env` file. They remain supported as a fallback for environments where `dsm.sys` stash is not available.

---

## CRED-3 — `.env` File Permission Check at Startup

### What to change

**File**: [`src/sp_mcp_server/config.py`](../../src/sp_mcp_server/config.py) — already included in the CRED-1 implementation above as `_load_env_permission_check()`.

**File**: [`src/sp_mcp_server/main.py`](../../src/sp_mcp_server/main.py)

Wrap the `load_dotenv()` call so the permission check runs before `dotenv` reads the file:

```python
# src/sp_mcp_server/main.py

from dotenv import load_dotenv
from .config import _load_env_permission_check

# ── CRED-3: check permissions before loading secrets ──
try:
    _load_env_permission_check(".env")
except PermissionError as exc:
    import sys
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)

load_dotenv()
```

### Apply the same guard in all `main_*.py` entry points

Each standalone entry point (`main_clients_core.py`, `main_system_admin.py`, etc.) calls `load_dotenv()` directly. Add the same guard to each. A helper in `main.py` can be imported:

```python
# src/sp_mcp_server/main.py — export the guard
def check_env_file_permissions() -> None:
    from .config import _load_env_permission_check
    try:
        _load_env_permission_check(".env")
    except PermissionError as exc:
        import sys
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
```

```python
# src/sp_mcp_server/main_clients_core.py (and all other main_*.py)
from .main import check_env_file_permissions
check_env_file_permissions()
load_dotenv()
```

### OS enforcement (applied during deployment)

```bash
# Restrict .env to owner-read/write only
chmod 600 /opt/sp-mcp-server/.env
chown mcp-runner:mcp-runner /opt/sp-mcp-server/.env
```

---

## CRED-4 — MFA Exemption Policy

### What to document

**File**: New section in [`docs/guides/configure-guide.md`](../guides/configure-guide.md)

IBM SP's `MFAREQUIRED=YES` (`REGISTER ADMIN` / `UPDATE ADMIN`) requires a TOTP passcode on every interactive login. `dsmadmc` run non-interactively (as done by this MCP server) cannot satisfy a TOTP challenge. Service accounts must therefore be explicitly exempt.

This is a deliberate security trade-off. The compensating controls are:

| Compensating control | Where implemented |
|---------------------|-------------------|
| `SESSIONSECURITY=STRICT` (TLS 1.2+) | `impl-security-network.md § NET-1` |
| Encrypted stash / no `-PA=` on CLI | `impl-security-identity-credentials.md § CRED-2` |
| 30-day password expiration | SP server provisioning (§ CRED-5 below) |
| Account lockout after 5 bad attempts | `impl-security-policy.md § POL-3` |
| LDAP-backed credentials (if available) | `impl-security-integrations.md § INT-1` |

### SP commands — MFA exemption (explicit, documented)

```
* MCP service accounts are explicitly MFAREQUIRED=NO.
* This is intentional: dsmadmc cannot satisfy TOTP interactively.
* Compensating controls are documented in impl-security-identity-credentials.md.
UPDATE ADMIN mcp-svc-system   MFAREQUIRED=NO
UPDATE ADMIN mcp-svc-storage  MFAREQUIRED=NO
UPDATE ADMIN mcp-svc-policy   MFAREQUIRED=NO
UPDATE ADMIN mcp-svc-operator MFAREQUIRED=NO
UPDATE ADMIN mcp-svc-readonly MFAREQUIRED=NO
```

### SP commands — MFA required for human admins

```
* All human administrators must use TOTP MFA.
UPDATE ADMIN <human-admin-name> MFAREQUIRED=YES
```

---

## CRED-5 — SP Server Provisioning Script

### What to add

**New file**: `scripts/provision-sp-service-accounts.sh`

This script is run once on each IBM SP server to create the five tiered service accounts. It is idempotent — accounts that already exist receive `UPDATE ADMIN` instead of `REGISTER ADMIN`.

```bash
#!/usr/bin/env bash
# scripts/provision-sp-service-accounts.sh
#
# Provisions five MCP service accounts on the IBM SP server.
# Run as: dsmadmc -id=<system-admin> -pa=<pwd> -dataonly=yes < provision-sp-service-accounts.sh
#
# Prerequisites:
#   - A system-privileged SP admin to run this script.
#   - IBM SP v8.1.16+ (MINPWLENGTH defaults to 15).
#
# Variables: set these before running, or export in the calling shell.
: "${MCP_PWD_READONLY:?MCP_PWD_READONLY must be set}"
: "${MCP_PWD_OPERATOR:?MCP_PWD_OPERATOR must be set}"
: "${MCP_PWD_STORAGE:?MCP_PWD_STORAGE must be set}"
: "${MCP_PWD_POLICY:?MCP_PWD_POLICY must be set}"
: "${MCP_PWD_SYSTEM:?MCP_PWD_SYSTEM must be set}"

set -euo pipefail

DSMADMC_OPTS="-NOConfirm -DATAONLY=YES"

run_sp() {
    dsmadmc $DSMADMC_OPTS -id="${SP_ADMIN_ID}" -pa="${SP_ADMIN_PASSWORD}" "$@"
}

echo "=== Provisioning MCP service accounts on SP server ==="

# ── Read-only (any-admin, no privilege class) ──────────────────────────
run_sp "REGISTER ADMIN mcp-svc-readonly ${MCP_PWD_READONLY} CONTACT='MCP readonly service account'"
run_sp "UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Operator ───────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-operator ${MCP_PWD_OPERATOR} CONTACT='MCP operator service account'"
run_sp "GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR"
run_sp "UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Storage ────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-storage ${MCP_PWD_STORAGE} CONTACT='MCP storage service account'"
run_sp "GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE"
run_sp "UPDATE ADMIN mcp-svc-storage SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Policy ─────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-policy ${MCP_PWD_POLICY} CONTACT='MCP policy service account'"
run_sp "GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY"
run_sp "UPDATE ADMIN mcp-svc-policy SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── System ─────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-system ${MCP_PWD_SYSTEM} CONTACT='MCP system service account'"
run_sp "GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM"
run_sp "UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Verify ─────────────────────────────────────────────────────────────
echo "=== Verifying accounts ==="
run_sp "QUERY ADMIN mcp-svc-* FORMAT=DETAILED" | grep -E "(Admin Name|System Priv|Storage Priv|Policy Priv|Operator Priv|Session Security|MFAR)"

echo "=== Done. Run provision-sp-service-accounts.sh on each SP server ==="
```

### Usage

```bash
export SP_ADMIN_ID=<your-system-admin>
export SP_ADMIN_PASSWORD=<your-system-admin-password>
export MCP_PWD_READONLY=$(openssl rand -base64 20)
export MCP_PWD_OPERATOR=$(openssl rand -base64 20)
export MCP_PWD_STORAGE=$(openssl rand -base64 20)
export MCP_PWD_POLICY=$(openssl rand -base64 20)
export MCP_PWD_SYSTEM=$(openssl rand -base64 20)

# Store these generated passwords securely before running
echo "mcp-svc-readonly: $MCP_PWD_READONLY"
echo "mcp-svc-operator: $MCP_PWD_OPERATOR"
echo "mcp-svc-storage:  $MCP_PWD_STORAGE"
echo "mcp-svc-policy:   $MCP_PWD_POLICY"
echo "mcp-svc-system:   $MCP_PWD_SYSTEM"

bash scripts/provision-sp-service-accounts.sh
```

---

## Verification Checklist

```bash
# CRED-1: Per-module credential loading
SP_ADMIN_ID_READONLY=mcp-svc-readonly \
SP_ADMIN_PASSWORD_READONLY=test \
python3 -c "
from sp_mcp_server.config import load_config
c = load_config()
cred = c.credential_for('any')
assert cred.privilege == 'any', cred
print('CRED-1 OK:', cred.admin_id)
"

# CRED-2: No -PA= in process args when stash mode enabled
SP_MCP_USE_PASSWORD_STASH=1 \
python3 -c "
from sp_mcp_server.cli_wrapper import DsmAdmcWrapper
from sp_mcp_server.config import ServerConfig, ModuleCredential
cfg = ServerConfig(server_address='localhost', server_port='1500',
                   credentials={'any': ModuleCredential('test-id', 'test-pw', 'any')})
w = DsmAdmcWrapper(cfg)
# Inspect that -PA= is absent from args construction
import unittest.mock, subprocess
with unittest.mock.patch('subprocess.run') as mock_run:
    mock_run.return_value = unittest.mock.MagicMock(returncode=0, stdout='', stderr='')
    w.execute('QUERY STATUS')
    call_args = mock_run.call_args[0][0]
    assert not any('-PA=' in a for a in call_args), 'FAIL: -PA= still in args: ' + str(call_args)
    print('CRED-2 OK: no -PA= in args')
"

# CRED-3: .env permission check
echo "test=1" > /tmp/test.env && chmod 644 /tmp/test.env
python3 -c "
from sp_mcp_server.config import _load_env_permission_check
try:
    _load_env_permission_check('/tmp/test.env')
    print('FAIL: should have raised')
except PermissionError as e:
    print('CRED-3 OK:', e)
"
rm /tmp/test.env
```

---

## RG-2 — `secure_startup()`: Atomic Entry-Point Guard (CRED-3 extension)

### Problem

CRED-3 requires every `main_*.py` entry point to call `check_env_file_permissions()` before `load_dotenv()`. Inspection found that 14 newer module-specific entry points called only `load_dotenv()` — the permission check was silently omitted.

### What changed

**File**: [`src/sp_mcp_server/config.py`](../../src/sp_mcp_server/config.py)

A new `secure_startup()` helper combines both operations atomically:

```python
def secure_startup(env_path: str = ".env") -> None:
    """CRED-3 / RG-2: Atomic permission check + dotenv load."""
    check_env_file_permissions(env_path)
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass
```

**All 15 `main_*.py` entry points** now use `secure_startup()` instead of separate `check_env_file_permissions()` + `load_dotenv()` calls:

```python
# Before (RG-2 gap):
from dotenv import load_dotenv
load_dotenv()

# After (RG-2 fixed):
from .config import secure_startup
secure_startup()
```

### Entry points updated

All 15 entry points now call `secure_startup()`:
`main.py`, `main_ops.py`, `main_ops_maintenance.py`, `main_ops_protection.py`, `main_ops_rules.py`, `main_clients_core.py`, `main_clients_config.py`, `main_policies_lifecycle.py`, `main_policies_management.py`, `main_storage_device.py`, `main_storage_hardware.py`, `main_storage_pools.py`, `main_system_admin.py`, `main_system_config.py`, `main_volumes.py`

### For new entry points

Any future `main_*.py` must use the same pattern. `secure_startup()` is the single canonical hook — do not split the permission check from `load_dotenv()`.

### Automated test coverage

[`tests/test_security_controls.py::TestSecureStartup`](../../tests/test_security_controls.py) and `TestEnvFilePermissions`

---

## RG-3 — `_execute_silent_query()`: Silent Execution for Password-Bearing Commands

### Problem

`execute_silent()` was added to `DsmAdmcWrapper` for `DefineConnection` / `UpdateConnection` (INT-3). However, `REGISTER ADMIN`, `UPDATE ADMIN <pwd>`, `REGISTER NODE`, and `UPDATE NODE <pwd>` commands all build a command string with the plaintext password and then call `_execute_simple_query()` → `execute()` → `logger.info(command)`. Node and admin passwords appeared in `mcp-server.log`.

### What changed

**File**: [`src/sp_mcp_server/commands/base.py`](../../src/sp_mcp_server/commands/base.py)

New helper on `BaseCommand`:

```python
def _execute_silent_query(self, query_cmd: str) -> str:
    """RG-3: Execute a command without logging the command string.
    Use for commands whose string contains a plaintext password."""
    stdout, stderr, code = self.cli.execute_silent(query_cmd)
    if code != 0:
        return self._format_command_error("Error executing command:", stdout, stderr)
    return stdout
```

**Files**: [`commands/system/admin.py`](../../src/sp_mcp_server/commands/system/admin.py), [`commands/clients/node.py`](../../src/sp_mcp_server/commands/clients/node.py)

| Command | Before | After |
|---------|--------|-------|
| `DefineAdmin.execute()` — `REGISTER ADMIN <name> <pwd>` | `_execute_simple_query` | `_execute_silent_query` |
| `UpdateUser.execute()` — `UPDATE ADMIN <name> <pwd>` (with password) | `_execute_simple_query` | `_execute_silent_query` |
| `UpdateUser.execute()` — contact-only update | `_execute_simple_query` | `_execute_simple_query` (unchanged) |
| `RegisterNode.execute()` — `REGISTER NODE <name> <pwd> DOMAIN=` | `_execute_simple_query` | `_execute_silent_query` |
| `UpdateNode.execute()` — `UPDATE NODE <name> <pwd>` (with password) | `_execute_simple_query` | `_execute_silent_query` |
| `UpdateNode.execute()` — domain/contact-only update | `_execute_simple_query` | `_execute_simple_query` (unchanged) |

### SP commands requiring silent execution (complete list)

Any SP command that embeds a credential as a positional or named argument must use `_execute_silent_query()`:

- `REGISTER ADMIN <name> <password>`
- `UPDATE ADMIN <name> <password>`
- `REGISTER NODE <name> <password> DOMAIN=<domain>`
- `UPDATE NODE <name> <password>`
- `DEFINE SERVER <name> ... PASSWORD=<password>` (if implemented)

### Automated test coverage

[`tests/test_security_controls.py::TestPasswordCommandsSilentExecution`](../../tests/test_security_controls.py)

