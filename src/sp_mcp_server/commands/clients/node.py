from typing import Any, Dict
from ..base import BaseCommand

class RegisterNode(BaseCommand):
    @property
    def name(self) -> str:
        return "register_node"
    @property
    def description(self) -> str:
        return (
            "Registers a new **Node** (also commonly called a Client) in SP for data protection. A Node represents a source system (like a server, laptop, or VM) that contains data to be backed up.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Required): The unique name of the node to register (also referred to as `node_name` in some APIs).\n"
            "- password (Required): The password used for node authentication.\n"
            "- domain_name (Required): The **Policy Domain** (SLA) to which the node will be assigned.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the node was registered."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Name of the client to register."},
                "password": {"type": "string", "description": "Client password."},
                "domain_name": {"type": "string", "description": "Policy domain name."},
            },
            "required": ["client_name", "password", "domain_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"REGISTER NODE {arguments['client_name']} {arguments['password']} DOMAIN={arguments['domain_name']}"
        return self._execute_simple_query(cmd)

class RenameClient(BaseCommand):
    @property
    def name(self) -> str:
        return "rename_client"
    @property
    def description(self) -> str:
        return (
            "Renames an existing **Node** (Client). This updates the unique identifier used for all backup and restore operations for the source system.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- current_name (Required): The current name of the node.\n"
            "- new_name (Required): The new name for the node.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the node was renamed."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_name": {"type": "string", "description": "Current client name."},
                "new_name": {"type": "string", "description": "New client name."}
            },
            "required": ["current_name", "new_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"RENAME NODE {arguments['current_name']} {arguments['new_name']}")

class SetClientLock(BaseCommand):
    @property
    def name(self) -> str:
        return "set_client_lock"
    @property
    def description(self) -> str:
        return (
            "Locks or unlocks a **Node** to control access to the backup server. A locked node cannot perform backups or restores.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Required): The name of the node.\n"
            "- lock_status (Required): Set to 'lock' to disable access, or 'unlock' to enable access.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the lock status was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name."},
                "lock_status": {"type": "string", "enum": ["lock", "unlock"], "description": "Action to perform."}
            },
            "required": ["client_name", "lock_status"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        action = "LOCK NODE" if arguments["lock_status"] == "lock" else "UNLOCK NODE"
        return self._execute_simple_query(f"{action} {arguments['client_name']}")

class UpdateNode(BaseCommand):
    @property
    def name(self) -> str:
        return "update_node"
    @property
    def description(self) -> str:
        return (
            "Updates properties of an existing **Node** (Client).\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): Name of the node to update.\n"
            "- domain_name (Optional): Assign to a different **Policy Domain**.\n"
            "- password (Optional): Update the node password.\n"
            "- contact (Optional): Update contact information.\n"
            "- cloptset (Optional): Assign a different **Client Configuration Profile** (Option Set).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the node was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."},
                "domain_name": {"type": "string", "description": "New domain."},
                "password": {"type": "string", "description": "New password."},
                "contact": {"type": "string", "description": "Contact info."},
                "cloptset": {"type": "string", "description": "Option set."}
            },
            "required": ["node_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE NODE {arguments['node_name']}"
        if arguments.get("password"): cmd += f" {arguments['password']}"
        if arguments.get("domain_name"): cmd += f" DOMAIN={arguments['domain_name']}"
        if arguments.get("contact"): cmd += f" CONTACT=\"{arguments['contact']}\""
        if arguments.get("cloptset"): cmd += f" CLOPTSET={arguments['cloptset']}"
        return self._execute_simple_query(cmd)

class DeleteClient(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_client"
    @property
    def description(self) -> str:
        return (
            "Decommissions a **Node** and removes all its configuration from the server. This is a destructive operation.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Required): The name of the node to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the node was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name."}
            },
            "required": ["client_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"REMOVE NODE {arguments['client_name']}")

class DeleteNode(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_node"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Client** (Node). Similar to delete_client but using 'node' terminology.\n"
            "**Input Parameters**:\n"
            "- node_name (Required): The name of the node to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the node was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name."}
            },
            "required": ["node_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"REMOVE NODE {arguments['node_name']}")

class QueryClient(BaseCommand):
    @property
    def name(self) -> str:
        return "query_client"

    @property
    def description(self) -> str:
        return (
            "Display information about registered clients (Nodes).\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Name of the node to query.\n"
            "- domain_name (Optional): Filter by Policy Domain. (historically `policy_group` in code)\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The name of the node.\n"
            "- Platform: The node operating system.\n"
            "- Policy Domain: The Policy Domain the node belongs to.\n"
            "- Last Access: Days since last communication.\n"
            "- Locked: Whether the node is locked.\n"
            "- Password Set Date: Date password was last set."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "isp_server_name": {"type": "string", "description": "Target ISP Server name from registry (optional)."},

                "client_name": {"type": "string", "description": "Name of the node to query."},
                "domain_name": {"type": "string", "description": "Filter by Policy Domain. (historically `policy_group` in code)"}
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY NODE"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        if arguments.get("domain_name"):
            cmd += f" DOMAIN={arguments['domain_name']}"
        return self._execute_simple_query(cmd)

class QueryProxyClient(BaseCommand):
    @property
    def name(self) -> str:
        return "query_proxy_client"

    @property
    def description(self) -> str:
        return (
            "Query relationships where one node (agent) is authorized to act on behalf of another (target).\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- target_client (Optional): Target node name.\n"
            "- agent_client (Optional): Agent node name.\n\n"
            "**Output Parameters**:\n"
            "- Target Node: The node whose data is being accessed.\n"
            "- Agent Node: The node granted access."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                 "target_client": {"type": "string", "description": "Target client name (maps to target_node)."},
                 "agent_client": {"type": "string", "description": "Agent client name (maps to agent_node)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY PROXYNODE"
        if arguments.get("target_client"):
            cmd += f" TARGET={arguments['target_client']}"
        if arguments.get("agent_client"):
            cmd += f" AGENT={arguments['agent_client']}"
        return self._execute_simple_query(cmd)

class QueryReplicationClient(BaseCommand):
    @property
    def name(self) -> str:
        return "query_replication_client"

    @property
    def description(self) -> str:
        return (
            "Display replication status for client node file spaces.\n\n"
            "**Input Parameters**:\n"
            "- node_name (Required): Client node name(s). Comma-separated, no spaces. Use * for all nodes.\n"
            "- target_server_name (Optional): Target replication server to query. Default: all configured target servers.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The client node.\n"
            "- File Space: Replicated file space.\n"
            "- Target Server: Destination replication server.\n"
            "- Files Sent/Received: Replication counts."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string",
                    "description": "Client node name(s). Comma-separated, no spaces. Use * for all nodes."
                },
                "target_server_name": {
                    "type": "string",
                    "description": "Target replication server name (optional). If omitted, all configured target servers are listed."
                }
            },
            "required": ["node_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"QUERY REPLNODE {arguments['node_name']}"
        if arguments.get("target_server_name"):
            cmd += f" {arguments['target_server_name']}"
        return self._execute_simple_query(cmd)

class QueryPVUEstimate(BaseCommand):
    @property
    def name(self) -> str:
        return "query_pvu_estimate"

    @property
    def description(self) -> str:
        return (
            "Display an estimate of the Processor Value Units (PVU) for license calculation.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Node name.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The client.\n"
            "- PVU Estimate: Estimated PVU details."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY PVUESTIMATE"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        return self._execute_simple_query(cmd)
