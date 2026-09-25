from typing import Any, Dict
from ..base import BaseCommand

class DefineDrive(BaseCommand):
    @property
    def name(self) -> str:
        return "define_drive"

    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Tape Drive** within a specific Tape Library.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): The name of the parent Library.\n"
            "- drive_name (Required): Unique name for the drive.\n"
            "- serial (Optional): Hardware serial number (use 'AUTODETECT' to auto-discover).\n"
            "- element (Optional): Element address in the library (use 'AUTODETECT' to auto-discover).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the drive was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "drive_name": {"type": "string", "description": "Drive name."},
                "serial": {"type": "string", "description": "Serial number."},
                "element": {"type": "string", "description": "Element address."}
            },
            "required": ["library_name", "drive_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE DRIVE {arguments['library_name']} {arguments['drive_name']}"
        if arguments.get("serial"):
            cmd += f" SERIAL={arguments['serial']}"
        if arguments.get("element"):
            cmd += f" ELEMENT={arguments['element']}"
        return self._execute_simple_query(cmd)

class UpdateDrive(BaseCommand):
    @property
    def name(self) -> str:
        return "update_drive"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates a **Drive** definition.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): The library name containing the drive.\n"
            "- drive_name (Required): The drive name.\n"
            "- online (Optional): 'YES' or 'NO' to bring online/offline.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the drive was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "drive_name": {"type": "string", "description": "Drive name."},
                "online": {"type": "string", "enum": ["YES", "NO"], "description": "Online status."},
                "element": {"type": "string", "description": "Element address."}
            },
            "required": ["library_name", "drive_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE DRIVE {arguments['library_name']} {arguments['drive_name']}"
        if arguments.get("online"): cmd += f" ONLINE={arguments['online']}"
        if arguments.get("element"): cmd += f" ELEMENT={arguments['element']}"
        return self._execute_simple_query(cmd)

class DeleteDrive(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_drive"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Drive** definition.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): The library containing the drive.\n"
            "- drive_name (Required): The name of the drive to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the drive was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "drive_name": {"type": "string", "description": "Drive name."}
            },
            "required": ["library_name", "drive_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE DRIVE {arguments['library_name']} {arguments['drive_name']}")

class QueryTapeDrive(BaseCommand):
    @property
    def name(self) -> str:
        return "query_tape_drive"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Display information about tape drives associated with a library.\n"
            "**Input Parameters**:\n"
            "- library_name (Optional): The library name.\n"
            "- drive_name (Optional): The drive name.\n"
            "**Output Parameters**:\n"
            "- Library Name: The library the drive belongs to.\n"
            "- Drive Name: Name of the drive.\n"
            "- Device Type: Type of drive device.\n"
            "- Online: Whether the drive is online and available."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "The library name."},
                "drive_name": {"type": "string", "description": "The drive name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DRIVE"
        if arguments.get("library_name"):
            cmd += f" {arguments['library_name']}"
        if arguments.get("drive_name"):
            cmd += f" {arguments['drive_name']}"
        return self._execute_simple_query(cmd)

class QueryTapeAlerts(BaseCommand):
    @property
    def name(self) -> str:
        return "query_tape_alerts"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Display settings and status for tape drive alerts."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY TAPEALERTMSG")
