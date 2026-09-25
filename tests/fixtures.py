"""
Shared test fixtures, constants, and factory helpers used across the test suite.

All hardcoded values (server addresses, credentials, paths, SP command output
snippets, etc.) are defined here so that each value has a single authoritative
source that is easy to locate and update.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Server / network constants
# ---------------------------------------------------------------------------

SP_SERVER_ADDRESS = "sp-server-01"
SP_SERVER_PORT = "1500"
SP_ALT_SERVER_PORT = "1600"
SP_ALT_SERVER_ADDRESS = "prod.server.com"
SP_TEST_SERVER_ADDRESS = "test.server.com"

# ---------------------------------------------------------------------------
# Credential constants
# ---------------------------------------------------------------------------

ADMIN_ID = "admin"
ADMIN_PASSWORD = "secret"          # generic test credential
ALT_ADMIN_ID = "superuser"
ALT_ADMIN_PASSWORD = "secret"
SVC_ADMIN_ID = "mcp-svc-system"
SVC_ADMIN_PASSWORD = "s3cr3t"
DYNAMIC_ADMIN_USER = "admin_test"
DYN_ADMIN_PASSWORD = "valid_password_123"
DYN_ADMIN_PASSWORD_WRONG = "wrong_password"
AUDIT_USER = "audited-admin@corp.com"

# Delegated-session credential pair used by subprocess / DAUTH tests
DELEGATED_USER = "dyn_user"
DELEGATED_PASS = "dyn_pass"
DELEGATED_USER_2 = "dyn_admin"
DELEGATED_PASS_2 = "dyn_pass"
DELEGATED_USER_3 = "dyn_admin2"
DELEGATED_PASS_3 = "dyn_pass2"

# Password used in session-lifecycle (AUD-08) tests
SESSION_PASSWORD_ALICE = "secret-pw"
SESSION_PASSWORD_BOB = "expired-pw"
SESSION_PASSWORD_CAROL = "cleanup-pw"
SESSION_PASSWORD_DAVE = "pw-a"
SESSION_PASSWORD_EVE = "pw-b"
SESSION_PASSWORD_FRANK = "frank-pw"
SESSION_PASSWORD_GRACE = "grace-pw"

# Password min-length override used in RG-3 silent-execution tests
TEST_PASSWORD_MINLENGTH = 8
TEST_PASSWORD_VALUE = "Password1!"
TEST_PASSWORD_NEW = "NewPass1!"

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

DSMADMC_PATH = "dsmadmc"            # resolved by shutil.which in production
DSMSERV_PATH = "/bin/dsmserv"
SERVERMON_PATH = "/bin/servermon"
SERVERMON_XML_DIR = "/tmp/servermon"
SP_INSTANCE_DIR = "/home/tsminst1"
SP_INSTANCE_USER = "tsminst1"

# Full-path variants used in environment-variable load tests
DSMSERV_PATH_FULL = "/opt/tivoli/tsm/server/bin/dsmserv"
SERVERMON_PATH_FULL = "/opt/tivoli/tsm/server/bin/servermon"
SERVERMON_XML_DIR_ALT = "/tsm/srvmon"
SP_INSTANCE_DIR_ALT = "/tsm/instance"

# TLS certificate paths (used in RG-5 HTTP-transport tests)
TLS_CERT_PATH = "/path/cert.crt"
TLS_KEY_PATH = "/path/cert.key"
TLS_CERT_PATH_SHORT = "/path/to/cert.crt"

# ---------------------------------------------------------------------------
# SP command output snippets (used as fake CLI stdout values)
# ---------------------------------------------------------------------------

SP_OUTPUT_SESSION_STRICT_TLS13 = (
    "Session Security: Strict\nTransport Method: TLS 1.3\nSystem Privilege: Yes"
)
SP_OUTPUT_SESSION_STRICT_TLS12 = (
    "Session Security: Strict\nTransport Method: TLS 1.2"
)
SP_OUTPUT_SESSION_TRANSITIONAL = (
    "Session Security: Transitional\nTransport Method: TLS 1.2"
)
SP_OUTPUT_SESSION_STRICT_ONLY = "Session Security: Strict"
SP_OUTPUT_QUERY_ADMIN_SYSTEM = (
    "Administrator Name: ADMIN_TEST\nSystem Privilege: Yes"
)
SP_OUTPUT_PRIVILEGE_SYSTEM = "SYSTEM PRIVILEGE: YES\nPOLICY PRIVILEGE: NO\n"
SP_OUTPUT_PRIVILEGE_OPERATOR = "SYSTEM PRIVILEGE: NO\nOPERATOR PRIVILEGE: YES\n"
SP_OUTPUT_PRIVILEGE_NONE = "No privilege classes listed.\n"
SP_OUTPUT_LOCKOUT_ZERO = "Invalid Sign-on Attempt Limit: 0"
SP_OUTPUT_LOCKOUT_FIVE = "Invalid Sign-on Attempt Limit: 5"
SP_OUTPUT_STATUS_OK = "STATUS OK"
SP_OUTPUT_SERVERMON_OK = "SERVERMON OK"
SP_OUTPUT_SCRATCHPAD_OK = "ANR0000I OK"
SP_OUTPUT_OFFLINE_OK = "offline ok"
SP_OUTPUT_SERVERMON_PLAIN = "servermon ok"
SP_OUTPUT_QUERY_OUTPUT = "Output data"
SP_OUTPUT_AUTH_OK = "ANR0000I Server status OK"
SP_OUTPUT_AUTH_FAIL_STDERR = "ANR2017E Invalid password"
SP_OUTPUT_DB_LOCKED_STDERR = "Database locked"
SP_OUTPUT_CONN_REFUSED_STDERR = "ANR0000E connection refused"
SP_OUTPUT_CONN_FAILED_STDERR = "connection failed"
SP_OUTPUT_PERMISSION_DENIED_STDERR = "Permission Denied"

# Servermon XML payload written to the results fixture directory
SERVERMON_XML_CONTENT = "<servermon>ready</servermon>"
SERVERMON_SUBDIR_NAME = ".20260306T1159-SERVER1"

# ---------------------------------------------------------------------------
# SP server / session binding identifiers
# ---------------------------------------------------------------------------

TARGET_SERVER_01 = "sp-server-01"
TARGET_SERVER_02 = "sp-server-02"

# Session-lease IDs used in unit tests for the helper functions
SESSION_LEASE_ID_A = "abc123"
SESSION_LEASE_ID_B = "def456"
SESSION_LEASE_ID_C = "ghi789"

# ---------------------------------------------------------------------------
# SP command strings asserted in unit tests
# ---------------------------------------------------------------------------

CMD_QUERY_STATUS = "QUERY STATUS"
CMD_QUERY_ACTLOG_SEARCH = "QUERY ACTLOG SEARCH=ANR2968E"
CMD_QUERY_ACTLOG_FILTERED = (
    "QUERY ACTLOG SEARCH=ERROR BEGINDATE=2026-07-15 ENDDATE=2026-07-16 "
    "BEGINTIME=08:00 ENDTIME=09:00"
)
CMD_DISPLAY_DBSPACE = "DISPLAY DBSPACE"
SERVERMON_ARGS_STANDARD = ["-standard"]
SERVERMON_ARGS_STANDARD_DBONLY = ["-standard", "-dbonly"]

# Activity-log query parameters used in test_query_activity_log_with_time_filters
ACTLOG_SEARCH_TERM = "ERROR"
ACTLOG_BEGIN_DATE = "2026-07-15"
ACTLOG_END_DATE = "2026-07-16"
ACTLOG_BEGIN_TIME = "08:00"
ACTLOG_END_TIME = "09:00"

# Admin / node names used in command-execution tests
ADMIN_NAME_OLD = "oldadmin"
ADMIN_NAME_TEST = "testadmin"
ADMIN_NAME_TARGET = "target_admin"
ADMIN_NAME_TARGET_NODE = "target_node"
NODE_NAME = "node1"
NODE_NAME_MY = "mynode"
DOMAIN_NAME = "STANDARD"
ADMIN_CONTACT = "ops@example.com"

# ---------------------------------------------------------------------------
# Typed CLI stubs
# ---------------------------------------------------------------------------
# Each stub satisfies the structural interface of the corresponding real wrapper
# so that type checkers accept them as constructor arguments for command classes.


class FakeAdmcCli:
    """Structural stub for DsmAdmcWrapper: execute(str) -> (str, str, int)."""

    def __init__(
        self,
        stdout: str = "OK",
        stderr: str = "",
        code: int = 0,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.calls: List[str] = []

    def execute(self, command: str) -> Tuple[str, str, int]:
        self.calls.append(command)
        return self.stdout, self.stderr, self.code

    def execute_silent(self, command: str) -> Tuple[str, str, int]:
        self.calls.append(command)
        return self.stdout, self.stderr, self.code


class FakeServermonCli:
    """Structural stub for ServermonWrapper: execute(List[str]) -> (str, str, int)."""

    def __init__(
        self,
        stdout: str = "OK",
        stderr: str = "",
        code: int = 0,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.calls: List[List[str]] = []

    def execute(self, args: List[str]) -> Tuple[str, str, int]:
        self.calls.append(args)
        return self.stdout, self.stderr, self.code


# ---------------------------------------------------------------------------
# ServerConfig factories
# ---------------------------------------------------------------------------


def make_server_config(
    *,
    server_address: Optional[str] = SP_TEST_SERVER_ADDRESS,
    server_port: str = SP_SERVER_PORT,
    admin_id: Optional[str] = ADMIN_ID,
    admin_password: Optional[str] = ADMIN_PASSWORD,
    dsmserv_path: Optional[str] = DSMSERV_PATH,
    servermon_path: Optional[str] = SERVERMON_PATH,
    servermon_xml_dir: Optional[str] = SERVERMON_XML_DIR,
    instance_user: Optional[str] = SP_INSTANCE_USER,
    server_instance_dir: Optional[str] = None,
):
    """Return a ServerConfig suitable for wrapper-level unit tests."""
    from sp_mcp_server.config import ServerConfig

    return ServerConfig(
        server_address=server_address,
        server_port=server_port,
        admin_id=admin_id,
        admin_password=admin_password,
        dsmserv_path=dsmserv_path,
        servermon_path=servermon_path,
        servermon_xml_dir=servermon_xml_dir,
        instance_user=instance_user,
        server_instance_dir=server_instance_dir,
    )


def make_config_with_cred(
    admin_id: str = SVC_ADMIN_ID,
    password: str = SVC_ADMIN_PASSWORD,
):
    """Return a minimal ServerConfig with a single system ModuleCredential."""
    from sp_mcp_server.config import ServerConfig, ModuleCredential

    cred = ModuleCredential(
        admin_id=admin_id,
        admin_password=password,
        privilege="system",
    )
    return ServerConfig(
        server_address=SP_SERVER_ADDRESS,
        server_port=SP_SERVER_PORT,
        credentials={"system": cred},
    )


def make_system_cred_config(
    server_address: str = TARGET_SERVER_01,
    admin_id: str = SVC_ADMIN_ID,
    password: str = SVC_ADMIN_PASSWORD,
):
    """Return a ServerConfig with explicit server_address for target-server binding tests."""
    from sp_mcp_server.config import ServerConfig, ModuleCredential

    cred = ModuleCredential(
        admin_id=admin_id,
        admin_password=password,
        privilege="system",
    )
    return ServerConfig(
        server_address=server_address,
        server_port=SP_SERVER_PORT,
        credentials={"system": cred},
    )


# ---------------------------------------------------------------------------
# Shared MCP tool-invocation helpers
# ---------------------------------------------------------------------------
# These helpers are used by every security-controls test file that invokes
# MCP CallToolRequest handlers directly.  Placing them here avoids duplication
# across the split test files.


def mock_admc(stdout: str = "", stderr: str = "", code: int = 0):
    """Return a MagicMock DsmAdmcWrapper whose execute/execute_silent always
    return the given (stdout, stderr, code) tuple."""
    from unittest.mock import MagicMock

    m = MagicMock()
    m.execute.return_value = (stdout, stderr, code)
    m.execute_silent.return_value = (stdout, stderr, code)
    return m


def run_tool(handler, req):
    """Run a MCP CallToolRequest handler synchronously and return a narrowed
    CallToolResult.

    Resolves two type-narrowing issues in one place:

    1. ``handler(req)`` returns a coroutine — asyncio.run() accepts it but the
       static type of ``handler`` is a broad Callable, so the checker needs the
       explicit asyncio.run() wrapper captured in a typed helper.
    2. ``server_result.root`` is typed as the ServerResultType union; the
       isinstance assertion narrows it to CallToolResult so ``.content``
       is known to exist.
    """
    import asyncio
    from mcp.types import CallToolResult

    server_result = asyncio.run(handler(req))
    assert isinstance(server_result.root, CallToolResult), (
        f"Expected CallToolResult, got {type(server_result.root)}: {server_result.root}"
    )
    return server_result.root


def first_text(result) -> str:
    """Extract the text from the first content block of a CallToolResult.
    Narrows ContentBlock → TextContent so the type checker knows .text exists.
    """
    from mcp.types import TextContent

    assert result.content, "CallToolResult.content is empty"
    block = result.content[0]
    assert isinstance(block, TextContent), (
        f"Expected TextContent as first content block, got {type(block)}"
    )
    return block.text
