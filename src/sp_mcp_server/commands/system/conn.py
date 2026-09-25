import os
import logging
import keyring
from typing import Any, Dict, Optional
from ..base import BaseCommand

logger = logging.getLogger(__name__)

_SECRETS_KEYRING_SERVICE = "sp-mcp-cloud-connections"


def _resolve_secret(secret_ref: str) -> str:
    """
    INT-3: Resolve a secrets reference to its actual value.

    Resolution order:
      1. 'keyring:<username>' — look up in OS keyring under service
         'sp-mcp-cloud-connections'
      2. 'env:<VAR_NAME>'     — read the named environment variable
      3. Literal value        — accepted but logs a warning in production

    Returns the resolved secret value.
    Raises ValueError if the reference cannot be resolved.
    """
    if secret_ref.startswith("keyring:"):
        username = secret_ref[len("keyring:"):]
        value = keyring.get_password(_SECRETS_KEYRING_SERVICE, username)
        if value is None:
            raise ValueError(
                f"INT-3: Secret '{username}' not found in keyring service "
                f"'{_SECRETS_KEYRING_SERVICE}'. "
                f"Store it with: python3 -c \"import keyring; "
                f"keyring.set_password('{_SECRETS_KEYRING_SERVICE}', "
                f"'{username}', '<value>')\""
            )
        return value

    if secret_ref.startswith("env:"):
        var_name = secret_ref[len("env:"):]
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(
                f"INT-3: Environment variable '{var_name}' is not set."
            )
        return value

    # Literal fallback — accepted for backward compatibility but not recommended
    logger.warning(
        "INT-3: Secret reference '%s...' is not prefixed with 'keyring:' or 'env:'. "
        "Treating as a literal value. Prefer 'keyring:<key>' for production.",
        secret_ref[:20],
    )
    return secret_ref


class DefineConnection(BaseCommand):
    @property
    def name(self) -> str:
        return "define_connection"

    @property
    def required_privilege(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "Define a **Cloud Connection** to a cloud storage service (S3, Azure, Google).\n\n"
            "**Security note (INT-3)**: Use secrets references instead of raw credentials:\n"
            "- Keyring:  `keyring:<key-name>` — resolved from the OS credential store\n"
            "- Env var:  `env:MY_ENV_VAR`    — resolved from environment at call time\n"
            "- Literal:  raw value           — accepted but logs a warning\n\n"
            "**Input Parameters**:\n"
            "- connection_name (Required): Name of the connection.\n"
            "- cloud_type (Required): Cloud type (S3, AZURE, GOOGLE, etc.).\n"
            "- bucket_name (Required): Target bucket or container name.\n"
            "- identity (Required): Access Key ID, username, or a secrets reference.\n"
            "- password (Required): Secret Access Key, password, or a secrets reference.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the connection was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Connection name."},
                "cloud_type":      {"type": "string", "description": "Cloud type (S3, AZURE, GOOGLE)."},
                "bucket_name":     {"type": "string", "description": "Bucket or container name."},
                "identity": {
                    "type": "string",
                    "description": (
                        "Access Key ID or secrets reference. "
                        "Use 'keyring:<key>' or 'env:VAR_NAME' for secure resolution."
                    ),
                },
                "password": {
                    "type": "string",
                    "description": (
                        "Secret Access Key or secrets reference. "
                        "Use 'keyring:<key>' or 'env:VAR_NAME' for secure resolution."
                    ),
                },
            },
            "required": ["connection_name", "cloud_type", "bucket_name", "identity", "password"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        # INT-3: resolve credentials — never log the resolved values
        try:
            identity = _resolve_secret(arguments["identity"])
            password = _resolve_secret(arguments["password"])
        except ValueError as e:
            return f"Error: {e}"

        cmd = (
            f"DEFINE CONNECTION {arguments['connection_name']} "
            f"CLOUDTYPE={arguments['cloud_type']} "
            f"BUCKETNAME={arguments['bucket_name']} "
            f"IDENTITY=\"{identity}\" "
            f"PASSWORD=\"{password}\""
        )
        # Do NOT log the assembled command — it contains resolved credentials.
        logger.info(
            "INT-3: Executing DEFINE CONNECTION %s CLOUDTYPE=%s BUCKETNAME=%s "
            "[credentials resolved from secrets store, not logged]",
            arguments["connection_name"],
            arguments["cloud_type"],
            arguments["bucket_name"],
        )
        stdout, stderr, code = self.cli.execute_silent(cmd)
        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout


class UpdateConnection(BaseCommand):
    @property
    def name(self) -> str:
        return "update_connection"

    @property
    def required_privilege(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "Updates a **Cloud Connection** configuration.\n\n"
            "**Security note (INT-3)**: Use a secrets reference for the password:\n"
            "- `keyring:<key-name>` or `env:MY_ENV_VAR`\n\n"
            "**Input Parameters**:\n"
            "- connection_name (Required): The name of the connection.\n"
            "- password (Optional): The new password or a secrets reference.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the connection was updated."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Connection name."},
                "password": {
                    "type": "string",
                    "description": "New password or secrets reference ('keyring:<key>' or 'env:VAR').",
                },
            },
            "required": ["connection_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE CONNECTION {arguments['connection_name']}"
        if arguments.get("password"):
            try:
                password = _resolve_secret(arguments["password"])
            except ValueError as e:
                return f"Error: {e}"
            cmd += f" PASSWORD=\"{password}\""
            logger.info(
                "INT-3: Executing UPDATE CONNECTION %s [password resolved from secrets store]",
                arguments["connection_name"],
            )
            stdout, stderr, code = self.cli.execute_silent(cmd)
        else:
            stdout, stderr, code = self.cli.execute(cmd)

        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout


class DeleteConnection(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_connection"

    @property
    def required_privilege(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "Deletes a **Cloud Connection** definition.\n\n"
            "**Input Parameters**:\n"
            "- connection_name (Required): The name of the connection to delete.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the connection was deleted."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Connection name."}
            },
            "required": ["connection_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(
            f"DELETE CONNECTION {arguments['connection_name']}"
        )
