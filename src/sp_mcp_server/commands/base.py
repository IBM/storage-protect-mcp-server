from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..cli_wrapper import DsmAdmcWrapper

# ── Privilege hierarchy (narrowest → broadest) ────────────────────────────────
# 'any'      — any registered administrator (no specific privilege class needed)
# 'operator' — requires SP Operator privilege class
# 'storage'  — requires SP Storage privilege class
# 'policy'   — requires SP Policy privilege class
# 'system'   — requires SP System privilege class (highest)
PRIVILEGE_TIERS = ("any", "operator", "storage", "policy", "system")


class BaseCommand(ABC):
    """Abstract base class for all dsmadmc commands exposed as MCP tools."""

    def __init__(self, cli: DsmAdmcWrapper):
        self.cli = cli

    @property
    @abstractmethod
    def name(self) -> str:
        """The tool name exposed to the MCP client."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """The tool description exposed to the MCP client."""
        pass

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]:
        """JSON schema describing the tool arguments."""
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str:
        """Execute the command with the given arguments."""
        pass

    # ── ACC-1: privilege annotation ───────────────────────────────────────────
    @property
    def required_privilege(self) -> str:
        """
        Minimum SP privilege class required to execute this tool.
        Values (narrowest → broadest): 'any' | 'operator' | 'storage' | 'policy' | 'system'
        Default 'any' means any registered administrator can run it.
        Override in concrete command subclasses to restrict access.
        """
        return "any"

    @property
    def tool_type(self) -> str:
        """Infers read-only vs destructive from name. Legacy — prefer required_privilege."""
        if self.name.lower().startswith("query") or "info" in self.name.lower():
            return "read-only"
        return "destructive"

    def _parse_comma_delimited(self, stdout: str) -> List[Dict[str, str]]:
        """Helper to parse dsmadmc -comma output."""
        lines = stdout.strip().splitlines()
        results = []
        if not lines:
            return results
        for line in lines:
            if not line.strip():
                continue
        return []

    def _format_command_error(self, prefix: str, stdout: str, stderr: str) -> str:
        """Return comprehensive error text from both stdout and stderr."""
        stdout_text = (stdout or "").strip()
        stderr_text = (stderr or "").strip()
        error_parts = []
        if stdout_text:
            error_parts.append(f"Output: {stdout_text}")
        if stderr_text:
            error_parts.append(f"Error: {stderr_text}")
        error_text = "\n".join(error_parts) if error_parts else "Unknown error occurred"
        return f"{prefix}\n{error_text}"

    def _execute_simple_query(self, query_cmd: str) -> str:
        """Common pattern: run a simple query and return stdout or error."""
        stdout, stderr, code = self.cli.execute(query_cmd)
        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout

    def _execute_silent_query(self, query_cmd: str) -> str:
        """
        RG-3: Execute a command without logging the command string.
        Use for commands whose string contains a plaintext password
        (e.g. REGISTER ADMIN, REGISTER NODE, UPDATE ADMIN <pwd>).
        The command is forwarded to execute_silent() which suppresses
        all log output of the command string itself.
        """
        stdout, stderr, code = self.cli.execute_silent(query_cmd)
        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout

    # ── POL-2: password policy helpers ───────────────────────────────────────

    def _get_pw_min_length(self) -> int:
        """
        Query the SP server for the minimum password length (MINPWLENGTH option).
        Returns the configured value, or 15 as the safe default (IBM SP v8.1.16+).
        """
        stdout, _, code = self.cli.execute("QUERY OPTION MINPWLENGTH")
        if code != 0:
            return 15
        for line in stdout.splitlines():
            if "MINPWLENGTH" in line.upper():
                parts = line.strip().split(",")
                # -DATAONLY=YES comma output: option_name,current_value
                if len(parts) >= 2:
                    try:
                        return int(parts[-1].strip())
                    except ValueError:
                        pass
        return 15

    def _validate_password_policy(self, password: str) -> Optional[str]:
        """
        POL-2: Validate *password* against the server's active MINPWLENGTH policy.
        Returns an error message string if the password is invalid, or None if acceptable.
        """
        if not password:
            return "Password must not be empty."
        min_len = self._get_pw_min_length()
        if len(password) < min_len:
            return (
                f"Password is too short ({len(password)} characters). "
                f"Server policy requires at least {min_len} characters "
                f"(MINPWLENGTH={min_len}). "
                "Provide a longer password before retrying."
            )
        return None


from ..cli_wrapper import DsmServWrapper


class BaseOfflineCommand(ABC):
    """Abstract base class for offline dsmserv utility commands."""

    def __init__(self, cli: DsmServWrapper):
        self.cli = cli

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str:
        pass

    # ── ACC-1: offline commands require system privilege by default ───────────
    @property
    def required_privilege(self) -> str:
        """Offline dsmserv commands require System privilege."""
        return "system"

    def _execute_utility(self, command: str) -> str:
        """Execute and return output."""
        stdout, stderr, code = self.cli.execute(command)
        if code != 0:
            return self._format_command_error("Error executing utility:", stdout, stderr)
        return stdout

    def _format_command_error(self, prefix: str, stdout: str, stderr: str) -> str:
        stdout_text = (stdout or "").strip()
        stderr_text = (stderr or "").strip()
        error_parts = []
        if stdout_text:
            error_parts.append(f"Output: {stdout_text}")
        if stderr_text:
            error_parts.append(f"Error: {stderr_text}")
        error_text = "\n".join(error_parts) if error_parts else "Unknown error occurred"
        return f"{prefix}\n{error_text}"


from ..cli_wrapper import ServermonWrapper


class BaseServermonCommand(ABC):
    """Abstract base class for servermon commands."""

    def __init__(self, cli: ServermonWrapper):
        self.cli = cli

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def args_schema(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str:
        pass

    # ── ACC-1: servermon commands require at least operator privilege ─────────
    @property
    def required_privilege(self) -> str:
        """Servermon diagnostic commands require at least Operator privilege."""
        return "operator"

    def _execute_servermon(self, args: List[str]) -> str:
        stdout, stderr, code = self.cli.execute(args)
        if code != 0:
            return self._format_command_error("Error running servermon:", stdout, stderr)
        return stdout

    def _format_command_error(self, prefix: str, stdout: str, stderr: str) -> str:
        stdout_text = (stdout or "").strip()
        stderr_text = (stderr or "").strip()
        error_parts = []
        if stdout_text:
            error_parts.append(f"Output: {stdout_text}")
        if stderr_text:
            error_parts.append(f"Error: {stderr_text}")
        error_text = "\n".join(error_parts) if error_parts else "Unknown error occurred"
        return f"{prefix}\n{error_text}"
