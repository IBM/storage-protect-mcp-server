from typing import Any, Dict
from ..base import BaseCommand

class DefineDeviceClass(BaseCommand):
    @property
    def name(self) -> str:
        return "define_device_class"

    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Device Class** in SP. Specifies the hardware type and management policies for storage devices.\n"
            "**Input Parameters**:\n"
            "- device_class_name (Required): Name for the Device Class.\n"
            "- dev_type (Required): The underlying technology (e.g., 'LTO', 'DISK', 'FILE').\n"
            "- library (Optional): The library associated with this device type (required for tape).\n"
            "- mount_limit (Optional): Maximum concurrent drives/volumes that can be mounted.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the device class was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "device_class_name": {"type": "string", "description": "Device class name."},
                "dev_type": {"type": "string", "description": "Device type (e.g. LTO, FILE)."},
                "library": {"type": "string", "description": "Library name."},
                "mount_limit": {"type": "string", "description": "Mount limit."}
            },
            "required": ["device_class_name", "dev_type"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE DEVCLASS {arguments['device_class_name']} DEVTYPE={arguments['dev_type']}"
        if arguments.get("library"):
            cmd += f" LIBRARY={arguments['library']}"
        if arguments.get("mount_limit"):
            cmd += f" MOUNTLIMIT={arguments['mount_limit']}"
        return self._execute_simple_query(cmd)

class UpdateDeviceClass(BaseCommand):
    @property
    def name(self) -> str:
        return "update_device_class"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates a **Device Class** definition.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- devclass_name (Required): The device class name.\n"
            "- mount_limit (Optional): Max number of mounts allowed (DRIVES or number).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the device class was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "device_class_name": {"type": "string", "description": "Device class name."},
                "mount_limit": {"type": "string", "description": "Mount limit."}
            },
            "required": ["device_class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE DEVCLASS {arguments['device_class_name']}"
        if arguments.get("mount_limit"): cmd += f" MOUNTLIMIT={arguments['mount_limit']}"
        return self._execute_simple_query(cmd)

class DeleteDeviceClass(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_device_class"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Device Class** definition.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- devclass_name (Required): The name of the device class to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the device class was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "device_class_name": {"type": "string", "description": "Device class name."}
            },
            "required": ["device_class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE DEVCLASS {arguments['device_class_name']}")

class QueryDeviceType(BaseCommand):
    @property
    def name(self) -> str:
        return "query_device_type"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Display information about device types (Device Classes) used for storage.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- device_type_name (Optional): Name of the device class.\n"
            "**Output Parameters**:\n"
            "- Device Class Name: Name of the device class.\n"
            "- Device Access Strategy: Sequential or Random (Disk).\n"
            "- Storage Type: Underlying storage medium."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "device_type_name": {"type": "string", "description": "Name of the device class (device type)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DEVCLASS"
        if arguments.get("device_type_name"):
            cmd += f" {arguments['device_type_name']}"
        return self._execute_simple_query(cmd)

class QuerySanDevices(BaseCommand):
    @property
    def name(self) -> str:
        return "query_san_devices"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Query storage devices detected on the Storage Area Network (SAN).\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- None.\n"
            "**Output Parameters**:\n"
            "- Device Name: Name of the device.\n"
            "- Serial Number: Hardware serial number."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY SAN")
