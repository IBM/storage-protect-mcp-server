# Implementation: Access Management

* **Domain**: Access Management
* **Analysis reference**: [`docs/analysis/security-design-analysis.md § 3`](../analysis/security-design-analysis.md)
* **Gaps addressed**: A1, A2, A3, A4
* **Files changed**: `src/sp_mcp_server/commands/base.py`, `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/cli_wrapper.py`, all command files under `src/sp_mcp_server/commands/`

---

## Overview

The static access-management controls are implemented, but dynamic-session and OIDC request authorization are not complete. Source remediation must add a call-time gate and negative tests before all access gaps can be considered closed.

The implemented static controls are:

| ID | Change | Gaps closed |
|----|--------|-------------|
| ACC-1 | Add `required_privilege` property to `BaseCommand`, `BaseOfflineCommand`, `BaseServermonCommand` | A1, A2 |
| ACC-2 | Self-narrowing tool registration in `mcp_factory.py` based on configured service-account privilege | Static gate implemented; dynamic/OIDC call-time gate pending |
| ACC-3 | Annotate all existing command classes with `required_privilege` | A2, A3 |
| ACC-4 | Replace `su` with `sudo` + sudoers allowlist in `DsmServWrapper` / `ServermonWrapper` | A4 |

---

## ACC-1 — `required_privilege` on All Base Command Classes

### What to change

**File**: [`src/sp_mcp_server/commands/base.py`](../../src/sp_mcp_server/commands/base.py)

Add a `required_privilege` property with a default of `"any"` to all three base classes. Each concrete command overrides this to declare the minimum SP privilege class it requires.

```python
# src/sp_mcp_server/commands/base.py

# ── Privilege hierarchy (narrowest → broadest) ───────────────────────────
# 'any'      — any registered admin (no specific privilege class needed)
# 'operator' — requires SP Operator privilege class
# 'storage'  — requires SP Storage privilege class
# 'policy'   — requires SP Policy privilege class
# 'system'   — requires SP System privilege class (highest)
PRIVILEGE_TIERS = ("any", "operator", "storage", "policy", "system")


class BaseCommand(ABC):
    """Abstract base class for all dsmadmc commands exposed as MCP tools."""

    def __init__(self, cli: DsmAdmcWrapper):
        self.cli = cli

    # ── existing abstract properties ────────────────────────────────────
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str: ...

    # ── NEW: privilege annotation ────────────────────────────────────────
    @property
    def required_privilege(self) -> str:
        """
        Minimum SP privilege class required to execute this tool.
        Values: 'system' | 'policy' | 'storage' | 'operator' | 'any'
        Default 'any' means any registered administrator can run it.
        Override in subclasses to restrict access.
        """
        return "any"

    # ── existing tool_type (kept for backward compatibility) ─────────────
    @property
    def tool_type(self) -> str:
        """Infers read-only vs destructive from name. Legacy — prefer required_privilege."""
        if self.name.lower().startswith("query") or "info" in self.name.lower():
            return "read-only"
        return "destructive"

    # ── existing helper methods unchanged ────────────────────────────────
    def _execute_simple_query(self, query_cmd: str) -> str:
        stdout, stderr, code = self.cli.execute(query_cmd)
        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout

    def _format_command_error(self, prefix: str, stdout: str, stderr: str) -> str:
        parts = []
        if (stdout or "").strip(): parts.append(f"Output: {stdout.strip()}")
        if (stderr or "").strip(): parts.append(f"Error: {stderr.strip()}")
        return f"{prefix}\n" + ("\n".join(parts) if parts else "Unknown error occurred")


class BaseOfflineCommand(ABC):
    """Abstract base class for offline dsmserv utility commands."""

    def __init__(self, cli):  # DsmServWrapper
        self.cli = cli

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str: ...

    @property
    def required_privilege(self) -> str:
        """Offline commands require system privilege by default."""
        return "system"

    def _execute_utility(self, command: str) -> str:
        stdout, stderr, code = self.cli.execute(command)
        if code != 0:
            return self._format_command_error("Error executing utility:", stdout, stderr)
        return stdout

    def _format_command_error(self, prefix, stdout, stderr):
        parts = []
        if (stdout or "").strip(): parts.append(f"Output: {stdout.strip()}")
        if (stderr or "").strip(): parts.append(f"Error: {stderr.strip()}")
        return f"{prefix}\n" + ("\n".join(parts) if parts else "Unknown error occurred")


class BaseServermonCommand(ABC):
    """Abstract base class for servermon commands."""

    def __init__(self, cli):  # ServermonWrapper
        self.cli = cli

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str: ...

    @property
    def required_privilege(self) -> str:
        """Servermon commands require at least operator privilege."""
        return "operator"

    def _execute_servermon(self, args: List[str]) -> str:
        stdout, stderr, code = self.cli.execute(args)
        if code != 0:
            return self._format_command_error("Error running servermon:", stdout, stderr)
        return stdout

    def _format_command_error(self, prefix, stdout, stderr):
        parts = []
        if (stdout or "").strip(): parts.append(f"Output: {stdout.strip()}")
        if (stderr or "").strip(): parts.append(f"Error: {stderr.strip()}")
        return f"{prefix}\n" + ("\n".join(parts) if parts else "Unknown error occurred")
```

---

## ACC-2 — Self-Narrowing Tool Registration in `mcp_factory.py`

This section describes service-account mode. It does not yet implement authorization from `SessionLease.privilege_classes` or `request.state.mcp_privilege`.

### What to change

**File**: [`src/sp_mcp_server/mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py)

Add a `_parse_sp_privilege()` helper and call it in `create_mcp_server()` to determine the effective privilege tier of the loaded service account. Register only tools whose `required_privilege` the account satisfies.

```python
# src/sp_mcp_server/mcp_factory.py

from .commands.base import PRIVILEGE_TIERS

# ── Privilege satisfaction table ─────────────────────────────────────────
# A 'system' account satisfies all privilege tiers.
# A 'storage' account satisfies 'storage' and 'any', but NOT 'policy' or 'system'.
_PRIVILEGE_SATISFIES: Dict[str, set] = {
    "system":   {"system", "policy", "storage", "operator", "any"},
    "policy":   {"policy", "any"},
    "storage":  {"storage", "any"},
    "operator": {"operator", "any"},
    "any":      {"any"},
}


def _parse_sp_privilege(query_admin_stdout: str) -> str:
    """
    Parse the privilege class from QUERY ADMIN <name> FORMAT=DETAILED output.
    Returns the broadest privilege tier the account holds.
    """
    upper = query_admin_stdout.upper()

    # IBM SP prints 'System Privilege: Yes' for system admins
    if "SYSTEM PRIVILEGE: YES" in upper:
        return "system"
    if "POLICY PRIVILEGE: YES" in upper:
        return "policy"
    if "STORAGE PRIVILEGE: YES" in upper:
        return "storage"
    if "OPERATOR PRIVILEGE: YES" in upper:
        return "operator"
    return "any"


def create_mcp_server(
    server_name: str,
    tool_classes: List[Any],
    allowed_modes: List[str] = None
):
    config = load_config()

    admc_cli = DsmAdmcWrapper(config)
    serv_cli = DsmServWrapper(config)
    mon_cli  = ServermonWrapper(config)

    # NET-1: session security check (see impl-security-network.md)
    _validate_session_security(admc_cli, config)

    # ── ACC-2: determine account privilege tier ──────────────────────────
    stdout, _, code = admc_cli.execute(
        f"QUERY ADMIN {config.admin_id} FORMAT=DETAILED"
    )
    if code == 0:
        account_privilege = _parse_sp_privilege(stdout)
    else:
        logger.warning(
            "ACC-2: Could not determine SP privilege for '%s'. "
            "Defaulting to 'any' (read-only tools only).",
            config.admin_id
        )
        account_privilege = "any"

    satisfies = _PRIVILEGE_SATISFIES.get(account_privilege, {"any"})
    logger.info(
        "ACC-2: Account '%s' has SP privilege '%s'. "
        "Will register tools requiring: %s",
        config.admin_id, account_privilege, satisfies
    )
    # ────────────────────────────────────────────────────────────────────

    commands = {}

    for obj in tool_classes:
        try:
            inst = None
            if inspect.isclass(obj) and issubclass(obj, BaseCommand) and obj is not BaseCommand:
                inst = obj(admc_cli)
            elif inspect.isclass(obj) and issubclass(obj, BaseOfflineCommand) and obj is not BaseOfflineCommand:
                inst = obj(serv_cli)
            elif inspect.isclass(obj) and issubclass(obj, BaseServermonCommand) and obj is not BaseServermonCommand:
                inst = obj(mon_cli)

            if inst is None:
                continue

            # ── ACC-2: privilege gate ────────────────────────────────────
            tool_priv = getattr(inst, "required_privilege", "any")
            if tool_priv not in satisfies:
                logger.debug(
                    "ACC-2: Skipping tool '%s' — requires '%s', "
                    "account satisfies: %s",
                    inst.name, tool_priv, satisfies
                )
                continue
            # ────────────────────────────────────────────────────────────

            # Legacy --mode filter (kept for backward compatibility)
            if allowed_modes and "full" not in allowed_modes:
                if inst.tool_type not in allowed_modes:
                    continue

            commands[inst.name] = inst

        except Exception as e:
            logger.error("Failed to instantiate command %s: %s", obj, e)

    logger.info(
        "ACC-2: Registered %d tools for privilege tier '%s'.",
        len(commands), account_privilege
    )

    # ── Rest of existing MCP server setup unchanged ──────────────────────
    server = Server(server_name)

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(name=cmd.name, description=cmd.description, inputSchema=cmd.args_schema)
            for cmd in commands.values()
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        if name not in commands:
            raise ValueError(f"Unknown tool: {name}")
        cmd = commands[name]
        try:
            result = await asyncio.to_thread(cmd.execute, arguments or {})
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error("Error executing tool %s: %s", name, e)
            return [TextContent(type="text", text=f"Error: {e}")]

    return server
```

### Registration behaviour by account tier

| Account privilege | Tools registered | Excluded |
|-------------------|-----------------|----------|
| `system` | All ~130 tools | None |
| `policy` | Policy tools + all `any`-privilege tools | `system`, `storage`, `operator` tools |
| `storage` | Storage tools + all `any`-privilege tools | `system`, `policy`, `operator` tools |
| `operator` | Operator tools + all `any`-privilege tools | `system`, `policy`, `storage` tools |
| `any` (readonly) | Only `any`-privilege tools (QUERY, info commands) | All write/modify tools |

---

## ACC-3 — Annotate Existing Command Classes

### What to change

Every command class under `src/sp_mcp_server/commands/` must override `required_privilege`. The table below documents the mapping; add the property to each class.

### `required_privilege` mapping by command group

#### System commands — `commands/system/admin.py`

```python
# Pattern to add to each class:
@property
def required_privilege(self) -> str:
    return "system"
```

| Class | `required_privilege` | Rationale |
|-------|---------------------|-----------|
| `DefineAdmin` | `"system"` | `REGISTER ADMIN` requires System privilege |
| `UpdateUser` | `"system"` | `UPDATE ADMIN` requires System privilege |
| `DeleteAdmin` | `"system"` | `REMOVE ADMIN` requires System privilege |
| `SetUserLock` | `"system"` | `LOCK/UNLOCK ADMIN` requires System privilege |
| `GrantAuthority` | `"system"` | `GRANT AUTHORITY` requires System privilege |
| `RevokeAuthority` | `"system"` | `REVOKE AUTHORITY` requires System privilege |
| `RegisterLicense` | `"system"` | `REGISTER LICENSE` requires System privilege |
| `QueryAdminUser` | `"any"` | `QUERY ADMIN` available to any admin |
| `QueryLicenseInfo` | `"any"` | `QUERY LICENSE` available to any admin |

#### System commands — `commands/system/server.py`

| Class | `required_privilege` |
|-------|---------------------|
| `DefineServer` | `"system"` |
| `UpdateServer` | `"system"` |
| `DeleteServer` | `"system"` |
| `DefineServerGroup` | `"system"` |
| `UpdateServerGroup` | `"system"` |
| `DeleteServerGroup` | `"system"` |
| `DefineGroupMember` | `"system"` |
| `DeleteGroupMember` | `"system"` |
| `DefineEventServer` | `"system"` |
| `DeleteEventServer` | `"system"` |
| `QueryServerStatus` | `"any"` |
| `QueryServerOption` | `"any"` |

#### System commands — `commands/system/conn.py`

| Class | `required_privilege` |
|-------|---------------------|
| `DefineConnection` | `"system"` |
| `UpdateConnection` | `"system"` |
| `DeleteConnection` | `"system"` |

#### Storage commands — `commands/storage/stgpool.py`, `volume.py`, `library.py`, etc.

| Class | `required_privilege` |
|-------|---------------------|
| `DefineStoragePool` | `"storage"` |
| `UpdateStoragePool` | `"storage"` |
| `DeleteStoragePool` | `"storage"` |
| `DefineVolume` | `"storage"` |
| `UpdateVolume` | `"operator"` |
| `DeleteVolume` | `"storage"` |
| `DefineLibrary` | `"storage"` |
| `UpdateLibrary` | `"storage"` |
| `DeleteLibrary` | `"storage"` |
| `DefineDrive` | `"storage"` |
| `UpdateDrive` | `"storage"` |
| `DeleteDrive` | `"storage"` |
| `DefineDeviceClass` | `"storage"` |
| `UpdateDeviceClass` | `"storage"` |
| `DeleteDeviceClass` | `"storage"` |
| `Query*` (all storage query classes) | `"any"` |

#### Policy commands — `commands/policies/`

| Class | `required_privilege` |
|-------|---------------------|
| `DefinePolicyDomain` | `"policy"` |
| `UpdatePolicyDomain` | `"policy"` |
| `DeletePolicyDomain` | `"policy"` |
| `DefinePolicySet` | `"policy"` |
| `UpdatePolicySet` | `"policy"` |
| `DeletePolicySet` | `"policy"` |
| `ActivatePolicySet` | `"policy"` |
| `ValidatePolicySet` | `"policy"` |
| `DefineManagementClass` | `"policy"` |
| `UpdateManagementClass` | `"policy"` |
| `DeleteManagementClass` | `"policy"` |
| `DefineCopyGroup` | `"policy"` |
| `UpdateCopyGroup` | `"policy"` |
| `DeleteCopyGroup` | `"policy"` |
| `DefineSchedule` | `"policy"` |
| `UpdateSchedule` | `"policy"` |
| `DeleteSchedule` | `"policy"` |
| `Query*` (all policy query classes) | `"any"` |

#### Client commands — `commands/clients/`

| Class | `required_privilege` |
|-------|---------------------|
| `RegisterNode` | `"policy"` |
| `UpdateNode` | `"policy"` |
| `DeleteNode` / `DeleteClient` | `"policy"` |
| `RenameClient` | `"policy"` |
| `SetClientLock` | `"operator"` |
| `DefineNodeGroup` | `"policy"` |
| `DefineAssociation` | `"policy"` |
| `Query*` (all client query classes) | `"any"` |

#### Operations — `commands/operations/`

| Class | `required_privilege` |
|-------|---------------------|
| `BackupDB` | `"operator"` |
| `RestoreDB` | `"system"` |
| `MoveDataContainer` | `"storage"` |
| `MoveClientData` | `"storage"` |
| `ReclaimStorageSpace` | `"storage"` |
| `DefineAlertTrigger` | `"operator"` |
| `UpdateAlertTrigger` | `"operator"` |
| `DeleteAlertTrigger` | `"operator"` |
| `DefineStorageRule` | `"storage"` |
| `DefineRetentionRule` | `"policy"` |
| `DefineHold` | `"policy"` |
| `Query*` (all ops query classes) | `"any"` |

#### Offline / Servermon commands

```python
# BaseOfflineCommand already defaults required_privilege = "system"
# BaseServermonCommand already defaults required_privilege = "operator"
# Override in subclasses only if a narrower privilege is appropriate.
```

---

## ACC-4 — Replace `su` with `sudo` in `DsmServWrapper` and `ServermonWrapper`

### What to change

**File**: [`src/sp_mcp_server/cli_wrapper.py`](../../src/sp_mcp_server/cli_wrapper.py)

Replace `su - <user> -c "<cmd>"` with `sudo -u <user> -- <binary> <args>` in both `DsmServWrapper.execute()` and `ServermonWrapper.execute()`. This constrains privilege escalation to the specific binary rather than allowing arbitrary shell commands.

```python
# src/sp_mcp_server/cli_wrapper.py — DsmServWrapper.execute()

def execute(self, command: str) -> Tuple[str, str, int]:
    args = [self.executable]
    if self.config.server_instance_dir:
        args.extend(["-i", self.config.server_instance_dir])
    args.extend(command.split())

    try:
        if self.config.instance_user:
            # ── ACC-4: use sudo instead of su ────────────────────────────
            # sudoers rule must exist:
            #   mcp-runner ALL=(tsmsvr01) NOPASSWD: /opt/tivoli/tsm/server/bin/dsmserv
            sudo_args = ["sudo", "-u", self.config.instance_user, "--"] + args
            logger.info(
                "Executing offline command via sudo as %s: %s",
                self.config.instance_user, " ".join(args)
            )
            process = subprocess.run(
                sudo_args,
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )
        else:
            logger.warning(
                "SP_INSTANCE_USER not configured. "
                "Running dsmserv as current user — may fail."
            )
            process = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )
        return process.stdout, process.stderr, process.returncode

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = e.stderr.decode() if e.stderr else ""
        return stdout, stderr or "Command timed out", 124
    except FileNotFoundError:
        return "", f"dsmserv not found at '{self.executable}'.", 127
    except Exception as e:
        return "", str(e), 1
```

Apply the identical change to `ServermonWrapper.execute()`.

### `sudoers` rule (deploy on SP server)

```bash
# /etc/sudoers.d/mcp-server  (create with visudo -f or deploy via Ansible)
# Allows mcp-runner to run dsmserv as tsmsvr01 with no password prompt.
# Adjust paths to match your SP installation.

mcp-runner ALL=(tsmsvr01) NOPASSWD: /opt/tivoli/tsm/server/bin/dsmserv
mcp-runner ALL=(tsmsvr01) NOPASSWD: /opt/tivoli/tsm/server/bin/servermon
```

```bash
# Deploy
sudo visudo -cf /etc/sudoers.d/mcp-server   # validate syntax
sudo chmod 440 /etc/sudoers.d/mcp-server

# Test — should run without a password prompt
sudo -u tsmsvr01 /opt/tivoli/tsm/server/bin/dsmserv -? 2>&1 | head -3
```

---

## Required Follow-Up Verification

- [ ] Add call-time dynamic-session privilege allow/deny tests.
- [ ] Add OIDC scope-to-tool allow/deny tests.
- [ ] Verify that the execution credential context matches the authorized context.
- [ ] Re-run the complete suite in an installed, dependency-complete environment.

## Verification Checklist

```bash
# ACC-1: required_privilege present on all base classes
python3 -c "
from sp_mcp_server.commands.base import BaseCommand, BaseOfflineCommand, BaseServermonCommand
# Check default values
assert hasattr(BaseCommand, 'required_privilege')
assert hasattr(BaseOfflineCommand, 'required_privilege')
assert hasattr(BaseServermonCommand, 'required_privilege')
print('ACC-1 OK: required_privilege present on all base classes')
"

# ACC-2: tool registration is narrowed by privilege tier
python3 -c "
from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES, _parse_sp_privilege
# system satisfies everything
assert 'storage' in _PRIVILEGE_SATISFIES['system']
# storage does not satisfy system
assert 'system' not in _PRIVILEGE_SATISFIES['storage']
# any only satisfies any
assert _PRIVILEGE_SATISFIES['any'] == {'any'}
print('ACC-2 OK: privilege satisfaction table correct')
"

# ACC-3: spot-check command annotations
python3 -c "
from sp_mcp_server.commands.system.admin import DefineAdmin, QueryAdminUser
from sp_mcp_server.commands.system.server import DeleteServer, QueryServerStatus
from sp_mcp_server.cli_wrapper import DsmAdmcWrapper
from sp_mcp_server.config import ServerConfig, ModuleCredential
cfg = ServerConfig('localhost', '1500', credentials={'any': ModuleCredential('t','t','any')})
cli = DsmAdmcWrapper(cfg)
assert DefineAdmin(cli).required_privilege == 'system', DefineAdmin(cli).required_privilege
assert QueryAdminUser(cli).required_privilege == 'any',  QueryAdminUser(cli).required_privilege
assert DeleteServer(cli).required_privilege == 'system', DeleteServer(cli).required_privilege
assert QueryServerStatus(cli).required_privilege == 'any', QueryServerStatus(cli).required_privilege
print('ACC-3 OK: command annotations correct')
"

# ACC-4: sudo in DsmServWrapper args (no 'su' string)
python3 -c "
import unittest.mock, subprocess
from sp_mcp_server.cli_wrapper import DsmServWrapper
from sp_mcp_server.config import ServerConfig
cfg = ServerConfig('localhost', '1500', admin_id='t', admin_password='t',
                   instance_user='tsmsvr01', dsmserv_path='/bin/echo')
w = DsmServWrapper(cfg)
with unittest.mock.patch('subprocess.run') as mock_run:
    mock_run.return_value = unittest.mock.MagicMock(returncode=0, stdout='', stderr='')
    w.execute('DISPLAY DBSPACE')
    call_args = mock_run.call_args[0][0]
    assert 'sudo' in call_args, 'FAIL: sudo not in args: ' + str(call_args)
    assert 'su' not in call_args, 'FAIL: su still in args: ' + str(call_args)
    print('ACC-4 OK: sudo used, su removed')
"
```
