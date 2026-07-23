from typing import Any, Dict
from ..base import BaseCommand

class DefineLibrary(BaseCommand):
    @property
    def name(self) -> str:
        return "define_library"

    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Tape Library** configuration physically or logically connected to the server.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): Unique name for the library.\n"
            "- lib_type (Required): The interface type (e.g., 'SCSI', 'VTL', 'SHARED').\n"
            "- shared (Optional): 'YES' if the library is shared via SAN, 'NO' otherwise.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the library was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "lib_type": {
                    "type": "string",
                    "description": "Type of library (e.g. SCSI, SHARED, VTL)."
                },
                "shared": {"type": "string", "enum": ["YES", "NO"], "description": "Shared library status."}
            },
            "required": ["library_name", "lib_type"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE LIBRARY {arguments['library_name']} LIBTYPE={arguments['lib_type']}"
        if arguments.get("shared"):
            cmd += f" SHARED={arguments['shared']}"
        return self._execute_simple_query(cmd)

class UpdateLibrary(BaseCommand):
    @property
    def name(self) -> str:
        return "update_library"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates a **Library** definition.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): The name of the library.\n"
            "- shared (Optional): 'YES' or 'NO' to indicate if shared (MANUAL/SCSI/VTL/ACSLS/FILE).\n"
            "- resetdrives (Optional): Whether server preempts drive reservation via persistent reserve on restart (MANUAL/SCSI/VTL/ACSLS).\n"
            "- autolabel (Optional): Whether server automatically labels tape volumes (MANUAL/SCSI/VTL/ACSLS/EXTERNAL).\n"
            "- libtype (Optional): Convert library type between SCSI and VTL (SCSI/VTL only).\n"
            "- serial (Optional): Serial number or AUTODETECT (SCSI/VTL only).\n"
            "- relabelscratch (Optional): Whether server relabels volumes deleted and returned to scratch (SCSI/VTL only).\n"
            "- primarylibmanager (Optional): Name of the primary library manager server (SHARED type only).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the library was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "shared": {"type": "string", "enum": ["YES", "NO"], "description": "Shared status."},
                "resetdrives": {"type": "string", "enum": ["YES", "NO"], "description": "Whether server preempts drive reservation via persistent reserve on restart (MANUAL/SCSI/VTL/ACSLS)."},
                "autolabel": {"type": "string", "enum": ["NO", "YES", "OVERWRITE"], "description": "Whether server automatically labels tape volumes (MANUAL/SCSI/VTL/ACSLS/EXTERNAL)."},
                "libtype": {"type": "string", "enum": ["SCSI", "VTL"], "description": "Convert library type between SCSI and VTL (SCSI/VTL only)."},
                "serial": {"type": "string", "description": "Serial number or AUTODETECT (SCSI/VTL only)."},
                "relabelscratch": {"type": "string", "enum": ["YES", "NO"], "description": "Whether server relabels volumes deleted and returned to scratch (SCSI/VTL only)."},
                "primarylibmanager": {"type": "string", "description": "Name of the primary library manager server (SHARED type only)."}
            },
            "required": ["library_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE LIBRARY {arguments['library_name']}"
        if arguments.get("shared"): cmd += f" SHARED={arguments['shared']}"
        if arguments.get("resetdrives"): cmd += f" RESETDRIVES={arguments['resetdrives']}"
        if arguments.get("autolabel"): cmd += f" AUTOLABEL={arguments['autolabel']}"
        if arguments.get("libtype"): cmd += f" LIBTYPE={arguments['libtype']}"
        if arguments.get("serial"): cmd += f" SERIAL={arguments['serial']}"
        if arguments.get("relabelscratch"): cmd += f" RELABELSCRATCH={arguments['relabelscratch']}"
        if arguments.get("primarylibmanager"): cmd += f" PRIMARYLIBMANAGER={arguments['primarylibmanager']}"
        return self._execute_simple_query(cmd)

class DeleteLibrary(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_library"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Library** definition.\n"
            "**Input Parameters**:\n"
            "- library_name (Required): The name of the library to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the library was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."}
            },
            "required": ["library_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE LIBRARY {arguments['library_name']}")

class QueryTapeLibrary(BaseCommand):
    @property
    def name(self) -> str:
        return "query_tape_library"

    @property
    def description(self) -> str:
        return (
            "- Description: Display information about tape libraries defined in the system.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- library_name (Optional): Name of the library.\n"
            "**Output Parameters**:\n"
            "- Library Name: Name of the library.\n"
            "- Library Type: Type of library (e.g., SCSI, SHARED).\n"
            "- Device: Device identifier."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Name of the library."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY LIBRARY"
        if arguments.get("library_name"):
            cmd += f" {arguments['library_name']}"
        return self._execute_simple_query(cmd)

class QueryLibraryVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "query_library_volume"

    @property
    def description(self) -> str:
        return (
            "Query specific volumes physically located within a tape library.\n\n"
            "**Input Parameters**:\n"
            "- library_name (Optional): Library name.\n"
            "- volume_name (Optional): Volume name.\n\n"
            "**Output Parameters**:\n"
            "- Library Name: Name of the library.\n"
            "- Volume Name: Name of the volume.\n"
            "- Status: Current status (e.g., Private, Scratch).\n"
            "- Owner: Owner of the volume (for private volumes)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library_name": {"type": "string", "description": "Library name."},
                "volume_name": {"type": "string", "description": "Volume name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY LIBVOLUME"
        if arguments.get("library_name"):
            cmd += f" {arguments['library_name']}"
        if arguments.get("volume_name"):
            cmd += f" {arguments['volume_name']}"
        return self._execute_simple_query(cmd)
