from typing import Any, Dict
from ..base import BaseCommand

class ProtectCatalog(BaseCommand):
    @property
    def name(self) -> str:
        return "protect_catalog"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Initiates a backup of the system metadata catalog (Database). The catalog is critical for recovering the system.\n"
            "**Input Parameters**:\n"
            "- type (Required): The type of backup ('FULL', 'INCREMENTAL', 'DBS').\n"
            "- devclass (Optional): The device class to use for the backup.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the backup process has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["FULL", "INCREMENTAL", "DBS"], "default": "FULL", "description": "Backup type."},
                "devclass": {"type": "string", "description": "Device class to use."}
            },
            "required": ["type"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"BACKUP DB TYPE={arguments['type']}"
        if arguments.get("devclass"): cmd += f" DEVCLASS={arguments['devclass']}"
        return self._execute_simple_query(cmd)

class RestoreCatalog(BaseCommand):
    @property
    def name(self) -> str:
        return "restore_catalog"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "Restores the system metadata catalog (Database) from a backup. This is a critical recovery operation.\n"
            "**Input Parameters**:\n"
            "- date (Optional): The date to restore to (MM/DD/YYYY) for point-in-time recovery.\n"
            "- time (Optional): The time to restore to (HH:MM:SS).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the restore process has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to restore to (MM/DD/YYYY)."},
                "time": {"type": "string", "description": "Time to restore to (HH:MM:SS)."},
            },
            "required": []
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "RESTORE DB"
        if arguments.get("date"): cmd += f" TODATE={arguments['date']}"
        if arguments.get("time"): cmd += f" TOTIME={arguments['time']}"
        return self._execute_simple_query(cmd)
