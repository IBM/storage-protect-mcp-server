import subprocess
import shutil
import os
import glob
import contextvars
from typing import List, Tuple, Dict, Any, Optional
import logging

from .config import ServerConfig

logger = logging.getLogger(__name__)

current_execution_credentials: contextvars.ContextVar[Optional[Tuple[str, str]]] = contextvars.ContextVar(
    "current_execution_credentials", default=None
)


class DsmAdmcWrapper:
    """Wrapper around dsmadmc for online IBM SP administration commands."""

    # Default privilege tier used when the wrapper is not given a specific one.
    DEFAULT_PRIVILEGE = "system"

    def __init__(self, config: ServerConfig, privilege: str = DEFAULT_PRIVILEGE):
        self.config = config
        self._privilege = privilege
        self.executable = shutil.which("dsmadmc") or "dsmadmc"

    def execute(self, command: str) -> Tuple[str, str, int]:
        """
        Execute a dsmadmc command.

        CRED-1: Selects the narrowest available credential that satisfies
                self._privilege.
        CRED-2: Omits -PA= from the subprocess arguments when
                SP_MCP_USE_PASSWORD_STASH=1, so the password never appears
                in /proc/<pid>/cmdline.  The password is then supplied by
                the encrypted PASSWORDACCESS=GENERATE stash in dsm.sys.

        Returns (stdout, stderr, return_code).
        """
        delegated = current_execution_credentials.get()
        if delegated:
            return self.execute_silent(command, admin_id=delegated[0], password=delegated[1])

        if not self.config.validate():
            return "", "Configuration incomplete. Missing required credentials.", 1

        cred = self.config.credential_for(self._privilege)
        if cred is None:
            return (
                "",
                f"No credential available for privilege tier '{self._privilege}'. "
                "Configure SP_ADMIN_ID_SYSTEM (or another tier) in the environment.",
                1,
            )

        # ── CRED-2: password stash mode ───────────────────────────────────────
        use_stash = os.environ.get("SP_MCP_USE_PASSWORD_STASH", "0") == "1"

        args = [
            self.executable,
            "-NOConfirm",
            "-DATAONLY=YES",
            f"-ID={cred.admin_id}",
            "-COMMAdelimited",
        ]

        if not use_stash:
            # Legacy mode: pass password on the CLI.
            # WARNING: this exposes the password via /proc/<pid>/cmdline.
            # Set SP_MCP_USE_PASSWORD_STASH=1 once dsm.sys stash is populated.
            args.insert(4, f"-PA={cred.admin_password}")
            logger.debug(
                "CRED-2: Password passed via -PA= argument. "
                "Set SP_MCP_USE_PASSWORD_STASH=1 and configure "
                "PASSWORDACCESS=GENERATE in dsm.sys to eliminate this exposure."
            )

        cmd_parts = command.split()
        args.extend(cmd_parts)

        logger.info("Executing dsmadmc command: %s", command)
        logger.debug(
            "Full command args: %s [credentials hidden] %s",
            " ".join(a for a in args if not a.startswith("-PA=")),
            " ".join(cmd_parts),
        )

        try:
            try:
                process = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode() if e.stdout else ""
                stderr = e.stderr.decode() if e.stderr else ""
                logger.error("Command timed out after 30 seconds")
                return stdout, stderr or "Command execution timed out after 30 seconds", 124

            if process.returncode == 0:
                logger.info(
                    "Command executed successfully. Output length: %d chars",
                    len(process.stdout),
                )
                logger.debug("Command output: %s...", process.stdout[:500])
            else:
                logger.error(
                    "Command failed with return code %d", process.returncode
                )
                logger.error("Error output: %s", process.stderr)
                if process.stdout:
                    logger.debug("Stdout: %s", process.stdout)

            return process.stdout, process.stderr, process.returncode

        except FileNotFoundError:
            logger.error("dsmadmc executable not found in PATH")
            return "", "dsmadmc executable not found. Please ensure it is in your PATH.", 127
        except Exception as e:
            logger.exception("Unexpected error executing command: %s", e)
            return "", str(e), 1

    def execute_silent(
        self,
        command: str,
        admin_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Tuple[str, str, int]:
        """
        INT-3 / CRED-2: Execute a dsmadmc command without logging the command string.
        Use for commands that contain resolved secrets (e.g. DEFINE CONNECTION)
        or dynamic authentication verification queries.
        The command string and credentials are never written to any log handler.

        If explicit `admin_id` and `password` are provided (e.g. from dynamic authentication),
        they override configured service account credentials.

        Returns (stdout, stderr, return_code).
        """
        if not (admin_id and password):
            delegated = current_execution_credentials.get()
            if delegated:
                admin_id, password = delegated

        if admin_id and password:
            effective_id = admin_id
            effective_pwd = password
            use_stash = False
        else:
            if not self.config.validate():
                return "", "Configuration incomplete. Missing required credentials.", 1

            cred = self.config.credential_for(self._privilege)
            if cred is None:
                return (
                    "",
                    f"No credential available for privilege tier '{self._privilege}'.",
                    1,
                )
            effective_id = cred.admin_id
            effective_pwd = cred.admin_password
            use_stash = os.environ.get("SP_MCP_USE_PASSWORD_STASH", "0") == "1"

        args = [
            self.executable,
            "-NOConfirm",
            "-DATAONLY=YES",
            f"-ID={effective_id}",
            "-COMMAdelimited",
        ]
        if not use_stash:
            args.insert(4, f"-PA={effective_pwd}")

        args.extend(command.split())

        # Intentionally NO logging of the command string — it may contain credentials
        logger.info(
            "Executing silent dsmadmc command (content not logged for security)"
        )
        try:
            try:
                process = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode() if e.stdout else ""
                stderr = e.stderr.decode() if e.stderr else ""
                return stdout, stderr or "Command execution timed out after 30 seconds", 124

            return process.stdout, process.stderr, process.returncode

        except FileNotFoundError:
            return "", "dsmadmc executable not found in PATH.", 127
        except Exception as e:
            return "", str(e), 1


class DsmServWrapper:
    """Wrapper for the offline dsmserv server utility."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.executable = self.config.dsmserv_path or shutil.which("dsmserv") or "dsmserv"

    def execute(self, command: str) -> Tuple[str, str, int]:
        """
        Execute a dsmserv command as the SP instance user.

        ACC-4: Uses 'sudo -u <user> --' instead of 'su - <user> -c <cmd>'
               to avoid shell-escaping pitfalls and align with the sudoers
               allowlist model.

        Returns (stdout, stderr, return_code).
        """
        args = [self.executable]

        if self.config.server_instance_dir:
            args.extend(["-i", self.config.server_instance_dir])

        cmd_parts = command.split()
        args.extend(cmd_parts)

        try:
            if self.config.instance_user:
                # ACC-4: sudo -u <user> -- <binary> [args...]
                # Requires a sudoers entry such as:
                #   mcp-runner ALL=(tsmsvr01) NOPASSWD: /usr/bin/dsmserv
                sudo_args = ["sudo", "-u", self.config.instance_user, "--"] + args
                logger.info(
                    "Executing offline command as %s (sudo): %s",
                    self.config.instance_user,
                    " ".join(args),
                )
                run_args = sudo_args
            else:
                logger.warning(
                    "SP_INSTANCE_USER not configured. "
                    "Running dsmserv as current user may fail."
                )
                logger.info("Executing offline command: %s", " ".join(args))
                run_args = args

            try:
                process = subprocess.run(
                    run_args,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode() if e.stdout else ""
                stderr = e.stderr.decode() if e.stderr else ""
                logger.error("Offline command timed out after 30 seconds")
                return stdout, stderr or "Command execution timed out after 30 seconds", 124

            return process.stdout, process.stderr, process.returncode

        except FileNotFoundError:
            return (
                "",
                f"dsmserv executable not found at '{self.executable}'. "
                "Please configure SP_DSMSERV_PATH.",
                127,
            )
        except Exception as e:
            return "", str(e), 1


class ServermonWrapper:
    """Wrapper for the servermon diagnostic utility."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.executable = (
            self.config.servermon_path or shutil.which("servermon") or "servermon"
        )

    def _check_servermon_running(self) -> bool:
        """Return True when another servermon process is already running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "servermon"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                logger.info(
                    "Found %d servermon process(es) running: %s",
                    len(pids),
                    ", ".join(pids),
                )
                return True
            return False
        except Exception as e:
            logger.warning("Error checking for servermon processes: %s", e)
            return False

    def _get_latest_servermon_output(self) -> Optional[str]:
        """
        Return the most recent servermon XML output, or None if not found.
        Servermon creates timestamped subdirectories (e.g., .20260306T1159-SERVER1)
        with XML files inside a results/ subdirectory.
        """
        if not self.config.servermon_xml_dir or not os.path.isdir(
            self.config.servermon_xml_dir
        ):
            logger.info("Servermon XML directory not configured or doesn't exist")
            return None

        try:
            subdir_pattern = os.path.join(self.config.servermon_xml_dir, ".*-*")
            subdirs = [
                d for d in glob.glob(subdir_pattern) if os.path.isdir(d)
            ]
            if not subdirs:
                logger.info(
                    "No timestamped subdirectories found in %s",
                    self.config.servermon_xml_dir,
                )
                return None

            latest_subdir = max(subdirs, key=os.path.getmtime)
            logger.info("Found latest servermon subdirectory: %s", latest_subdir)

            results_dir = os.path.join(latest_subdir, "results")
            if not os.path.isdir(results_dir):
                logger.info("No results directory found in %s", latest_subdir)
                return None

            xml_files = glob.glob(os.path.join(results_dir, "*.xml"))
            if not xml_files:
                logger.info("No XML files found in %s", results_dir)
                return None

            latest_file = max(xml_files, key=os.path.getmtime)
            logger.info("Found latest servermon XML output: %s", latest_file)

            with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return f"Using existing servermon diagnostics from: {latest_file}\n\n{content}"

        except Exception as e:
            logger.warning("Error reading servermon output files: %s", e)
            return None

    def execute(self, args: List[str]) -> Tuple[str, str, int]:
        """
        Execute a servermon command as the SP instance user.

        ACC-4: Uses 'sudo -u <user> --' instead of 'su - <user> -c <cmd>'.
        If another servermon is running, attempts to return the latest cached output.

        Returns (stdout, stderr, return_code).
        """
        if self._check_servermon_running():
            logger.info(
                "Another servermon instance is running. "
                "Attempting to use existing diagnostics..."
            )
            existing_output = self._get_latest_servermon_output()
            if existing_output:
                logger.info("Successfully retrieved existing servermon diagnostics")
                return existing_output, "", 0
            logger.warning("No existing servermon output found")
            return (
                "",
                "Another servermon instance is currently running and no recent "
                "diagnostics are available. Please wait for the running instance "
                "to complete or check the servermon XML directory.",
                1,
            )

        full_cmd = [self.executable] + args

        try:
            if self.config.instance_user:
                # ACC-4: sudo -u <user> -- <binary> [args...]
                # Requires a sudoers entry such as:
                #   mcp-runner ALL=(tsmsvr01) NOPASSWD: /usr/bin/servermon
                sudo_args = ["sudo", "-u", self.config.instance_user, "--"] + full_cmd
                logger.info(
                    "Executing servermon command as %s (sudo): %s",
                    self.config.instance_user,
                    " ".join(full_cmd),
                )
                run_args = sudo_args
            else:
                logger.warning(
                    "SP_INSTANCE_USER not configured. "
                    "Running servermon as current user may fail."
                )
                logger.info("Executing servermon command: %s", " ".join(full_cmd))
                run_args = full_cmd

            try:
                process = subprocess.run(
                    run_args,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode() if e.stdout else ""
                stderr = e.stderr.decode() if e.stderr else ""
                logger.error("Servermon command timed out after 30 seconds")
                return stdout, stderr or "Command execution timed out after 30 seconds", 124

            return process.stdout, process.stderr, process.returncode

        except FileNotFoundError:
            return (
                "",
                f"servermon executable not found at '{self.executable}'. "
                "Please configure SP_SERVERMON_PATH.",
                127,
            )
        except Exception as e:
            return "", str(e), 1
