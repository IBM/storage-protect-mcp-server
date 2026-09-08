from __future__ import annotations
import asyncio
import sys
import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
import inspect
from typing import Any, Sequence, List, Dict, Optional, Set
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .config import load_config
from .cli_wrapper import DsmAdmcWrapper, DsmServWrapper, ServermonWrapper
from .commands.base import BaseCommand, BaseOfflineCommand, BaseServermonCommand, PRIVILEGE_TIERS

# Configure logging with both file and stderr output
def setup_logging():
    """Configure logging with file rotation and stderr output."""
    # Get log file path from environment or use default
    log_dir = os.environ.get("SP_MCP_LOG_DIR", "/var/log/ibm-sp-mcp-server")
    log_file = os.path.join(log_dir, "mcp-server.log")
    
    # Create log directory if it doesn't exist
    try:
        os.makedirs(log_dir, exist_ok=True)
    except (OSError, PermissionError) as e:
        # If we can't create /var/log directory, fall back to /tmp
        log_dir = "/tmp/ibm-sp-mcp-server"
        log_file = os.path.join(log_dir, "mcp-server.log")
        os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler (stderr) - less verbose for console
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Get our logger
    logger = logging.getLogger("ibm-sp-mcp-server")
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger

# Initialize logging
logger = setup_logging()


def _validate_session_security(admc_cli: DsmAdmcWrapper, config) -> None:
    """
    NET-1: Assert that every configured SP service account has SESSIONSECURITY=STRICT.

    For each privilege tier with a configured credential, queries IBM SP via
    QUERY ADMIN <admin_id> FORMAT=DETAILED and checks:
      - Session Security: Strict
      - Transport Method: TLS 1.2 or TLS 1.3  (advisory — blank is also accepted)

    Refuses server startup (sys.exit(1)) if:
      - The query fails (wrong credentials, SP unreachable)
      - Session Security is not 'Strict'
      - Transport Method is present but contains no 'TLS'

    CRED-1: Uses credential_for() to resolve the admin ID for each tier so
            the check works with both per-module and legacy single credentials.

    Override for testing only:
      Set SP_MCP_SKIP_SECURITY_CHECKS=1 to bypass this check.
      NEVER use this in production.
    """
    if os.environ.get("SP_MCP_SKIP_SECURITY_CHECKS") == "1":
        # RG-1: Distinguish test bypass from a misconfigured production deployment.
        # In production (SP_MCP_ENV=production) this variable must never be set.
        if os.environ.get("SP_MCP_ENV", "").lower() == "production":
            logger.error(
                "SECURITY [RG-1]: SP_MCP_SKIP_SECURITY_CHECKS=1 is set but "
                "SP_MCP_ENV=production. "
                "PRODUCTION UNSAFE — all session security checks are disabled. "
                "Unset SP_MCP_SKIP_SECURITY_CHECKS before running in production."
            )
            sys.exit(1)
        logger.warning(
            "NET-1: SESSIONSECURITY check SKIPPED (SP_MCP_SKIP_SECURITY_CHECKS=1). "
            "Do not use this override in production. "
            "Set SP_MCP_ENV=production to prevent this bypass on production hosts."
        )
        return

    # Collect the unique admin IDs that are actually configured.
    # With per-module credentials, there may be up to 5 distinct accounts.
    # With a legacy single credential, there is exactly 1.
    from .config import PRIVILEGE_TIERS
    seen_ids: set = set()
    accounts_to_check = []
    for tier in PRIVILEGE_TIERS:
        cred = config.credential_for(tier)
        if cred and cred.admin_id not in seen_ids:
            seen_ids.add(cred.admin_id)
            accounts_to_check.append(cred.admin_id)

    if not accounts_to_check:
        logger.warning(
            "NET-1: No service account credentials configured — "
            "cannot validate session security. Skipping check."
        )
        return

    for admin_id in accounts_to_check:
        stdout, stderr, code = admc_cli.execute(
            f"QUERY ADMIN {admin_id} FORMAT=DETAILED"
        )

        if code != 0:
            logger.error(
                "SECURITY [NET-1]: Cannot query service account '%s'. "
                "Verify credentials and SP server connectivity. stderr: %s",
                admin_id, stderr.strip()
            )
            sys.exit(1)

        # Parse key: value pairs from QUERY ADMIN FORMAT=DETAILED output.
        # IBM SP uses comma-delimited mode (-DATAONLY=YES -COMMAdelimited) in
        # the wrapper, but QUERY ADMIN FORMAT=DETAILED returns labelled rows
        # even in that mode.
        fields: Dict[str, str] = {}
        for line in stdout.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                fields[key.strip()] = val.strip().rstrip(",")

        session_security = fields.get("Session Security", "")
        transport_method = fields.get("Transport Method", "")

        if session_security.lower() != "strict":
            logger.error(
                "SECURITY [NET-1]: Service account '%s' has SESSIONSECURITY=%s. "
                "Required value: Strict. "
                "Remediate on the SP server: UPDATE ADMIN %s SESSIONSECURITY=STRICT",
                admin_id,
                session_security if session_security else "(unknown — not in QUERY ADMIN output)",
                admin_id,
            )
            sys.exit(1)

        if transport_method and "TLS" not in transport_method.upper():
            logger.error(
                "SECURITY [NET-1]: Service account '%s' transport method is '%s'. "
                "TLS 1.2 or TLS 1.3 required.",
                admin_id, transport_method
            )
            sys.exit(1)

        logger.info(
            "NET-1: Session security check passed — account '%s': "
            "Session Security=%s, Transport Method=%s",
            admin_id,
            session_security,
            transport_method if transport_method else "(not reported)",
        )


# ── ACC-2: Privilege satisfaction table ──────────────────────────────────────
# A 'system' account satisfies all privilege tiers.
# A 'storage' account satisfies 'storage' and 'any', but not 'policy' or 'system'.
_PRIVILEGE_SATISFIES: Dict[str, Set[str]] = {
    "system":   {"system", "policy", "storage", "operator", "any"},
    "policy":   {"policy", "any"},
    "storage":  {"storage", "any"},
    "operator": {"operator", "any"},
    "any":      {"any"},
}


def _parse_sp_privilege(query_admin_stdout: str) -> str:
    """
    ACC-2: Parse the privilege class from QUERY ADMIN <name> FORMAT=DETAILED output.
    Returns the broadest privilege tier the account holds.
    """
    upper = query_admin_stdout.upper()
    if "SYSTEM PRIVILEGE: YES" in upper:
        return "system"
    if "POLICY PRIVILEGE: YES" in upper:
        return "policy"
    if "STORAGE PRIVILEGE: YES" in upper:
        return "storage"
    if "OPERATOR PRIVILEGE: YES" in upper:
        return "operator"
    return "any"


# ── POL-4: privilege tiers that require audit trail correlation entries ────────
_WRITE_PRIVILEGES: Set[str] = {"system", "policy", "storage", "operator"}


def _check_lockout_policy(admc_cli: DsmAdmcWrapper) -> None:
    """
    POL-3: Warn if IBM SP's account lockout threshold is disabled (limit = 0).
    Default at installation is 0 (disabled), which allows unlimited brute-force attempts.
    Recommended remediation: SET INVALIDPWLIMIT 5
    """
    stdout, _, code = admc_cli.execute("QUERY STATUS")
    if code != 0:
        logger.warning(
            "POL-3: Could not query SP server status for lockout check."
        )
        return

    for line in stdout.splitlines():
        if "Invalid Sign-on Attempt Limit" in line or "INVALIDPWLIMIT" in line.upper():
            parts = line.split(":")
            if len(parts) >= 2:
                val = parts[-1].strip().rstrip(",")
                if val == "0" or val == "" or val.lower() == "unlimited":
                    logger.warning(
                        "SECURITY [POL-3]: IBM SP account lockout is DISABLED "
                        "(Invalid Sign-on Attempt Limit = %s). "
                        "Brute-force attacks on SP accounts are unrestricted. "
                        "Remediate on SP server: SET INVALIDPWLIMIT 5",
                        val,
                    )
                else:
                    logger.info(
                        "POL-3: Account lockout threshold = %s. OK.", val
                    )
            return

    logger.warning(
        "POL-3: Could not determine lockout policy from QUERY STATUS output. "
        "Manually verify: SET INVALIDPWLIMIT 5 on the SP server."
    )


def create_mcp_server(server_name: str, tool_classes: List[Any], allowed_modes: Optional[List[str]] = None):
    """
    Creates an MCP Server instance populated with the provided tool command classes.

    Args:
        server_name: The name of the MCP server.
        tool_classes: A list of command classes to instantiate and register.
        allowed_modes: List of allowed modes (e.g. ["read-only", "destructive"]).
                       If None, all modes are allowed.
    """

    # Load configuration
    config = load_config()

    # Initialize CLI wrappers
    admc_cli = DsmAdmcWrapper(config)
    serv_cli = DsmServWrapper(config)
    mon_cli = ServermonWrapper(config)

    # ── NET-1: validate SP session security before registering any tools ──────
    _validate_session_security(admc_cli, config)

    # ── POL-3: warn if account lockout threshold is disabled ──────────────────
    _check_lockout_policy(admc_cli)

    # ── ACC-2: determine account privilege tier and narrow tool registration ──
    from .config import PRIVILEGE_TIERS as CONFIG_TIERS
    # Use the broadest credential to discover privilege (system is the default tier
    # used by DsmAdmcWrapper when no privilege is specified).
    cred = config.credential_for("system")
    account_id_for_query = cred.admin_id if cred else None
    account_privilege = "any"  # safe default if we can't query

    if account_id_for_query:
        stdout, _, code = admc_cli.execute(
            f"QUERY ADMIN {account_id_for_query} FORMAT=DETAILED"
        )
        if code == 0:
            account_privilege = _parse_sp_privilege(stdout)
        else:
            logger.warning(
                "ACC-2: Could not determine SP privilege for '%s'. "
                "Defaulting to 'any' (read-only tools only).",
                account_id_for_query,
            )

    satisfies: Set[str] = _PRIVILEGE_SATISFIES.get(account_privilege, {"any"})
    logger.info(
        "ACC-2: Account '%s' has SP privilege '%s'. "
        "Will register tools requiring: %s",
        account_id_for_query, account_privilege, satisfies,
    )
    # ─────────────────────────────────────────────────────────────────────────

    commands = {}

    # Instantiate commands
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

            # ── ACC-2: privilege gate ─────────────────────────────────────────
            tool_priv = getattr(inst, "required_privilege", "any")
            if tool_priv not in satisfies:
                logger.debug(
                    "ACC-2: Skipping tool '%s' — requires '%s', account satisfies: %s",
                    inst.name, tool_priv, satisfies,
                )
                continue

            # Legacy --mode filter (kept for backward compatibility)
            if allowed_modes and "full" not in allowed_modes:
                tool_type = getattr(inst, "tool_type", "read-only")
                if tool_type not in allowed_modes:
                    continue

            commands[inst.name] = inst

        except Exception as e:
            logger.error("Failed to instantiate command %s: %s", obj, e)

    logger.info(
        "ACC-2: Registered %d tools for privilege tier '%s'.",
        len(commands), account_privilege,
    )

    # Create MCP Server
    server = Server(server_name)

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(name=cmd.name, description=cmd.description, inputSchema=cmd.args_schema)
            for cmd in commands.values()
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        if name not in commands:
            raise ValueError(f"Unknown tool: {name}")

        cmd = commands[name]
        tool_privilege = getattr(cmd, "required_privilege", "any")

        # ── POL-4: emit attribution scratchpad entry for write operations ─────
        correlation_id = None
        if tool_privilege in _WRITE_PRIVILEGES:
            correlation_id = uuid.uuid4().hex[:12]
            audit_msg = (
                f"MCP_AUDIT tool={name} "
                f"priv={tool_privilege} "
                f"corr={correlation_id}"
            )
            logger.info("POL-4: Emitting audit correlation: %s", audit_msg)
            try:
                _stdout, _stderr, _code = await asyncio.to_thread(
                    admc_cli.execute,
                    f'DEFINE SCRATCHPADENTRY MCP_AUDIT DESCRIPTION="{audit_msg}"',
                )
                if _code != 0:
                    # RG-4: Explicit ERROR so SIEM/log aggregators can detect audit gaps.
                    logger.error(
                        "SECURITY [POL-4 / RG-4]: Audit write FAILED for tool='%s' "
                        "corr=%s (SP returned code %d: %s). "
                        "Write operation will proceed but this event has no ACTLOG record. "
                        "Verify SCRATCHPADENTRY write permission for the service account.",
                        name, correlation_id, _code, (_stderr or "no detail").strip(),
                    )
            except Exception as audit_exc:
                # RG-4: Promoted from WARNING to ERROR for SIEM detectability.
                logger.error(
                    "SECURITY [POL-4 / RG-4]: Audit write raised exception for "
                    "tool='%s' corr=%s: %s. "
                    "Write operation will proceed but this event has no ACTLOG record.",
                    name, correlation_id, audit_exc,
                )

        try:
            result = await asyncio.to_thread(cmd.execute, arguments or {})
            if correlation_id:
                logger.info(
                    "POL-4: Tool '%s' completed. SP ACTLOG correlation key: %s",
                    name, correlation_id,
                )
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error("Error executing tool %s: %s", name, e)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server

async def run_server(server: Server):
    """Run the server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
