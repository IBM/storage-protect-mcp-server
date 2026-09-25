from typing import Any, Dict
import logging
from ..base import BaseCommand

# Configure logger for admin operations
logger = logging.getLogger(__name__)

PROTECTED_SYSTEM_ADMINS = {"ADMIN"}

class DefineAdmin(BaseCommand):
    @property
    def name(self) -> str:
        return "define_admin"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Defines an **Administrator** account with specific privileges.\n\n"
            "**Input Parameters**:\n"
            "- admin_name (Required): The name of the administrator.\n"
            "- password (Required): The password for the administrator.\n"
            "- contact (Optional): Contact information.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the administrator was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "admin_name": {"type": "string"},
                "password": {"type": "string"},
                "contact": {"type": "string"}
            },
            "required": ["admin_name", "password"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        password = arguments.get("password", "")

        # POL-2: pre-validate password length against server's MINPWLENGTH policy
        pw_error = self._validate_password_policy(password)
        if pw_error:
            return f"Error defining administrator: {pw_error}"

        cmd = f"REGISTER ADMIN {arguments['admin_name']} {password}"
        if arguments.get("contact"):
            cmd += f" CONTACT=\"{arguments['contact']}\""
        # RG-3: password is embedded in the command string — use silent execution
        return self._execute_silent_query(cmd)

class UpdateUser(BaseCommand):
    @property
    def name(self) -> str:
        return "update_user"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates an **Administrator** account (System User). Modify password or contact info.\n\n"
            "**Input Parameters**:\n"
            "- user_name (Required): The name of the administrator to update.\n"
            "- password (Optional): The new password.\n"
            "- contact (Optional): New contact information.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the user was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "User name (Admin)."},
                "password": {"type": "string", "description": "New password."},
                "contact": {"type": "string", "description": "Contact info."}
            },
            "required": ["user_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        # POL-2: if a new password is supplied, validate it before sending
        if arguments.get("password"):
            pw_error = self._validate_password_policy(arguments["password"])
            if pw_error:
                return f"Error updating account: {pw_error}"

        cmd = f"UPDATE ADMIN {arguments['user_name']}"
        if arguments.get("password"): cmd += f" {arguments['password']}"
        if arguments.get("contact"): cmd += f" CONTACT=\"{arguments['contact']}\""
        # RG-3: password may be in the command string — use silent execution
        if arguments.get("password"):
            return self._execute_silent_query(cmd)
        return self._execute_simple_query(cmd)

class SetUserLock(BaseCommand):
    @property
    def name(self) -> str:
        return "set_user_lock"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Locks or unlocks an **Administrator** account. Locked admins cannot log in.\n\n"
            "**Input Parameters**:\n"
            "- user_name (Required): The name of the administrator.\n"
            "- lock_status (Required): 'lock' to disable access, 'unlock' to enable access.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the lock status was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "User name."},
                "lock_status": {"type": "string", "enum": ["lock", "unlock"], "description": "Action to perform."}
            },
            "required": ["user_name", "lock_status"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        user_name = arguments["user_name"].strip()
        lock_status = arguments["lock_status"]
        
        # Protect administrators with SYSTEM privileges from being locked
        if lock_status == "lock":
            query_result = self._execute_simple_query(f"QUERY ADMIN {user_name}")
            
            if "System" in query_result or "SYSTEM" in query_result:
                logger.warning(
                    f"SECURITY: Blocked attempt to lock administrator with SYSTEM privileges: {user_name}"
                )
                return (
                    f"Refusing to lock administrator account: {user_name}. "
                    f"This account has SYSTEM privileges which are critical for system administration. "
                    "Use direct server access if this operation is truly required."
                )
        
        action = "LOCK ADMIN" if lock_status == "lock" else "UNLOCK ADMIN"
        logger.info(f"Setting lock status for user: {user_name}, action: {action}")
        return self._execute_simple_query(f"{action} {user_name}")

class GrantAuthority(BaseCommand):
    @property
    def name(self) -> str:
        return "grant_authority"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Grants specific **Privilege Classes** to an administrator. Controls authorization level.\n\n"
            "**Input Parameters**:\n"
            "- user_name (Required): The name of the administrator.\n"
            "- classes (Required): Space-separated list of privilege classes (e.g., 'system policy storage').\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the authority was granted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "User name."},
                "classes": {"type": "string", "description": "Privilege classes (e.g. SYSTEM, POLICY, STORAGE)."}
            },
            "required": ["user_name", "classes"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        user_name = arguments["user_name"].strip()
        classes = arguments["classes"].strip()
        normalized_classes = {part.strip().upper() for part in classes.replace(",", " ").split() if part.strip()}
        
        # Log privilege grants, especially SYSTEM privileges
        if "SYSTEM" in normalized_classes:
            logger.warning(
                f"SECURITY: Granting SYSTEM authority to user: {user_name}. "
                f"Requested classes: {classes}"
            )
        else:
            logger.info(f"Granting authority to user: {user_name}, classes: {classes}")
        
        # Syntax: GRANT AUTHORITY admin_name CLASSES=class_name
        return self._execute_simple_query(f"GRANT AUTHORITY {user_name} CLASSES={classes}")

class RevokeAuthority(BaseCommand):
    @property
    def name(self) -> str:
        return "revoke_authority"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Revokes specific **Privilege Classes** from an administrator.\n\n"
            "**IMPORTANT**: Administrators with SYSTEM privileges cannot have those privileges revoked via this tool. "
            "This safeguard prevents accidental lockout of system administrators. "
            "The tool will query the administrator's current privileges before attempting revocation. "
            "Use direct server access with explicit manual procedures if such changes are truly required.\n\n"
            "**Input Parameters**:\n"
            "- user_name (Required): The name of the administrator.\n"
            "- classes (Required): Space-separated list of privilege classes to revoke.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the authority was revoked, or a protection message if the operation was blocked."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "User name."},
                "classes": {"type": "string", "description": "Privilege classes to revoke."}
            },
            "required": ["user_name", "classes"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        user_name = arguments["user_name"].strip()
        classes = arguments["classes"].strip()
        normalized_classes = {part.strip().upper() for part in classes.replace(",", " ").split() if part.strip()}

        # Check if trying to revoke SYSTEM privileges
        if "SYSTEM" in normalized_classes:
            # Query current privileges of the user
            query_result = self._execute_simple_query(f"QUERY ADMIN {user_name}")
            
            # Check if user currently has SYSTEM privileges
            if "System" in query_result or "SYSTEM" in query_result:
                logger.warning(
                    f"SECURITY: Blocked attempt to revoke SYSTEM authority from administrator with SYSTEM privileges: {user_name}. "
                    f"Requested classes: {classes}"
                )
                return (
                    f"Refusing to revoke SYSTEM authority from administrator account: {user_name}. "
                    f"This account currently has SYSTEM privileges which are critical for system administration. "
                    "Use direct server access and an explicit manual change process if this is truly required."
                )

        logger.info(f"Revoking authority from user: {user_name}, classes: {classes}")
        return self._execute_simple_query(f"REVOKE AUTHORITY {user_name} CLASSES={classes}")

class RegisterLicense(BaseCommand):
    @property
    def name(self) -> str:
        return "register_license"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Registers a new **Software License** key from a specified file.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- file_path (Required): The full path to the license file on the server.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the license was registered."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the license file."}
            },
            "required": ["file_path"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"REGISTER LICENSE FILE={arguments['file_path']}")

class DeleteAdmin(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_admin"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes an **Administrator** account.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- admin_name (Required): The name of the administrator to delete.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the administrator was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "admin_name": {"type": "string", "description": "Admin name."}
            },
            "required": ["admin_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        admin_name = arguments["admin_name"].strip()
        
        # Protect administrators with SYSTEM privileges from deletion
        query_result = self._execute_simple_query(f"QUERY ADMIN {admin_name}")
        
        if "System" in query_result or "SYSTEM" in query_result:
            logger.warning(
                f"SECURITY: Blocked attempt to delete administrator with SYSTEM privileges: {admin_name}"
            )
            return (
                f"Refusing to delete administrator account: {admin_name}. "
                f"This account has SYSTEM privileges which are critical for system administration. "
                "Use direct server access if this operation is truly required."
            )
        
        logger.info(f"Deleting administrator account: {admin_name}")
        return self._execute_simple_query(f"REMOVE ADMIN {admin_name}")

class QueryAdminUser(BaseCommand):
    @property
    def name(self) -> str:
        return "query_admin_user"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Display information about server administrators/users.\n\n"
            "**Input Parameters**:\n"
            "- admin_name (Optional): Administrator name.\n\n"
            "**Output Parameters**:\n"
            "- Administrator Name: User ID.\n"
            "- Last Access: When they last logged in.\n"
            "- Days Since Password Set: Password age.\n"
            "- Locked: Account status."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "admin_name": {"type": "string", "description": "Administrator name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY ADMIN"
        if arguments.get("admin_name"):
            cmd += f" {arguments['admin_name']}"
        return self._execute_simple_query(cmd)

class QueryLicenseInfo(BaseCommand):
    @property
    def name(self) -> str:
        return "query_license_info"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Display software license compliance information.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- License Name: Name of the licensed feature.\n"
            "- Compliance Status: Whether the server is compliant.\n"
            "- Licensed Units: Number of units authorized."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY LICENSE")
