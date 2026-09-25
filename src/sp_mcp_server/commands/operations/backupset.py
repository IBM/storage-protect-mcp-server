from typing import Any, Dict
from ..base import BaseCommand

class DefineBackupSet(BaseCommand):
    @property
    def name(self) -> str:
        return "define_backup_set"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Define a **Backup Set** from existing backup versions on the server. Backup sets are portable collections of node data.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): The node name.\n"
            "- backup_set_name (Required): The name of the new backup set.\n"
            "- file_space_name (Optional): Specific file space to include.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the backup set was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "backup_set_name": {"type": "string", "description": "Backup set name."},
                "file_space_name": {"type": "string", "description": "File space name (optional)."}
            },
            "required": ["node_name", "backup_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE BACKUPSET {arguments['node_name']} {arguments['backup_set_name']}"
        if arguments.get("file_space_name"): cmd += f" {arguments['file_space_name']}"
        return self._execute_simple_query(cmd)

class UpdateBackupSet(BaseCommand):
    @property
    def name(self) -> str:
        return "update_backup_set"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Updates the retention rule for a **Backup Set**.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): The client node name.\n"
            "- backup_set_name (Required): The backup set name.\n"
            "- retention (Required): New retention period in days or NOLIMIT.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the backup set was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "backup_set_name": {"type": "string", "description": "Backup set name."},
                "retention": {"type": "string", "description": "Retention period (days or NOLIMIT)."}
            },
            "required": ["node_name", "backup_set_name", "retention"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"UPDATE BACKUPSET {arguments['node_name']} {arguments['backup_set_name']} RETENTION={arguments['retention']}")

class DeleteBackupSet(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_backup_set"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Backup Set**.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): The client node name.\n"
            "- backup_set_name (Required): The backup set name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the backup set was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "backup_set_name": {"type": "string", "description": "Backup set name."}
            },
            "required": ["node_name", "backup_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE BACKUPSET {arguments['node_name']} {arguments['backup_set_name']}")
