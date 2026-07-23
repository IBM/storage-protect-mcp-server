from typing import Any, Dict
from ..base import BaseCommand

class DefinePath(BaseCommand):
    @property
    def name(self) -> str:
        return "define_path"
        
    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Data Path** allowing communication between a source and destination.\n"
            "**Input Parameters**:\n"
            "- source_name (Required): Name of the source (e.g., Server Name).\n"
            "- destination_name (Required): Name of the destination (e.g., Drive Name).\n"
            "- source_type (Required): Type of source system ('SERVER', 'DATAMOVER').\n"
            "- destination_type (Required): Type of destination hardware ('LIBRARY', 'DRIVE').\n"
            "- library_name (Optional): Name of the library (required if destination is a Drive).\n"
            "- device (Required): OS-level device path (e.g., /dev/rmt0).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the path was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "Source name."},
                "destination_name": {"type": "string", "description": "Destination name."},
                "source_type": {"type": "string", "description": "Source type.", "enum": ["SERVER", "DATAMOVER"]},
                "destination_type": {"type": "string", "description": "Destination type.", "enum": ["LIBRARY", "DRIVE"]},
                "library_name": {"type": "string", "description": "Library name (if destination is drive)."},
                "device": {"type": "string", "description": "Device path."}
            },
            "required": ["source_name", "destination_name", "source_type", "destination_type", "device"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = (f"DEFINE PATH {arguments['source_name']} {arguments['destination_name']} "
               f"SRCTYPE={arguments['source_type']} DESTTYPE={arguments['destination_type']} "
               f"DEVICE=\"{arguments['device']}\"")
        if arguments.get("library_name"):
            cmd += f" LIBRARY={arguments['library_name']}"
        return self._execute_simple_query(cmd)

class UpdatePath(BaseCommand):
    @property
    def name(self) -> str:
        return "update_path"
    @property
    def description(self) -> str:
        return (
            "- Description: Update the data path between a source (like a server or data mover) and a destination (drive, library) to allow data transfer.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- source_name (Required): Name of the source (e.g., server name).\n"
            "- destination_name (Required): Name of the destination (e.g., drive name).\n"
            "- source_type (Required): Type of source (e.g., SERVER, DATAMOVER).\n"
            "- destination_type (Required): Type of destination (e.g., DRIVE, LIBRARY).\n"
            "- library (Optional): Name of the library (required for drive paths).\n"
            "- online (Optional): 'Yes' or 'No' to set path availability.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the path was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "Source name."},
                "destination_name": {"type": "string", "description": "Destination name."},
                "source_type": {"type": "string", "description": "Source type."},
                "destination_type": {"type": "string", "description": "Destination type."},
                "online": {"type": "string", "enum": ["YES", "NO"], "description": "Online status."},
                "library": {"type": "string", "description": "Library (if drive)."}
            },
            "required": ["source_name", "destination_name", "source_type", "destination_type"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE PATH {arguments['source_name']} {arguments['destination_name']} SRCTYPE={arguments['source_type']} DESTTYPE={arguments['destination_type']}"
        if arguments.get("library"): cmd += f" LIBRARY={arguments['library']}"
        if arguments.get("online"): cmd += f" ONLINE={arguments['online']}"
        return self._execute_simple_query(cmd)

class DeletePath(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_path"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Path** definition.\n"
            "**Input Parameters**:\n"
            "- source_name (Required): Source name.\n"
            "- destination_name (Required): Destination name.\n"
            "- source_type (Required): Source type.\n"
            "- destination_type (Required): Destination type.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the path was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "Source name."},
                "destination_name": {"type": "string", "description": "Destination name."},
                "source_type": {"type": "string", "description": "Source type."},
                "destination_type": {"type": "string", "description": "Destination type."},
                "library": {"type": "string", "description": "Library name (for drives)."}
            },
            "required": ["source_name", "destination_name", "source_type", "destination_type"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DELETE PATH {arguments['source_name']} {arguments['destination_name']} SRCTYPE={arguments['source_type']} DESTTYPE={arguments['destination_type']}"
        if arguments.get("library"): cmd += f" LIBRARY={arguments['library']}"
        return self._execute_simple_query(cmd)

class QueryDataPath(BaseCommand):
    @property
    def name(self) -> str:
        return "query_data_path"

    @property
    def description(self) -> str:
        return (
            "- Description: Display information about data paths between source and destination.\n"
            "**Input Parameters**:\n"
            "- source_name (Optional): Name of the source component.\n"
            "- destination_name (Optional): Name of the destination component.\n"
            "**Output Parameters**:\n"
            "- Source Name: The source of the path (e.g., Server Name).\n"
            "- Source Type: Type of source (e.g., SERVER).\n"
            "- Destination Name: The destination (e.g., Drive or Library).\n"
            "- Destination Type: Type of destination.\n"
            "- Device: The device path."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "Name of the source component."},
                "destination_name": {"type": "string", "description": "Name of the destination component."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY PATH"
        if arguments.get("source_name"):
            cmd += f" {arguments['source_name']}"
        if arguments.get("destination_name"):
            cmd += f" {arguments['destination_name']}"
        return self._execute_simple_query(cmd)
