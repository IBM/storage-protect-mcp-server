from typing import Any, Dict
from ..base import BaseCommand

class DefineNodeGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "define_node_group"
    
    @property
    def description(self) -> str:
        return (
            "Defines a **Node Group** in SP. Groups allow you to manage multiple Nodes collectively.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- group_name (Required): Name of the new Client Group.\n"
            "- description (Optional): Description of the group.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the group was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Node group name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["group_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE NODEGROUP {arguments['group_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DefineNodeGroupMember(BaseCommand):
    @property
    def name(self) -> str:
        return "define_node_group_member"
    
    @property
    def description(self) -> str:
        return (
            "Adds a **Node** to a **Node Group**.\n"
            "**Input Parameters**:\n"
            "- group_name (Required): The name of the Node Group.\n"
            "- node_name (Required): The name of the Node to add to the group.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the Node was added to the group."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Node group name."},
                "node_name": {"type": "string", "description": "Node name."}
            },
            "required": ["group_name", "node_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(
            f"DEFINE NODEGROUPMEMBER {arguments['group_name']} {arguments['node_name']}"
        )

class UpdateNodeGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "update_node_group"
    @property
    def description(self) -> str:
        return (
            "Updates an existing **Node Group**.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- group_name (Required): The name of the node group to update.\n"
            "- description (Optional): The new description for the group.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the group was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Group name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["group_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE NODEGROUP {arguments['group_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class RemoveClientFromGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "remove_client_from_group"
    @property
    def description(self) -> str:
        return (
            "Removes a **Node** from a **Node Group**.\n"
            "**Input Parameters**:\n"
            "- group_name (Required): The name of the Node Group.\n"
            "- node_name (Required): The name of the Node to remove from the group.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the Node was removed from the group."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Group name."},
                "node_name": {"type": "string", "description": "Node name."}
            },
            "required": ["group_name", "node_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"REMOVE NODE {arguments['group_name']} {arguments['node_name']}")

class DeleteNodeGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_node_group"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Node Group**.\n"
            "**Input Parameters**:\n"
            "- group_name (Required): The name of the group to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the group was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Group name."}
            },
            "required": ["group_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE NODEGROUP {arguments['group_name']}")

class QueryClientGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "query_client_group"

    @property
    def description(self) -> str:
        return (
            "Query definitions of node groups.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- group_name (Optional): Name of the node group.\n\n"
            "**Output Parameters**:\n"
            "- Group Name: Name of the node group.\n"
            "- Description: Description of the group."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Name of the client group."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY NODEGROUP"
        if arguments.get("group_name"):
            cmd += f" {arguments['group_name']}"
        return self._execute_simple_query(cmd)
