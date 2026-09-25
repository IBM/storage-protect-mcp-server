from typing import Any, Dict
from ..base import BaseCommand

class DefineObjectDomain(BaseCommand):
    @property
    def name(self) -> str:
        return "define_object_domain"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Define a policy domain for object clients (e.g., S3 clients).\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The name of the new domain.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the domain was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."}
            },
            "required": ["domain_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE OBJECTDOMAIN {arguments['domain_name']}")

class DefineVirtualFSMapping(BaseCommand):
    @property
    def name(self) -> str:
        return "define_virtual_fs_mapping"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Define a **Virtual File Space Mapping**. Maps a client file space to a target server.\n"
            "**Input Parameters**:\n"
            "- node_name (Required): The client node name.\n"
            "- fs_name (Required): The name of the virtual file space.\n"
            "- target_server (Required): The target server where data is stored.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the mapping was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "fs_name": {"type": "string", "description": "Filespace name."},
                "target_server": {"type": "string", "description": "Target server."}
            },
            "required": ["node_name", "fs_name", "target_server"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE VIRTUALFSMAPPING {arguments['node_name']} {arguments['fs_name']} SERVER={arguments['target_server']}")

class UpdateVirtualFSMapping(BaseCommand):
    @property
    def name(self) -> str:
        return "update_virtual_fs_mapping"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Updates a **Virtual File Space Mapping**.\n"
            "**Input Parameters**:\n"
            "- node_name (Required): The client node name.\n"
            "- fs_name (Required): The virtual filespace name.\n"
            "- target_server (Optional): The new target server for the mapping.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the mapping was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "fs_name": {"type": "string", "description": "FS name."},
                "target_server": {"type": "string", "description": "New target server."}
            },
            "required": ["node_name", "fs_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE VIRTUALFSMAPPING {arguments['node_name']} {arguments['fs_name']}"
        if arguments.get("target_server"): cmd += f" SERVER={arguments['target_server']}"
        return self._execute_simple_query(cmd)

class DeleteVirtualFSMapping(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_virtual_fs_mapping"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Virtual File Space Mapping**.\n"
            "**Input Parameters**:\n"
            "- node_name (Required): The client node name.\n"
            "- fs_name (Required): The virtual filespace name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the mapping was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "fs_name": {"type": "string", "description": "FS name."}
            },
            "required": ["node_name", "fs_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE VIRTUALFSMAPPING {arguments['node_name']} {arguments['fs_name']}")
